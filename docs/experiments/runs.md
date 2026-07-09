# Historical Run Index

This is a compact index only. Full artifacts remain local under `results_pull/` or in the original scratch location until deliberately preserved.

## known runs

- `vanilla_0708_1743`: historical vanilla building comparison, artifacts under `results_pull/vanilla_0708_1743/`
- `helpers_0708_1817`: historical helpers v2 building comparison, artifacts under `results_pull/helpers_0708_1817/`
- `primitives_0708_2201`: historical primitive artifact at `/tmp/primitives_0708_2201.json`; preserve a complete run directory before treating it as canonical
- `primitives_0709_1321`: PartPrimitives smoke on cottage + dragon; artifacts: `results_pull/primitives_0709_1321/`; execution completed 2/2, visual review failed promotion to the full run
- `primitives_0709_1347`: dragon-only infrastructure failure; artifacts: `results_pull/primitives_0709_1347/`; no model construction
- `primitives_0709_1353`: repeated dragon-only infrastructure failure; artifacts: `results_pull/primitives_0709_1353/`; no model construction
- `primitives_0709_1402`: one-round diagnostic; artifacts: `results_pull/primitives_0709_1402/`; exposed the primitive trace regex bug, not benchmark data
- `primitives_0709_1405`: clean dragon-only usage run; artifacts: `results_pull/primitives_0709_1405/`; P usage confirmed, 15 floating parts, 33 overlaps, not promoted
- `primitives_0709_1411`: dragon-only origin-anchor follow-up; artifacts: `results_pull/primitives_0709_1411/`; 12 generic floating flags, 71 overlaps, not promoted
- `anchor_calibration_0709_160219`: zero-token deterministic anchor test; artifacts: `results_pull/anchor_calibration_0709_160219/`; exact top, bottom, side, and back joins verified; generic horizontal-floating flags identified as evaluator false positives

## required entry format

For future runs, add:

```text
- <run_id>: <arm>, <model>, <eval set>, <date>; artifacts: results_pull/<run_id>/; verdict: pending
```

Use `verdict: pending` until screenshots have been reviewed. Use a short factual note, not a score-only conclusion.
