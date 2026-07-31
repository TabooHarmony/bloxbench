# Architecture

## eval loop

```
fixture prompt
  → subagent (model under test)
    → rsc_submit / rsc_job (iterative tool use)
      → RSC worker → Studio
    → screenshots via RSC
  → human pairwise A/B review
```

There is no python harness, no MCP stdio client, no hand-rolled LLM loop. The subagent IS the loop. RSC IS the transport.

## components

- **Fixtures** (`Evals/`): prompts, rubrics, metadata, setup/check functions. The dataset.
- **Subagents**: hermes `delegate_task`. The model under test gets the prompt and iterates with RSC tools.
- **RSC** (`/root/roblox-studio-control`): durable job control, Studio lifecycle, screenshots.
- **Human review**: pairwise comparison. A better, B better, tie, both bad.

## what was removed

The old `harness.py` (2000+ lines, MCP stdio client, hand-rolled LLM loop, screenshot pipeline) was archived on 2026-07-30 to `archive/harness-2026-07-30/`. It was built before RSC existed and duplicated everything RSC and hermes already provide.
