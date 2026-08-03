# BloxBench

BloxBench is a deterministic construction benchmark for Roblox builds generated from text prompts.

## active pilot

The first real model-backed evaluation set contains two task families and one
small control:

- `Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua`
- `Evals/Gameplay/VB_GAMEPLAY_001_grapple_traversal_course.lua`
- `Evals/Gameplay/VB_GAMEPLAY_002_lucky_block.lua`

Each fixture declares its prompt, semantic components, deterministic commands or states, runtime mode, evidence requirements, reset and cleanup contract, and human-review boundary.

## execution pipeline

1. `scripts/benchmark/fixture_contract.py` discovers and validates a fixture.
2. A model or subagent produces one candidate Luau source file.
3. `scripts/benchmark/review_runner.py` submits the source through RSC and Studio.
4. The runner performs setup, scene checks, runtime actions, readbacks, fixed-frame viewport screenshots, cleanup, reset, provenance, and optional video attachment only when viewport-only proof exists.
5. `scripts/benchmark/pairwise_packet.py` packages two valid runs for blind human pairwise review.

RSC and Studio are the execution boundary. Nested application results must succeed in addition to transport success.

Automated checks establish executable facts such as object identity, spatial relationships, state transitions, traces, reset, cleanup, and evidence identity. Human pairwise review judges overall quality: A better, B better, tie, or both bad.

## engineering qualification

`scripts/test_flight/` contains the separate unscored qualification runner. It exercises the pinned model-output contract, bounded Studio readiness, RSC transport, nested runtime results, cleanup, and screenshot provenance on a file-backed calibration prompt.

## results

Run artifacts live under `results/evaluations/<fixture>/<evaluation-id>/`. They contain the generated source/fixture copies, structured evidence, screenshots, optional proof-backed video, manifests, and review packets. Historical diagnostics remain under their existing result directories.
