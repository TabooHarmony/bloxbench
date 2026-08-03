# BloxBench results and artifact policy

## canonical locations

Benchmark output is operator data:

```text
results/<run-id>/
```

A run directory may contain source identity, fixture and place identity, operation records, readbacks, traces, screenshots, attached videos, cleanup/reset records, manifests, and human-review packets.

## rejected historical packet

The historical drawbridge packet at:

```text
results/human-review-drawbridge-final-20260803/
```

is preserved for audit but is **not** a human-review packet. It has no generated
candidate place, its sources are synthetic canaries rather than model arms, and
its desktop-level videos have no verified viewport-only capture proof. No human
quality label exists.

The replacement evaluation bundle contract is under `results/evaluations/` and
requires model-generation provenance, a generated `.rbxl`/`.rbxlx` place,
named screenshots, structured readbacks/traces, and optional videos only when a
matching viewport-only proof is present.

## review sequence

1. validate the fixture and candidate source identity
2. inspect the complete manifest and operation results
3. inspect readbacks, traces, screenshots, and video
4. verify cleanup, reset, and evidence hashes
5. create a blind pairwise packet from two distinct valid runs
6. record one of `A better`, `B better`, `tie`, or `both bad`

A successful process exit is an execution fact. Human pairwise review is the quality decision. The withdrawn drawbridge packet is historical pipeline evidence only, not a model-quality conclusion.
