# BloxBench

Visual construction benchmark for Roblox Studio agents. Tests whether LLM agents can **build** UIs and 3D structures from scratch, scored by a vision-model judge.

Unlike [OpenGameEval](https://github.com/Roblox/open-game-eval), which tests *modification* (find the script, change the behavior, verify deterministically), BloxBench tests *construction* (build from nothing, judge visually).

## Categories

- **UI** — build ScreenGuis from scratch (shop menus, trade windows, loading screens, etc.)
- **Building** — construct 3D structures via code (pet shops, obby courses, campfires, etc.)

## Scoring Model

### Layer 1: Structural Gate (deterministic)

`check_scene` verifies minimum structure exists. Same mechanism as OpenGameEval — assert-based Lua checks run in edit mode. If the gate fails, score = 0, no screenshot, no judge call.

### Layer 2: Visual Judge (LLM-as-judge)

Only runs on evals that pass the gate. Takes screenshots + structural text dump + rubric, sends to a vision model, gets structured 1-5 scores back.

**Scoring dimensions:** correctness, layout, aesthetics, completeness.

**Two modes:**
- Absolute scoring (1-5 per dimension) for leaderboard tables
- Pairwise comparison for head-to-head posts

## Architecture

```
harness.py          # Forked from OpenGameEval local harness, adds:
                    #   - @judge_rubric / @screenshot eval parsing
                    #   - Camera framing + multi-angle screenshots
                    #   - Structure text dump
                    #   - Judge integration
judge.py            # VisualJudge module (score + compare)
evalutils/          # Reverse-engineered EvalUtils Lua modules
Evals/
  UI/               # 5 UI construction evals
  Building/         # 5 BUILD construction evals
Places/
  baseplate.rbxl    # Empty baseplate (all evals start from here)
```

## Running

```bash
# Set up .env
cp .env.example .env
# Edit .env with your LLM_API_BASE, LLM_API_KEY, and JUDGE_* vars

# Run all 10 evals with judge scoring
python harness.py \
  --evals-dir Evals/UI \
  --places-dir Places \
  --studio-exe "C:\Users\Admin\AppData\Local\Roblox\Versions\version-XXX\RobloxStudioBeta.exe" \
  --mcp-bat "%LOCALAPPDATA%\Roblox\mcp.bat" \
  --model-name "your-model" \
  --judge \
  --judge-model "claude-sonnet-4-20250514" \
  --judge-api-base "https://api.anthropic.com/v1" \
  --judge-api-key "your-key"

# Run only building evals
python harness.py \
  --evals-dir Evals/Building \
  --places-dir Places \
  --studio-exe "..." \
  --mcp-bat "..." \
  --model-name "your-model" \
  --judge
```

## Eval Format

Evals use the same Lua format as OpenGameEval, with two comment directives:

```lua
-- @judge_rubric correctness="..." layout="..." aesthetics="..." completeness="..."
-- @screenshot type=ui angles=1

local eval: BaseEval = {
    scenario_name = "VB_UI_001_egg_hatch",
    prompt = { ... },
    place = "baseplate.rbxl",
}

eval.check_scene = function()
    -- Structural gate: assert minimum structure exists
end
```

`type=ui` → 1 screenshot (ScreenGui renders on edit viewport)
`type=build` → 3 screenshots (camera framing at 3 angles)

## Results

Results JSON includes standard OpenGameEval metrics plus:
- `judge_scores`: per-dimension 1-5 scores
- `judge_overall`: holistic 1-5
- `judge_reasoning`: brief explanation
- `judge_issues`: list of specific problems
- `screenshot_paths`: all screenshot file paths
- `structure_dump`: text tree dump of created elements
