# BloxBench architecture

## execution flow

```text
fixture task, public knowledge, and provenance
  -> fixture contract validation
  -> direct one-shot candidate Luau source (no fixer in v1)
  -> source, prompt, context, treatment, and settings identity
  -> parent-owned review runner
  -> RSC bridge
  -> Roblox Studio edit or play runtime
  -> scene and game hooks
  -> deterministic commands and readbacks
  -> exported place file (raw model output)
  -> diagnostic screenshots
  -> cleanup, reset, manifest, and review packet
  -> blind human pairwise review of the place file in Studio
```

## components

- **Fixtures** (`Evals/`): prompts, semantic components, deterministic states, hooks, evidence declarations, and reset/cleanup contracts.
- **Fixture contract** (`scripts/benchmark/fixture_contract.py`): parses task metadata, public context, provenance, evidence declarations, and task-family-agnostic starter-place settings.
- **Review runner** (`scripts/benchmark/review_runner.py`): owns the execution sequence and evidence manifest. It records observations, exports the place file, and does not score beauty or fun.
- **RSC** (`/root/roblox-studio-control`): owns the Studio control plane, durable jobs, runtime operations, and artifact capture.
- **Qualification runner** (`scripts/test_flight/`): separate engineering coverage for transport, readiness, result-shape, cleanup, and calibration provenance.
- **Pairwise packet** (`scripts/benchmark/pairwise_packet.py`): creates anonymized A/B place-file artifacts and diagnostics while preserving internal identity mapping for later audit. v1 pairs are direct one-shot only.

## suites

The interim v1 suite is five tasks, one per family, locked by `suites/v1.json` and `suites/v1.lock.json`. The full 25-task selection is archived at `suites/archive/v1-25.json` and `suites/v1-25.json` for later expansion. v1 is direct one-shot only. Future suites keep the same lock shape.

## starter-place boundary

Repository-relative starter places are resolved and copied into run bundles. The attached Studio runner does not currently open them; it assumes the requested place is already loaded in the attached session. RSC's isolated batch path accepts `--localPlaceFile`, but it is a one-shot execution surface and is not yet integrated with interactive screenshots or presentation review. BloxBench must not claim arbitrary starter-place execution until that boundary is implemented and tested.

## protocol boundary

Outer RSC transport success is not application success. The bridge validates nested Luau or runtime results before the runner records an operation as successful. Every reviewable run carries source, fixture, operation, manifest, and review-artifact identity metadata; the available evidence types are recorded separately.
