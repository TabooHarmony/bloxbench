#!/usr/bin/env python3
"""Build a blind A/B packet from two reviewable BloxBench runs."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from scripts.benchmark.evaluation_bundle import validate_place_file
from scripts.benchmark.fixture_contract import resolve_starter_place


PACKET_VERSION = "bloxbench-pairwise-human-review-v3"
ALLOWED_HUMAN_LABELS = ("A better", "B better", "tie", "both bad")


def evidence_gaps(manifest: dict[str, Any]) -> list[str]:
    """Describe missing declared evidence without making it a quality verdict."""
    gaps = [str(item) for item in manifest.get("evidence_gaps") or []]
    fixture = manifest.get("fixture") or {}
    evidence = fixture.get("evidence") or {}
    static_mode = evidence.get("static", "required")
    if static_mode != "not-applicable" and not manifest.get("screenshots"):
        gaps.append("screenshots")
    if evidence.get("video") == "required" and not manifest.get("videos"):
        gaps.append("video")
    if evidence.get("presentation") == "required" and not manifest.get("presentation_artifacts"):
        gaps.append("presentation")
    return list(dict.fromkeys(gaps))


def _has_review_artifact(manifest: dict[str, Any], run_dir: Path) -> bool:
    if manifest.get("screenshots") or manifest.get("videos") or manifest.get("presentation_artifacts"):
        return True
    place = manifest.get("place") or {}
    if place.get("generated") is True:
        return bool(_place_records(place, run_dir))
    return False


def _diagnostic_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []

    def visit(value: Any, key: str = "") -> None:
        normalized_key = key.lower()
        if normalized_key in {"warning", "warnings", "error", "errors"}:
            if isinstance(value, dict) and isinstance(value.get("message"), str):
                text = value["message"]
            elif isinstance(value, (dict, list)):
                text = json.dumps(value, sort_keys=True, default=str)
            else:
                text = str(value)
            if text and text not in warnings:
                warnings.append(text)
            return
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, child_key)
        elif isinstance(value, list):
            for item in value:
                visit(item, key)
        elif value not in (None, "") and normalized_key in {"warning", "warnings", "error", "errors"}:
            text = str(value)
            if text not in warnings:
                warnings.append(text)

    visit(manifest.get("readbacks") or {})
    visit(manifest.get("error") or {})
    return {
        "state": manifest.get("state"),
        "evidence_state": manifest.get("evidence_state"),
        "warning_count": len(warnings),
        "warnings": warnings[:20],
        "evidence_gaps": evidence_gaps(manifest),
        "evidence_summary": manifest.get("evidence_summary") or {},
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path, expected_sha: str | None = None, expected_size: int | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_size = path.stat().st_size
    actual_sha = sha256_file(path)
    if expected_sha is not None and actual_sha != expected_sha:
        raise ValueError(f"artifact hash mismatch: {path}")
    if expected_size is not None and actual_size != expected_size:
        raise ValueError(f"artifact size mismatch: {path}")
    return {"path": str(path), "sha256": actual_sha, "size": actual_size}


def _resolve_artifact_path(run_dir: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute() or path.is_file():
        return path
    for base in (Path.cwd(), run_dir, *run_dir.parents):
        candidate = base / path
        if candidate.is_file():
            return candidate
    return path


def _place_records(place: dict[str, Any], run_dir: Path | None = None) -> list[dict[str, Any]]:
    """Return the exported manifest and any converted review place."""
    resolve = (lambda value: _resolve_artifact_path(run_dir, value)) if run_dir is not None else Path
    records: list[dict[str, Any]] = []
    raw_path = place.get("path")
    if raw_path:
        path = resolve(str(raw_path))
        records.append(
            {
                "kind": "place-export" if path.suffix.lower() == ".json" else "place",
                "path": path,
                "sha256": place.get("sha256"),
                "size": place.get("bytes"),
                "format": place.get("format"),
            }
        )
    converted = place.get("rbxlx")
    if isinstance(converted, dict) and converted.get("path"):
        records.append(
            {
                "kind": "place",
                "path": resolve(str(converted["path"])),
                "sha256": converted.get("sha256"),
                "size": converted.get("bytes"),
                "format": "rbxlx-xml",
            }
        )
    return records


def _validate_place_record(record: dict[str, Any], template_path: Path | None = None) -> None:
    path = record["path"]
    if record["kind"] == "place-export":
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"run place export JSON is invalid: {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"run place export JSON must contain an object: {path}")
    else:
        place_info = validate_place_file(path, template_path=template_path)
        expected_format = record.get("format")
        if expected_format is not None and expected_format != place_info["format"]:
            raise ValueError(f"run place format metadata mismatch: {path}")
    verify_file(path, record.get("sha256"), record.get("size"))


def load_run(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("state") not in {"completed", "completed_unexported", "failed"}:
        raise ValueError(f"run has no reviewable terminal state: {run_dir}")
    candidate = manifest.get("candidate") or {}
    if candidate.get("is_model_evaluation") is not True:
        raise ValueError(f"run has no model-generation provenance: {run_dir}")
    place = manifest.get("place") or {}
    template_path = resolve_starter_place(Path(__file__).resolve().parents[2], str(manifest.get("fixture", {}).get("place", "")))
    records = _place_records(place, run_dir) if place.get("generated") is True else []
    try:
        for record in records:
            _validate_place_record(record, template_path=template_path)
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError(f"run has an invalid generated candidate place: {run_dir}: {exc}") from exc
    if manifest.get("fixture", {}).get("sha256") is None:
        raise ValueError(f"run has no fixture digest: {run_dir}")
    if not _has_review_artifact(manifest, run_dir):
        raise ValueError(f"run has no review evidence artifact: {run_dir}")
    for artifact in manifest.get("presentation_artifacts") or []:
        if not isinstance(artifact, dict) or not (artifact.get("path") or artifact.get("uri")):
            raise ValueError(f"run has an invalid presentation artifact record: {run_dir}")
    for video in manifest.get("videos") or []:
        if video.get("reviewable") is not True:
            raise ValueError(f"run has an unverified video artifact: {run_dir}")
    return manifest


def collect_artifacts(run_dir: Path, manifest: dict[str, Any], label: str, packet_dir: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for name, raw_path in sorted((manifest.get("screenshots") or {}).items()):
        source = _resolve_artifact_path(run_dir, raw_path)
        checked = verify_file(source)
        destination = packet_dir / label / "screenshots" / f"{name}{source.suffix.lower() or '.png'}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        artifacts.append({"kind": "screenshot", "name": name, "path": str(destination), **{k: checked[k] for k in ("sha256", "size")}})
    for index, video in enumerate(manifest.get("videos") or []):
        source = _resolve_artifact_path(run_dir, video["path"])
        checked = verify_file(source, video.get("sha256"), video.get("size"))
        destination = packet_dir / label / "video" / f"video-{index}{source.suffix.lower() or '.mp4'}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        artifacts.append({"kind": "video", "name": f"video-{index}", "path": str(destination), **{k: checked[k] for k in ("sha256", "size")}})
    for index, item in enumerate(manifest.get("presentation_artifacts") or []):
        if not isinstance(item, dict):
            raise ValueError(f"presentation artifact record is not an object: {run_dir}")
        raw_path = item.get("path")
        if raw_path:
            source = _resolve_artifact_path(run_dir, raw_path)
            checked = verify_file(source, item.get("sha256"), item.get("bytes", item.get("size")))
            name = str(item.get("name") or source.name or f"artifact-{index}")
            destination = packet_dir / label / "presentation" / f"{index:03d}-{source.name}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            artifacts.append(
                {
                    "kind": item.get("kind") or "presentation-artifact",
                    "name": name,
                    "role": item.get("role") or "presentation",
                    "path": str(destination),
                    **{k: checked[k] for k in ("sha256", "size")},
                }
            )
        elif item.get("uri"):
            artifacts.append(
                {
                    "kind": item.get("kind") or "presentation-artifact",
                    "name": str(item.get("name") or f"artifact-{index}"),
                    "role": item.get("role") or "presentation",
                    "uri": str(item["uri"]),
                }
            )
        else:
            raise ValueError(f"presentation artifact has no path or uri: {run_dir}")
    place = manifest.get("place") or {}
    if place.get("generated") is True:
        for record in _place_records(place, run_dir):
            source = record["path"]
            checked = verify_file(source, record.get("sha256"), record.get("size"))
            destination = packet_dir / label / "place" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            place_format = record.get("format") or "unknown"
            if record["kind"] == "place":
                place_format = validate_place_file(source)["format"]
            artifacts.append({"kind": record["kind"], "name": source.name, "format": place_format, "path": str(destination), **{k: checked[k] for k in ("sha256", "size")}})
    return artifacts


def build_pairwise_packet(run_a: Path, run_b: Path, output_dir: Path) -> Path:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    manifest_a = load_run(run_a)
    manifest_b = load_run(run_b)
    fixture_a = manifest_a["fixture"]
    fixture_b = manifest_b["fixture"]
    for key in ("id", "sha256", "prompt_sha256", "place"):
        if fixture_a.get(key) != fixture_b.get(key):
            raise ValueError(f"arms do not match on fixture {key}: {fixture_a.get(key)!r} != {fixture_b.get(key)!r}")
    candidate_a = manifest_a.get("candidate") or {}
    candidate_b = manifest_b.get("candidate") or {}
    generation_a = manifest_a.get("generation") or {}
    generation_b = manifest_b.get("generation") or {}
    comparable_fields = {
        "treatment": (candidate_a.get("treatment"), candidate_b.get("treatment")),
        "knowledge_profile": (
            generation_a.get("knowledge_profile") or fixture_a.get("knowledge_profile"),
            generation_b.get("knowledge_profile") or fixture_b.get("knowledge_profile"),
        ),
        "knowledge_sha256": (generation_a.get("knowledge_sha256"), generation_b.get("knowledge_sha256")),
        "suite": (generation_a.get("suite"), generation_b.get("suite")),
        "effective_prompt_sha256": (
            generation_a.get("prompt_sha256"),
            generation_b.get("prompt_sha256"),
        ),
        "system_prompt_sha256": (
            generation_a.get("system_prompt_sha256"),
            generation_b.get("system_prompt_sha256"),
        ),
        "generator_sha256": (
            (generation_a.get("generator") or {}).get("sha256"),
            (generation_b.get("generator") or {}).get("sha256"),
        ),
        "tool_surface": (generation_a.get("tool_surface"), generation_b.get("tool_surface")),
        "prompt_order": (generation_a.get("prompt_order"), generation_b.get("prompt_order")),
        "repair_policy": (generation_a.get("repair_policy"), generation_b.get("repair_policy")),
    }
    for key, (value_a, value_b) in comparable_fields.items():
        if value_a != value_b:
            raise ValueError(f"arms do not match on comparison context {key}: {value_a!r} != {value_b!r}")
    source_a = manifest_a["source"]["sha256"]
    source_b = manifest_b["source"]["sha256"]
    if source_a == source_b:
        raise ValueError("pairwise arms must have distinct candidate source digests")
    output_dir.mkdir(parents=True)
    label_for_run = {str(run_a.resolve()): "A", str(run_b.resolve()): "B"}
    # Keep the A/B assignment deterministic while not exposing model names to the reviewer.
    if source_a > source_b:
        label_for_run = {str(run_a.resolve()): "B", str(run_b.resolve()): "A"}
    artifacts_a = collect_artifacts(run_a, manifest_a, label_for_run[str(run_a.resolve())], output_dir)
    artifacts_b = collect_artifacts(run_b, manifest_b, label_for_run[str(run_b.resolve())], output_dir)
    packet = {
        "kind": PACKET_VERSION,
        "fixture": {
            "id": fixture_a["id"],
            "scenario_name": fixture_a["scenario_name"],
            "sha256": fixture_a["sha256"],
            "prompt_sha256": fixture_a["prompt_sha256"],
            "place": fixture_a["place"],
            "screenshot_purpose": fixture_a.get("screenshot_purpose", "diagnostic"),
        },
        "labels": {
            "A": {
                "artifacts": artifacts_a if label_for_run[str(run_a.resolve())] == "A" else artifacts_b,
                "diagnostics": _diagnostic_summary(manifest_a if label_for_run[str(run_a.resolve())] == "A" else manifest_b),
                "evidence_gaps": evidence_gaps(manifest_a if label_for_run[str(run_a.resolve())] == "A" else manifest_b),
            },
            "B": {
                "artifacts": artifacts_b if label_for_run[str(run_b.resolve())] == "B" else artifacts_a,
                "diagnostics": _diagnostic_summary(manifest_b if label_for_run[str(run_b.resolve())] == "B" else manifest_a),
                "evidence_gaps": evidence_gaps(manifest_b if label_for_run[str(run_b.resolve())] == "B" else manifest_a),
            },
        },
        "automated_boundary": {
            "quality_scored": False,
            "allowed_human_labels": list(ALLOWED_HUMAN_LABELS),
            "diagnostics_are_not_quality": True,
        },
        "human_decision": None,
    }
    (output_dir / "packet.json").write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    internal = {
        "A_run_dir": str(run_a.resolve()) if label_for_run[str(run_a.resolve())] == "A" else str(run_b.resolve()),
        "B_run_dir": str(run_b.resolve()) if label_for_run[str(run_b.resolve())] == "B" else str(run_a.resolve()),
        "A_source_sha256": source_a if label_for_run[str(run_a.resolve())] == "A" else source_b,
        "B_source_sha256": source_b if label_for_run[str(run_b.resolve())] == "B" else source_a,
    }
    internal_path = output_dir.parent / f".{output_dir.name}.provenance_internal.json"
    internal_path.write_text(json.dumps(internal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "review_form.json").write_text(
        json.dumps(
            {
                "schema": "bloxbench-human-review-form-v1",
                "packet_kind": PACKET_VERSION,
                "fixture_id": fixture_a["id"],
                "allowed_labels": list(ALLOWED_HUMAN_LABELS),
                "label": None,
                "notes": None,
                "reviewer": None,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# BloxBench blind pairwise review",
        "",
        f"- fixture: `{fixture_a['id']}`",
        f"- scenario: {fixture_a['scenario_name']}",
        "- automated quality score: none",
        "",
        "Review the two arms using only the attached evidence. Use exactly one label: `A better`, `B better`, `tie`, or `both bad`.",
        "Judge construction quality, visual coherence, completeness, legibility, and gameplay or animation feel only where the evidence actually shows it.",
        "Screenshots are diagnostic evidence in the current phase. They do not prove hidden state, dynamic gameplay, multiplayer behavior, timing, or causal attribution.",
        "Automated diagnostics are included as context and are not quality scores or approval gates.",
        "The A/B-to-source mapping is stored in a parent-only provenance file and is not repeated here.",
        "",
    ]
    for label in ("A", "B"):
        lines.extend([f"## arm {label}", ""])
        for artifact in packet["labels"][label]["artifacts"]:
            location = artifact.get("path") or artifact.get("uri") or "unresolved"
            lines.append(f"- {artifact['kind']} `{artifact['name']}`: `{location}`")
        diagnostics = packet["labels"][label].get("diagnostics") or {}
        gaps = packet["labels"][label].get("evidence_gaps") or []
        lines.append(f"- diagnostic state: `{diagnostics.get('state')}`, evidence: `{diagnostics.get('evidence_state')}`, warnings: `{diagnostics.get('warning_count', 0)}`")
        lines.append(f"- evidence gaps: `{', '.join(gaps) if gaps else 'none recorded'}`")
        lines.append("")
    lines.extend(["## decision", "", "- label: ` `", "- notes: ", ""])
    (output_dir / "human_review.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_a", type=Path)
    parser.add_argument("run_b", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    output = build_pairwise_packet(args.run_a, args.run_b, args.output_dir)
    print(json.dumps({"output_dir": str(output), "state": "ready_for_human_review"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
