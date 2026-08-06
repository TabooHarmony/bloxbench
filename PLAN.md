# BloxBench task-suite plan

The checked-in fixtures define the suite. The interim launch version, v1, is a focused five-task diagnostic suite (one per family) that validates the one-shot place-file pipeline before broadening. The selected matrix is documented in `docs/V1_TASK_MATRIX.md`; membership is locked by `suites/v1.json` and `suites/v1.lock.json`. The broader 25-task matrix is preserved in `suites/archive/v1-25.json` and `suites/v1-25.json` for later expansion. Future breadth can draw on `Roblox-brain` knowledge and the real-world Roblox game-data atlas.

## suite layers

- task fixture and starter place
- frozen public knowledge profile and exact effective prompt
- direct candidate (one-shot only for v1)
- Studio/RSC observations and artifact provenance, including the exported `.rbxl` place file
- diagnostic screenshots during the current phase
- blinded human pairwise preference on the place file

## v1 work

1. complete: select and freeze five diagnostic fixtures (one per family) with recorded provenance and coverage using `scripts/benchmark/suite_manifest.py --expected-count 5`; the tracked outputs are `suites/v1.json` and `suites/v1.lock.json`
2. run independent one-shot generations for each model/task condition (no repair, no fixer)
3. preserve exact prompts, knowledge profiles, settings, source hashes, and the exported place file
4. package reviewable place files without converting runtime observations into a quality gate
5. collect blinded pairwise labels with `A better`, `B better`, `tie`, or `both bad` directly from the place files in Studio
6. report preference by task family alongside runtime, artifact, usage, and cost diagnostics; broaden to the archived 25-task suite once the five run clean
