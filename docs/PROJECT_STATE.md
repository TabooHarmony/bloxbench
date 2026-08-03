# BloxBench pilot state

Updated: 2026-08-03

## active corpus

The active `Evals/` tree contains the three first model-backed fixtures listed
in `README.md`. Historical and withdrawn fixture sources remain outside the
active set.

## active tooling

- `scripts/benchmark/fixture_contract.py` validates fixture metadata and required evidence declarations.
- `scripts/benchmark/review_runner.py` owns candidate execution, deterministic hooks, readbacks, screenshots, cleanup, reset, provenance, and review manifests.
- `scripts/benchmark/attach_video.py` attaches an externally captured recording only after viewport-only proof is verified.
- `scripts/benchmark/pairwise_packet.py` builds blind A/B review packets.
- `scripts/test_flight/` remains the separate qualification path.

## pilot evidence status

Strict Studio/RSC canaries exist as pipeline diagnostics for the four fixture
contracts, but they are not model evaluations. The final-digest drawbridge
artifacts and packet are preserved at:

- `results/live-canary-final-drawbridge-a-20260803`
- `results/live-canary-final-drawbridge-b-20260803`
- `results/human-review-drawbridge-final-20260803`

They are rejected for presentation because the sources are synthetic canaries,
there is no generated candidate place, and the desktop videos have no verified
viewport-only proof. No human label exists.

The final-digest waterfall session-1 run remains a valid execution diagnostic.
The later restart attempts opened Studio at its login modal and did not load the
external MCP plugin. Cross-session stability remains unproven.

## evidence boundary

Automated checks establish executable facts. Human review supplies the quality decision through pairwise comparison. A transport or parser success is not a human-review decision. The withdrawn drawbridge artifacts are historical diagnostics only and do not establish model quality.

## publication boundary

Pilot redesign changes remain subject to repository review. No push is part of the benchmark execution path. The redesign remains uncommitted; the qualification boundary remains isolated in commit `1552524`.
