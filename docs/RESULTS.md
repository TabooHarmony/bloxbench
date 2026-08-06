# BloxBench results and artifact policy

## canonical locations

Benchmark output is operator data:

```text
results/<run-id>/
```

A run directory may contain source identity, fixture and place identity, operation records, readbacks, traces, screenshots, attached videos, cleanup/reset records, manifests, and human-review packets.

## rejected historical packet

The historical drawbridge packet at:

```text
results/human-review-drawbridge-final-20260803/
```

is preserved for audit but is **not** a human-review packet. It has no generated
candidate place, its sources are synthetic canaries rather than model arms, and
its desktop-level videos have no verified viewport-only capture proof. No human
quality label exists.

The replacement evaluation bundle contract is under `results/evaluations/` and
requires model-generation provenance, a generated `.rbxl`/`.rbxlx` place,
named screenshots, structured readbacks/traces, and optional videos only when a
matching viewport-only proof is present.

## review sequence

1. validate the fixture and candidate source identity
2. inspect the complete manifest and operation results
3. inspect readbacks, traces, screenshots, and video
4. verify cleanup, reset, and evidence hashes
5. create a blind pairwise packet from two distinct valid runs
6. record one of `A better`, `B better`, `tie`, or `both bad`

A successful process exit is an execution fact. Human pairwise review is the quality decision. The withdrawn drawbridge packet is historical pipeline evidence only, not a model-quality conclusion.

## pilot sweep 2026-08-05: flash (deepseek-v4-flash) first real model-arm run

Ran all three pilot fixtures through generate_candidate (flash) + review_runner
against the live Studio/RSC stack. Outcome: 0/3 passed; all failed at setup or
check stage, each with a concrete, reproducible bug class:

- waterfall (VB_SCENE_001): candidate setup crashed on
  `Enum.Material.Leaf` (invalid material enum). Repair pass did NOT fix it.
- grapple (VB_GAMEPLAY_001): scene shape checks passed after repairs
  (GrappleController Script, TraversalBounds 64x20x20), but runtime state
  never reached "Swinging". Root cause: the model put the BindableEvent
  listener + state machine in the module `setup()` (edit-time), creating an
  EMPTY `Script`; in play the Script has no body so nothing drives
  `BloxBenchState`. 4 repair passes, same structural bug.
- lucky block (VB_GAMEPLAY_002): setup crashed on `Visible is not a valid
  member of Part`; after repair, fixed Idle casing + added BloxBenchRuntime,
  then failed at the play-mode transition check for the same structural
  reason: no executable Script, all logic in setup().

Headline failure mode for this model: generated runtime logic lives in the
setup module instead of inside an executable Script/LocalScript body, so
play-mode state machines never run. Secondary: invalid Roblox API enums
(`Enum.Material.Leaf`) and properties (`Part.Visible`) slip through.

Repair loop (mode B) fixed typed/mechanical contract violations
(GrappleController type, bounds size, state casing, missing runtime folder)
but did NOT fix structural execution-model mistakes. Consistent with the
earlier fixer verdict in docs/experiments/fixer.md: a repair pass can fix
shallow issues but not the execution-model misunderstanding.

Conclusion for the pilot: flash alone does not satisfy the runtime-state
fixtures. Next candidate arm should be a stronger model (pro), and/or the
prompt must mandate "runtime logic inside a Script/LocalScript body, never in
setup".

## pilot sweep v2 2026-08-05: hardened prompt + syntax gate

After adding cheat-sheet rules (execution model: runtime logic lives in a
Script/LocalScript body, never setup(); valid enums/properties only) and a
local luau-compile syntax gate, regenerated flash candidates and reran:

- waterfall: COMPLETED with reviewable evidence (place + screenshots +
  readbacks). Runtime warnings remain: route_walkable=false,
  route_can_collide=false, runtime effect not verified. Candidate origin
  unattributed in this run (generation-dir detail below).
- grapple: the execution-model rule worked (Script body now exists and runs).
  6 repair iterations each fixed one contract violation (controller NAME,
  Swinging transient timing, current_pad, trace instance, etc.) but each fix
  surfaced the next. Stalled at exact state-attribute matching. Bigger
  win: the structural bug is gone.
- lucky block: COMPLETED with state "valid reviewable result" — the first
  fully-attributed model evaluation. All runtime hooks passed:
  Idle -> Damaged1 -> Damaged2 -> Damaged3 -> Broken (reward shown) -> reset
  -> Idle with correct trace per command, exported .rbxlx, screenshots.

Key numbers: 2/3 fixtures reached completed; 1 (lucky block) reached the
full "valid reviewable result" state.

New findings:
- flash continues to substitute its own state vocabulary (Armed/Triggered vs
  fixture Damaged1-3/Broken) and its own attribute placement (attributes on
  sub-parts instead of candidate root). The repair loop corrects these one at
  a time; each repair pass is reliable for a SINGLE specific contract detail.
- REPAIR CLI GOTCHA: for repaired candidates the generation manifest lives at
  <arm_dir>/generation/manifest.json, not <arm_dir>/manifest.json. Pass
  --generation-dir <arm_dir>/generation (the nested dir) or the run stays
  "candidate origin is unattributed".
