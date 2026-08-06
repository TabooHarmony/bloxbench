# BloxBench

BloxBench is a deterministic construction benchmark for Roblox builds generated from text prompts.

## task suite

The interim v1 suite is a focused set of five diagnostic tasks, one per family, validating the one-shot pipeline before broadening.
The task matrix is in `docs/V1_TASK_MATRIX.md`; membership is locked by
`suites/v1.json`, and the generator/evaluator/treatment lock is
`suites/v1.lock.json`. The broader 25-task selection is archived at
`suites/archive/v1-25.json` and `suites/v1-25.json`. Later breadth is informed by `Roblox-brain` and the
real-world Roblox game-data atlas. The fixture contract is intentionally
task-family agnostic and records task provenance when a fixture is hand-authored
or derived from an external corpus.

Each fixture declares its prompt, semantic components, deterministic commands or states, runtime mode, evidence requirements, reset and cleanup contract, and human-review boundary. v1 is direct one-shot only; no fixer and no agentic self-repair count in the score. The corpus and model-context boundary is documented in `docs/KNOWLEDGE_BOUNDARY.md`.

## execution pipeline

1. `scripts/benchmark/fixture_contract.py` discovers and validates a fixture.
2. A model or subagent produces one candidate Luau source file.
3. `scripts/benchmark/review_runner.py` submits the source through RSC and Studio.
4. The runner performs setup, scene checks, runtime actions, readbacks, fixed-frame viewport screenshots, cleanup, reset, provenance, and optional video attachment only when viewport-only proof exists.
5. `scripts/benchmark/pairwise_packet.py` packages two reviewable runs for blind human pairwise review.
6. A reviewer fills `review_form.json`; `scripts/benchmark/record_human_review.py` validates and records the human decision without exposing the A/B source mapping.

RSC and Studio are the execution boundary. Nested application results must succeed in addition to transport success.

Automated checks establish executable facts such as object identity, spatial relationships, state transitions, traces, reset, cleanup, and evidence identity. Human pairwise review judges overall quality: A better, B better, tie, or both bad.

## engineering qualification

`scripts/test_flight/` contains the separate unscored qualification runner. It exercises the pinned model-output contract, bounded Studio readiness, RSC transport, nested runtime results, cleanup, and screenshot provenance on a file-backed calibration prompt.

## results

Run artifacts live under `results/evaluations/<fixture>/<evaluation-id>/`. They contain the generated source/fixture copies, structured evidence, screenshots, optional proof-backed video, manifests, and review packets. Historical diagnostics remain under their existing result directories.
