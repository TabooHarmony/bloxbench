# BloxBench-EXP Architecture

## execution flow

```text
eval Lua files
    |
    v
harness.py parses prompts, gates, screenshot directives, and categories
    |
    v
Roblox Studio starts from an empty baseplate
    |
    v
model receives the construction prompt and uses Studio MCP tools
    |
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
- vanilla, protocol, primitives, skills, helpers, fixer, or solver mode
- temperature
- maximum tool rounds
- token cap
- gate policy
- screenshot policy
- judge configuration

The harness writes these values into the run manifest and results metadata.

## active versus legacy code

`PartPrimitives.lua` is preserved for historical reproduction only. It is not an active research arm.

The model-side decomposition protocol was tested and rejected. It reduced token cost and geometry, but the clean replicate produced an incomplete, miscomposed watchtower with giant floating cylinders. No construction intervention is active now. The benchmark is paused pending a more specific decomposition hypothesis.

`legacy/SpatialHelpers.lua` and `legacy/StructuralFixer.lua` are preserved for historical reproduction only. Their launchers are under `legacy/experiments/`. They are not the next research arm.

The old spatial solver is external to this repository and is only used when an explicit solver path is supplied.

## measurement interpretation

`--no-gate` is an operator review mode. The harness still captures screenshots and structural flags, but a completed run is not evidence that the structure is good.

The structural dump reports diagnostic counts such as floating parts, overlaps, ground contact, and total parts. These counts require visual interpretation because intentional intersections can be valid construction.

## result persistence

Results are written after each eval so a crashed run retains completed work. Keep the result directory local, then preserve important runs in `results_pull/` with a matching short entry in the experiment index.
