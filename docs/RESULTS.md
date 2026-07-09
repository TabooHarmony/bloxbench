# Results and Artifact Policy

## canonical locations

Benchmark output is operator data, not source:

```text
results/                 fresh harness output
results_pull/<run_id>/   canonical local staging for historical runs
results.html             generated comparison viewer
_serve/                  generated sharing directory
/tmp/                    scratch only
```

These paths are ignored by git. Do not commit screenshots, result JSON, HTML viewers, API responses, or temporary MCP output.

## preserving a run

For a run worth keeping:

1. copy the complete run directory into `results_pull/<run_id>/`
2. keep `results.json`, `run_manifest.json`, screenshots, and relevant logs together
3. add one short line to `docs/experiments/runs.md`
4. record the interpretation in the relevant experiment note

Do not preserve only the aggregate score. The screenshots and configuration are necessary to interpret it.

## review order

1. confirm the run configuration matches the comparison target
2. check whether the harness completed or failed
3. inspect screenshots manually
4. inspect structural flags as diagnostics
5. compare edit count, rounds, token use, and tool errors
6. only then consider judge scores

A `--no-gate` run that reaches the end is execution success, not construction success.

## sharing

The local viewer can be regenerated with:

```bash
python3 gen_results_html.py
```

If a local web share is needed, serve the generated viewer from the normal operator sharing path. Do not expose raw environment files or logs.
