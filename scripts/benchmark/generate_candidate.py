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

# Grounded API cheat-sheet for generated code (see task 1 research:
# Roblox/open-game-eval and imezx/luau-bench both constrain the API surface
# to keep mid/small models from crashing on subtle engine rules).
API_CHEAT_SHEET = """ROBLOX API RULES THAT BREAK GENERATED CODE (memorize these):

1. ParticleEmitter.Attachment0 is READ-ONLY. You CANNOT assign it directly.
   Instead: parent the ParticleEmitter to the Attachment (or a part with an
   Attachment child), or set emitter.Attachment to an Attachment instance.
   Correct pattern:
     local attach = Instance.new("Attachment"); attach.Parent = part
     local emitter = Instance.new("ParticleEmitter")
     emitter.Parent = attach                -- NOT emitter.Attachment0 = attach

2. Terrain:FillBlock is fragile and can silently no-op or error. Prefer
   building scene geometry from Parts (Anchored = true). If you must use
   terrain, call it with a Material enum and a valid region, treat its return
   as a BasePart, and set properties on the RETURNED part, not the terrain.

3. Only use these engine classes unless the fixture explicitly asks for more:
   Model, Part, BasePart, Attachment, ParticleEmitter, PointLight,
   SurfaceLight, Decal, UnionOperation, Script, LocalScript, ModuleScript,
   Folder, StringValue, NumberValue, BoolValue, CFrame, Vector3, Color3,
   BrickColor, NumberRange, NumberSequence, ColorSequence, Enum.*, math.*.
   Avoid: Terrain, Lighting FX (Bloom/Blur/DepthOfField), tween service,
   rays, sounds, Humanoid/Rig/Character manipulation.

4. Every Part you create should set: Size (Vector3), CFrame or Position,
   Anchored = true (unless you want physics), Material, and optionally
   Color/BrickColor. Never leave a part at default size in the scene.

5. Instance.new("Model") then set .Name, .Parent = workspace. Name is what
   the evaluator searches for. Match component names EXACTLY as the prompt
   lists them.

6. Do not call workspace.CurrentCamera in setup() unless needed; camera
   setup is the evaluator's job. If you do set it, use
   camera.CameraType = Enum.CameraType.Scriptable then camera.CFrame.
"""


def system_prompt_with_cheatsheet() -> str:
    return SYSTEM_PROMPT + "\n\n" + API_CHEAT_SHEET


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


def call_model(api_key: str, model_id: str, prompt: str, max_tokens: int, extra_system: str = "") -> tuple[str, dict[str, Any]]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    started = time.monotonic()
    completion = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_prompt_with_cheatsheet() + (("\n\n" + extra_system) if extra_system else "")},
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


def repair_prompt(fixture, original_source: str, error_text: str) -> tuple[str, str]:
    """Build a repair prompt: original task + the exact runtime error + the
    broken source. Returns (user_prompt, extra_system_section)."""
    user_prompt = make_prompt(fixture) + f"""

--- REPAIR REQUEST ---

The candidate source below failed to run in Roblox Studio. The evaluator
returned this exact runtime error:

{error_text.strip()[:1500]}

Fix the source so it runs without error and still satisfies the contract.
Common causes (check these first): assigning a read-only property (like
ParticleEmitter.Attachment0), misusing Terrain/FillBlock, wrong property
names, or camera/lighting service misuse.

Here is the previous candidate source (fix it, do not drop its components):

```lua
{original_source}
```

Return the COMPLETE corrected Luau source in a single ```lua block.
"""
    extra_system = (
        "You are repairing a BloxBench candidate that crashed at runtime. "
        "Keep the candidate's intended scene intact. Fix ONLY the runtime error "
        "using the API rules provided. Return the full corrected source."
    )
    return user_prompt, extra_system


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--model", choices=sorted(MODELS), default="flash")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--no-run", action="store_true", help="parse fixture and print the prompt only")
    parser.add_argument(
        "--repair-source",
        type=Path,
        help="previous candidate.luau to repair (enables repair mode)",
    )
    parser.add_argument(
        "--repair-error",
        type=str,
        default="",
        help="exact runtime error text from the failed run (repair mode)",
    )
    args = parser.parse_args(argv)

    api_key = os.environ.get("HYPER_API_KEY")
    if not api_key and not args.no_run:
        raise SystemExit("HYPER_API_KEY must be in the environment (never written to artifacts)")
    assert isinstance(api_key, str) or args.no_run
    api_key_str = api_key or ""

    fixture = parse_fixture(args.fixture)

    repair_mode = args.repair_source is not None
    if repair_mode and not args.repair_error:
        raise SystemExit("--repair-source requires --repair-error (the runtime error text)")

    original = ""
    if repair_mode:
        original = args.repair_source.read_text(encoding="utf-8")
        prompt, extra_system = repair_prompt(fixture, original, args.repair_error)
    else:
        prompt = make_prompt(fixture)
        extra_system = ""

    arm_dir = args.output_root / fixture.fixture_id.replace(".", "_") / f"arm-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    arm_dir.mkdir(parents=True, exist_ok=True)
    (arm_dir / "generation").mkdir(parents=True, exist_ok=True)
    (arm_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    if args.no_run:
        print(json.dumps({"arm_dir": str(arm_dir), "prompt": prompt}, indent=2))
        return 0

    model_id = MODELS[args.model]["id"]
    raw, meta = call_model(api_key_str, model_id, prompt, MODELS[args.model]["max_tokens"], extra_system=extra_system)
    source_text = extract_lua(raw)

    if not source_text:
        raise SystemExit(f"model returned no usable source. raw response: {raw[:200]!r}")

    if repair_mode:
        source_path = arm_dir / "source" / "candidate.repaired.luau"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(source_text, encoding="utf-8")
        manifest_path = write_manifest(arm_dir, fixture, args.model, meta, source_text)
        repair_manifest = {
            "schema": "bloxbench-repair-v1",
            "repaired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": MODELS[args.model]["id"],
            "fixture": fixture.fixture_id,
            "original_source": str(args.repair_source),
            "original_source_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
            "error_text": args.repair_error[:1500],
            "repair_manifest": str(manifest_path),
        }
        repair_path = arm_dir / "repair" / "manifest.json"
        repair_path.parent.mkdir(parents=True, exist_ok=True)
        repair_path.write_text(json.dumps(repair_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        source_path = arm_dir / "source" / "candidate.luau"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(source_text, encoding="utf-8")
        manifest_path = write_manifest(arm_dir, fixture, args.model, meta, source_text)
        repair_path = None

    print(
        json.dumps(
            {
                "arm_dir": str(arm_dir),
                "source": str(source_path),
                "source_bytes": source_path.stat().st_size,
                "generation_manifest": str(manifest_path),
                "repair_manifest": str(repair_path) if repair_path else None,
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
