# relation-context follow-up

## scope

This follow-up tested whether the relation-context signal survives an independent artifact audit, a structured pre-edit commitment, and a third matched repair layout. The official BloxBench pass field was never modified.

The arms kept the same model and matched settings:

- model: `cline-pass/deepseek-v4-flash`
- temperature: `0`
- pass: `pass@1`
- normal `check_scene` gate
- screenshots enabled
- `--existing-scene`
- maximum 12 rounds
- 250,000 input tokens per eval

## additions

- `scripts/analyze_spatial_relation_pilot.py` reads captured structure dumps and reports diagnostic relation checks.
- declared checks use only sidecar relations.
- strict checks add reviewer-defined invariants when a sidecar is incomplete. The watchtower strict audit adds `LooseRoof supported_by LookoutColumn`.
- `--relation-commitment-dir` injects a compact task-specific target, anchor, relation, preservation, and postcheck object into the actor prompt.
- task-002 received its own relation context and commitment sidecars.

Diagnostic relation checks use bounding boxes, not names or raw part counts:

- `centered_over`: horizontal center tolerance plus subject-bottom to target-top contact
- `supported_by`: vertical contact plus horizontal overlap
- `attached_to`: vertical overlap plus 2d horizontal bounding-box gap

## first commitment arm

The two-task set was `VB_REPAIR_001_watchtower` and `VB_REPAIR_003_roof_and_flag`.

Official result: `2/2` for relation context plus commitment.

Aggregate commitment metrics:

- average rounds: `8.5`
- average input tokens: `153,683`
- average output tokens: `5,162`
- average latency: `55.1s`
- average edits: `1.0`
- model tool errors: `0%`

The watchtower structure was restrained:

- raw: `57` parts, `17` generic floating flags, `55` overlaps
- relation context: `29` parts, `1` generic floating flag, `9` overlaps
- commitment: `10` parts, `0` generic floating flags, `2` overlaps

The commitment result retained the named foundation, shaft, door, platform, column, roof, and four battlements. It also changed the existing platform material from WoodPlanks to Cobblestone and reconstructed the upper rim, so the low part count is not proof of preservation. A preservation-sensitive invariant is still missing.

The first sidecar audit found:

- raw: declared relation `1/2`
- relation context: declared relation `2/2`
- commitment: strict relation `2/2`

## third-layout generalization

Fixture: `VB_REPAIR_002_roof_attachment`.

Three matched arms were run: raw, relation context, and relation context plus commitment. All passed the official gate and produced the same 16-part result with the same three required relations satisfied.

Raw:

- input: `99,282`
- output: `3,251`
- rounds: `6`
- latency: `33.1s`
- edits: `1`
- model tool errors: `0%`

Relation context:

- input: `92,480`, `-6.9%` versus raw
- output: `1,841`, `-43.4%`
- rounds: `6`
- latency: `22.1s`, `-33.1%`
- edits: `1`
- one recovered harness-side Studio probe error

Commitment:

- input: `146,157`
- output: `2,624`
- rounds: `9`
- latency: `45.2s`
- edits: `1`
- one recovered harness-side Studio probe error

## interpretation

The durable signal is the compact relation representation. It generalized to a third layout and reduced output, latency, and peak context without changing the model tool surface or official pass result.

The structured commitment is not a default intervention. It appears to restrain overbuilding on the complex watchtower, but it increased cost on the third task and did not improve its artifact. It should only be revisited with explicit unchanged-object and unchanged-property checks.

Do not promote relation context from this evidence alone. The next valid study needs a preservation-sensitive matched fixture, declared and strict audits, screenshots at every angle, and raw/relation/commitment arms under identical settings. Stop if the result only improves counts or ties pass rate without a clear preservation or visual-quality win.

## artifacts

- first raw: `results_pull/spatial_relation_raw_0710_1905/`
- first relation: `results_pull/spatial_relation_context_0710_1901/`
- first commitment: `results_pull/spatial_relation_commitment_0710_1929/`
- third-layout raw: `results_pull/spatial_generalization_raw_0710_1940/`
- third-layout relation: `results_pull/spatial_generalization_relation_0710_1941/`
- third-layout commitment: `results_pull/spatial_generalization_commitment_0710_1943/`
- declared audit: `results_pull/spatial_relation_generalization_diagnostic.json`
- strict audit: `results_pull/spatial_relation_diagnostic_strict.json`
- harness: `harness.py`
- analyzer: `scripts/analyze_spatial_relation_pilot.py`
- commitments: `research/spatial_behavior/relation_commitments/`
