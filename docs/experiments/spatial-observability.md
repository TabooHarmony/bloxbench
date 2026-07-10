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
