#!/usr/bin/env python3
"""Build a deterministic manifest for a named BloxBench task suite."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark.fixture_contract import FixtureContractError, discover_fixtures  # noqa: E402

SCHEMA = "bloxbench-suite-v1"
SUITE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _suite_digest(manifest: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "sha256"}
    return hashlib.sha256(_canonical(unsigned)).hexdigest()


def build_suite_manifest(
    fixtures_root: str | Path,
    suite_id: str,
    suite_version: str,
    *,
    repo_root: str | Path | None = None,
    expected_count: int | None = None,
) -> dict[str, Any]:
    if not SUITE_ID_PATTERN.fullmatch(suite_id):
        raise ValueError(f"suite id must be lowercase slug-like text: {suite_id!r}")
    if not suite_version.strip():
        raise ValueError("suite version must not be empty")
    if expected_count is not None and expected_count < 1:
        raise ValueError("expected task count must be positive")

    root = Path(repo_root or ROOT).resolve()
    fixtures = discover_fixtures(fixtures_root)
    if expected_count is not None and len(fixtures) != expected_count:
        raise FixtureContractError(
            f"suite {suite_id} expected {expected_count} fixtures, found {len(fixtures)}"
        )

    tasks = []
    for fixture in fixtures:
        try:
            relative_path = fixture.path.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError(f"fixture is outside repo root: {fixture.path}") from exc
        tasks.append(
            {
                "id": fixture.fixture_id,
                "path": relative_path.as_posix(),
                "sha256": fixture.sha256,
                "prompt_sha256": hashlib.sha256(fixture.prompt.encode("utf-8")).hexdigest(),
                "track": fixture.track,
                "place": fixture.place,
                "runtime": fixture.runtime,
                "knowledge_profile": fixture.knowledge_profile,
                "candidate_root": fixture.candidate_root,
                "provenance": dict(sorted(fixture.provenance.items())),
                "evidence": dict(sorted(fixture.evidence.items())),
            }
        )
    tasks.sort(key=lambda item: item["id"])

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "suite_id": suite_id,
        "suite_version": suite_version,
        "task_count": len(tasks),
        "tasks": tasks,
    }
    if expected_count is not None:
        manifest["expected_task_count"] = expected_count
    manifest["sha256"] = _suite_digest(manifest)
    return manifest


def validate_suite_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unsupported suite manifest schema")
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("suite manifest tasks must be a list")
    if manifest.get("task_count") != len(tasks):
        raise ValueError("suite manifest task_count does not match tasks")
    ids = [task.get("id") for task in tasks if isinstance(task, dict)]
    if len(ids) != len(tasks) or len(set(ids)) != len(ids):
        raise ValueError("suite manifest task ids must be unique")
    expected_count = manifest.get("expected_task_count")
    if expected_count is not None and expected_count != len(tasks):
        raise ValueError("suite manifest expected_task_count does not match tasks")
    if manifest.get("sha256") != _suite_digest(manifest):
        raise ValueError("suite manifest sha256 does not match its contents")


def suite_reference(path: str | Path, fixture_id: str, fixture_sha256: str) -> dict[str, str]:
    manifest_path = Path(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_suite_manifest(manifest)
    task = next((item for item in manifest["tasks"] if item.get("id") == fixture_id), None)
    if task is None:
        raise ValueError(f"fixture {fixture_id!r} is not in suite manifest {manifest_path}")
    if task.get("sha256") != fixture_sha256:
        raise ValueError(f"fixture digest does not match suite manifest for {fixture_id}")
    return {
        "suite_id": str(manifest["suite_id"]),
        "suite_version": str(manifest["suite_version"]),
        "suite_sha256": str(manifest["sha256"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures-root", type=Path, default=ROOT / "Evals")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--suite-id", required=True)
    parser.add_argument("--suite-version", required=True)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    manifest = build_suite_manifest(
        args.fixtures_root,
        args.suite_id,
        args.suite_version,
        repo_root=args.repo_root,
        expected_count=args.expected_count,
    )
    validate_suite_manifest(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": manifest["sha256"], "task_count": manifest["task_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
