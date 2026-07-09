# Windows Studio Operator Runbook

## host assumptions

The Roblox Studio host is the Windows development VM. Studio authentication may require RDP. The MCP adapter uses one persistent ClientSession.

Before a run:

- confirm Studio is authenticated
- confirm the active Studio instance is the intended place
- confirm the baseplate and MCP launcher paths
- remove a stale `.rbxl.lock` only when Studio is fully stopped
- avoid force-killing Roblox Studio unless the normal close path failed, because WebView2 cookies can be lost

## targeted primitive smoke

Run from the Windows checkout:

```text
scripts\windev\smoke_test.bat
```

The script runs `VB_BUILD_001_cozy_cottage` and `VB_BUILD_010_dragon_statue` with `--primitives`, screenshots, `--no-gate`, a 45-second startup wait, a 25-round limit, and a 500,000 input-token cap per eval.

The script contains machine-specific placeholders for the Studio executable and MCP launcher. Update those locally on the VM, never in a public or shared commit.

## after the run

Copy important output into the local canonical staging directory:

```text
results_pull/<run_id>/
```

Then inspect:

- final and alternate screenshots
- `results.json`
- `run_manifest.json`
- floating and overlap flags
- edit count and round count
- whether the model actually used `P.*`

Record the verdict in `docs/experiments/partprimitives.md` and add the run to `docs/experiments/runs.md`.
