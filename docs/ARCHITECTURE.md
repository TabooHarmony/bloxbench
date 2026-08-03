# BloxBench architecture

## execution flow

```text
fixture metadata and prompt
  -> fixture contract validation
  -> candidate Luau source and source identity
  -> parent-owned review runner
  -> RSC bridge
  -> Roblox Studio edit or play runtime
  -> scene and game hooks
  -> deterministic commands and readbacks
  -> fixed-frame viewport screenshots and optional proof-backed video
  -> cleanup, reset, manifest, and review packet
  -> blind human pairwise review
```

## components

- **Fixtures** (`Evals/`): prompts, semantic components, deterministic states, hooks, evidence declarations, and reset/cleanup contracts.
- **Fixture contract** (`scripts/benchmark/fixture_contract.py`): parses metadata and rejects incomplete or non-pairwise fixture declarations.
- **Review runner** (`scripts/benchmark/review_runner.py`): owns the execution sequence and evidence manifest. It does not score beauty or fun.
- **RSC** (`/root/roblox-studio-control`): owns the Studio control plane, durable jobs, runtime operations, and artifact capture.
- **Qualification runner** (`scripts/test_flight/`): separate engineering coverage for transport, readiness, result-shape, cleanup, and calibration provenance.
- **Pairwise packet** (`scripts/benchmark/pairwise_packet.py`): creates anonymized A/B artifacts and preserves internal identity mapping for later audit.

## protocol boundary

Outer RSC transport success is not application success. The bridge validates nested Luau or runtime results before the runner records an operation as successful. Every reviewable run carries source, fixture, place, operation, screenshot, video, and manifest identity metadata.
