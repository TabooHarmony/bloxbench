# BloxBench-EXP Architecture

## execution flow

```text
eval Lua files
    |
    v
harness.py parses prompts, gates, screenshot directives, and categories
    |
    v
Roblox Studio starts from an empty baseplate, or an eval setup provides an existing scene
    |
    v
model receives the construction or repair prompt and uses Studio MCP tools
    |
    +--> optional spatial observation and intent tools
    +--> optional model-side protocol injection
    +--> optional skill injection
    +--> optional legacy helpers/fixer
    +--> rejected PartPrimitives module (historical only)
    |
    v
check_scene gate, unless --no-gate is selected
    |
    v
screenshots and structural dump
    |
    v
optional OpenAI-compatible visual judge
    |
    v
incremental results.json, run_manifest.json, screenshots/
```

## benchmark conditions

The meaningful comparison unit is a complete run configuration, not just a score. At minimum, record:

- model and API endpoint identity
- eval set and filter
- vanilla, protocol, primitives, spatial, skills, helpers, fixer, or solver mode
- temperature
- maximum tool rounds
- token cap
- gate policy
- screenshot policy
- judge configuration

The harness writes these values into the run manifest and results metadata.

## active versus legacy code

`PartPrimitives.lua` is preserved for historical reproduction only. It is not an active research arm.

The model-side decomposition protocol was tested and rejected. The repair-first spatial observability prototype is retained as a tool-research direction, not a benchmark arm. Its connected-component linter improved main-assembly repair but did not guarantee visually convincing attachments. Relation checking was not adopted, automatic post-edit feedback caused a visually bad early stop, and the cheap alternate model did not edit. A fresh-context actor/verifier condition produced one narrow positive on an isolated roof repair, but its two-defect follow-up matched vanilla at higher cost and left the flag physically detached. Spatial is frozen except as historical evidence.

The retained compile-once execution mode changes loop shape without adding geometry APIs: one complete raw Luau edit followed by one bounded correction pass. It reduced token and edit churn against the current vanilla watchtower control, but visual review did not establish a quality win. Use it as a controlled baseline for future task-representation or model/data experiments, not as a scene-understanding intervention.

`legacy/SpatialHelpers.lua` and `legacy/StructuralFixer.lua` are preserved for historical reproduction only. Their launchers are under `legacy/experiments/`. They are not the next research arm.

The old spatial solver is external to this repository and is only used when an explicit solver path is supplied.

## measurement interpretation

`--no-gate` is an operator review mode. The harness still captures screenshots and structural flags, but a completed run is not evidence that the structure is good.

The structural dump reports diagnostic counts such as floating parts, overlaps, ground contact, and total parts. These counts require visual interpretation because intentional intersections can be valid construction.

## result persistence

Results are written after each eval so a crashed run retains completed work. Keep the result directory local, then preserve important runs in `results_pull/` with a matching short entry in the experiment index.
