# BloxBench-EXP Active Plan

This file contains only active work. The historical 23-question design record is preserved at [`docs/archive/design-grill-plan.md`](docs/archive/design-grill-plan.md).

## goal

Close the PartPrimitives experiment with an evidence-backed verdict, then choose whether to test a decomposition/model intervention or pause Roblox construction work.

## current status

- primitive source patch applied for wall openings, roof seating, limb orientation, and explicit limb origin faces
- structural dump now emits flags before the capped part listing
- run metadata records the actual experiment configuration
- primitive usage instrumentation is verified
- legacy helper and fixer files are separated under `legacy/`
- post-patch local validation passed
- dragon usage and anchor follow-up runs completed, but neither passed visual/structural review

## next sequence

1. preserve and index the dragon diagnostic and follow-up artifacts
2. record the matched vanilla control, cottage replicate, and failed architecture smoke
3. mark `PartPrimitives` as a rejected benchmark intervention
4. do not run the full 10-building primitive experiment or more primitive smoke tests
5. choose a decomposition/model intervention or pause the construction benchmark

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
