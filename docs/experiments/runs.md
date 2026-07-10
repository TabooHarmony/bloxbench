# Historical Run Index

This is a compact index only. Full artifacts remain local under `results_pull/` or in the original scratch location until deliberately preserved.

## known runs

- `vanilla_0708_1743`: historical vanilla building comparison, artifacts under `results_pull/vanilla_0708_1743/`
- `helpers_0708_1817`: historical helpers v2 building comparison, artifacts under `results_pull/helpers_0708_1817/`
- `primitives_0708_2201`: historical primitive artifact at `/tmp/primitives_0708_2201.json`; preserve a complete run directory before treating it as canonical
- `primitives_0709_1321`: PartPrimitives smoke on cottage + dragon; artifacts: `results_pull/primitives_0709_1321/`; execution completed 2/2, visual review failed promotion to the full run
- `primitives_0709_1347`: dragon-only infrastructure failure; artifacts: `results_pull/primitives_0709_1347/`; no model construction
- `primitives_0709_1353`: repeated dragon-only infrastructure failure; artifacts: `results_pull/primitives_0709_1353/`; no model construction
- `primitives_0709_1402`: one-round diagnostic; artifacts: `results_pull/primitives_0709_1402/`; exposed the primitive trace regex bug, not benchmark data
- `primitives_0709_1405`: clean dragon-only usage run; artifacts: `results_pull/primitives_0709_1405/`; P usage confirmed, 15 floating parts, 33 overlaps, not promoted
- `primitives_0709_1411`: dragon-only origin-anchor follow-up; artifacts: `results_pull/primitives_0709_1411/`; 12 generic floating flags, 71 overlaps, not promoted
- `anchor_calibration_0709_160219`: zero-token deterministic anchor test; artifacts: `results_pull/anchor_calibration_0709_160219/`; exact top, bottom, side, and back joins verified; generic horizontal-floating flags identified as evaluator false positives
- `primitives_0709_1608`: instrumented dragon follow-up; artifacts: `results_pull/primitives_0709_1608/`; duplicate chain segments after two model tool errors, contaminated and not promoted
- `primitives_0709_1616`: near-clean instrumented dragon follow-up; artifacts: `results_pull/primitives_0709_1616/`; zero duplicate primitive names, 4 generic floating flags, 49 overlaps, one model tool error, not promoted
- `vanilla_0709_1644`: matched vanilla cottage replicate; artifacts: `results_pull/vanilla_0709_1644/`; 128 parts, 8 floating, 274 overlaps, zero model tool errors
- `primitives_0709_1648`: matched primitive cottage replicate; artifacts: `results_pull/primitives_0709_1648/`; 71 parts, 4 floating, 53 overlaps, zero model tool errors, visibly better but higher token cost
- `primitives_0709_1621`: final clean-model-error dragon follow-up; artifacts: `results_pull/primitives_0709_1621/`; zero model tool errors, zero duplicate primitive names, 14 generic floating flags, 77 overlaps, visually unacceptable dragon
- `primitives_0709_1653`: failed three-eval architecture smoke; artifacts: `results_pull/primitives_0709_1653/`; cottage hit the token budget at 8 parts, watchtower and market stall were visually unreadable, all `passed_cons=false`, intervention rejected
- `protocol_0709_1730`: first matched model-side decomposition protocol run; artifacts: `results_pull/protocol_0709_1730/`; 0 model tool errors, lower cost and geometry, visually promising but not promoted
- `vanilla_0709_1737`: matched vanilla replicate; artifacts: `results_pull/vanilla_0709_1737/`; cottage hit token budget, watchtower visually recognizable but structurally noisy
- `protocol_0709_1747`: failed clean protocol replicate; artifacts: `results_pull/protocol_0709_1747/`; 0 model tool errors but watchtower was giant floating cylinders and not a valid construction, protocol rejected
- `vanilla_repair_0709_1854`: raw-tool repair control on seeded partial watchtower; artifacts: `results_pull/vanilla_repair_0709_1854/`; grounded main assembly, but roof and flag remained visibly floating
- `spatial_repair_0709_1858`: first spatial observation repair; artifacts: `results_pull/spatial_repair_0709_1858/`; main assembly improved, but model falsely claimed a single grounded component
- `spatial_repair_0709_2110`: first actual component-lint repair; artifacts: `results_pull/spatial_repair_0709_2110/`; visually improved but exceeded token cap after lint-driven retries
- `spatial_repair_0709_2117`: corrected component-lint repair; artifacts: `results_pull/spatial_repair_0709_2117/`; best within-budget spatial result, retained as prototype evidence
- `spatial_repair_0709_2122`: strict-contact linter follow-up; artifacts: `results_pull/spatial_repair_0709_2122/`; token cap exceeded and generic tolerance iteration rejected
- `spatial_repair_0709_2144`: targeted relation-check follow-up; artifacts: `results_pull/spatial_repair_0709_2144/`; relation tool was not adopted, token cap exceeded, and visual result regressed
- `auto_feedback_repair_0709_2216`: harness-injected post-edit feedback; artifacts: `results_pull/auto_feedback_repair_0709_2216/`; efficient but visually regressed after one bad edit
- `actor_verifier_repair_0709_2307`: corrected focused roof actor/verifier; artifacts: `results_pull/actor_verifier_repair_0709_2307/`; narrow positive, roof repaired and valid parts preserved; verifier report finalization was incomplete
- `vanilla_repair_0709_2311`: matched focused roof control; artifacts: `results_pull/vanilla_repair_0709_2311/`; zero edits, roof remained detached
- `vanilla_repair_0709_2228`: one cheap `cline-pass/minimax-m3` model comparison; artifacts: `results_pull/vanilla_repair_0709_2228/`; model inspected but made zero edits, so no quality comparison was possible

## required entry format

For future runs, add:

```text
- <run_id>: <arm>, <model>, <eval set>, <date>; artifacts: results_pull/<run_id>/; verdict: pending
```

Use `verdict: pending` until screenshots have been reviewed. Use a short factual note, not a score-only conclusion.
