# PartPrimitives Experiment

## status

active. This is the next arm after the rejected helpers, fixer, and solver experiments.

## hypothesis

A small composition API can improve decomposition and connected placement by making common structures explicit: walls with openings, pitched roofs, limbs, stacks, and primitive parts.

## current implementation

`PartPrimitives.lua` is uploaded in `--primitives` mode. Recent fixes cover:

- real rectangular window gaps, including door plus window combinations
- roof placement from the support top plane
- orientation-independent limb segment alignment
- primitive calls counted as edits
- structural flags placed before the capped structure listing

## old evidence

Earlier primitive runs were not sufficient validation:

- bridge: 19 rounds, approximately 313K input tokens, 8 floating parts, 136 overlaps
- dragon: 5 rounds, approximately 80K input tokens, 56 parts, 3 floating parts, 73 overlaps

Those numbers came before the current geometry and measurement fixes. They should not be used as a success claim.

## smoke result: `primitives_0709_1321`

The infrastructure path completed both evals with screenshots and incremental results. The aggregate `100%` is not a quality pass because the run used `--no-gate` and the harness marked both evals `passed_cons: false` and `passed_all: false`.

- cottage: 23 rounds, 500,635 input tokens, 10 edits, 85 parts, 11 floating parts, 41 overlaps. The exterior is recognizable and the wall openings, door, porch, and windows are visible. The roof is boxy and several fascia, sill, handle, and chimney pieces are structurally flagged as floating. One eval exhausted the 500K budget.
- dragon: 11 rounds, 198,057 input tokens, 8 edits, 85 parts, 7 floating parts, 88 overlaps. The pedestal is grounded, but the head is visibly detached above the body and several limb, tail, wing, pillar, and flame pieces are disconnected. The dark material/lighting makes the anatomy difficult to judge.

No visual judge ran. Human screenshot review is the current verdict: execution succeeded, but this smoke does not justify the full ten-eval run.

## next run

Do a narrow follow-up before the full benchmark:

1. verify from the tool trace whether the model actually used `P.limb` and other `P.*` constructors
2. inspect the primitive API prompt and the dragon composition instructions for parent-chain ambiguity
3. rerun only dragon after the smallest demonstrated fix

Do not run all ten building evals until the dragon head and limb-chain failure is understood.
