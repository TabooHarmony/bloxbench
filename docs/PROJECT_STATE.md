# BloxBench benchmark architecture

BloxBench is a fixture-driven Roblox construction benchmark. A fixture defines a task, starter place, semantic contract, deterministic observations, runtime mode, diagnostic evidence plan, and human-review boundary.

## task suite

The interim v1 suite is a focused five-task diagnostic set (one per family) locked by `suites/v1.json` and `suites/v1.lock.json`; its matrix is in `docs/V1_TASK_MATRIX.md`. The broader 25-task selection remains archived at `suites/archive/v1-25.json` and `suites/v1-25.json`. Later breadth can be derived from `Roblox-brain` knowledge and the real-world Roblox game-data atlas. Fixture provenance records the origin and source record for those selections. v1 is direct one-shot only.

The contract accepts task-family identifiers, repository-relative starter places, task-scoped knowledge profiles, declared candidate roots, and future review artifact types. The runner resolves and copies a declared starter place into the bundle, but attached Studio execution still assumes the correct place is already open. Arbitrary starter-place loading remains an RSC integration task.

## evaluation layers

1. The task and public knowledge context are frozen and hashed.
2. A model produces a direct one-shot candidate (no fixer, no self-repair in the v1 score).
3. Studio/RSC execution records runtime observations, warnings, readbacks, timing, usage, artifact hashes, and an exported `.rbxl` place file containing the raw model output.
4. Diagnostic screenshots describe the current execution surface; human in-Studio review of the place file is the holistic quality judgment (A better, B better, tie, both bad).
5. A reviewable place file remains available for human judgment even when its execution diagnostics contain warnings. A missing place file is recorded as an evidence-availability outcome.
