# spatial behavior corpus

## purpose

This corpus describes what a Roblox-building model must preserve and verify. It is not a collection of final Luau answers. The useful unit is a scene state, an intended relation, an allowed change, and the observed behavior that follows.

## task record

Each JSONL record uses these fields:

- `task_id`: stable task identifier
- `source_fixture`: repository-relative source eval
- `status`: `task_spec_only`, `trajectory_pending`, `complete`, or `rejected`
- `instruction`: user-facing task text
- `coordinate_frame`: explicit coordinate convention, normally world studs with Y up
- `objects`: named scene entities relevant to the task
- `relations`: current and intended spatial relations
- `allowed_changes`: fields the model may change
- `preserve`: objects or properties that must remain unchanged
- `trajectory`: optional inspect/plan/act/verify trace metadata
- `evidence`: independent checks and screenshot paths

## relation vocabulary

Use a small controlled vocabulary first:

- `grounded_on`
- `centered_over`
- `supported_by`
- `attached_to`
- `aligned_with`
- `offset_from`
- `parented_under`
- `preserve_rigid_assembly`
- `preserve_transform`

A relation record should include:

```json
{
  "subject": "LooseRoof",
  "predicate": "centered_over",
  "object": "LookoutColumn",
  "state": "violated",
  "target": "satisfied",
  "tolerance_studs": 0.25,
  "evidence": "independent_check_scene"
}
```

## behavior labels

Trajectory annotations should distinguish:

- `inspect`: did the model identify the relevant instances and current state?
- `plan`: did it name the relation and intended transform before editing?
- `act`: did it make only allowed changes?
- `verify`: did it check the relation after editing?
- `failure_mode`: `wrong_object`, `wrong_frame`, `missing_relation`, `partial_repair`, `overbuild`, `no_verification`, or `tool_failure`

## quality rules

- Never label a task as successful from the final response alone.
- Numeric checks and screenshots are separate evidence fields.
- A task can pass geometry and still fail visual attachment review.
- Do not use a task for training data while its fixture, gate, or intended relation is ambiguous.
## relation-context and commitment sidecars

Per-eval relation sidecars live under `research/spatial_behavior/relation_contexts/`. They are optional prompt inputs, not official labels. Preserve their hashes in the run manifest and keep the model-facing representation separate from derived audit output.

Per-eval structured commitments live under `research/spatial_behavior/relation_commitments/`. A commitment contains only task-scoped `target`, `anchor`, `relation`, `preserve`, and `postcheck` fields. It is a prompt condition, not a geometry API or an official verifier.

Derived relation audits belong outside `results.json`, for example under `results_pull/`. Keep `declared_context` checks separate from reviewer-defined `strict` checks. Neither may overwrite official `passed`, gate, or score fields.

## evidence requirements

For representation experiments, retain:

- raw, relation-context, and any commitment run artifacts
- all configured screenshot angles
- captured structure dumps
- run manifests with sidecar hashes
- token, round, edit, latency, model-error, and harness-error metrics
- named-object and unchanged-property comparisons when preservation is part of the task

A lower part count is not preservation evidence. A relation check is not visual evidence. Both require independent interpretation.

Keep raw model trajectories immutable. Store derived annotations separately.
