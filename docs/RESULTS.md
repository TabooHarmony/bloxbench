# Results and Artifact Policy

## canonical locations

Benchmark output is operator data, not source:

```text
results/                 eval output (screenshots, logs)
```

This path is ignored by git. Do not commit screenshots, result JSON, or API responses.

## preserving a run

For a run worth keeping:

1. keep screenshots, result metadata, and relevant logs together under `results/<run_id>/`
2. record the configuration (model, fixture, transport) alongside the artifacts

## review

1. confirm the run configuration matches the comparison target
2. inspect screenshots manually
3. pairwise vote: A better, B better, tie, both bad

A successful process exit is not construction quality. Screenshots are the evidence.
