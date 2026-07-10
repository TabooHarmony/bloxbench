# Spatial Observability Repair Experiment

## question

Can compact spatial state and intent feedback help the baseline model repair a flawed Roblox scene without adding a geometry builder API?

## tooling

The prototype added local harness tools that call the existing Studio `execute_luau` tool:

- `spatial_snapshot`: named parts, bounds, grounding, and connected components
- `spatial_intent_add`: model-declared expected components
- `spatial_intent_check`: compares declared intent with live state
- `spatial_lint`: checks actual disconnected components independently of the intent ledger

The model still created and moved geometry with raw Luau.

## matched repair

The eval seeded a partial watchtower with a grounded foundation, shaft, and door, plus a misplaced upper assembly. The model had to repair the existing scene.

Control: `vanilla_repair_0709_1854`

- 10 rounds
- 207,553 input tokens
- 0 model tool errors
- grounded shaft, door, platform, and battlements
- roof and flag remained visibly floating

Spatial tools: `spatial_repair_0709_1858`

- 12 rounds
- 280,791 input tokens
- 0 model tool errors
- all spatial tools used
- platform and battlements improved, but the model falsely claimed every part was one grounded component

## linter follow-ups

`spatial_repair_0709_2110` added actual component linting but retained an overly broad elevated-component rule:

- 16 rounds
- 326,657 input tokens
- token budget exceeded
- screenshot quality improved, but the feedback caused excessive retries

`spatial_repair_0709_2117` corrected the elevated-component semantics:

- 12 rounds
- 262,690 input tokens
- 0 model tool errors
- 2 edits
- best within-budget repair result
- tower, platform, battlements, and flagpole were coherent; the remaining flag/roof contact was visually marginal and the model still overclaimed completion

A strict near-zero contact tolerance was then tested as `spatial_repair_0709_2122` and rejected:

- 15 rounds
- 313,566 input tokens
- token budget exceeded
- the model churned on repeated snapshots and never called `spatial_lint`

## decision

Keep the spatial observability direction as a prototype. Do not promote the current tools as a solved repair system or benchmark intervention.

The useful signal is that compact scene state helped the model repair the main assembly better than raw inspection alone. The boundary is equally clear: generic connected-component checks are not enough. A future tool should answer explicit support and attachment relations with compact, actionable diagnostics, rather than tightening one global tolerance.

A targeted `spatial_relation_check` follow-up was tested as `spatial_repair_0709_2144`:

- 15 rounds
- 301,863 input tokens, over the 300k cap
- 1 execute error
- 2 edits
- the model never adopted the new relation tool
- the final screenshot regressed to an incomplete tower with 3 floating parts and 12 overlaps

This follow-up is negative evidence. Do not retain the relation tool in the active harness or continue iterating on this repair branch without a materially different hypothesis.

## automatic feedback follow-up

`auto_feedback_repair_0709_2216` moved observation into the harness. No new spatial tools were exposed to the model; the harness appended a compact diff after edit-like `execute_luau` calls.

Operationally:

- 7 rounds
- 128,612 input tokens
- 1 edit
- 0 model tool errors
- no token-cap failure

Visually it was a failure. The model stopped after a bad edit that moved `LooseRoof` into the doorway area, removed the coherent lookout assembly, and left the flag floating. Efficiency without visual correctness is not a win, so this path is retained only as an experimental harness feature and not promoted.

## focused actor-verifier follow-up

The first roof fixture was invalid and excluded: it used a horizontal cylinder as the lookout column, so numerical roof alignment did not imply visual support. The corrected fixture used a vertical block column and a 16-part preservation gate.

Matched results on `VB_REPAIR_002_roof_attachment`:

- actor/verifier: `actor_verifier_repair_0709_2307`, 14 phase rounds, 148,128 input tokens, 1 edit, roof moved from x=10 to x=0, all 16 parts preserved, visually correct roof support
- vanilla: `vanilla_repair_0709_2311`, 6 rounds, 91,573 input tokens, 0 edits, roof remained at x=10 and visibly detached

This is a narrow positive result for the bounded actor/verifier condition on an isolated repair. It is not evidence that the verifier itself improved the result: the actor made the successful edit before verification, and the verifier exhausted its read-only rounds without returning a report. The harness now forces a final report call when a verifier or repair phase exhausts its tool rounds. Replicate or test one harder two-defect repair before promoting Spatial beyond this narrow arm.

The matched two-defect follow-up did not promote the approach. Actor/verifier and vanilla produced the same final structure: the roof was repaired, but the flag remained physically detached at x=1.5 under independent geometry inspection. Vanilla used 90,577 input tokens, 6 rounds, and 0 errors; actor/verifier used 176,774 input tokens, 16 rounds, and 1 `execute_luau` error. The verifier identified the remaining flag defect, but its report was polluted by provider tool-call markup and did not improve the final artifact. The two-defect fixture gate was tightened from 0.25 to 0.1 after this review. Do not promote Spatial from this arm.

## compile-once execution control

The next materially different experiment changed execution shape rather than adding scene observers. On `VB_REPAIR_001_watchtower`, the script-first arm was limited to one edit-bearing initial `execute_luau` call plus one bounded correction phase. It used no spatial tools or geometry APIs.

Matched current results:

- compile-once: `compile_once_repair_0710_1012`, 9 phase rounds, 121,788 input tokens, 1 edit, 0 model tool errors
- vanilla: `vanilla_repair_0710_1016`, 10 rounds, 192,700 input tokens, 4 edits, 0 model tool errors

Compile-once reduced input tokens by 37% and edit count by 75%. Both artifacts were readable watchtowers. Visual review did not establish a clear quality win: compile-once seated the upper assembly but left a visibly floating flag and omitted some window detail, while vanilla produced a cleaner-looking battlement ring but had more structurally noisy floating window parts. Keep this mode as an execution-control baseline, not as a promoted quality intervention. The next quality hypothesis should change task representation or model/data, not add another verifier or linter.
