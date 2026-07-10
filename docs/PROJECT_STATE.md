# BloxBench-EXP Project State

## identity

This is a private, experimental operator branch of BloxBench. Upstream is parked. The repository is optimized for one operator running controlled Roblox Studio experiments, not for public onboarding.

No active construction intervention is approved. `PartPrimitives.lua` is preserved as a rejected experiment. The matched cottage replicate was a useful but expensive positive signal; the follow-up architecture smoke failed to generalize. Further work should target decomposition/model behavior directly, or pause the construction benchmark.

The last attempted architecture smoke used:

- `VB_BUILD_001_cozy_cottage`
- `VB_BUILD_003_watchtower`
- `VB_BUILD_006_market_stall`

The operator script remains under `scripts/windev/` for historical reproduction only.

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
- `P.limb` accepts explicit origin-face anchors for top, bottom, left, right, front, and back attachments
- structural flags appear before the capped structure listing
- run manifests record the experiment configuration
- primitive constructor calls count as edits

Local syntax checks passed. The zero-token calibration verified exact primitive anchor joins. The clean dragon run had no model errors and no duplicate primitive names but remained visually unacceptable. A matched cottage control showed one promising primitive result, with fewer parts and overlaps and a clearer screenshot, but at substantially higher token cost. The follow-up three-eval architecture smoke then hit the token budget on cottage and produced unreadable watchtower and market stall results. `PartPrimitives` is rejected as a benchmark intervention.

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

Do not start the full ten-building experiment with `PartPrimitives`, and do not run more primitive smoke tests. Preserve the negative result and pivot to a different decomposition/model intervention, or pause the construction benchmark.
