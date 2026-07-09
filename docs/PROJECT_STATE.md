# BloxBench-EXP Project State

## identity

This is a private, experimental operator branch of BloxBench. Upstream is parked. The repository is optimized for one operator running controlled Roblox Studio experiments, not for public onboarding.

## active arm

`PartPrimitives.lua` is the active intervention. It exposes a small inline API for connected walls, roofs, limbs, stacks, and primitive parts. The hypothesis is that explicit composition primitives reduce decomposition errors, especially floating or disconnected parts.

The next experiment is a two-eval smoke run:

- `VB_BUILD_001_cozy_cottage`: wall, roof, door/window composition
- `VB_BUILD_010_dragon_statue`: limb chain composition

The operator script is `scripts/windev/smoke_test.bat`.

## completed decisions

- helpers v2 is rejected as the next intervention because it increased cost and did not reduce floating geometry
- the structural fixer is rejected as the next intervention because visual review was worse on most reviewed evals
- the old solver is not the active path
- visual review outranks a completion percentage from a `--no-gate` run
- historical artifacts stay local and out of git
- legacy source remains available, but is separated under `legacy/`

## current code state

Recent primitive and harness patches have been applied. The important changes are:

- `P.wall` makes actual window gaps and can combine door and window openings
- pitched roofs use the support top plane as their base
- limb segments align their longest physical axis to the chain direction
- structural flags appear before the capped structure listing
- run manifests record the experiment configuration
- primitive constructor calls count as edits

Local syntax checks passed. The targeted Studio smoke `primitives_0709_1321` completed, but visual review found disconnected dragon geometry and several cottage floating-detail flags. The primitive patch is not experimentally validated as a benchmark improvement yet.

## source map

- `harness.py`: orchestration, tool loop, gates, screenshots, structure dump, result persistence
- `judge.py`: visual judge request and response parsing
- `PartPrimitives.lua`: active primitive module
- `Evals/UI/`: five UI evals
- `Evals/Building/`: ten building evals
- `Reference/`: hand-built judge and gate calibration places/scripts
- `legacy/`: rejected helpers, fixer, and their old experiment launchers
- `scripts/windev/`: operator-facing Windows scripts
- `docs/experiments/`: arm-specific evidence and verdicts

## known environment hazards

- Studio authentication can expire; use RDP to re-authenticate
- stale StudioMCP processes can poison the MCP TCP connection
- force-killing Roblox Studio can damage WebView2 cookies and log the account out
- the Studio MCP setup uses one persistent ClientSession
- standalone Luau analysis lacks Roblox engine type definitions
- never record API keys, cookies, or connection strings in results, docs, or commits

## artifact policy

- `results/`: local harness output
- `results_pull/`: canonical local staging for pulled historical runs
- `results.html`, `_serve/`, and `review.html`: generated local viewers
- `/tmp/`: scratch only, never the authoritative result location

All of these are ignored by git. Preserve an important run by copying it into `results_pull/<run_id>/` and adding a short entry to `docs/experiments/runs.md`.

## next verification

Inspect the dragon tool trace and primitive usage, then make only the smallest demonstrated fix. Rerun dragon before considering the full ten-building experiment. Keep the pulled smoke artifacts under `results_pull/primitives_0709_1321/`.
