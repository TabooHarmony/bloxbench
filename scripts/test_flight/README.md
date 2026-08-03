# qualification runner

This directory contains the parent-owned, unscored BloxBench qualification runner.

It checks the boundary from pinned Pi source generation through the RSC bridge, Roblox Studio execution, nested Luau validation, screenshot capture, cleanup, and artifact provenance. The current calibration path uses the file-backed dirt-bike prompt at `scripts/test_flight/calibration_prompt.txt`; it is independent of the benchmark fixture set.

The canonical benchmark path remains fixture prompt → subagent → RSC → Studio → screenshots → human pairwise review. This runner is for transport and stability qualification, not ranking or judging.

Local checks:

```bash
python3 -m unittest scripts.test_flight.test_harness
PYTHONPATH=/root/roblox-studio-control/src \
  python3 -m unittest scripts.test_flight.test_rsc_bridge
```