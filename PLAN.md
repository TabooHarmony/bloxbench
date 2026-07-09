# BloxBench-EXP Active Plan

This file contains only active work. The historical 23-question design record is preserved at [`docs/archive/design-grill-plan.md`](docs/archive/design-grill-plan.md).

## goal

Measure whether the small `PartPrimitives` API improves connected Roblox construction without confusing the model or hiding failures behind the harness.

## current status

- primitive source patch applied for wall openings, roof seating, and limb orientation
- structural dump now emits flags before the capped part listing
- run metadata records the actual experiment configuration
- legacy helper and fixer files are separated under `legacy/`
- post-patch local validation is still pending
- no post-patch Studio smoke run has been executed

## next sequence

1. run local syntax and diff checks
2. run the targeted cottage + dragon primitive smoke test
3. inspect screenshots, structural flags, edit counts, and run metadata
4. fix only issues demonstrated by that smoke run
5. run the controlled 10-building primitive experiment
6. review screenshots manually before comparing against vanilla
7. decide whether to keep primitives v1, revise the API, or stop the arm

## active constraints

- preserve vanilla versus primitives comparability
- use the same model, eval set, round limit, token cap, temperature, and screenshot policy across arms
- keep `--no-gate` completion separate from build quality
- do not revive helpers, fixer, or the old solver as the next intervention
- keep generated runs and screenshots out of git
- keep credentials in local environment configuration only

## not active

- pairwise judge comparison
- Elo scoring
- automated structural repair
- visual-feedback loops
- fine-tuning from successful traces
- broad benchmark redesign

## useful files

- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/RUNBOOK_LOCAL.md`](docs/RUNBOOK_LOCAL.md)
- [`docs/RUNBOOK_WINDEV.md`](docs/RUNBOOK_WINDEV.md)
- [`docs/RESULTS.md`](docs/RESULTS.md)
- [`docs/experiments/partprimitives.md`](docs/experiments/partprimitives.md)
