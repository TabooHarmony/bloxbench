# relation-grounded context pilot

## question

Does a compact fixture-grounded relation representation improve existing-scene Roblox repair without adding Roblox APIs, spatial tools, verifiers, or feedback loops?

## matched design

- model: `cline-pass/deepseek-v4-flash`
- temperature: `0`
- pass: `pass@1`
- gate: normal `check_scene`, no `--no-gate`
- screenshots: enabled, three angles per eval
- max rounds: `12`
- input cap: `250000` tokens per eval
- existing-scene mode: enabled
- evals:
  - `Evals/Building/VB_REPAIR_001_watchtower.lua`
  - `Evals/Building/VB_REPAIR_003_roof_and_flag.lua`
- raw arm: normal hierarchy/tools only
- relation arm: same setup plus one JSON sidecar per eval, injected as system context; the sidecar explicitly told the model to verify against live Studio state

The first attempted pilot was invalid infrastructure, not a model run: `scripts\\windev\\mcp.bat` did not exist, both evals made zero model calls, and that run is excluded.

## artifacts

- raw: `results_pull/spatial_relation_raw_0710_1905/`
- relation: `results_pull/spatial_relation_context_0710_1901/`
- contexts: `research/spatial_behavior/relation_contexts/`
- corpus: `research/spatial_behavior/seed_corpus.jsonl`
- schema: `research/spatial_behavior/SCHEMA.md`

Both valid arms used the same harness and eval hashes:

- harness: `de79b50d9962c79cf2116039de784bcb9352e3a22efa24dab3df2ac8ab38c73a`
- watchtower eval: `11cdbe238d8c7af37cad41b9eddaa075061d64138fd5d210c92f66d7cd2e4b5f`
- roof/flag eval: `e4100afc74f351c1b74eae5476c19f6c94d3f2b649a0a097321ac138987c56ab`

Relation sidecar hashes:

- watchtower: `79c911b49536fc0e9dc0a2f4cf571588595e9245d3caddba7c565109b997e08d`
- roof/flag: `6ee4c2b376324aa536cb9d97fd04e069629e05924b6b5692be87a1579c172ce6`

## machine results

Both arms passed the weak machine gate on both tasks:

- raw: `2/2`, `100%`
- relation: `2/2`, `100%`

Aggregate raw versus relation:

- average input tokens: `164,623` versus `163,055`, relation `-0.95%`
- average output tokens: `5,870` versus `4,103`, relation `-30.10%`
- average LLM latency: `67.1s` versus `51.4s`, relation `-23.35%`
- average edit count: `1.0` versus `2.0`, relation used more correction edits
- model tool errors: `0` in both arms
- harness-side error rate: `5.56%` versus `2.86%`, readiness/screenshot plumbing rather than model tool failure

Per-task structural result:

- watchtower, raw: `57` parts, `17` generic floating flags, `55` overlaps
- watchtower, relation: `29` parts, `1` generic floating flag, `9` overlaps
- roof/flag, both arms: `16` parts, `1` generic floating flag, `4` overlaps

The generic floating detector flags elevated decorative pieces such as the flag. It is not an attachment proof, so it is not used as the sole relation result.

## screenshot review

- raw watchtower: visually overbuilt, with many protruding details and visibly detached upper/decorative pieces. The machine pass does not represent a clean repair.
- relation watchtower: substantially cleaner and closer to the intended compact watchtower. The main upper assembly reads coherently, but the flag remains visibly detached/floating in the reviewed angles. This is an improvement in preservation and restraint, not a complete visual success.
- raw roof/flag: roof and flag read as seated/attached in the three-angle set.
- relation roof/flag: same visual result, no meaningful quality difference from raw.

## verdict

**promising, not promoted as a default intervention.**

The relation representation improved the harder watchtower outcome materially, mainly by reducing overbuild and structural noise, without increasing average input cost. It did not improve pass rate on this two-task pilot, and it did not eliminate the remaining flag-attachment defect. The focused roof/flag task was already solved by raw context, so it provides no evidence of generalization there.

Keep the schema, sidecars, harness flag, and artifacts as research infrastructure. Do not add more APIs, automatic verifiers, or fine-tuning from this result. The independent audit, commitment arm, and third-layout follow-up are documented in `docs/experiments/spatial_relation_followup.md`.
