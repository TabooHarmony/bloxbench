# Decomposition Protocol Experiment

## status

rejected. This was tested as a plain-text model-side decomposition intervention after the primitive API was rejected. The first matched run looked promising, but a clean replicate produced a non-watchtower with giant floating cylinders. It is not reliable enough to keep as a benchmark arm.

## intervention

The protocol is plain text injected into the model system prompt with `--protocol-path`. It does not upload a module, add a geometry API, or change the eval prompts.

It requires the model to:

- plan a root, primary-mass, secondary, and detail hierarchy
- build the recognizable silhouette before detail
- preserve parent connections from actual workspace instances
- build one subsystem per edit and inspect between subsystems
- make edits retry-safe and inspect after tool errors
- finish with a coherence pass for grounding, required features, contrast, and attachment

## first matched run

`vanilla_0709_1723` versus `protocol_0709_1730` gave a positive directional result:

- protocol had 0 model tool errors versus vanilla's 18.18%
- protocol averaged 175,058 input tokens versus vanilla's 242,176
- protocol averaged 55 parts versus vanilla's 133
- protocol averaged 7 floating flags versus vanilla's 44
- protocol averaged 65 overlaps versus vanilla's 190.5

Manual review found the protocol cottage simpler but more coherent, and the protocol watchtower cleaner while still recognizable. This was promising, not sufficient.

## replicate

`vanilla_0709_1737` versus `protocol_0709_1747` broke the promotion case:

- protocol cottage: 45 parts, 2 floating flags, 26 overlaps, 0 model tool errors; sparse but coherent
- protocol watchtower: 41 parts, 4 floating flags, 48 overlaps, 0 model tool errors; giant floating cylinders and disconnected pieces, not a watchtower
- vanilla watchtower: 249 parts, 34 floating flags, 383 overlaps, 5 model tool errors; visually recognizable despite poor structural metrics
- vanilla cottage hit the 500,000-token budget; protocol did not

The protocol reduced cost and geometry, but the watchtower failure shows that it can produce a smaller incomplete or miscomposed result rather than a better construction. Raw counts do not rescue this.

## current verdict

Reject the decomposition protocol as a benchmark intervention. Do not broaden it or tune it through more blind runs. Preserve the prompt, runners, matched artifacts, and screenshots. Pause the construction benchmark until a more specific decomposition intervention has a falsifiable design.
