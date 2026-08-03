#!/usr/bin/env python3
"""Build a blind A/B packet from two completed BloxBench review runs."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from scripts.benchmark.evaluation_bundle import validate_place_file


PACKET_VERSION = "bloxbench-pairwise-human-review-v1"


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


def load_run(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("state") != "completed" or manifest.get("evidence_state") != "valid reviewable result":
        raise ValueError(f"run is not completed and reviewable: {run_dir}")
    candidate = manifest.get("candidate") or {}
    if candidate.get("is_model_evaluation") is not True:
        raise ValueError(f"run has no model-generation provenance: {run_dir}")
    place = manifest.get("place") or {}
    if place.get("generated") is not True:
        raise ValueError(f"run has no generated candidate place: {run_dir}")
    place_path = Path(place.get("path", ""))
    template_path = Path(__file__).resolve().parents[2] / "Places" / str(manifest.get("fixture", {}).get("place", ""))
    try:
        place_info = validate_place_file(place_path, template_path=template_path)
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError(f"run has an invalid generated candidate place: {run_dir}: {exc}") from exc
    if place.get("format") is not None and place.get("format") != place_info["format"]:
        raise ValueError(f"run place format metadata mismatch: {run_dir}")
    verify_file(place_path, place.get("sha256"), place.get("bytes"))
    if manifest.get("fixture", {}).get("sha256") is None:
        raise ValueError(f"run has no fixture digest: {run_dir}")
    if not manifest.get("final_reset"):
        raise ValueError(f"run has no verified final reset: {run_dir}")
    if "cleanup" not in manifest.get("readbacks", {}):
        raise ValueError(f"run has no fixture cleanup readback: {run_dir}")
    if not manifest.get("screenshots"):
        raise ValueError(f"run has no screenshot evidence: {run_dir}")
    for video in manifest.get("videos") or []:
        if video.get("reviewable") is not True:
            raise ValueError(f"run has an unverified video artifact: {run_dir}")
    return manifest


def collect_artifacts(run_dir: Path, manifest: dict[str, Any], label: str, packet_dir: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for name, raw_path in sorted(manifest["screenshots"].items()):
        source = Path(raw_path)
        checked = verify_file(source)
        destination = packet_dir / label / "screenshots" / f"{name}{source.suffix.lower() or '.png'}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        artifacts.append({"kind": "screenshot", "name": name, "path": str(destination), **{k: checked[k] for k in ("sha256", "size")}})
    for index, video in enumerate(manifest["videos"]):
        source = Path(video["path"])
        checked = verify_file(source, video.get("sha256"), video.get("size"))
        destination = packet_dir / label / "video" / f"video-{index}{source.suffix.lower() or '.mp4'}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        artifacts.append({"kind": "video", "name": f"video-{index}", "path": str(destination), **{k: checked[k] for k in ("sha256", "size")}})
    place = manifest.get("place") or {}
    if place.get("generated") is True:
        source = Path(place["path"])
        checked = verify_file(source, place.get("sha256"), place.get("bytes"))
        destination = packet_dir / label / "place" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        place_format = place.get("format") or "unknown"
        if place_format == "roblox-bench-export-json":
            # The studio build export is a parts/material manifest JSON, not a
            # .rbxl place. Validate it parses as JSON and records the format.
            try:
                json.loads(source.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"run place export JSON is invalid: {source}: {exc}") from exc
        else:
            place_info = validate_place_file(source)
            place_format = place_info["format"]
        artifacts.append({"kind": "place", "name": source.name, "format": place_format, "path": str(destination), **{k: checked[k] for k in ("sha256", "size")}})
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
        },
        "labels": {
            "A": {"artifacts": artifacts_a if label_for_run[str(run_a.resolve())] == "A" else artifacts_b},
            "B": {"artifacts": artifacts_b if label_for_run[str(run_b.resolve())] == "B" else artifacts_a},
        },
        "provenance_internal": {
            "A_run_dir": str(run_a.resolve()) if label_for_run[str(run_a.resolve())] == "A" else str(run_b.resolve()),
            "B_run_dir": str(run_b.resolve()) if label_for_run[str(run_b.resolve())] == "B" else str(run_a.resolve()),
            "A_source_sha256": source_a if label_for_run[str(run_a.resolve())] == "A" else source_b,
            "B_source_sha256": source_b if label_for_run[str(run_b.resolve())] == "B" else source_a,
        },
        "automated_boundary": {
            "quality_scored": False,
            "allowed_human_labels": ["A better", "B better", "tie", "both bad"],
            "final_label": None,
            "review_notes": None,
        },
    }
    (output_dir / "packet.json").write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "review_form.json").write_text(
        json.dumps({"label": None, "notes": None, "reviewer": None}, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# BloxBench blind pairwise review",
        "",
        f"- fixture: `{fixture_a['id']}`",
        f"- scenario: {fixture_a['scenario_name']}",
        "- automated quality score: none",
        "",
        "Review the two arms using only the attached evidence. Use exactly one label: `A better`, `B better`, `tie`, or `both bad`.",
        "Judge construction quality, visual coherence, completeness, legibility, and gameplay or animation feel.",
        "The A/B-to-source mapping is stored only in packet.json for parent-side provenance and is not repeated here.",
        "",
    ]
    for label in ("A", "B"):
        lines.extend([f"## arm {label}", ""])
        for artifact in packet["labels"][label]["artifacts"]:
            lines.append(f"- {artifact['kind']} `{artifact['name']}`: `{artifact['path']}`")
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
