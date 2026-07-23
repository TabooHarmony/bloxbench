# repair core

status: `QUALIFIED`

qualification run: `results_pull/repair_core_qualification_20260710_174517/qualification.json`
qualification mode: zero-token Studio run, `model_calls: 0`, `api_calls: 0`, `scenario_count: 3`

this is a three-task benchmark-label qualification set, not a model-quality result. qualification proves only that the tasks distinguish their known broken and known correct states consistently. no model comparison is authorized by this document.

## shared rules

- each setup deletes the old `workspace.RepairTarget`.
- checks use direct instance properties and an explicit `0.001` tolerance.
- historical repair evals are untouched.
- screenshot review is separate from the machine check.
- physical contact and visible readability are recorded as different questions.

## fixtures

### `VB_CORE_REPAIR_001_single_part`

status: `QUALIFIED`

- broken state: `LooseRoof` is at `(8, 7.5, 0)`.
- allowed change: move only the existing `LooseRoof` to `(0, 7.5, 0)` with identity rotation.
- preservation: exactly three existing parts, with names, classes, parents, sizes, materials, anchored state, colors, transparency, collision, and fixed-part CFrames preserved.
- attachment meaning: exact physical placement on the tower shaft, with visual agreement recorded below.
- qualification artifact: `results_pull/repair_core_qualification_20260710_174517/qualification.json`.
- eval SHA-256: `eb55896be239319e4ed155343da7f464b03c2d5fa1ed61e1d688a306a305c98e`.
- machine result: seeded broken state failed on `LooseRoof.CFrame`; repaired state returned `good_state_passed`.
- manual screenshot agreement: bad screenshot shows the roof displaced to the right; good screenshot shows it seated on the tower. visual evidence agrees with the direct assertion.

### `VB_CORE_REPAIR_002_two_parts`

status: `QUALIFIED`

- broken state: `LooseRoof` is at `(8, 7.5, 0)` and `LooseFlag` is at `(3, 12.5, 0)`.
- allowed changes: move only those two existing parts to `(0, 7.5, 0)` and `(1.3, 12.5, 0)` respectively, with identity rotations.
- preservation: exactly five existing parts and all non-transform properties remain unchanged. fixing only one defect fails.
- attachment meaning: the flag must physically overlap the pole along X by at least `0.1` studs. this is not a claim of visual readability.
- qualification artifact: `results_pull/repair_core_qualification_20260710_174517/qualification.json`.
- eval SHA-256: `028e62a931e9954456ac0bc12a1ddd45b95281cf0a0634a9371594718e499543`.
- machine result: seeded broken state failed on `LooseRoof.CFrame`; repaired state returned `good_state_passed`.
- manual screenshot agreement: bad screenshot shows the roof displaced right and the flag off the pole; good screenshot shows both restored. visual evidence agrees with the direct assertion.

### `VB_CORE_REPAIR_003_preserve_assembly`

status: `QUALIFIED`

- broken state: the existing `UpperAssembly` pivot is displaced 10 studs on X.
- allowed change: translate only `UpperAssembly` left by 10 studs with `PivotTo`.
- preservation: `Foundation` and `TowerShaft` remain fixed; all six assembly parts retain their identity, parent, non-transform properties, and exact relative CFrame to `Platform`; the `ServerStorage.RepairCoreIdentity` references remain live.
- attachment meaning: the assembly and its children must be physically in the exact expected positions. visible readability remains a separate human check.
- qualification artifact: `results_pull/repair_core_qualification_20260710_174517/qualification.json`.
- eval SHA-256: `1bf2db544cbf754006123e240f941283f5b6ecbd889fcea42ba6c2d072c656d3`.
- machine result: seeded broken state failed on `UpperAssembly` pivot; repaired state returned `good_state_passed`.
- manual screenshot agreement: bad screenshot shows the upper assembly displaced to the right of the tower; good screenshot shows it restored over the tower. visual evidence agrees with the direct assertion.

## qualification boundary

The deterministic runner contains no LLM or model call. It must prove all three seeded broken states fail, all three known-good repairs pass, and write six screenshots before any fixture is marked `QUALIFIED`.

The authorized run above proved all three seeded broken states fail, all three known-good repairs pass, and wrote six screenshots. Each screenshot agrees with its direct assertion. This document does not authorize a model comparison.
