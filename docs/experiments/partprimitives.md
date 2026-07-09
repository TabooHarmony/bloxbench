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

## next run

Use the targeted cottage and dragon smoke. Review screenshots first, then structural flags and model behavior. Do not run the full ten-building set until the smoke exposes no obvious primitive integration failure.
