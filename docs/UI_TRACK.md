# BloxBench UI visual track

The UI track is a separate evaluation mode for Roblox interface tasks. It keeps functional correctness and visual quality as different measurements.

## Run

Run all evals in `Evals/` as usual:

```bash
python3 harness.py --evals-dir Evals --places-dir Places --track all ...
```

Run only the tagged UI evals:

```bash
python3 harness.py --evals-dir Evals --places-dir Places --track ui --judge ...
```

`--track ui` selects eval files containing:

```lua
-- @track ui
```

The current UI seed contains five scenarios under `Evals/UI/`.

## Scoring contract

The existing scene and game checks remain the functional gate. They answer whether the requested interface exists and satisfies the task's deterministic requirements.

The visual judge runs only after the scene gate has passed and a screenshot is available. UI visual scoring uses seven dimensions, each scored from 1 to 5:

- hierarchy
- composition
- spacing
- typography
- contrast
- state clarity
- art direction

The default visual pass threshold is `3.0/5`. It is a provisional operating point, not a human-calibrated production-quality threshold. The current official visual scalar is the validated judge's holistic `overall` score, while per-dimension scores are retained for diagnosis. Score provenance and validation status are stored when a judge response is accepted.

Results contain separate rates with explicit denominators:

- `functional_pass_rate`: deterministic scene/game gate over determinate evals
- `conditional_visual_pass_rate`: visual passes among functionally passing evals with valid visual scores
- `visual_evidence_coverage`: valid visual scores as a percentage of functional passes
- `confirmed_combined_pass_rate`: confirmed passes of both gates over all determinate evals
- `combined_pass_rate_lower_bound`: same as confirmed combined rate
- `combined_pass_rate_upper_bound`: confirmed passes plus unresolved visual reviews over all determinate evals

`visual_pass_rate` remains as a backward-compatible alias for `conditional_visual_pass_rate`. `combined_pass_rate` now means the confirmed end-to-end rate, not the conditional visual rate.

A functionally passing eval without a valid visual score is `visual_review_required`, not an automatic visual failure. A functional failure is a known combined failure, even when it has a screenshot.

The judge response is accepted only when it contains exactly the rubric dimensions, integer scores from 1 to 5, an integer overall score from 1 to 5, string reasoning, and a string-array issues field. Invalid responses become unresolved visual evidence and are recorded with validation status instead of entering the score aggregates.

The accepted result also records model, endpoint, prompt version and hash, rubric hash, screenshot paths/hashes/dimensions, structure-dump hash, and judge attempt count.

## Rubric override

A UI eval can provide task-specific visual descriptions with:

```lua
-- @ui_visual_rubric hierarchy="clear focal hierarchy" composition="balanced composition"
```

If it omits the directive, the harness uses the default UI rubric from `ui_track.py`.

The older `@judge_rubric` directive remains available for non-UI evals and is not used for UI visual dimensions when a UI rubric is present.

## Evidence modes

The current implementation uses the existing screenshot and structure-dump pipeline. It does not claim multi-device visual coverage yet.

- screenshot-capable runs receive the primary screenshot and structure dump
- structure data remains available to the judge as supporting evidence
- missing screenshots or judge output produce review status
- deterministic scene checks remain usable without a vision judge

Responsive and input-mode variants should be added only after the WinDev capture path can produce controlled device/orientation evidence. They are deliberately not inferred from a single desktop screenshot.

## Reporting

UI runs write `summary.ui_track` in `results.json` and render a dedicated UI Track section in generated markdown reports. Per-eval UI rows show functional status, visual score, and each visual dimension separately.

This track measures visual coherence and implementation quality. It does not yet measure style diversity, asset originality, or similarity to a reference image.
