# BloxBench Project State

## Identity

BloxBench is a construction benchmark for Roblox Studio. It tests whether an agent can build Roblox UI and 3D structures from prompts. The benchmark captures screenshots, structure dumps, functional gates, and visual judge scores.

Current shape:
- 5 UI construction evals under `Evals/UI/` (tagged with `--track ui`)
- 10 building construction evals under `Evals/Building/`
- 3 RepairCore qualification fixtures under `Evals/RepairCore/`
- Visual judge with validation and provenance tracking
- UI visual track with separate functional/visual/combined scoring
- Style extraction for project-local UI references

The spatial intervention research (relation context, primitives, helpers, fixer, solver, actor/verifier, compile-once, repair contracts) is frozen. The fine-tuning pilot is in a separate repository at `/root/partwise-trainer/`.

## Current Code State

Recent work added:
- Judge response validation with score key matching and integer range checks
- Evidence provenance with SHA-256 hashes for prompt, rubric, screenshots, structure dump
- UI visual track (`ui_track.py`) separating functional passes, conditional visual passes, and confirmed combined rate with evidence bounds
- Style extraction (`style_extraction.py`) for conservative regex-based token extraction from reference Lua files
- RepairCore qualification fixtures with deterministic gates
- Report generation for UI track dimensions and comparison tables

All tests pass (24 in bloxbench, 82 in partwise-trainer).

## Source Map

- `harness.py`: orchestration, tool loop, gates, screenshots, structure dump, result persistence
- `judge.py`: visual judge with validation and provenance
- `ui_track.py`: UI visual track scoring helpers
- `style_extraction.py`: project-local UI reference token extraction
- `generate_report.py`: text reports with UI track support
- `gen_results_html.py`: local HTML comparison viewer
- `Evals/UI/`: five UI evals (tagged `@track ui`)
- `Evals/Building/`: ten building evals
- `Evals/RepairCore/`: three repair qualification fixtures
- `Reference/`: hand-built judge and gate calibration places/scripts
- `legacy/`: rejected helpers, fixer, and their old experiment launchers
- `scripts/windev/`: operator-facing Windows scripts
- `docs/experiments/`: arm-specific evidence and verdicts
- `research/`: frozen spatial relation pilot data

## Known Environment Hazards

- Studio authentication can expire; use RDP to re-authenticate
- Stale StudioMCP processes can poison the MCP TCP connection
- Force-killing Roblox Studio can damage WebView2 cookies and log the account out
- The Studio MCP setup uses one persistent ClientSession
- Standalone Luau analysis lacks Roblox engine type definitions
- Never record API keys, cookies, or connection strings in results, docs, or commits

## Artifact Policy

- `results/`: local harness output
- `results_pull/`: canonical local staging for pulled historical runs
- `results.html`, `_serve/`, and `review.html`: generated local viewers
- `/tmp/`: scratch only, never the authoritative result location

All of these are ignored by git. Preserve an important run by copying it into `results_pull/<run_id>/` and adding a short entry to `docs/experiments/runs.md`.

## Next Work

The experience/gameplay vertical slice category design is open. The previous session rejected all proposals as not matching real 2026 Roblox games. The next session should ask the user for specific reference games or gameplay footage before proposing new slices.
