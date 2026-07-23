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
- `actor_verifier_repair_0710_0852`: two-defect actor/verifier follow-up; artifacts: `results_pull/actor_verifier_repair_0710_0852/`; same final structure as vanilla, flag remained physically detached, one tool error, no promotion
- `vanilla_repair_0710_0858`: matched two-defect control; artifacts: `results_pull/vanilla_repair_0710_0858/`; same final structure as actor/verifier at lower cost, flag remained physically detached
- `compile_once_repair_0710_1012`: script-first existing-scene watchtower repair; artifacts: `results_pull/compile_once_repair_0710_1012/`; 1 edit, 121,788 input tokens, visually coherent but flag remained floating; retained as execution-control evidence
- `vanilla_repair_0710_1016`: current same-cap vanilla watchtower control; artifacts: `results_pull/vanilla_repair_0710_1016/`; 4 edits, 192,700 input tokens, visually comparable but structurally noisier
- `compile_once_repair_contract_0710_1126`: named repair-contract condition; artifacts: `results_pull/compile_once_repair_contract_0710_1126/`; 1 edit, 132,700 input tokens, fewer overlaps and less optional detail, but flag attachment still failed; no quality promotion
- `vanilla_repair_0709_2228`: one cheap `cline-pass/minimax-m3` model comparison; artifacts: `results_pull/vanilla_repair_0709_2228/`; model inspected but made zero edits, so no quality comparison was possible

- `vanilla_repair_0710_1807`: RepairCore vanilla baseline, `cline-pass/deepseek-v4-flash`, three qualified RepairCore evals, 2026-07-10; artifacts: `results_pull/vanilla_repair_0710_1807/`; verdict: 3/3 machine-gate passes and 3/3 screenshots visually agree, with one harness-side Studio readiness retry per eval; no intervention comparison yet
- `vanilla_repair_0710_1905`: raw arm of the relation-context pilot, same model and two harder Building repair evals; artifacts: `results_pull/spatial_relation_raw_0710_1905/`; verdict: 2/2 weak-gate passes, but watchtower overbuilt to 57 parts with 17 generic floating flags and 55 overlaps
- `relations_repair_0710_1901`: relation-context arm of the same pilot; artifacts: `results_pull/spatial_relation_context_0710_1901/`; verdict: 2/2 weak-gate passes, watchtower reduced to 29 parts with 1 generic floating flag and 9 overlaps, visually cleaner but flag attachment remained unresolved; promising, not promoted

- `relations_commitment_repair_0710_1929`: relation context plus structured pre-edit commitment on the two-task follow-up; artifacts: `results_pull/spatial_relation_commitment_0710_1929/`; verdict: 2/2 official passes, strict relation 2/2, watchtower reduced to 10 parts and 2 overlaps but changed existing material/rebuilt the rim, so commitment is conditional and not promoted
- `vanilla_repair_0710_1940`: raw arm of the third-layout generalization, `VB_REPAIR_002_roof_attachment`; artifacts: `results_pull/spatial_generalization_raw_0710_1940/`; verdict: 1/1 official pass, 99,282 input tokens, 3,251 output tokens, 33.1s latency
- `relations_repair_0710_1941`: relation-context arm of the third-layout generalization; artifacts: `results_pull/spatial_generalization_relation_0710_1941/`; verdict: 1/1 official pass, same 16-part artifact as raw, 92,480 input tokens, 1,841 output tokens, 22.1s latency; relation context retained its efficiency signal
- `relations_commitment_repair_0710_1943`: relation context plus structured commitment on the third layout; artifacts: `results_pull/spatial_generalization_commitment_0710_1943/`; verdict: 1/1 official pass, same artifact as raw/relation, 146,157 input tokens, 2,624 output tokens, 45.2s latency; commitment cost more without improving the result

## required entry format

For future runs, add:

```text
- <run_id>: <arm>, <model>, <eval set>, <date>; artifacts: results_pull/<run_id>/; verdict: pending
```

Use `verdict: pending` until screenshots have been reviewed. Use a short factual note, not a score-only conclusion.
