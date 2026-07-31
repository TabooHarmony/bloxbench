# BloxBench active plan

The eval loop is: fixture prompt → subagent (delegate_task) with rsc_submit/rsc_job → RSC → Studio → screenshots → human pairwise review.

There is no python harness. Do not build one.

## next

1. Run one canary: single fixture, subagent + RSC
2. Verify screenshots exist and are visually valid
3. Small batch run, pull results for human A/B review

## constraints

- human pairwise review only: A better, B better, tie, both bad
- no automated visual gate or LLM judge
- no new harness, runner, screenshot pipeline, or result aggregator
- do not revive rejected helpers, primitive arms, fixer paths, or `partwise-trainer`
