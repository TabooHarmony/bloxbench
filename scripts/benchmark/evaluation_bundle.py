"""Portable evaluation-bundle helpers for BloxBench.

The runner owns execution. This module only normalizes provenance and writes a
human-readable bundle around the execution evidence. It never scores a candidate.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENERATION_FILES = (
    "manifest.json",
    "pi-command.json",
    "prompt.txt",
    "system_prompt.txt",
    "pi.jsonl",
    "pi.stderr",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_place_file(path: Path, *, template_path: Path | None = None) -> dict[str, Any]:
    """Validate the shallow on-disk signature of a Roblox place artifact.

    This intentionally does not claim that the place is visually correct or that
    candidate scripts play successfully. It only prevents arbitrary bytes with a
    Roblox filename from entering a reviewable bundle.
    """
    if not path.is_file():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix not in {".rbxl", ".rbxlx"}:
        raise ValueError("place_file must be a .rbxl or .rbxlx file")
    size = path.stat().st_size
    if template_path is not None and template_path.is_file():
        if path.resolve() == template_path.resolve() or sha256_file(path) == sha256_file(template_path):
            raise ValueError(f"place file is the unchanged input template: {path}")
    if size < 32:
        raise ValueError(f"place file is too small to be a Roblox place: {path}")
    if suffix == ".rbxl":
        data = path.read_bytes()
        required = (b"<roblox!", b"SSTR", b"INST", b"PRNT")
        if not all(marker in data for marker in required):
            raise ValueError(f"place file does not have a valid Roblox binary header: {path}")
        return {"format": "rbxl-binary", "bytes": size}
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError(f"place file is not valid Roblox XML: {path}") from exc
    root_name = root.tag.rsplit("}", 1)[-1]
    item_count = sum(1 for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "Item")
    if root_name != "roblox" or item_count == 0:
        raise ValueError(f"place file is not a Roblox XML place: {path}")
    return {"format": "rbxlx-xml", "bytes": size, "items": item_count}


def _number(value: Any) -> int | float:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _add_usage(total: dict[str, int | float], usage: dict[str, Any]) -> None:
    mapping = {
        "input_tokens": ("input", "input_tokens"),
        "output_tokens": ("output", "output_tokens"),
        "cache_read_tokens": ("cacheRead", "cache_read_tokens"),
        "cache_write_tokens": ("cacheWrite", "cache_write_tokens"),
        "total_tokens": ("totalTokens", "total_tokens"),
    }
    for destination, sources in mapping.items():
        value = next((usage.get(source) for source in sources if source in usage), 0)
        total[destination] += _number(value)
    cost = usage.get("cost")
    if isinstance(cost, dict):
        for destination, sources in {
            "input": ("input", "input_tokens"),
            "output": ("output", "output_tokens"),
            "cache_read": ("cacheRead", "cache_read"),
            "cache_write": ("cacheWrite", "cache_write"),
            "total": ("total", "total_cost"),
        }.items():
            value = next((cost.get(source) for source in sources if source in cost), 0)
            total[f"cost_{destination}"] += _number(value)
    for destination in ("input", "output", "cache_read", "cache_write", "total"):
        total[f"cost_{destination}"] += _number(usage.get(f"cost_{destination}"))


def _generation_manifest(path: Path) -> tuple[Path | None, dict[str, Any]]:
    candidates = [path.as_posix()]
    if not path.is_file():
        candidates.append((path / "manifest.json").as_posix())
        # Repaired candidates keep the generation manifest one level deeper:
        # <arm_dir>/generation/manifest.json. Accepting the arm root (or the
        # nested dir) here removes a CLI footgun where a valid model run was
        # mislabeled "candidate origin is unattributed".
        candidates.append((path / "generation" / "manifest.json").as_posix())
    for candidate in candidates:
        manifest_path = Path(candidate)
        if manifest_path.is_file():
            try:
                value = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return manifest_path, {}
            return manifest_path, value if isinstance(value, dict) else {}
    return None, {}


def _repair_manifest_path(generation_manifest_path: Path) -> Path:
    if generation_manifest_path.parent.name == "generation":
        return generation_manifest_path.parent.parent / "repair" / "manifest.json"
    return generation_manifest_path.parent / "repair" / "manifest.json"


def _repair_summary(generation_manifest_path: Path) -> dict[str, Any]:
    repair_path = _repair_manifest_path(generation_manifest_path)
    summary: dict[str, Any] = {"is_repaired": repair_path.is_file()}
    if not repair_path.is_file():
        return summary
    summary["manifest_path"] = str(repair_path)
    summary["manifest_sha256"] = sha256_file(repair_path)
    try:
        value = json.loads(repair_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        summary["metadata_readable"] = False
        return summary
    if not isinstance(value, dict):
        summary["metadata_readable"] = False
        return summary
    summary["metadata_readable"] = True
    for key in (
        "repaired_at",
        "model",
        "fixture",
        "attempt",
        "parent_arm_id",
        "original_source_sha256",
        "parent_source_sha256",
        "error_sha256",
        "knowledge_profile",
        "knowledge_sha256",
        "suite",
        "prompt_sha256",
        "system_prompt_sha256",
    ):
        if value.get(key) is not None:
            summary[key] = value[key]
    if "error_sha256" not in summary and isinstance(value.get("error_text"), str):
        summary["error_sha256"] = hashlib.sha256(value["error_text"].encode("utf-8")).hexdigest()
    return summary


def summarize_generation(generation_path: str | Path | None) -> dict[str, Any]:
    """Read generation metadata without copying credentials or raw environment data."""
    if generation_path is None:
        return {
            "origin": "unattributed",
            "is_model_evaluation": False,
            "note": "No generation manifest was supplied. This run is not a model evaluation.",
        }
    path = Path(generation_path).resolve()
    manifest_path, manifest = _generation_manifest(path)
    if manifest_path is None:
        return {
            "origin": "unattributed",
            "is_model_evaluation": False,
            "path": str(path),
            "note": "Generation path has no manifest.json. This run is not a model evaluation.",
        }

    pi_data = manifest.get("pi")
    pi: dict[str, Any] = pi_data if isinstance(pi_data, dict) else {}
    usage: dict[str, int | float] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "total_tokens": 0,
        "cost_input": 0,
        "cost_output": 0,
        "cost_cache_read": 0,
        "cost_cache_write": 0,
        "cost_total": 0,
    }
    assistant_messages = 0
    turn_starts = 0
    event_assistant_messages = 0
    event_counts: dict[str, int] = {}
    first_timestamp: int | float | None = None
    last_timestamp: int | float | None = None
    pi_path = manifest_path.parent / "pi.jsonl"
    if pi_path.is_file():
        with pi_path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                event_type = str(event.get("type", "unknown"))
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
                if event_type == "turn_start":
                    turn_starts += 1
                message = event.get("message")
                if event_type != "message_end" or not isinstance(message, dict):
                    continue
                if message.get("role") != "assistant":
                    continue
                assistant_messages += 1
                event_assistant_messages += 1
                raw_usage = message.get("usage")
                if isinstance(raw_usage, dict):
                    _add_usage(usage, raw_usage)
                timestamp = message.get("timestamp")
                if isinstance(timestamp, (int, float)):
                    first_timestamp = timestamp if first_timestamp is None else min(first_timestamp, timestamp)
                    last_timestamp = timestamp if last_timestamp is None else max(last_timestamp, timestamp)

    # Some direct generation runs store usage in the generation manifest rather
    # than a pi event log. Preserve that data instead of reporting zero usage.
    if assistant_messages == 0:
        fallback_usage = pi.get("usage") if isinstance(pi.get("usage"), dict) else manifest.get("usage")
        if isinstance(fallback_usage, dict):
            _add_usage(usage, fallback_usage)
            assistant_messages = int(
                _number(pi.get("assistant_messages")) or _number(manifest.get("assistant_messages"))
            ) or 1
    fallback_rounds = pi.get("rounds") or manifest.get("rounds")
    rounds = turn_starts or assistant_messages or int(_number(fallback_rounds))
    elapsed_seconds: float | None = None
    if first_timestamp is not None and last_timestamp is not None and last_timestamp >= first_timestamp:
        elapsed_seconds = round((last_timestamp - first_timestamp) / 1000.0, 3)
    if elapsed_seconds is None and isinstance(pi.get("elapsed_seconds"), (int, float)):
        elapsed_seconds = float(pi["elapsed_seconds"])

    allowed = {
        "provider": manifest.get("provider"),
        "provider_id": manifest.get("provider_id"),
        "base_url": manifest.get("base_url"),
        "model": manifest.get("model"),
        "model_name": manifest.get("model_name"),
        "treatment": manifest.get("treatment"),
        "knowledge_profile": manifest.get("knowledge_profile"),
        "knowledge_sha256": manifest.get("knowledge_sha256"),
        "task_provenance": manifest.get("task_provenance"),
        "suite": manifest.get("suite"),
        "generator": manifest.get("generator"),
        "tool_surface": manifest.get("tool_surface"),
        "decoding": manifest.get("decoding"),
        "prompt_order": manifest.get("prompt_order"),
        "repair_policy": manifest.get("repair_policy"),
        "pi_version": manifest.get("pi_version"),
        "thinking": manifest.get("thinking"),
        "max_output_tokens": manifest.get("max_output_tokens"),
        "prompt_sha256": manifest.get("prompt_sha256")
        or manifest.get("calibration_prompt_sha256"),
        "fixture_prompt_sha256": manifest.get("fixture_prompt_sha256"),
        "system_prompt_sha256": manifest.get("system_prompt_sha256"),
        "fixture_sha256": manifest.get("fixture_sha256"),
        "prompt_path": manifest.get("prompt_path") or manifest.get("calibration_prompt"),
        "prompt_mode": manifest.get("prompt_mode") or manifest.get("calibration_prompt_mode"),
        "task_id": manifest.get("task_id") or manifest.get("fixture_id"),
        "source_sha256": manifest.get("source_sha256"),
        "source_bytes": manifest.get("source_bytes"),
        "started_at": manifest.get("started_at"),
        "completed_at": manifest.get("completed_at"),
    }
    metadata = {key: value for key, value in allowed.items() if value is not None}
    metadata.update(
        {
            "origin": "model",
            "is_model_evaluation": True,
            "manifest_path": str(manifest_path),
            "repair": _repair_summary(manifest_path),
            "rounds": rounds,
            "assistant_messages": assistant_messages,
            "event_counts": event_counts or pi.get("event_counts", {}),
            "usage": usage,
            "usage_source": "pi.jsonl message_end events" if event_assistant_messages else "generation manifest",
            "usage_available": assistant_messages > 0 and usage["total_tokens"] > 0,
        }
    )
    if elapsed_seconds is not None:
        metadata["elapsed_seconds"] = elapsed_seconds
    if metadata.get("base_url") and "route" not in metadata:
        metadata["route"] = str(metadata["base_url"]).rstrip("/")
    return metadata


def copy_generation_bundle(generation_path: str | Path | None, destination: Path) -> dict[str, Any]:
    """Copy safe, already-redacted generation records into the evaluation bundle."""
    summary = summarize_generation(generation_path)
    destination.mkdir(parents=True, exist_ok=True)
    if generation_path is None:
        return summary
    path = Path(generation_path).resolve()
    manifest_path, _ = _generation_manifest(path)
    source_dir = manifest_path.parent if manifest_path is not None else (path if path.is_dir() else path.parent)
    copied: list[dict[str, Any]] = []
    for name in GENERATION_FILES:
        source = source_dir / name
        if not source.is_file():
            continue
        target = destination / name
        shutil.copy2(source, target)
        copied.append({"name": name, "path": str(target), "sha256": sha256_file(target), "bytes": target.stat().st_size})
    if manifest_path is not None:
        repair_source = _repair_manifest_path(manifest_path)
        if repair_source.is_file():
            repair_target = destination / "repair" / "manifest.json"
            repair_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repair_source, repair_target)
            copied.append({"name": "repair/manifest.json", "path": str(repair_target), "sha256": sha256_file(repair_target), "bytes": repair_target.stat().st_size})
    summary["copied_files"] = copied
    return summary


def artifact_record(path: Path, *, kind: str, scope: str | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "kind": kind,
        "path": str(path),
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if scope is not None:
        record["scope"] = scope
    return record


def write_structured_evidence(run_dir: Path, manifest: dict[str, Any]) -> Path:
    fixture = manifest.get("fixture") or {}
    contract = manifest.get("screenshot_contract") or {}
    readbacks = manifest.get("readbacks") or {}
    screenshot_metadata = manifest.get("screenshot_metadata") or {}
    modes = list(contract.get("states") or [])
    observations = []
    for mode in modes:
        run_key = f"run:{mode}"
        check_key = f"check_game:{mode}"
        prefix = f"state-{mode}"
        angle_screenshots = [
            record
            for key, record in sorted(screenshot_metadata.items())
            if key == prefix or key.startswith(prefix + "-")
        ]
        primary_key = prefix if prefix in screenshot_metadata else f"{prefix}-{contract.get('primary', 'hero')}"
        observations.append(
            {
                "mode": mode,
                "execution_status": "observed" if run_key in readbacks and check_key in readbacks else "not_observed",
                "run_readback": readbacks.get(run_key),
                "check_readback": readbacks.get(check_key),
                "screenshot": screenshot_metadata.get(primary_key) or (angle_screenshots[0] if angle_screenshots else None),
                "screenshots": angle_screenshots,
            }
        )
    payload = {
        "format": "bloxbench-structured-evidence-v1",
        "generated_at": utc_now(),
        "evaluation_id": manifest.get("evaluation_id"),
        "fixture": {
            "id": fixture.get("id"),
            "scenario_name": fixture.get("scenario_name"),
            "sha256": fixture.get("sha256"),
            "runtime": fixture.get("runtime"),
            "states": modes,
        },
        "candidate": manifest.get("candidate"),
        "provenance": {
            "source": manifest.get("source"),
            "generation": manifest.get("generation"),
            "place": manifest.get("place"),
        },
        "setup": readbacks.get("setup"),
        "state_observations": observations,
        "cleanup": readbacks.get("cleanup"),
        "final_reset": manifest.get("final_reset"),
        "trace": manifest.get("trace"),
        "screenshots": screenshot_metadata,
        "videos": manifest.get("videos", []),
        "presentation_artifacts": manifest.get("presentation_artifacts", []),
        "evidence_gaps": manifest.get("evidence_gaps", []),
        "evidence_summary": manifest.get("evidence_summary", {}),
        "quality_scored": False,
        "human_review_required": True,
    }
    path = run_dir / "evidence.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def write_evaluation_summary(run_dir: Path, manifest: dict[str, Any]) -> None:
    """Write a compact JSON record intended for a person, not only the runner."""
    summary_keys = (
        "framework",
        "evaluation_id",
        "state",
        "evidence_state",
        "evidence_gaps",
        "evidence_summary",
        "created_at",
        "started_at",
        "completed_at",
        "fixture",
        "candidate",
        "generation",
        "place",
        "readiness",
        "runtime_client_discovery",
        "operations",
        "readbacks",
        "trace",
        "screenshot_contract",
        "screenshots",
        "videos",
        "presentation_artifacts",
        "human_review",
        "error",
    )
    summary = {key: manifest[key] for key in summary_keys if key in manifest}
    evidence_path = write_structured_evidence(run_dir, manifest)
    summary["structured_evidence_path"] = str(evidence_path)
    summary["bundle_root"] = str(run_dir)
    summary["generated_at"] = utc_now()
    (run_dir / "evaluation.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )


def write_bundle_readme(run_dir: Path, manifest: dict[str, Any]) -> None:
    fixture = manifest.get("fixture") or {}
    candidate = manifest.get("candidate") or {}
    generation = manifest.get("generation") or {}
    place = manifest.get("place") or {}
    lines = [
        "# BloxBench evaluation bundle",
        "",
        f"- fixture: `{fixture.get('id', 'unknown')}`",
        f"- scenario: `{fixture.get('scenario_name', 'unknown')}`",
        f"- state: `{manifest.get('state')}`",
        f"- evidence: `{manifest.get('evidence_state')}`",
        f"- candidate origin: `{candidate.get('origin', 'unknown')}`",
        "",
        "This folder contains execution facts and review media. It does not contain an automated quality score.",
        "",
        "## files",
        "",
        "- `evaluation.json`: compact evaluation record for inspection.",
        "- `evidence.json`: normalized per-state readbacks, screenshots, and provenance.",
        "- `manifest.json`: full parent-owned execution manifest.",
        "- `source/`: candidate Luau source as executed.",
        "- `fixture/`: fixture contract as executed.",
        "- `generation/`: model/provider/route/prompt/token metadata when supplied.",
        "- `screenshots/`: RSC screenshots and their recorded hashes, including declared state/angle frames.",
        "- `trace/`: normalized operation trace and raw RSC request/response records.",
        "- `place/`: exported playable place when a verified save was supplied; unchanged input templates are rejected.",
        "- `videos/`: only capture artifacts that pass the viewport-only evidence contract.",
        "- `review_packet.md`: human review instructions and automated observations.",
        "",
        "## provenance",
        "",
        f"- source SHA-256: `{(manifest.get('source') or {}).get('sha256', 'unknown')}`",
        f"- fixture SHA-256: `{fixture.get('sha256', 'unknown')}`",
        f"- model evaluation: `{generation.get('is_model_evaluation', False)}`",
    ]
    if generation.get("model"):
        lines.extend(
            [
                f"- model: `{generation.get('model_name') or generation.get('model')}`",
                f"- provider: `{generation.get('provider') or generation.get('provider_id')}`",
                f"- route: `{generation.get('route') or generation.get('base_url', 'unknown')}`",
                f"- rounds: `{generation.get('rounds', 'unknown')}`",
                f"- usage available: `{generation.get('usage_available', False)}`",
            ]
        )
    if place.get("generated"):
        lines.append(f"- playable place: `{place.get('path')}`")
    else:
        lines.append("- playable place: NOT EXPORTED. The template is not the generated result.")
    (run_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
