# BloxBench Project State

## Identity

BloxBench is a construction benchmark for Roblox Studio. Models build from prompts using the full Studio MCP tool surface. Humans evaluate results pairwise (A better / B better / tie / both bad). No automated gates, no LLM judge scores.

## Tracks

- **Building** (`Evals/Building/`): 10 static construction tasks (cottage, bridge, watchtower, etc.)
- **UI** (`Evals/UI/`): 5 UI construction tasks (egg hatch, daily reward, trade window, etc.)
- **Gameplay** (`Evals/Gameplay/`): interactive experience slices for pairwise play. First task: AK-47 shooting range.

Props, Scenes, and VFX tracks are planned but not yet populated.

## Evaluation Model

Pairwise human preference. Two models build the same prompt. A human enters Studio (or views recordings), experiences both results, and votes. Votes feed Bradley-Terry ratings over time.

No automated pass/fail gates. No LLM-as-judge scoring. The `check_scene` and `check_game` functions in fixtures exist as documentation but the harness does not call them.

## Current Code State

- `harness.py` (2075 lines): orchestration, MCP tool loop, screenshots, structure dump, metrics, incremental save
- `gen_results_html.py`: operator debug viewer (side-by-side screenshots, not a voting interface)
- `Evals/`: Building (10), UI (5), Gameplay (1)
- `legacy/`: archived experiment code (helpers, fixer, solver, evaluation modules)
- `scripts/windev/`: operator-facing Windows scripts

All frozen spatial research (relation context, primitives, helpers, fixer, solver, actor/verifier, compile-once, repair contracts) has been removed from the harness and archived. The fine-tuning pilot is in a separate repository at `/root/partwise-trainer/`.

## Harness CLI

```
python harness.py \
  --evals-dir Evals/ --places-dir Places/ \
  --studio-exe "path/to/RobloxStudioBeta.exe" \
  --mcp-bat "path/to/studio-mcp.bat" \
  --model-name "model-id" \
  --api-base "https://..." --api-key "..." \
  --screenshots --max-rounds 25
```

Optional: `--skills` (skill index + skill_view tool), `--track ui|gameplay|all`, `--eval-filter <regex>`, `--existing-scene`, `--temperature`, `--pass-n 1|5`.

## Known Environment Hazards

- Studio authentication can expire; use RDP to re-authenticate
- Stale StudioMCP processes can poison the MCP TCP connection
- Force-killing Roblox Studio can damage WebView2 cookies
- The harness connects via one persistent MCP ClientSession per eval
- WINDEV VM (150) currently has 8GB RAM; Studio is tight until RAM is upgraded

## Artifact Policy

- `results/`: local harness output (gitignored)
- `results_pull/`: canonical staging for important runs
- Preserve a run by copying to `results_pull/<run_id>/` and logging in `docs/experiments/runs.md`

## Next Work

1. Verify the studio pipeline end-to-end once RAM is upgraded
2. Run two models on the AK-47 task, evaluate pairwise in Studio
3. Write more Gameplay/Props/Scenes/VFX task prompts
4. Build the pairwise arena viewer (anonymized A/B, vote recording, Bradley-Terry)
5. Eventually: Roblox showcase game as the native evaluation surface
