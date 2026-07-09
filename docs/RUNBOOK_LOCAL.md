# Local Operator Runbook

## before editing

```bash
cd /root/bloxbench
python3 harness.py --help
```

Keep `.env` local. Never paste API keys into commands, logs, screenshots, manifests, or documentation.

## local validation

Run these after source changes and before using the Windows Studio host:

```bash
python3 -m py_compile harness.py judge.py generate_report.py gen_results_html.py
luau PartPrimitives.lua
git diff --check
```

`luau-analyze` is not a clean project gate without Roblox engine type definitions. Unknown Roblox globals in standalone analysis are expected; syntax parsing is still useful.

## artifact review

For an existing run:

```bash
python3 generate_report.py results_pull/<run_id>/results.json
python3 gen_results_html.py
```

The HTML viewer is generated at `results.html` and is not committed.

## experiment discipline

- use one or two evals for a smoke run
- keep the model, temperature, token cap, and round limit explicit
- use `--no-gate` only when a human will review screenshots
- inspect `run_manifest.json`, `results.json`, `screenshots/`, and structural flags together
- do not start a full ten-building run to investigate a failure that a two-eval smoke can expose
