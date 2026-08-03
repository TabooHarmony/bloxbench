#!/usr/bin/env python3
"""Generate one model-backed candidate for a BloxBench fixture.

Calls Charm Hyper (OpenAI-compatible) directly with HYPER_API_KEY:

  fixture prompt -> model -> candidate.luau + generation/manifest.json

The runner's review path consumes the generation directory with
`--generation-dir`, which turns the run into a true model evaluation.

Usage:
  HYPER_API_KEY=... python -m scripts.benchmark.generate_candidate \
      --fixture Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua \
      --model flash --output-root results/generated
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark.fixture_contract import parse_fixture  # noqa: E402

DEFAULT_OUTPUT_ROOT = ROOT / "results" / "generated"
BASE_URL = "https://hyper.charm.land/v1"
MODELS = {
    "flash": {"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash", "max_tokens": 8192},
    "pro": {"id": "deepseek-v4-pro", "name": "DeepSeek V4 Pro", "max_tokens": 16384},
}

SYSTEM_PROMPT = (
    "You are a focused Roblox Luau source generator. "
    "Produce ONLY the complete Luau source in a single ```lua code block. "
    "No commentary outside the block."
)


def make_prompt(fixture) -> str:
    rubric_lines = [f"- {key}: {value}" for key, value in fixture.rubric.items()]
    rubric = "\n".join(rubric_lines) or "none"
    return f"""You are generating Roblox Luau source for a benchmark fixture.

Scenario: {fixture.scenario_name}

The evaluator will load your source as a ModuleScript and call these hooks
when present: {", ".join(fixture.hooks) or "none"}.

The final build must follow this contract:
- create exactly one top-level Model named `BloxBenchCandidate` in workspace;
- honor the fixture's semantic components and states;
- report runtime facts through BloxBenchState / BloxBenchRuntime attributes
  or folders so the evaluator can read them back;
- use only supported Roblox classes and enums.

Here is the full user prompt from the fixture:

{fixture.prompt}

Rubric (for your own reference on what reviewers weight):
{rubric}

Write the complete Luau source and nothing else.
"""


def extract_lua(text: str) -> str:
    """Pull the first fenced ```lua block out of a model response."""
    marker = "```lua"
    start = text.find(marker)
    if start == -1:
        marker = "```"
        start = text.find(marker)
    if start == -1:
        return text.strip()
    start += len(marker)
    end = text.find("```", start)
    if end == -1:
        return text[start:].strip()
    return text[start:end].strip()


def call_model(api_key: str, model_id: str, prompt: str, max_tokens: int) -> tuple[str, dict[str, Any]]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    started = time.monotonic()
    completion = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
    )
    elapsed = round(time.monotonic() - started, 3)
    text = (completion.choices[0].message.content or "").strip()
    raw_usage = completion.usage
    usage = {
        "input_tokens": raw_usage.prompt_tokens if raw_usage else 0,
        "output_tokens": raw_usage.completion_tokens if raw_usage else 0,
        "total_tokens": raw_usage.total_tokens if raw_usage else 0,
    }
    meta = {
        "model": model_id,
        "elapsed_seconds": elapsed,
        "usage": usage,
        "finish_reason": completion.choices[0].finish_reason,
    }
    return text, meta


def write_manifest(arm_dir: Path, fixture, model_id: str, meta: dict[str, Any], source_text: str) -> Path:
    manifest = {
        "schema": "bloxbench-generation-v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": MODELS[model_id]["id"],
        "model_name": MODELS[model_id]["name"],
        "provider": "charm-hyper",
        "provider_id": "charm-hyper",
        "base_url": BASE_URL,
        "fixture": fixture.fixture_id,
        "prompt_sha256": hashlib.sha256(fixture.prompt.encode("utf-8")).hexdigest(),
        "is_model_evaluation": True,
        "usage": meta.get("usage", {}),
        "elapsed_seconds": meta.get("elapsed_seconds"),
        "finish_reason": meta.get("finish_reason"),
        "source_bytes": len(source_text.encode("utf-8")),
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
    }
    manifest_path = arm_dir / "generation" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--model", choices=sorted(MODELS), default="flash")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--no-run", action="store_true", help="parse fixture and print the prompt only")
    args = parser.parse_args(argv)

    api_key = os.environ.get("HYPER_API_KEY")
    if not api_key and not args.no_run:
        raise SystemExit("HYPER_API_KEY must be in the environment (never written to artifacts)")
    assert api_key or args.no_run

    fixture = parse_fixture(args.fixture)
    prompt = make_prompt(fixture)

    arm_dir = args.output_root / fixture.fixture_id.replace(".", "_") / f"arm-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    arm_dir.mkdir(parents=True, exist_ok=True)
    (arm_dir / "generation").mkdir(parents=True, exist_ok=True)
    (arm_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    if args.no_run:
        print(json.dumps({"arm_dir": str(arm_dir), "prompt": prompt}, indent=2))
        return 0

    model_id = MODELS[args.model]["id"]
    raw, meta = call_model(api_key, model_id, prompt, MODELS[args.model]["max_tokens"])
    source_text = extract_lua(raw)

    if not source_text:
        raise SystemExit(f"model returned no usable source. raw response: {raw[:200]!r}")

    source_path = arm_dir / "source" / "candidate.luau"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source_text, encoding="utf-8")
    manifest_path = write_manifest(arm_dir, fixture, args.model, meta, source_text)

    print(
        json.dumps(
            {
                "arm_dir": str(arm_dir),
                "source": str(source_path),
                "source_bytes": source_path.stat().st_size,
                "generation_manifest": str(manifest_path),
                "succeeded": True,
                "meta": meta,
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
