# BloxBench Architecture

## execution flow

```text
eval Lua files (Evals/)
    |
    v
harness.py parses prompts, screenshot config, track tags
    |
    v
Roblox Studio starts from an empty baseplate (or eval setup provides a scene)
    |
    v
model receives the construction prompt and the full MCP tool surface
(execute_luau, multi_edit, script_read, start_stop_play, generate_mesh,
 search_asset, insert_asset, user_keyboard_input, character_navigation, etc.)
    |
    v
model builds using tool calls (up to --max-rounds)
    |
    v
screenshots + structure dump + metrics captured
    |
    v
incremental results.json + run_manifest.json + screenshots/
    |
    v
human enters Studio, experiences both results, votes A/B/tie/both-bad
```

## benchmark conditions

The meaningful comparison unit is a complete run configuration. At minimum, record:

- model and API endpoint identity
- eval set and filter
- temperature
- maximum tool rounds
- token cap
- screenshot policy

The harness writes these values into the run manifest and results metadata.

## evaluation

No automated gates. No LLM judge. Human pairwise preference is the only evaluation.

The `check_scene` and `check_game` functions in fixtures are documentation, not gates. The harness does not call them.

## measurement interpretation

Structural dump reports diagnostic counts (floating parts, overlaps, ground contact, total parts). These are debugging aids, not scores. Screenshots are for early-stage debugging and sharing. The end goal is interactive evaluation in Studio or a Roblox showcase game.

## result persistence

Results are written after each eval so a crashed run retains completed work. Keep the result directory local, then preserve important runs in `results_pull/` with a matching short entry in the experiment index.
