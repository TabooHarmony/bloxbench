# BloxBench manual review packet

A pairwise packet contains two matched, blinded candidate arms and the evidence available for review.

## labels

Use exactly one label:

- `A better`
- `B better`
- `tie`
- `both bad`

Pairwise preference is the holistic quality signal. Runtime checks, artifact hashes, warnings, reset state, usage, and time remain diagnostic dimensions.

## evidence

The packet may contain diagnostic screenshots, viewport-proven videos, generated place files, and presentation-game artifacts.

Screenshots are diagnostic evidence during the current Studio phase. They do not prove hidden state, dynamic gameplay, timing, multiplayer behavior, or causal attribution. Reviewers should judge only what the attached evidence actually shows.

A run with warnings can remain reviewable. A run with evidence gaps can remain reviewable when another artifact, such as a generated place or presentation output, is available. A run with no reviewable artifact is recorded separately and is not silently converted into a quality judgment.

`evidence_gaps` and `evidence_summary` describe availability. They are not quality scores and do not replace the human decision.

## blind-boundary files

- `packet.json`: reviewer-facing packet metadata and blinded A/B artifacts. It contains no source-to-A/B mapping.
- `human_review.md`: readable review instructions and diagnostic context.
- `review_form.json`: the form the reviewer fills in.
- `provenance_internal` sidecar: parent-only A/B-to-source mapping written beside the packet as a hidden file. Keep it out of the reviewer handoff.
- `human_decision.json`: the normalized decision written after ingestion.

## record a decision

After filling `review_form.json`, run:

```bash
python3 scripts/benchmark/record_human_review.py path/to/packet
```

The command validates the label, preserves the notes hash, records the reviewer and timestamp, and writes `human_decision` into `packet.json`. It does not create an automated quality score. Existing decisions cannot be overwritten unless `--replace` is supplied explicitly.

The packet records the effective fixture, prompt, knowledge context, treatment, source hashes, and artifact provenance internally. Model identity and the A/B mapping stay out of the reviewer-facing files.
