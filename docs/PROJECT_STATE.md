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
- `P.limb` accepts explicit origin-face anchors for top, bottom, left, right, front, and back attachments
- structural flags appear before the capped structure listing
- run manifests record the experiment configuration
- primitive constructor calls count as edits

Local syntax checks passed. The clean dragon usage run `primitives_0709_1405` confirmed model-authored primitive adoption, but reported 15 floating parts and 33 overlaps. The origin-anchor follow-up `primitives_0709_1411` reduced floating parts to 12 but increased overlaps to 71, and its screenshots remained structurally cluttered and too dark for a quality pass. The zero-token calibration `anchor_calibration_0709_160219` verified exact top, bottom, side, and back face joins; the six horizontal floating flags were evaluator false positives. The instrumented run `primitives_0709_1608` exposed duplicate chain segments after two model tool errors. The final clean-model-error run `primitives_0709_1621` had no model errors and no duplicate primitive names, but remained visually unacceptable with 14 generic floating flags, 77 overlaps, and `passed_cons=false`. The primitive arm is rejected for the full benchmark, while the anchor implementation passed isolation testing.

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

Do not start the full ten-building experiment with `PartPrimitives`. The zero-token calibration passed, but the final clean-model-error dragon run remained visually unacceptable despite zero model tool errors and zero duplicate primitive names. Preserve the arm as a rejected, reproducible experiment. Return to the broader benchmark only with a different intervention or a materially different task decomposition strategy.
