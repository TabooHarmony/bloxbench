# BloxBench-EXP Active Plan

This file contains only active work. The historical 23-question design record is preserved at [`docs/archive/design-grill-plan.md`](docs/archive/design-grill-plan.md).

## goal

Measure whether the small `PartPrimitives` API improves connected Roblox construction without confusing the model or hiding failures behind the harness.

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
2. add primitive-link awareness to the structural report without changing the existing generic metrics
3. decide whether to stop the primitive arm or define one narrower construction test
4. run the controlled 10-building primitive experiment only after a focused visual/structural pass succeeds
5. review screenshots manually before comparing against vanilla

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
