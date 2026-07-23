# project-local UI style extraction

`style_extraction.py` extracts concrete observations from hand-built reference Lua files. It is a local prior for agent context, not a universal Roblox design system and not a visual-quality score.

## usage

From the BloxBench root:

```bash
python3 style_extraction.py \
  Reference/VB_UI_002_daily_reward_ref.lua \
  Reference/VB_UI_003_trade_window_ref.lua \
  --output /tmp/ui_style_profile.json \
  --prompt-output /tmp/ui_style_context.txt
```

The JSON profile records:

- source paths and SHA-256 hashes
- observed Instance class counts
- observed RGB assignments and property contexts
- font and text-size usage
- corner-radius and stroke-thickness values
- transparency values
- literal `UDim2` layout signals
- basic local variable names and parent edges

The prompt output is intentionally cautious. It labels the values as reference-derived observations and tells the construction agent not to copy them blindly.

The harness can inject the compact context only into UI-track evals and records the profile in the run manifest:

```bash
python3 harness.py \
  --track ui \
  --style-reference Reference/VB_UI_002_daily_reward_ref.lua \
  --style-reference Reference/VB_UI_003_trade_window_ref.lua \
  ...
```

The generated run directory contains `style_profile.json`, while the manifest records the reference paths and profile hash. Building evals in an `all` run do not receive the UI context.

## scope limits

The prototype parses literal property assignments in Lua. It skips computed expressions such as `UDim2.new(0, startX + ..., ...)` rather than guessing their final values.

It does not infer:

- whether the reference is aesthetically good
- responsive behavior
- input usability
- accessibility compliance
- semantic roles from variable names
- a universal palette or component system

Those require runtime evidence or human review. Add more known-good references before treating extracted frequencies as a project-wide prior.
