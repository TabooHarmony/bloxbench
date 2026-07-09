# Historical Run Index

This is a compact index only. Full artifacts remain local under `results_pull/` or in the original scratch location until deliberately preserved.

## known runs

- `vanilla_0708_1743`: historical vanilla building comparison, artifacts under `results_pull/vanilla_0708_1743/`
- `helpers_0708_1817`: historical helpers v2 building comparison, artifacts under `results_pull/helpers_0708_1817/`
- `primitives_0708_2201`: historical primitive artifact at `/tmp/primitives_0708_2201.json`; preserve a complete run directory before treating it as canonical

## required entry format

For future runs, add:

```text
- <run_id>: <arm>, <model>, <eval set>, <date>; artifacts: results_pull/<run_id>/; verdict: pending
```

Use `verdict: pending` until screenshots have been reviewed. Use a short factual note, not a score-only conclusion.
