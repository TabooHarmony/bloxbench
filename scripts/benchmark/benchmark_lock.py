#!/usr/bin/env python3
"""Build and validate a deterministic BloxBench benchmark lock.

The suite manifest fixes task membership. This lock additionally fixes the
model-facing knowledge, generator/evaluator revisions, model arms, tool
surface, decoding defaults, evidence semantics, and treatment policy.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark.generate_candidate import (  # noqa: E402
    BASE_URL,
    MODELS,
    build_system_prompt,
    file_sha256,
    knowledge_profile_path,
)
from scripts.benchmark.suite_manifest import SCHEMA as SUITE_SCHEMA  # noqa: E402
from scripts.benchmark.suite_manifest import validate_suite_manifest  # noqa: E402

SCHEMA = "bloxbench-benchmark-lock-v1"
LOCKED_GENERATOR = "scripts/benchmark/generate_candidate.py"
LOCKED_EVALUATORS = (
    "scripts/benchmark/fixture_contract.py",
    "scripts/benchmark/suite_manifest.py",
    "scripts/benchmark/review_runner.py",
    "scripts/benchmark/evaluation_bundle.py",
    "scripts/benchmark/pairwise_packet.py",
    "scripts/benchmark/record_human_review.py",
    "scripts/benchmark/build_to_place.py",
)
REVIEWER_LABELS = ("A better", "B better", "tie", "both bad")


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def lock_digest(lock: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in lock.items() if key != "sha256"}
    return hashlib.sha256(_canonical(unsigned)).hexdigest()


def _relative_artifact(repo_root: Path, relative_path: str) -> dict[str, str]:
    path = (repo_root / relative_path).resolve()
    try:
        path.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"locked artifact is outside repo root: {relative_path}") from exc
    if not path.is_file():
        raise ValueError(f"locked artifact is missing: {relative_path}")
    return {"path": relative_path, "sha256": file_sha256(path)}


def _knowledge_entry(repo_root: Path, profile: str) -> dict[str, str]:
    path = knowledge_profile_path(profile)
    try:
        relative_path = path.resolve().relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"knowledge profile is outside repo root: {path}") from exc
    content = path.read_text(encoding="utf-8").strip()
    return {
        "name": profile,
        "path": relative_path,
        "sha256": file_sha256(path),
        "system_prompt_sha256": hashlib.sha256(build_system_prompt(profile).encode("utf-8")).hexdigest(),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }


def build_benchmark_lock(suite_manifest: dict[str, Any], *, repo_root: str | Path | None = None) -> dict[str, Any]:
    """Build a deterministic lock from a validated suite manifest."""
    validate_suite_manifest(suite_manifest)
    root = Path(repo_root or ROOT).resolve()
    profiles = sorted({str(task["knowledge_profile"]) for task in suite_manifest["tasks"]})
    knowledge = [_knowledge_entry(root, profile) for profile in profiles]
    models = {
        key: {
            "id": value["id"],
            "name": value["name"],
            "max_output_tokens": value["max_tokens"],
        }
        for key, value in sorted(MODELS.items())
    }
    lock: dict[str, Any] = {
        "schema": SCHEMA,
        "suite": {
            "suite_id": suite_manifest["suite_id"],
            "suite_version": suite_manifest["suite_version"],
            "suite_sha256": suite_manifest["sha256"],
            "task_count": suite_manifest["task_count"],
            "manifest": copy.deepcopy(suite_manifest),
        },
        "treatment": {
            "primary": "direct",
            "repair_track": "separate",
            "repair_in_primary": False,
            "repair_policy": "explicit-source-error-repair",
        },
        "generation": {
            "provider": "charm-hyper",
            "base_url": BASE_URL,
            "models": models,
            "prompt_order": ["system", "user"],
            "tool_surface": {"protocol": "openai-chat-completions", "tools": []},
            "decoding": {
                "temperature": None,
                "top_p": None,
                "seed": None,
            },
            "generator": _relative_artifact(root, LOCKED_GENERATOR),
            "knowledge": knowledge,
        },
        "evaluation": {
            "quality_signal": "human-pairwise",
            "reviewer_labels": list(REVIEWER_LABELS),
            "evidence_is_quality_judgment": False,
            "diagnostic_screenshots_are_proof": False,
            "artifacts": [_relative_artifact(root, path) for path in LOCKED_EVALUATORS],
        },
        "tasks": copy.deepcopy(suite_manifest["tasks"]),
    }
    lock["sha256"] = lock_digest(lock)
    return lock


def _validate_artifact(repo_root: Path, artifact: Any, label: str) -> None:
    if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
        raise ValueError(f"{label} artifact is malformed")
    relative = artifact["path"]
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError(f"{label} artifact path must be repository-relative")
    expected = artifact.get("sha256")
    actual_path = (repo_root / relative).resolve()
    try:
        actual_path.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"{label} artifact is outside repo root") from exc
    if not actual_path.is_file():
        raise ValueError(f"{label} artifact is missing: {relative}")
    if expected != file_sha256(actual_path):
        raise ValueError(f"{label} artifact sha256 does not match: {relative}")


def validate_benchmark_lock(lock: dict[str, Any], *, repo_root: str | Path | None = None) -> None:
    """Validate lock structure, digest, suite copy, and referenced file hashes."""
    if lock.get("schema") != SCHEMA:
        raise ValueError("unsupported benchmark lock schema")
    if lock.get("sha256") != lock_digest(lock):
        raise ValueError("benchmark lock sha256 does not match its contents")
    root = Path(repo_root or ROOT).resolve()
    suite = lock.get("suite")
    if not isinstance(suite, dict) or not isinstance(suite.get("manifest"), dict):
        raise ValueError("benchmark lock suite manifest is missing")
    manifest = suite["manifest"]
    validate_suite_manifest(manifest)
    if manifest.get("schema") != SUITE_SCHEMA:
        raise ValueError("benchmark lock contains an unsupported suite schema")
    if suite.get("suite_id") != manifest.get("suite_id") or suite.get("suite_version") != manifest.get("suite_version"):
        raise ValueError("benchmark lock suite identity does not match its manifest")
    if suite.get("suite_sha256") != manifest.get("sha256"):
        raise ValueError("benchmark lock suite sha256 does not match its manifest")
    if suite.get("task_count") != manifest.get("task_count"):
        raise ValueError("benchmark lock suite task_count does not match its manifest")
    if lock.get("tasks") != manifest.get("tasks"):
        raise ValueError("benchmark lock task copy does not match its suite manifest")

    treatment = lock.get("treatment")
    if treatment != {
        "primary": "direct",
        "repair_track": "separate",
        "repair_in_primary": False,
        "repair_policy": "explicit-source-error-repair",
    }:
        raise ValueError("benchmark lock treatment policy is not the locked direct/separate policy")

    generation = lock.get("generation")
    if not isinstance(generation, dict):
        raise ValueError("benchmark lock generation section is missing")
    _validate_artifact(root, generation.get("generator"), "generator")
    if generation.get("provider") != "charm-hyper" or generation.get("base_url") != BASE_URL:
        raise ValueError("benchmark lock provider is not the locked provider")
    if generation.get("prompt_order") != ["system", "user"]:
        raise ValueError("benchmark lock prompt order is not system/user")
    if generation.get("tool_surface") != {"protocol": "openai-chat-completions", "tools": []}:
        raise ValueError("benchmark lock tool surface changed")
    if generation.get("decoding") != {"temperature": None, "top_p": None, "seed": None}:
        raise ValueError("benchmark lock decoding defaults changed")
    if generation.get("models") != {
        key: {"id": value["id"], "name": value["name"], "max_output_tokens": value["max_tokens"]}
        for key, value in sorted(MODELS.items())
    }:
        raise ValueError("benchmark lock model arms changed")

    knowledge = generation.get("knowledge")
    if not isinstance(knowledge, list) or not knowledge:
        raise ValueError("benchmark lock knowledge profiles are missing")
    for entry in knowledge:
        if not isinstance(entry, dict):
            raise ValueError("benchmark lock knowledge entry is malformed")
        profile = entry.get("name")
        if not isinstance(profile, str):
            raise ValueError("benchmark lock knowledge profile name is missing")
        expected = _knowledge_entry(root, profile)
        if entry != expected:
            raise ValueError(f"benchmark lock knowledge hash changed: {profile}")

    evaluation = lock.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ValueError("benchmark lock evaluation section is missing")
    if evaluation.get("quality_signal") != "human-pairwise":
        raise ValueError("benchmark lock quality signal changed")
    if evaluation.get("reviewer_labels") != list(REVIEWER_LABELS):
        raise ValueError("benchmark lock reviewer labels changed")
    if evaluation.get("evidence_is_quality_judgment") is not False or evaluation.get("diagnostic_screenshots_are_proof") is not False:
        raise ValueError("benchmark lock evidence semantics changed")
    artifacts = evaluation.get("artifacts")
    if not isinstance(artifacts, list) or [entry.get("path") for entry in artifacts] != list(LOCKED_EVALUATORS):
        raise ValueError("benchmark lock evaluator surface changed")
    for artifact in artifacts:
        _validate_artifact(root, artifact, "evaluator")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-manifest", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    suite = json.loads(args.suite_manifest.read_text(encoding="utf-8"))
    lock = build_benchmark_lock(suite, repo_root=args.repo_root)
    validate_benchmark_lock(lock, repo_root=args.repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": lock["sha256"], "task_count": lock["suite"]["task_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
