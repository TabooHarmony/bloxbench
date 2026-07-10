# BloxBench-EXP Project State

## identity

This is a private, experimental operator branch of BloxBench. Upstream is parked. The repository is optimized for one operator running controlled Roblox Studio experiments, not for public onboarding.

No active construction benchmark arm is approved. `PartPrimitives.lua` and the decomposition protocol are preserved as rejected experiments. A repair-first spatial observability prototype produced a useful but incomplete signal and is retained for tool research, not as a promoted arm.

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
- generic connected-component linting is not sufficient to guarantee visually convincing attachments
- automatic post-edit feedback is retained as an experimental harness feature but is not a quality intervention
- the one cheap alternate model comparison did not enter edit mode, so it is not evidence of model quality
- the repair-first spatial observability prototype is retained as a tool-research direction, not an approved benchmark arm

## current code state

Recent primitive and harness patches have been applied. The important changes are:

- `P.wall` makes actual window gaps and can combine door and window openings
- pitched roofs use the support top plane as their base
- limb segments align their longest physical axis to the chain direction
- `P.limb` accepts explicit origin-face anchors for top, bottom, left, right, front, and back attachments
- structural flags appear before the capped structure listing
- run manifests record the experiment configuration
- `spatial_tools.py` provides the retained repair-first observation and intent prototype
- primitive constructor calls count as edits

Local syntax checks passed. The zero-token calibration verified exact primitive anchor joins. The clean dragon run had no model errors and no duplicate primitive names but remained visually unacceptable. A matched cottage control showed one promising primitive result, with fewer parts and overlaps and a clearer screenshot, but at substantially higher token cost. The follow-up three-eval architecture smoke then hit the token budget on cottage and produced unreadable watchtower and market stall results. `PartPrimitives` is rejected as a benchmark intervention.

## source map

- `harness.py`: orchestration, tool loop, gates, screenshots, structure dump, result persistence
- `judge.py`: visual judge request and response parsing
- `PartPrimitives.lua`: rejected primitive module retained for reproduction
- `spatial_tools.py`: repair-first observation and intent prototype
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

The spatial observability prototype is retained as historical positive evidence, but relation checking and automatic post-edit feedback did not produce a visual win. The cheap alternate model comparison did not edit. Stop this construction-tool branch. Do not run more variants until there is a materially different hypothesis with a cheaper adoption path and an explicit visual success criterion.
