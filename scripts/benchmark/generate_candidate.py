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
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark.fixture_contract import parse_fixture  # noqa: E402
from scripts.benchmark.suite_manifest import suite_reference  # noqa: E402

def _load_hyper_key_from_dotenv() -> str | None:
    "Try to load HYPER_API_KEY from a local .env without requiring the caller to export it."

    if os.environ.get("HYPER_API_KEY"):
        return os.environ["HYPER_API_KEY"]
    for candidate in (ROOT / ".env", pathlib.Path("/root/bloxbench/.env") if False else ROOT / ".env"):
        try:
            text = candidate.read_text(encoding="utf-8", errors="ignore")
        except FileNotFoundError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == "HYPER_API_KEY":
                value = value.strip().strip('"').strip("'")
                if value and value != "your-api-key-here":
                    return value
    # also try the canonical location even if ROOT differs
    try:
        text = pathlib.Path("/root/bloxbench/.env").read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == "HYPER_API_KEY":
                value = value.strip().strip('"').strip("'")
                if value and value != "your-api-key-here":
                    return value
    except FileNotFoundError:
        pass
    return None

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

# Kept as a compatibility fallback for callers that import this module directly.
# Generation runs load the versioned file under scripts/benchmark/knowledge/.
API_CHEAT_SHEET = """Use documented Roblox APIs and follow the task-specific contract. Runtime behavior belongs in executable Script or LocalScript source. This fallback does not prohibit UI, animation, VFX, audio, input, Humanoids, rigs, physics, services, or client/server code."""


KNOWLEDGE_ROOT = ROOT / "scripts" / "benchmark" / "knowledge"
DEFAULT_KNOWLEDGE_PROFILE = "roblox-core-v1"


def knowledge_profile_path(profile: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", profile):
        raise ValueError(f"invalid knowledge profile: {profile!r}")
    return KNOWLEDGE_ROOT / f"{profile}.txt"


def load_knowledge_profile(profile: str = DEFAULT_KNOWLEDGE_PROFILE) -> str:
    path = knowledge_profile_path(profile)
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"knowledge profile is not present: {path}") from exc


def system_prompt_with_cheatsheet(profile: str = DEFAULT_KNOWLEDGE_PROFILE) -> str:
    return SYSTEM_PROMPT + "\n\n" + load_knowledge_profile(profile)


def make_prompt(fixture) -> str:
    rubric_lines = [f"- {key}: {value}" for key, value in fixture.rubric.items()]
    rubric = "\n".join(rubric_lines) or "none"
    components = ", ".join(fixture.semantic_components)
    states_line = f"States: {', '.join(fixture.states)}" if fixture.states else "States: none (static scene)"
    runtime_line = f"Runtime: {fixture.runtime}" + (" (play — needs Script/LocalScript with BindableEvent commands)" if fixture.runtime == "play" else " (edit — static build)")
    return f"""You are generating Roblox Luau source for a benchmark fixture.

Scenario: {fixture.scenario_name}
{runtime_line}
Required semantic components (EXACT Instance names inside BloxBenchCandidate): {components}
{states_line}
The evaluator will load your source as a ModuleScript and call these hooks
when present: {", ".join(fixture.hooks) or "none"}.

The final build MUST:
- create exactly one top-level Model named `{fixture.candidate_root}` in workspace and put ALL components inside it;
- create an Instance for EVERY name in the required list above (Instance.new with the exact Name, not an Attribute);
- for play fixtures, set attributes exactly as the prompt specifies (BloxBenchState on the model, booleans on the BloxBenchRuntime folder, last_command on BloxBenchTrace) and handle commands in a Script/LocalScript Source — not only in setup;
- use only supported Roblox classes and enums.

Authoritative task prompt (follow this verbatim — it contains the exact attribute names, command strings, and envelope guidance):

{fixture.prompt}

Rubric (what human reviewers weight — not a machine gate):
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


def luau_syntax_errors(source: str) -> list[str]:
    """Validate Luau syntax locally with luau-compile. Returns error lines (empty = OK).

    A generated candidate that does not parse can never run in Studio, so
    catching it here (vs. a wasted live run) is a strict win. Falls back to
    [] on environments without luau-compile (best effort).
    """
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".luau", delete=False) as handle:
        handle.write(source)
        tmp_path = handle.name
    try:
        result = subprocess.run(
            ["luau-compile", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return []
    finally:
        import os

        os.unlink(tmp_path)
    if result.returncode == 0:
        return []
    return [line for line in (result.stderr or "").splitlines() if line.strip()]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_system_prompt(knowledge_profile: str, extra_system: str = "") -> str:
    base = system_prompt_with_cheatsheet(knowledge_profile)
    return base + (("\n\n" + extra_system) if extra_system else "")


def call_model(
    api_key: str,
    model_id: str,
    prompt: str,
    max_tokens: int,
    extra_system: str = "",
    knowledge_profile: str = DEFAULT_KNOWLEDGE_PROFILE,
) -> tuple[str, dict[str, Any]]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    system_prompt = build_system_prompt(knowledge_profile, extra_system)
    started = time.monotonic()
    completion = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_prompt},
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
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "system_prompt_sha256": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
        "knowledge_profile": knowledge_profile,
        "knowledge_sha256": hashlib.sha256(load_knowledge_profile(knowledge_profile).encode("utf-8")).hexdigest(),
    }
    return text, meta


def write_manifest(
    arm_dir: Path,
    fixture,
    model_id: str,
    meta: dict[str, Any],
    source_text: str,
    *,
    treatment: str,
    repair: dict[str, Any],
    suite: dict[str, str] | None = None,
) -> Path:
    manifest = {
        "schema": "bloxbench-generation-v2",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": MODELS[model_id]["id"],
        "model_name": MODELS[model_id]["name"],
        "provider": "charm-hyper",
        "provider_id": "charm-hyper",
        "base_url": BASE_URL,
        "generator": {
            "path": str(Path(__file__).resolve()),
            "sha256": file_sha256(Path(__file__).resolve()),
        },
        "tool_surface": {"protocol": "openai-chat-completions", "tools": []},
        "decoding": {
            "max_output_tokens": MODELS[model_id]["max_tokens"],
            "temperature": None,
            "top_p": None,
            "seed": None,
        },
        "prompt_order": ["system", "user"],
        "repair_policy": "explicit-source-error-repair" if repair.get("is_repaired") else "direct-only",
        "fixture": fixture.fixture_id,
        "fixture_sha256": fixture.sha256,
        "fixture_prompt_sha256": hashlib.sha256(fixture.prompt.encode("utf-8")).hexdigest(),
        "suite": suite,
        "prompt_sha256": meta.get("prompt_sha256"),
        "system_prompt_sha256": meta.get("system_prompt_sha256"),
        "knowledge_profile": meta.get("knowledge_profile", fixture.knowledge_profile),
        "knowledge_sha256": meta.get("knowledge_sha256"),
        "task_provenance": fixture.provenance,
        "prompt_path": "prompt.txt",
        "system_prompt_path": "system_prompt.txt",
        "treatment": treatment,
        "repair": repair,
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
    parser.add_argument("--suite-manifest", type=Path, help="locked suite manifest to verify and record")
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
    parser.add_argument(
        "--repair-attempt",
        type=int,
        default=1,
        help="1-based repair attempt number for provenance",
    )
    args = parser.parse_args(argv)

    api_key = _load_hyper_key_from_dotenv()
    if not api_key and not args.no_run:
        raise SystemExit("HYPER_API_KEY must be in the environment (never written to artifacts)")
    assert isinstance(api_key, str) or args.no_run
    api_key_str = api_key or ""

    fixture = parse_fixture(args.fixture)
    suite = suite_reference(args.suite_manifest, fixture.fixture_id, fixture.sha256) if args.suite_manifest else None

    repair_mode = args.repair_source is not None
    if repair_mode and not args.repair_error:
        raise SystemExit("--repair-source requires --repair-error (the runtime error text)")
    if args.repair_attempt < 1:
        raise SystemExit("--repair-attempt must be at least 1")

    original = ""
    if repair_mode:
        original = args.repair_source.read_text(encoding="utf-8")
        prompt, extra_system = repair_prompt(fixture, original, args.repair_error)
    else:
        prompt = make_prompt(fixture)
        extra_system = ""

    arm_dir = args.output_root / fixture.fixture_id.replace(".", "_") / f"arm-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    generation_dir = arm_dir / "generation"
    generation_dir.mkdir(parents=True, exist_ok=True)
    (generation_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    system_prompt = build_system_prompt(fixture.knowledge_profile, extra_system)
    (generation_dir / "system_prompt.txt").write_text(system_prompt, encoding="utf-8")

    if args.no_run:
        print(json.dumps({"arm_dir": str(arm_dir), "prompt": prompt, "suite": suite}, indent=2))
        return 0

    model_id = MODELS[args.model]["id"]
    raw, meta = call_model(
        api_key_str,
        model_id,
        prompt,
        MODELS[args.model]["max_tokens"],
        extra_system=extra_system,
        knowledge_profile=fixture.knowledge_profile,
    )
    source_text = extract_lua(raw)

    if not source_text:
        raise SystemExit(f"model returned no usable source. raw response: {raw[:200]!r}")

    syntax_errors = luau_syntax_errors(source_text)
    if syntax_errors:
        raise SystemExit(
            "model returned source that does not parse: "
            + "; ".join(syntax_errors[:4])
        )

    if repair_mode:
        source_path = arm_dir / "source" / "candidate.repaired.luau"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(source_text, encoding="utf-8")
        parent_source_sha256 = hashlib.sha256(original.encode("utf-8")).hexdigest()
        repair_info = {
            "is_repaired": True,
            "attempt": args.repair_attempt,
            "parent_arm_id": args.repair_source.parents[1].name if len(args.repair_source.parents) > 1 else None,
            "parent_source_path": str(args.repair_source),
            "parent_source_sha256": parent_source_sha256,
            "error_sha256": hashlib.sha256(args.repair_error.encode("utf-8")).hexdigest(),
        }
        manifest_path = write_manifest(
            arm_dir,
            fixture,
            args.model,
            meta,
            source_text,
            treatment="repaired",
            repair=repair_info,
            suite=suite,
        )
        repair_manifest = {
            "schema": "bloxbench-repair-v2",
            "repaired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": MODELS[args.model]["id"],
            "fixture": fixture.fixture_id,
            "suite": suite,
            "attempt": args.repair_attempt,
            "parent_arm_id": repair_info["parent_arm_id"],
            "original_source": str(args.repair_source),
            "original_source_sha256": parent_source_sha256,
            "error_sha256": repair_info["error_sha256"],
            "knowledge_profile": fixture.knowledge_profile,
            "knowledge_sha256": meta.get("knowledge_sha256"),
            "prompt_sha256": meta.get("prompt_sha256"),
            "system_prompt_sha256": meta.get("system_prompt_sha256"),
            "repair_manifest": str(manifest_path),
        }
        repair_path = arm_dir / "repair" / "manifest.json"
        repair_path.parent.mkdir(parents=True, exist_ok=True)
        repair_path.write_text(json.dumps(repair_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        source_path = arm_dir / "source" / "candidate.luau"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(source_text, encoding="utf-8")
        manifest_path = write_manifest(
            arm_dir,
            fixture,
            args.model,
            meta,
            source_text,
            treatment="direct",
            repair={"is_repaired": False, "attempt": 0},
            suite=suite,
        )
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
