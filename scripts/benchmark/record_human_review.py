#!/usr/bin/env python3
"""Persist a completed human decision for a BloxBench pairwise packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.benchmark.pairwise_packet import ALLOWED_HUMAN_LABELS, PACKET_VERSION


FORM_SCHEMA = "bloxbench-human-review-form-v1"


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(raw_path, path)
    except BaseException:
        try:
            os.unlink(raw_path)
        except FileNotFoundError:
            pass
        raise


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def ingest_human_review(
    packet_dir: Path,
    form_path: Path | None = None,
    *,
    replace: bool = False,
) -> Path:
    """Validate and persist the reviewer-facing form without exposing A/B mapping."""
    packet_path = packet_dir / "packet.json"
    form_path = form_path or packet_dir / "review_form.json"
    packet = _read_object(packet_path)
    form = _read_object(form_path)
    if packet.get("kind") != PACKET_VERSION:
        raise ValueError(f"packet kind must be {PACKET_VERSION}")
    if form.get("schema") not in {None, FORM_SCHEMA}:
        raise ValueError(f"review form schema must be {FORM_SCHEMA}")
    if form.get("packet_kind") not in {None, PACKET_VERSION}:
        raise ValueError("review form packet kind does not match packet")
    fixture_id = (packet.get("fixture") or {}).get("id")
    if form.get("fixture_id") not in {None, fixture_id}:
        raise ValueError("review form fixture does not match packet")
    allowed = tuple((packet.get("automated_boundary") or {}).get("allowed_human_labels") or ALLOWED_HUMAN_LABELS)
    label = form.get("label")
    if label not in allowed:
        raise ValueError(f"label must be an allowed human label: {', '.join(allowed)}")
    previous = packet.get("human_decision")
    if previous is not None and not replace:
        raise ValueError("human decision is already recorded; pass replace=True to overwrite it")
    notes = form.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise ValueError("review notes must be a string or null")
    reviewer = form.get("reviewer")
    if reviewer is not None and not isinstance(reviewer, str):
        raise ValueError("reviewer must be a string or null")
    decision = {
        "label": label,
        "reviewer": reviewer,
        "notes": notes,
        "notes_sha256": hashlib.sha256(notes.encode("utf-8")).hexdigest() if notes else None,
        "reviewed_at": _utc_now(),
    }
    packet["human_decision"] = decision
    packet.setdefault("automated_boundary", {})["human_decision_recorded"] = True
    packet["automated_boundary"]["quality_scored"] = False
    _atomic_json(packet_path, packet)
    _atomic_json(packet_dir / "human_decision.json", decision)

    review_path = packet_dir / "human_review.md"
    if review_path.is_file():
        existing = review_path.read_text(encoding="utf-8")
        prefix = existing.split("\n## decision", 1)[0].rstrip()
        suffix = [
            "",
            "## recorded human decision",
            "",
            f"- label: `{label}`",
            f"- reviewer: `{reviewer or 'anonymous'}`",
            f"- notes: {notes or '(none)' }",
            "",
        ]
        review_path.write_text(prefix + "\n" + "\n".join(suffix), encoding="utf-8")
    return packet_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet_dir", type=Path)
    parser.add_argument("--form", type=Path, help="review form path; defaults to packet_dir/review_form.json")
    parser.add_argument("--replace", action="store_true", help="replace an existing decision explicitly")
    args = parser.parse_args(argv)
    output = ingest_human_review(args.packet_dir, args.form, replace=args.replace)
    print(json.dumps({"packet": str(output), "state": "human_decision_recorded"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
