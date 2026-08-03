# BloxBench pilot plan

## selected tasks

- waterfall landmark: composed scene, route, and persistent effect
- grapple traversal course: deterministic stateful interaction
- Lucky Block: small interaction control

## parent-owned pipeline

The benchmark path is fixture selection, candidate-source identity, RSC and Studio execution, deterministic hooks, runtime readbacks, fixed-frame evidence, cleanup, reset, and blind pairwise packaging. The implementation lives in `scripts/benchmark/`.

## validation sequence

1. validate every fixture against the declared contract
2. run bounded live canaries for each pilot fixture
3. inspect manifests, readbacks, traces, screenshots, videos, cleanup, reset, and artifact hashes
4. run matched model arms only after the canaries are valid
5. collect human pairwise votes using `A better`, `B better`, `tie`, or `both bad`

The pilot stays small until the execution and evidence contracts are stable.
