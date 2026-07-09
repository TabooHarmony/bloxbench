# Structural Fixer Experiment

## verdict

rejected as the next intervention.

## evidence

The fixer was visually worse than vanilla on most reviewed evals. It also had a historical Studio Assistant parse failure. A post-hoc repair pass adds cost and can damage an otherwise coherent build.

The implementation remains under `legacy/StructuralFixer.lua` only for historical reproduction.

## reproduction

The old launcher is `legacy/experiments/run_fixer_experiment.bat`. Do not use it for the active primitive experiment.
