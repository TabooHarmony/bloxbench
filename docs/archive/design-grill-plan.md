# BloxBench Revised Design Plan

Outcome of adversarial design grill (23 questions, 2026-07-03).

## Design Decisions

### 1. Gate ordering: check_scene BEFORE visual pipeline
**Status:** bug fix
**Change:** Move `check_scene` execution (currently line 1377) above the screenshot/judge pipeline (currently line 1140+). Gate-failed evals get score=0, no screenshots, no judge call. Matches the README's stated design.
**Files:** harness.py `_run_single_eval_inner`

### 2. Strengthen UI gates, keep building gates loose
**Status:** enhancement
**Change:** UI gates should verify structural relationships, not just element existence. Add assertions for:
- ZIndex ordering (background behind content)
- Vertical stacking order (title Y < content Y < buttons Y)
- Button colors (green/red where specified)
- Container coverage (background frame covers screen)
Building gates stay as-is (loose "did you try" filter, judge handles the rest).
**Files:** all `Evals/UI/*.lua` check_scene functions

### 3. UI screenshots via play mode
**Status:** bug fix
**Change:** ScreenGuis in StarterGui don't render in the edit viewport. For `type=ui` evals, enter play mode briefly (`start_stop_play(is_start=True)`), wait ~3s for ScreenGui to render, `screen_capture`, then exit play mode. Building evals continue using edit-mode viewport screenshots.
**Files:** harness.py screenshot section (~line 1140)

### 4. Skip check_game when empty
**Status:** optimization
**Change:** Detect at parse time whether `check_game` has a non-empty body. If empty, set a flag on `EvalFile` and skip the entire StudioTestService bridge call. Saves 2.5-3.5 min per run (15-20s × 10 evals of dead play mode overhead).
**Files:** harness.py `parse_eval`, `_run_single_eval_inner`, `run_check_game_sts` call site

### 5. Judge retry + JSON extraction fix
**Status:** bug fix
**Change:**
- Add 3 retries with exponential backoff to `_call_vision_api` (same pattern as `llm_chat`)
- Raise `max_tokens` from 1000 to 2000
- Replace greedy `r'\{.*\}'` regex with proper JSON fence extraction: strip ```json fences, `json.loads` the cleaned string, fall back to regex only if that fails
**Files:** judge.py `_call_vision_api`

### 6. Expand UI structure dump
**Status:** enhancement
**Change:** Add to the UI structure dump Lua script:
- UICorner radius (check for UICorner children)
- UIStroke (color, thickness, check for UIStroke children)
- Transparency
- Font, TextSize, TextColor3 for TextLabel/TextButton
- ZIndex for all GuiObjects
Building dump already captures Position, Size, BrickColor, Transparency (workable).
**Files:** harness.py structure dump section (~line 1257)

### 7. Recursive eval glob
**Status:** bug fix
**Change:** `glob("*.lua")` → `rglob("*.lua")`. Allows `--evals-dir Evals` to find all 10 evals across UI/ and Building/ subdirectories. Category-only runs still work by passing `Evals/UI` or `Evals/Building`.
**Files:** harness.py line 1671

### 8. Cut pairwise comparison (V2)
**Status:** scope cut
**Change:** Remove `compare()` from judge.py, remove "Two modes" claim from README, remove/ rename Pairwise Winners section in generate_report.py. Pairwise comparison is a V2 feature (see V2 Roadmap).
**Files:** judge.py, README.md, generate_report.py

### 9. Eval-specified primary screenshot angle
**Status:** enhancement
**Change:** Add `primary=front|side|top` to `@screenshot` directive. Judge receives only the primary angle. Default `front` when unspecified. Maps to which captured angle gets sent to the judge:
- `front` → angle 0 (front-right 45°)
- `side` → angle 1 (front-left 45°)
- `top` → angle 2 (top-down)
Eval author picks the most diagnostic angle for their structure. Other angles still captured for report.
**Files:** all `Evals/Building/*.lua` `@screenshot` lines, harness.py `parse_eval` + judge screenshot selection (~line 1352)

### 10. Reorder categorize_error
**Status:** bug fix
**Change:** Move specific infra/transient patterns (HTTP 403/429/500, CONNECTION, NETWORK, ECONNRESET, ETIMEDOUT, SOCKET, DNS, SSL, etc.) ABOVE the generic keyword list ("is not", "expected", "missing", etc.). Prevents transient failures from being misclassified as model_fail and silently not retried.
**Files:** harness.py `categorize_error`

### 11. Cut liar detection (V2)
**Status:** scope cut
**Change:** Remove the "Self-Awareness (claimed but missing)" keyword-matching section from generate_report.py. It produces false positives/negatives. Revisit as V2 with judge-asked self-awareness question or proper semantic comparison.
**Files:** generate_report.py lines 157-184

### 12. Loosen eval prompts — describe what to build, not how
**Status:** design change
**Change:** Rewrite all 10 eval prompts to describe the visual outcome, not the implementation:
- Remove exact pixel dimensions (replace with "large", "small", "wide")
- Remove RGB values (replace with "dark background", "green button", "light blue")
- Remove font names (replace with "bold", "large title")
- Remove Instance type names (ScreenGui, UICorner, UIStroke) — let the model decide
- Keep functional descriptions: "title at top", "7 day slots in a row", "green hatch button"
The benchmark tests construction ability, not instruction-following precision.
**Files:** all 10 `Evals/**/*.lua` prompt content

### 13. Per-eval token cap
**Status:** cost guardrail
**Change:** Add `--max-tokens-per-eval` flag (default 500000). Abort eval if `total_tokens_in` exceeds cap. Log as "token_budget_exceeded" error category. Prevents runaway loops from bleeding API credits.
**Files:** harness.py LLM loop (~line 1056), CLI args

### 14. Reference implementations (2-3 evals)
**Status:** new
**Change:** Hand-build reference implementations for 3 evals:
- VB_UI_002 (daily rewards — most complex UI: 7 slots, UIStroke, transparency states)
- VB_BUILD_004 (campfire — most parts, most shapes)
- VB_UI_003 (trade window — multi-panel layout)
Run them through the harness, screenshot them, have the judge score them. Calibrates the judge and validates gates against correct output. If judge scores reference < 4/5, judge is broken. If gate fails on reference, gate is wrong.
**Files:** new `Reference/` directory with 3 .lua files

### 15. Save results after each eval
**Status:** bug fix
**Change:** Move `results.json` write inside the eval loop. After each eval completes, write the current results array to `results.json` (overwrite). On crash, you have everything up to the last completed eval.
**Files:** harness.py `run_eval_set` or `main`

### 16. Keep kill+relaunch Studio per eval (for first run)
**Status:** deferred optimization
**Change:** No change for v1. After first run validates cleanly, investigate `game:Load()` / `OpenPlaceFile` via MCP to reload baseplate.rbxl without killing Studio. Also tune `startup_wait` from 20s to actual boot time + 5s buffer.
**Files:** none (v1), harness.py `launch_studio` (v2)

### 17. Document vanilla vs skills-mode as separate leaderboards
**Status:** docs fix
**Change:** Add to README: "Vanilla mode (no --skills) and skills-mode (--skills) are different benchmarks. Do not compare scores across modes without flagging the config difference." Skill router and skill_view are already gated behind --skills flag, no code change needed.
**Files:** README.md

### 18. Fix judge docs to OpenAI-compatible + startup validation ping
**Status:** bug fix
**Change:**
- Update .env.example and README to show an OpenAI-compatible judge endpoint (not Anthropic, which uses different headers and API format)
- Add comment: "Judge must be an OpenAI-compatible vision model endpoint"
- Add startup validation: before running evals, make a test judge API call (send 1x1 pixel, ask for a score). If it fails, abort with clear error message. Prevents spending $15 on evals with a dead judge.
**Files:** .env.example, README.md, harness.py `main` (startup validation)

### 19. Set temperature to 0 with --temperature flag
**Status:** reproducibility fix
**Change:** Add `temperature: 0` to the `llm_chat` payload. Add `--temperature` CLI flag (default 0). Ensures reproducible runs. Flag allows experiments at higher temperatures later.
**Files:** harness.py `llm_chat` payload, CLI args

### 20. Fully despecify prompts
**Status:** design change (extends Q12)
**Change:** Remove all API hints from prompts. Describe visual outcomes only — no mention of ScreenGui, UICorner, UIStroke, Instance types, property names. The model must know the Roblox API AND reason about how to achieve the visual effect. This is the logical conclusion of Q12: the benchmark tests construction, not API recall or instruction-following.
**Files:** all 10 `Evals/**/*.lua` prompt content (same rewrite as Q12)

### 21. Truncate tool results to 4K chars with footer
**Status:** quality fix
**Change:** Before appending tool results to messages: `if len(tool_out) > 4000: tool_out = tool_out[:4000] + "\n... [truncated, full result in tool log]"`. Prevents context bloat from degrading model reasoning quality in later rounds.
**Files:** harness.py LLM loop (~line 1125)

### 22. Expand system prompt with environment context
**Status:** quality fix
**Change:** Replace the 3-sentence system prompt with expanded environment context:
- Working in Roblox Studio edit mode on an empty baseplate
- ScreenGuis go in StarterGui
- Scripts go in ServerScriptService or StarterPlayerScripts
- Use execute_luau with datamodel_type='Edit' to create and modify instances
- The workspace contains only a Baseplate
Does NOT include eval-specific answers — just baseline environment knowledge so the differentiator is construction ability, not environment familiarity.
**Files:** harness.py `LUAU_SYSTEM_PROMPT`

### 23. Pass@5 best-attempt selection (tracked bug, V2 fix)
**Status:** tracked bug
**Change:** When pass@5 is enabled, `best = run_results[0]` should pick the highest-scoring or first-passing attempt, not always attempt 0. Defer until pass@5 is actually used.
**Files:** harness.py `run_eval_set` (~line 1759)

## Implementation Order

Priority grouped by dependency and risk:

**Phase 1: Critical fixes (must do before any run)**
1. Gate ordering (#1) — judge scores gate-failed evals currently
2. UI screenshots via play mode (#3) — UI screenshots are blank currently
3. Recursive glob (#7) — can't run all 10 evals in one invocation
4. Judge retry + JSON fix (#5) — one bad API call wastes an eval
5. Save results after each eval (#15) — crash loses everything
6. Temperature 0 (#19) — non-reproducible runs
7. Fix judge docs + startup validation (#18) — following docs crashes the judge
8. Reorder categorize_error (#10) — transient failures not retried

**Phase 2: Quality improvements (do before first real run)**
9. Loosen + despecify prompts (#12, #20) — rewrite all 10 eval prompts
10. Expand system prompt (#22) — environment context
11. Truncate tool results (#21) — context bloat prevention
12. Skip empty check_game (#4) — saves 3 min per run
13. Per-eval token cap (#13) — cost guardrail
14. Eval-specified primary angle (#9) — better judge visibility
15. Expand UI structure dump (#6) — judge gets styling context
16. Strengthen UI gates (#2) — gates verify structure not just existence

**Phase 3: Calibration (do before first model run)**
17. Reference implementations (#14) — 3 hand-built evals
18. Document vanilla vs skills (#17) — README update

**Phase 4: Cleanup**
19. Cut pairwise comparison (#8) — remove dead code
20. Cut liar detection (#11) — remove broken analysis

## V2 Roadmap

Features deferred during this grill. Track so they're not forgotten:

1. **Pairwise comparison** — two models' screenshots side by side, judge picks "A, B, or tie." Research shows LLM judges are better at relative comparison than absolute scoring. Requires: multiple models scored with screenshots captured, `judge.compare()` re-added, CLI flag for comparison runs.
2. **Elo leaderboard** — derived from many pairwise comparisons. Each model gets an Elo rating that updates based on wins/losses. Requires: many pairwise comparisons to converge.
3. **Self-awareness analysis** — replace keyword-matching liar detection with judge-asked question: "Does the agent's final claim match what you see? List discrepancies."
4. **Guided prompt variants** — 2-3 evals with API hints (ScreenGui, UICorner mentioned) to compare against despecified versions. Spike: run guided vs open on 2-3 evals, measure the gap.
5. **Pass@5 best-attempt fix** (#23) — pick highest-scoring attempt, not attempt 0.
6. **Studio reuse optimization** (#16) — reload baseplate.rbxl via `game:Load()` instead of kill+relaunch. Saves 5-8 min per run.
7. **Context compaction** — summarize old tool results when context exceeds threshold (upgrade from Q21's truncation).
8. **Stronger building gates** — adjacency analysis for walls, continuity checks for door gaps. Hard to write in Lua, defer until gate false negatives are observed in practice.
9. **\*Error taxonomy\*** *(pending review)* — sub-classify model failures by type (wrong container, missing instance, wrong property, visual mismatch). Inspired by GameDevBench's failure analysis (63% mis-parented nodes, 36% missing methods, 26% wrong UI tree). Pure reporting improvement, no benchmark design change. Needs review: decide on categories and whether classification is rule-based or judge-based.
10. **\*Difficulty tiering\*** *(pending review)* — split results by UI (more visually complex) vs Building (more spatial), similar to GameDevBench's easy/hard split showing weaker models collapse on hard tasks. Already have the category data, just need explicit reporting. Needs review: confirm the UI=hard/Building=easy mapping holds after first run data.
11. **\*Soft gate scoring\*** *(pending review)* — distinguish "partially passed" (key elements present but not all) from "fully passed" and "failed", similar to GameDevBench's core vs full pass@1. Currently a model building 3 of 4 walls gets gate=fail, score=0, same as building nothing. Needs review: decide if partial gate credit is worth the added complexity, or if judge 1-5 scores already capture this signal.

## First Run Config

- pass@1 (not pass@5)
- temperature 0
- vanilla mode (no --skills)
- all 10 evals (rglob)
- judge enabled (OpenAI-compatible endpoint)
- token cap: 500K per eval
- startup_wait: 20s (tune after first run)
