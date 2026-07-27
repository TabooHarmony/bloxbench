# qualify the repair core before another model comparison

> **executor instructions:** read this entire plan before touching source. present the scope and approach to the operator, then wait for explicit approval. follow each step in order. do not improvise past a stop condition.
>
> this plan has two authorization boundaries:
>
> 1. source changes and local tests
> 2. the zero-token Roblox Studio qualification
>
> approval for source work does not authorize the Studio step. no step in this plan authorizes an llm/model benchmark run, commit, push, or pull request.

**goal:** produce three small repair tasks whose correct and incorrect states are unambiguous, and make future BloxBench artifacts honest about review status and source provenance.

**architecture:** keep the historical repair evals untouched. add a separate three-task repair core with direct, task-specific assertions. add one deterministic Studio qualification script that seeds each broken state, proves it fails, applies a known-good repair without an llm, proves it passes, and captures before/after evidence. update the existing result schema minimally so `--no-gate` means `review_required`, not `passed`.

**tech stack:** python 3.11, stdlib `unittest`, Luau eval modules, existing Roblox Studio MCP path, existing BloxBench harness.

## status

- priority: p1
- effort: medium
- risk: medium
- dependency: none
- category: benchmark stabilization
- planned at: commit `1c2a6ac`, 2026-07-10

## plain-language context

BloxBench currently records useful screenshots and geometry, but it is not ready to rank models. most building checks only count parts. runs using `--no-gate` are currently written as successful even though they have not been judged. the recent flag task also showed that a part can look attached in a screenshot while exact geometry says it is separated by a tiny gap.

this plan fixes the exam before testing another student. it does not improve the model, add Spatial machinery, or tune prompts.

## locked decisions

- BloxBench is the benchmark and evidence recorder.
- BloxBench-EXP is the private experimental repository, not a separate capability.
- Spatial is frozen historical work.
- the raw-Luau model remains the subject being measured.
- any asset-first Roblox product remains separate from this repository.
- no historical eval file may be rewritten because old artifacts lack source hashes.
- no new builder helper, verifier agent, linter, relation service, automatic feedback, judge prompt, or model prompt is allowed.
- exactly three repair-core tasks, no more.
- no model or llm call anywhere in qualification.

## drift check

run first from `/root/bloxbench`:

```bash
git diff --stat 1c2a6ac..HEAD -- harness.py Evals scripts/windev docs tests
```

expected at the planned commit: no output.

if there is output, inspect the changed files. stop if `EvalMetrics`, `aggregate_results`, manifest creation, eval parsing, or any repair eval convention changed in a way that invalidates this plan.

also run:

```bash
git status --short
```

expected before implementation: no source changes. an existing `.hermes/plans/` file is allowed.

## files in scope

modify:

- `harness.py`

create:

- `tests/test_harness_review_status.py`
- `tests/test_harness_provenance.py`
- `Evals/RepairCore/VB_CORE_REPAIR_001_single_part.lua`
- `Evals/RepairCore/VB_CORE_REPAIR_002_two_parts.lua`
- `Evals/RepairCore/VB_CORE_REPAIR_003_preserve_assembly.lua`
- `scripts/windev/repair_core_qualification.py`
- `scripts/windev/repair_core_qualification.bat`
- `docs/REPAIR_CORE.md`

files that are read-only and must not change:

- `Evals/Building/VB_REPAIR_001_watchtower.lua`
- `Evals/Building/VB_REPAIR_002_roof_attachment.lua`
- `Evals/Building/VB_REPAIR_003_roof_and_flag.lua`
- `spatial_tools.py`
- `judge.py`
- everything under `legacy/`
- every existing experiment note and historical artifact

## task 1: make `--no-gate` results honest

### objective

make an unjudged run machine-readable as `review_required`, without reporting it as a pass or failure.

### implementation

in `harness.py`, update `EvalMetrics` near lines 243-250:

```python
passed: bool = False
review_required: bool = False
scene_passed: Optional[bool] = None
game_passed: Optional[bool] = None
```

in the `run.no_gate` result block near lines 1863-1866, replace unconditional success with:

```python
if run.no_gate:
    m.review_required = True
    m.passed = False
else:
    m.passed = (m.scene_passed is True) and (m.game_passed is not False)
```

in `aggregate_results` near lines 2252-2291, add:

```python
review_required = sum(1 for r in results if r.review_required)
```

and include this in `summary`:

```python
"review_required": review_required,
"scored_evals": total - review_required,
```

calculate `pass_rate` over scored evals only. when every result requires review, `pass_rate` must be `None`, not `0` or `100`:

```python
scored = total - review_required
"pass_rate": round(passed / scored * 100, 2) if scored else None,
```

in the per-eval logger near lines 2667-2676, use three statuses:

```python
if result.review_required:
    status = "REVIEW"
else:
    status = "PASS" if result.passed else "FAIL"
```

in `print_summary` near lines 2745-2754, print `REVIEW REQUIRED` when `review_required > 0`. do not print a fake percentage when `pass_rate is None`.

### tests

create `tests/test_harness_review_status.py` with stdlib `unittest`. cover exactly these cases:

1. one passed scored result gives `passed=1`, `review_required=0`, `scored_evals=1`, `pass_rate=100.0`.
2. one failed scored result gives `passed=0`, `review_required=0`, `scored_evals=1`, `pass_rate=0.0`.
3. one unjudged result gives `passed=0`, `review_required=1`, `scored_evals=0`, `pass_rate=None`.
4. one passed plus one unjudged gives `passed=1`, `review_required=1`, `scored_evals=1`, `pass_rate=100.0`.

instantiate `EvalMetrics` directly and call `aggregate_results`; do not mock Studio or network code.

### verify

```bash
python3 -m unittest tests.test_harness_review_status -v
```

expected: four tests pass.

```bash
python3 -m py_compile harness.py
```

expected: exit 0, no output.

### stop conditions

stop if making `passed` honest requires changing historical JSON files or report generators. those are follow-up compatibility concerns, not permission to expand this patch.

## task 2: add immutable source provenance to new runs

### objective

make every future result identify the exact harness and eval source that produced it.

### implementation

in `harness.py`, import `hashlib`.

add two small module-level helpers near existing general helpers. do not add a class:

```python
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_source_provenance(repo_root: Path, harness_path: Path, eval_files: list[Path]) -> dict:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        commit = None
        dirty = None

    return {
        "git_commit": commit,
        "git_dirty": dirty,
        "harness_sha256": sha256_file(harness_path),
        "evals": {
            str(path.resolve().relative_to(repo_root.resolve())): sha256_file(path)
            for path in sorted(eval_files)
        },
    }
```

if the repository root calculation differs in the live source, use `Path(__file__).resolve().parent`. do not guess another root.

at manifest creation near lines 2598-2633, after eval filtering and before writing `run_manifest.json`, add:

```python
manifest["source_provenance"] = build_source_provenance(
    Path(__file__).resolve().parent,
    Path(__file__).resolve(),
    [Path(ev.source_path) for ev in evals],
)
```

`EvalFile` may not currently preserve its source path. inspect the dataclass and `parse_eval` first. if it lacks a source-path field, add only this field and populate it in `parse_eval`:

```python
source_path: str = ""
```

stop if this requires changing eval semantics or parsing beyond carrying the path.

### tests

create `tests/test_harness_provenance.py` with stdlib `unittest` and `tempfile.TemporaryDirectory`.

cover:

1. `sha256_file` returns the known SHA-256 for a short fixture byte string, calculated in the test with `hashlib.sha256`.
2. `build_source_provenance` includes one eval using a repository-relative key and a 64-character hash.
3. the harness hash is present and 64 characters.
4. a non-git temporary directory returns `git_commit=None` and `git_dirty=None` without failing.

### verify

```bash
python3 -m unittest tests.test_harness_provenance -v
```

expected: four tests pass.

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

expected: eight tests pass.

### stop conditions

stop if provenance collection includes credentials, environment variables, API keys, raw prompts, or machine-specific authentication paths. only hashes, relative eval paths, commit, and dirty state belong here.

## task 3: create the three repair-core evals

### shared rules

all three files must follow the existing eval module shape:

```lua
local eval = {}
eval.scenario_name = "..."
eval.description = "..."
eval.place = "baseplate.rbxl"
eval.prompt = [[...]]
eval.setup = function() ... end
eval.check_scene = function() ... end
return eval
```

use only ordinary Roblox instances and raw properties. do not require `spatial_tools.py`, helpers, primitives, a judge, or play mode.

all numeric comparisons must use a local explicit tolerance:

```lua
local EPSILON = 0.001
local function near(a, b)
    return math.abs(a - b) <= EPSILON
end
```

for vectors, compare X, Y, and Z separately. do not use generic global overlap or floating-part reports as pass criteria.

all tasks must use `workspace.RepairTarget` and must delete an old `RepairTarget` during setup.

### fixture 1: exact single-part repair

create `Evals/RepairCore/VB_CORE_REPAIR_001_single_part.lua`.

seed exactly three anchored parts under `RepairTarget`:

- `Foundation`: position `(0, 0.5, 0)`, size `(12, 1, 12)`, Slate.
- `TowerShaft`: position `(0, 4, 0)`, size `(6, 6, 6)`, Cobblestone. its bottom is exactly on the foundation top.
- `LooseRoof`: position `(8, 7.5, 0)`, size `(8, 1, 8)`, WoodPlanks.

required repair: move only `LooseRoof` to position `(0, 7.5, 0)` with identity rotation.

`check_scene` must assert:

- `RepairTarget` exists and contains exactly those three `BasePart` descendants.
- every name, class, parent, size, material, anchored value, color, transparency, and collision value is unchanged.
- Foundation and TowerShaft retain their exact CFrames.
- LooseRoof has the required exact CFrame.
- no new descendants were added anywhere under `RepairTarget`.

prompt: state that exactly one existing part is misplaced, only its transform may change, and no creation, deletion, decoration, resizing, recoloring, or material change is allowed.

### fixture 2: two independent repairs

create `Evals/RepairCore/VB_CORE_REPAIR_002_two_parts.lua`.

seed exactly five anchored parts:

- the same Foundation and TowerShaft as fixture 1.
- `LooseRoof`: broken position `(8, 7.5, 0)`, correct position `(0, 7.5, 0)`, size `(8, 1, 8)`.
- `Flagpole`: position `(0, 11, 0)`, size `(0.4, 7, 0.4)`, Metal.
- `LooseFlag`: broken position `(3, 12.5, 0)`, correct position `(1.3, 12.5, 0)`, size `(2.5, 1.5, 0.1)`, Fabric.

required repair: move only `LooseRoof` and `LooseFlag` to their exact correct CFrames.

`check_scene` must assert all shared preservation rules and exact target CFrames. it must also assert that the final flag visibly intersects the pole along X by at least `0.1` studs using the known axis-aligned sizes. this criterion is task-specific and must not become a general relation helper.

prompt: name both defects, name both allowed instances, and state that fixing only one is failure.

### fixture 3: move one assembly while preserving its internals

create `Evals/RepairCore/VB_CORE_REPAIR_003_preserve_assembly.lua`.

seed:

- `RepairTarget/Foundation`: position `(0, 0.5, 0)`, size `(12, 1, 12)`, Slate.
- `RepairTarget/TowerShaft`: position `(0, 4, 0)`, size `(6, 6, 6)`, Cobblestone.
- `RepairTarget/UpperAssembly`: a Model whose pivot is broken by exactly `10` studs on X.
- `UpperAssembly/Platform`: local position `(0, 0, 0)`, size `(8, 1, 8)`, WoodPlanks.
- four children named `CornerNW`, `CornerNE`, `CornerSW`, and `CornerSE`, each size `(1, 2, 1)`, Slate, positioned symmetrically at local X/Z coordinates `±3.5`, with local Y `1.5`.
- `UpperAssembly/Cap`: local position `(0, 3, 0)`, size `(6, 1, 6)`, WoodPlanks.

place the broken UpperAssembly so Platform world position is `(10, 7.5, 0)`. the correct Platform world position is `(0, 7.5, 0)`.

required repair: translate the existing UpperAssembly by `(-10, 0, 0)` without changing any relative child transform or any non-transform property.

identity preservation:

- during setup, create `ServerStorage.RepairCoreIdentity` with one `ObjectValue` per existing part, each pointing to its original instance.
- `check_scene` must require each ObjectValue still points to the named live descendant under the expected parent.
- require Foundation and TowerShaft exact CFrames.
- require the final UpperAssembly placement.
- require every child-to-Platform relative CFrame to match the setup constants.
- require exact part count and no extra descendants.

prompt: permit only moving the existing UpperAssembly as a rigid group. forbid rebuilding, replacing, deleting, adding, decorating, resizing, or editing individual child relationships.

### static verification

```bash
luau-compile Evals/RepairCore/VB_CORE_REPAIR_001_single_part.lua > /dev/null
luau-compile Evals/RepairCore/VB_CORE_REPAIR_002_two_parts.lua > /dev/null
luau-compile Evals/RepairCore/VB_CORE_REPAIR_003_preserve_assembly.lua > /dev/null
```

expected: every command exits 0.

verify historical evals are untouched:

```bash
git diff --exit-code -- Evals/Building/VB_REPAIR_001_watchtower.lua Evals/Building/VB_REPAIR_002_roof_attachment.lua Evals/Building/VB_REPAIR_003_roof_and_flag.lua
```

expected: exit 0, no output.

### stop conditions

- stop rather than adding a fourth fixture.
- stop if a task needs a generic relation engine, connected-component analysis, or screenshot judge to decide pass/fail.
- stop if the executor wants to “improve realism” with extra decoration. these are deliberately small tests.
- stop if preserving identity cannot be expressed with ordinary `ObjectValue` references and direct property checks.

## task 4: add a zero-token qualification runner

### objective

prove the three tests can distinguish broken and correct states without involving a model.

### implementation

create `scripts/windev/repair_core_qualification.py` by following the connection and cleanup pattern in `scripts/windev/primitive_anchor_calibration.py`. read that file before writing anything.

reuse these existing patterns instead of creating new infrastructure:

- newest Studio executable discovery under `%LOCALAPPDATA%/Roblox/Versions`.
- `harness.StudioConfig`.
- one persistent MCP `ClientSession`.
- `execute_luau` readiness polling.
- `screen_capture` image extraction.
- `try/finally` Studio cleanup.
- JSON output under `results/`.

for each repair-core Lua source:

1. upload it as `game.ReplicatedStorage._RepairCoreEval`.
2. require it and execute `eval.setup()`.
3. execute `eval.check_scene()` inside `pcall`.
4. require the broken state to fail.
5. capture `SCENARIO_bad.png` using a fixed camera that shows the entire small tower.
6. apply the known-good raw Luau repair from a Python dictionary keyed by scenario name.
7. execute `eval.check_scene()` again.
8. require the correct state to pass.
9. capture `SCENARIO_good.png` using the identical camera.
10. record the eval SHA-256, bad check message, good check message, and screenshot paths.

known-good repair snippets:

fixture 1:

```lua
workspace.RepairTarget.LooseRoof.CFrame = CFrame.new(0, 7.5, 0)
```

fixture 2:

```lua
workspace.RepairTarget.LooseRoof.CFrame = CFrame.new(0, 7.5, 0)
workspace.RepairTarget.LooseFlag.CFrame = CFrame.new(1.3, 12.5, 0)
```

fixture 3:

```lua
workspace.RepairTarget.UpperAssembly:PivotTo(
    workspace.RepairTarget.UpperAssembly:GetPivot() * CFrame.new(-10, 0, 0)
)
```

write output to:

```text
results/repair_core_qualification_<timestamp>/qualification.json
results/repair_core_qualification_<timestamp>/screenshots/
```

`qualification.json` must have top-level `status: "completed"` only when all three bad states failed and all three good states passed. otherwise exit nonzero with `status: "error"` and the exact scenario/check message.

create `scripts/windev/repair_core_qualification.bat` following the calibration batch-file pattern. do not add API keys or model arguments. keep cleanup commands separate so an absent process cannot abort the script.

### local tests before Studio

factor source-independent helpers so they can be unit tested without importing Windows-only state. add tests to the existing provenance test file for:

- the runner discovers exactly three `VB_CORE_REPAIR_*.lua` files.
- every scenario has exactly one known-good repair snippet.
- no repair snippet contains model, API, HTTP, judge, spatial, helper, primitive, or verifier calls.

if importing the runner launches Studio or reads `%LOCALAPPDATA%`, refactor so all side effects remain inside `main()`.

### verify

```bash
python3 -m py_compile scripts/windev/repair_core_qualification.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

expected: all tests pass; expected total is at least eleven tests.

```bash
git diff --check
```

expected: exit 0, no output.

### authorization boundary

stop here and report the local diff and test results. do not run the batch file until the operator explicitly authorizes the zero-token Studio qualification.

## task 5: run deterministic Studio qualification only after approval

this task is not an llm experiment. it still requires separate operator approval because it launches Roblox Studio and mutates the temporary place.

on the Windows checkout, after syncing only the approved changed files, run:

```text
scripts\windev\repair_core_qualification.bat
```

expected:

- process exits 0.
- `qualification.json` says `status: "completed"`.
- exactly three scenarios are present.
- every bad state reports failure.
- every good state reports pass.
- exactly six screenshots exist.
- total model calls and API calls are zero because the runner contains neither.

manual review is limited to one question per screenshot pair: does the visible before/after state agree with the exact task definition? record only `agree` or `disagree` with one sentence.

if any human review disagrees with the task assertion, mark the fixture blocked and stop. do not tune a tolerance or add another camera in the same execution cycle.

## task 6: document only verified facts

create `docs/REPAIR_CORE.md` after Tasks 1-4. before Studio qualification, mark all three fixtures `UNQUALIFIED`.

after an authorized successful Task 5, update each to `QUALIFIED` and record:

- scenario name.
- exact allowed changes.
- exact preservation requirement.
- physical versus visible attachment meaning.
- qualification artifact path.
- eval SHA-256 from `qualification.json`.
- manual screenshot agreement result.

also state prominently:

- the repair core is not a model-quality result.
- qualification proves only that the tasks label known broken and known correct states consistently.
- no model comparison is authorized by this document.

### verify

```bash
python3 -m py_compile harness.py scripts/windev/repair_core_qualification.py
luau-compile Evals/RepairCore/VB_CORE_REPAIR_001_single_part.lua > /dev/null
luau-compile Evals/RepairCore/VB_CORE_REPAIR_002_two_parts.lua > /dev/null
luau-compile Evals/RepairCore/VB_CORE_REPAIR_003_preserve_assembly.lua > /dev/null
python3 -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

expected: all commands exit 0 and all tests pass.

## final diff review

run:

```bash
git status --short
git diff --stat
git diff -- Evals/Building/VB_REPAIR_001_watchtower.lua Evals/Building/VB_REPAIR_002_roof_attachment.lua Evals/Building/VB_REPAIR_003_roof_and_flag.lua spatial_tools.py judge.py legacy/
```

expected:

- modifications are limited to the in-scope files.
- the last command produces no output.
- no result artifact is staged or committed.
- no credentials appear in the diff.

search for forbidden intervention drift:

```bash
python3 - <<'PY'
from pathlib import Path
paths = [
    Path('Evals/RepairCore'),
    Path('scripts/windev/repair_core_qualification.py'),
    Path('docs/REPAIR_CORE.md'),
]
forbidden = ['spatial_tools', 'actor_verifier', 'auto_spatial_feedback', 'PartPrimitives', 'VisualJudge']
for path in paths:
    files = [path] if path.is_file() else list(path.rglob('*'))
    for file in files:
        if not file.is_file():
            continue
        text = file.read_text(encoding='utf-8', errors='ignore')
        for term in forbidden:
            if term in text:
                raise SystemExit(f'forbidden intervention reference: {term} in {file}')
print('forbidden intervention references: 0')
PY
```

expected: `forbidden intervention references: 0`.

## done criteria

all must hold:

- [ ] `--no-gate` produces `review_required=true`, `passed=false`, and no fake pass percentage.
- [ ] future manifests include commit, dirty state, harness hash, and selected eval hashes.
- [ ] historical repair evals are byte-for-byte untouched.
- [ ] exactly three new repair-core evals exist.
- [ ] each task has direct expected-state and preservation assertions.
- [ ] local Python and Luau checks pass.
- [ ] the qualification runner contains no llm, API, judge, Spatial, helper, primitive, or verifier path.
- [ ] no Studio process was launched without the second approval.
- [ ] if Studio qualification was approved, all three broken states failed and all three known-good states passed.
- [ ] no source file outside the in-scope list changed.
- [ ] no commit, push, PR, model run, or broad benchmark run occurred.

## global stop conditions

stop and report without improvising if:

- any historical eval must be edited.
- scope grows beyond three fixtures.
- correctness requires subjective judge scoring.
- a proposed change adds a model-facing tool or feedback loop.
- one verification fails twice.
- the known-good state fails or a seeded broken state passes.
- the before/after screenshots contradict the direct assertions.
- Studio authentication or MCP readiness fails.
- proceeding appears to require force-killing Studio after a normal close attempt fails; report the host problem first.
- implementation exceeds roughly 500 added source lines before docs/tests. report the size and ask whether to split the work.

## what remains frozen after completion

completion qualifies a tiny benchmark core. it does not reopen:

- Spatial tools or linting.
- actor/verifier.
- automatic feedback.
- compile-once as a quality intervention.
- repair-contract prompt tuning.
- PartPrimitives or decomposition protocols.
- a broad model sweep.
- training-data extraction.
- product development inside BloxBench.

## later decision, explicitly not part of this plan

only after the repair core is qualified may the operator consider one matched vanilla pilot. that pilot requires a new plan and explicit approval. if its machine label and human review disagree, model comparison stops again.