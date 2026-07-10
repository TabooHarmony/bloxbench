# BloxBench-EXP

private operator-facing research branch of BloxBench. this branch is for testing Roblox Studio construction agents, not for upstream release.

## start here

1. read [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
2. use [`docs/RUNBOOK_LOCAL.md`](docs/RUNBOOK_LOCAL.md) for local checks
3. use [`docs/RUNBOOK_WINDEV.md`](docs/RUNBOOK_WINDEV.md) for Studio runs
4. record outcomes in [`docs/RESULTS.md`](docs/RESULTS.md) and the relevant experiment note

## purpose

BloxBench-EXP tests whether an LLM can construct Roblox UIs and 3D structures from an empty place. The harness drives Roblox Studio through MCP, captures structural and visual evidence, and can send screenshots to an OpenAI-compatible vision judge.

The primitive-composition hypothesis is now closed. `PartPrimitives.lua` remains in the repository for historical reproduction, but the intervention was rejected after calibration, matched control, dragon, cottage, watchtower, and market-stall evidence. The observed bottleneck remains model decomposition and parent-connected composition.

## current benchmark shape

- 5 UI construction evals under `Evals/UI/`
- 10 building construction evals under `Evals/Building/`
- one empty baseplate at `Places/baseplate.rbxl`
- reference implementations under `Reference/`
- pass@1 is the normal first-run setting
- `--no-gate` means a human reviews the result, not that the build passed

## repository map

```text
harness.py              benchmark runner and Studio orchestration
judge.py                OpenAI-compatible visual judge integration
generate_report.py      text reports for completed runs
gen_results_html.py     local HTML comparison viewer
PartPrimitives.lua      rejected primitive composition module, retained for reproduction
protocols/              model-side intervention prompts
Evals/                  UI and building prompts/checks
Reference/              hand-built calibration solutions
Places/                 base places used by evals
legacy/                 rejected helpers and fixer implementations
scripts/windev/         operator scripts for the Windows Studio host
docs/                   current state, runbooks, architecture, and experiment notes
```

Generated runs and screenshots are local operator data. They are intentionally ignored by git. See [`docs/RESULTS.md`](docs/RESULTS.md).

## operator quickstart

Set up the local environment without putting credentials in the repository:

```bash
cp .env.example .env
# edit .env locally
python3 harness.py --help
```

The current construction benchmark is paused. The plain-text decomposition protocol was tested on matched cottage and watchtower runs, looked promising once, then failed cleanly on replication. Do not promote it from lower token or part counts.

The historical protocol runners remain under `scripts/windev/` for reproduction only.

For a direct harness invocation, supply the Studio executable, MCP launcher, model, and any judge settings explicitly. Never commit those values.

## modes

- vanilla: no helper, primitive, or protocol injection
- protocol: historical model-side decomposition experiment, rejected after replication
- primitives: historical `PartPrimitives.lua` experiment, not an active arm
- helpers: legacy experiment using `legacy/SpatialHelpers.lua`
- fixer: legacy post-processing experiment using `legacy/StructuralFixer.lua`
- solver: external legacy solver path, if explicitly configured
- skills: roblox-brain skill injection, a separate benchmark condition

Do not compare scores across modes unless the run manifest shows matching model, eval set, round limit, token cap, gate policy, temperature, and screenshot settings.

## quality rules

- human screenshot review is authoritative for `--no-gate` experiments
- structural counts are diagnostic, not a visual score
- keep historical run artifacts outside git
- preserve rejected experiments as documented legacy material, not as active recommendations
- do not push or publish this private branch without explicit approval

## deeper documentation

- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md): compact current truth
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): execution and data flow
- [`docs/RUNBOOK_LOCAL.md`](docs/RUNBOOK_LOCAL.md): local validation and preparation
- [`docs/RUNBOOK_WINDEV.md`](docs/RUNBOOK_WINDEV.md): Windows Studio operations
- [`docs/RESULTS.md`](docs/RESULTS.md): artifact policy and review procedure
- [`docs/experiments/`](docs/experiments/): arm-by-arm decisions and evidence
- [`PLAN.md`](PLAN.md): active work only
- [`docs/archive/design-grill-plan.md`](docs/archive/design-grill-plan.md): historical design record
