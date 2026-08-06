# BloxBench v1 task matrix

This is the active v1 diagnostic suite of five tasks, one per family. Membership is locked by `suites/v1.json`, suite version `1.0`, manifest SHA-256 `2e5bfc9ec267b32503792835433e862b23c52e0e7014e4f93208a3e6d1dc50cd`. The benchmark lock is `suites/v1.lock.json`, SHA-256 `79a12ce3dc7bfe5ab6e6e8f89f8a1b37d2fa0d99d`.

The broader 25-task selection matrix remains archived at `suites/archive/v1-25.json` (and `suites/v1-25.json`) for later expansion. The active five were chosen as the simplest diagnostic representative per family with the highest prior signal for producing a reviewable `.rbxl` place file. The matrix deliberately keeps every v1 task on `Places/baseplate.rbxl`. The attached Studio runner does not yet load arbitrary starter places. UI tasks use world-space `SurfaceGui`/`BillboardGui` artifacts inside the candidate model, not hidden `PlayerGui` state. Screenshots remain diagnostic; human pairwise review of the place file is the holistic quality signal. v1 is direct one-shot only — no external fixer and no agentic self-repair in the score.

## selection rules

- One diagnostic task per family for this interim suite; broader coverage will re-expand from the archived 25.
- No task requires third-party asset IDs, hidden corpus files, or undocumented APIs.
- Runtime tasks expose deterministic commands through a declared `BindableEvent` or equivalent fixture hook.
- UI and VFX behavior may be visually reviewed, but static evidence does not prove timing, client behavior, or multiplayer behavior.
- Direct generation is the v1 primary treatment. Repair-assisted runs remain a separate track and are not part of the v1 score.
- `source_record` identifies design provenance. It is not a quality claim or a license grant. Atlas/corpus license status remains `unknown` unless independently verified.

## building and prop construction

| fixture id | task | runtime/evidence | source_record | status |
|---|---|---|---|---|
| `v1.build.001` | open-top off-road buggy with readable chassis, wheels, seat, and controls | edit; static diagnostic; optional input readback | `a020-car-place`, `a021-car-crash-system` | selected |

## scene and level composition

| fixture id | task | runtime/evidence | source_record | status |
|---|---|---|---|---|
| `v1.scene.005` | disaster-room escape diorama with a visible hazard source, safe route, and goal area | edit; static diagnostic; optional route readback | `a075-op-file-escape-tsunami`, `a081-pu-escape-tsunami`, `a113-survive-lava-for-cars` | selected |

## visual effects and feedback

| fixture id | task | runtime/evidence | source_record | status |
|---|---|---|---|---|
| `v1.vfx.001` | arcane impact burst with readable origin, short-lived particles, and restrained secondary glow | play; deterministic trigger; timing is human-review evidence only | `a124-crossfire-ffa`, common ParticleEmitter patterns | selected |

## gameplay and deterministic interaction

| fixture id | task | runtime/evidence | source_record | status |
|---|---|---|---|---|
| `v1.gameplay.005` | one-tap break-wall or mining loop with intact, damaged, broken, reward-marker, and reset states | play; deterministic state trace; no economy claim | `a126-break-wall-simulator`, `a067-mine-a-template`, `a119-mine-a-template` | selected |

## world-space UI and interaction surfaces

| fixture id | task | runtime/evidence | source_record | status |
|---|---|---|---|---|
| `v1.ui.002` | daily-reward panel with day progression, claimed/available states, and clear primary action | edit; static diagnostic; state labels can be inspected | `a096-reward-screen-by-arnavdabest`, reward-pattern corpus records | selected |

## lock record

- [x] Checked-in fixture paths and exact fixture IDs match the matrix.
- [ ] Record independently verified license/permission status for every external provenance record.
- [x] Every fixture has a task-family track, semantic components, deterministic states or commands where applicable, and an explicit evidence declaration.
- [x] Compile every fixture with the pinned Luau compiler.
- [x] Run contract and fixture tests.
- [x] Build `v1` version `1.0` with `--expected-count 5`.
- [x] Validate the manifest after writing it and record its SHA-256.
- [x] Finalize the direct-generation protocol and benchmark lock; model arms remain pending until the key is available.
