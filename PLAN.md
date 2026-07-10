# BloxBench-EXP Active Plan

This file contains only active work. The historical 23-question design record is preserved at [`docs/archive/design-grill-plan.md`](docs/archive/design-grill-plan.md).

## goal

Close the rejected construction interventions, then use repair-first spatial experiments to discover tools that improve a baseline model's scene understanding without hiding geometry creation behind a builder API.

## current status

- primitive source patch applied for wall openings, roof seating, limb orientation, and explicit limb origin faces
- structural dump now emits flags before the capped part listing
- run metadata records the actual experiment configuration
- primitive usage instrumentation is verified
- legacy helper and fixer files are separated under `legacy/`
- post-patch local validation passed
- dragon usage and anchor follow-up runs completed, but neither passed visual/structural review
- the spatial observability prototype improved the main repair assembly, but generic component linting did not guarantee visually valid attachments
- the strict-tolerance lint variant increased churn and exceeded the token cap
- the targeted relation-oracle follow-up was not adopted, exceeded the token cap, and regressed visually
- automatic post-edit feedback reduced rounds and tokens but produced a visually worse early stop
- the cheap MiniMax M3 comparison inspected the scene but made zero edits
- the corrected focused actor/verifier roof repair beat its vanilla control, but the verifier exhausted its read-only rounds without producing a report
- the matched two-defect follow-up produced the same physically incomplete artifact as vanilla at substantially higher cost; Spatial is not promoted
- compile-once/repair matched the current vanilla control with fewer tokens and edits, but did not clearly improve final visual quality

## next sequence

1. preserve and index the dragon diagnostic and follow-up artifacts
2. record the matched vanilla control, cottage replicate, and failed architecture smoke
3. record the matched protocol run and its failed replicate
4. preserve the spatial observability repair prototype and its matched evidence
5. retain compile-once/repair as a bounded execution mode, not a quality intervention
6. next test task representation or model/data improvements, not another verifier, linter, or feedback variant

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
