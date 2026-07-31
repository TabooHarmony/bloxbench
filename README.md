# BloxBench

Construction benchmark for Roblox builds from text prompts.

## architecture

There is no python harness. The eval loop is:

1. **Fixtures** in `Evals/` define prompts, rubrics, and metadata.
2. **Subagents** (hermes `delegate_task`) are the model under test. They iterate using `rsc_submit`/`rsc_job` to execute luau in Studio.
3. **RSC** (`/root/roblox-studio-control`) owns the Studio control plane.
4. **Human pairwise review** is the sole quality gate.

## fixture tree

32 Lua fixtures across six tracks:

- `Evals/Building/`: 13
- `Evals/UI/`: 5
- `Evals/Gameplay/`: 5
- `Evals/Props/`: 3
- `Evals/Scenes/`: 3
- `Evals/VFX/`: 3

## rules

- One benchmark entrypoint: subagent + RSC. No harness, no wrapper, no second runner.
- Human pairwise review only: A better, B better, tie, both bad. No automated gates, LLM judges, or Elo.
- Run one canary before any batch. Keep model, transport, and fixture constant while diagnosing.
- Screenshots and video are evidence. A process exit or result JSON is not.
- Do not revive `legacy/`, `archive/`, or any old runner.
