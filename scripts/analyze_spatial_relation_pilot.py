#!/usr/bin/env python3
"""Offline relation checks for BloxBench structure dumps.

This is diagnostic only. It never changes official results.json pass fields.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable


_NUMBER = r"[-+]?\d+(?:\.\d+)?"
_PART_RE = re.compile(
    rf"^Part:(?P<name>\S+) .*?"
    rf"Pos=\((?P<px>{_NUMBER}),(?P<py>{_NUMBER}),(?P<pz>{_NUMBER})\) "
    rf"Size=\((?P<sx>{_NUMBER}),(?P<sy>{_NUMBER}),(?P<sz>{_NUMBER})\)"
)
_RELATION_RE = re.compile(
    r"^(?P<subject>\S+)\s+(?P<predicate>grounded_on|centered_over|supported_by|attached_to|aligned_with|offset_from|parented_under|preserve_rigid_assembly|preserve_transform)\s+(?P<object>\S+)$"
)


_STRICT_RELATIONS = {
    "VB_REPAIR_001_watchtower": [
        ("LookoutPlatform", "centered_over", "TowerShaft"),
        ("LookoutColumn", "supported_by", "LookoutPlatform"),
        ("LooseRoof", "centered_over", "LookoutColumn"),
        ("LooseRoof", "supported_by", "LookoutColumn"),
        ("LooseBattlement", "supported_by", "LookoutPlatform"),
    ],
}


@dataclass(frozen=True)
class PartState:
    name: str
    position: tuple[float, float, float]
    size: tuple[float, float, float]

    def with_position(self, position: tuple[float, float, float]) -> "PartState":
        return replace(self, position=position)

    @property
    def bounds(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        half = (self.size[0] / 2, self.size[1] / 2, self.size[2] / 2)
        low = (
            self.position[0] - half[0],
            self.position[1] - half[1],
            self.position[2] - half[2],
        )
        high = (
            self.position[0] + half[0],
            self.position[1] + half[1],
            self.position[2] + half[2],
        )
        return low, high


def parse_structure_dump(dump: str) -> dict[str, list[PartState]]:
    """Parse the harness's stable Part:name Pos/Size lines."""
    parts: dict[str, list[PartState]] = {}
    for line in dump.splitlines():
        match = _PART_RE.match(line.strip())
        if not match:
            continue
        values = [float(match.group(key)) for key in ("px", "py", "pz", "sx", "sy", "sz")]
        state = PartState(
            name=match.group("name"),
            position=(values[0], values[1], values[2]),
            size=(values[3], values[4], values[5]),
        )
        parts.setdefault(state.name, []).append(state)
    return parts


def _first(parts: dict[str, list[PartState]], name: str) -> PartState | None:
    values = parts.get(name)
    return values[0] if values else None


def _overlap(a_low: float, a_high: float, b_low: float, b_high: float) -> float:
    return min(a_high, b_high) - max(a_low, b_low)


def _vertical_contact(subject: PartState, target: PartState, tolerance: float) -> bool:
    subject_low, _ = subject.bounds
    _, target_high = target.bounds
    return abs(subject_low[1] - target_high[1]) <= tolerance


def relation_passes(
    parts: dict[str, list[PartState]],
    subject_name: str,
    predicate: str,
    object_name: str,
    tolerance: float = 0.5,
) -> bool:
    """Evaluate a conservative relation predicate over parsed part bounds."""
    subject = _first(parts, subject_name)
    target = _first(parts, object_name)
    if subject is None or target is None:
        return False
    subject_low, subject_high = subject.bounds
    target_low, target_high = target.bounds

    if predicate == "centered_over":
        return (
            abs(subject.position[0] - target.position[0]) <= tolerance
            and abs(subject.position[2] - target.position[2]) <= tolerance
            and abs(subject_low[1] - target_high[1]) <= tolerance
        )

    if predicate == "supported_by":
        return (
            _vertical_contact(subject, target, tolerance)
            and _overlap(subject_low[0], subject_high[0], target_low[0], target_high[0]) > 0
            and _overlap(subject_low[2], subject_high[2], target_low[2], target_high[2]) > 0
        )

    if predicate == "attached_to":
        x_gap = max(target_low[0] - subject_high[0], subject_low[0] - target_high[0], 0)
        z_gap = max(target_low[2] - subject_high[2], subject_low[2] - target_high[2], 0)
        horizontal_gap = math.hypot(x_gap, z_gap)
        return (
            _overlap(subject_low[1], subject_high[1], target_low[1], target_high[1]) > 0
            and horizontal_gap <= tolerance
        )

    if predicate == "aligned_with":
        return (
            abs(subject.position[0] - target.position[0]) <= tolerance
            and abs(subject.position[2] - target.position[2]) <= tolerance
        )

    raise ValueError(f"unsupported diagnostic predicate: {predicate}")


def parse_required_relations(values: Iterable[str]) -> list[tuple[str, str, str]]:
    relations = []
    for value in values:
        match = _RELATION_RE.match(value.strip())
        if match:
            relations.append((match.group("subject"), match.group("predicate"), match.group("object")))
    return relations


def load_expected_relations(context_dir: Path, scenario: str) -> list[tuple[str, str, str]]:
    path = context_dir / f"{scenario}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse_required_relations(data.get("required_relations", []))


def _diagnostic_count(dump: str, label: str) -> int | None:
    match = re.search(rf"{label}:(\d+)", dump)
    return int(match.group(1)) if match else None


def analyze_results(results_path: Path, context_dir: Path, strict: bool = False) -> dict:
    data = json.loads(results_path.read_text(encoding="utf-8"))
    evals = []
    for result in data.get("evals", []):
        dump = result.get("structure_dump") or ""
        parts = parse_structure_dump(dump)
        relations = _STRICT_RELATIONS.get(result["scenario"]) if strict else None
        if relations is None:
            relations = load_expected_relations(context_dir, result["scenario"])
        checks = []
        for subject, predicate, object_name in relations:
            checks.append(
                {
                    "subject": subject,
                    "predicate": predicate,
                    "object": object_name,
                    "passed": relation_passes(parts, subject, predicate, object_name),
                }
            )
        evals.append(
            {
                "scenario": result["scenario"],
                "official_passed": result.get("passed"),
                "relation_passed": bool(checks) and all(check["passed"] for check in checks),
                "relation_checks": checks,
                "part_count": sum(len(values) for values in parts.values()),
                "floating_flags": _diagnostic_count(dump, "floating_parts"),
                "overlap_flags": _diagnostic_count(dump, "overlaps"),
            }
        )
    return {
        "diagnostic_only": True,
        "relation_mode": "strict" if strict else "declared_context",
        "results_path": str(results_path),
        "official_passed": sum(1 for item in evals if item["official_passed"]),
        "official_total": len(evals),
        "relation_passed": sum(1 for item in evals if item["relation_passed"]),
        "relation_total": len(evals),
        "evals": evals,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path, help="results.json files or run directories")
    parser.add_argument("--context-dir", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Use reviewer-defined support invariants where the sidecar is incomplete")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    reports = []
    for path in args.results:
        results_path = path / "results.json" if path.is_dir() else path
        reports.append(analyze_results(results_path, args.context_dir, strict=args.strict))
    payload = {"diagnostic_only": True, "runs": reports}
    text = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
