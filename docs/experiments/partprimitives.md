# PartPrimitives Experiment

## status

rejected. The matched cottage replicate was a useful positive data point, but it was expensive and did not generalize to the three-eval architecture smoke. Preserve the module and instrumentation for historical reproduction only.

## hypothesis

A small composition API can improve decomposition and connected placement by making common structures explicit: walls with openings, pitched roofs, limbs, stacks, and primitive parts.

## current implementation

`PartPrimitives.lua` is uploaded in `--primitives` mode. Recent fixes cover:

- real rectangular window gaps, including door plus window combinations
- roof placement from the support top plane
- orientation-independent limb segment alignment
- explicit `P.limb` origin-face anchors for top, bottom, left, right, front, and back attachments
- primitive calls counted as edits and recorded by constructor type
- structural flags placed before the capped structure listing

## old evidence

Earlier primitive runs were not sufficient validation:

- bridge: 19 rounds, approximately 313K input tokens, 8 floating parts, 136 overlaps
- dragon: 5 rounds, approximately 80K input tokens, 56 parts, 3 floating parts, 73 overlaps

Those numbers came before the current geometry and measurement fixes. They should not be used as a success claim.

## smoke result: `primitives_0709_1321`

The infrastructure path completed both evals with screenshots and incremental results. The aggregate `100%` is not a quality pass because the run used `--no-gate` and the harness marked both evals `passed_cons: false` and `passed_all: false`.

- cottage: 23 rounds, 500,635 input tokens, 10 edits, 85 parts, 11 floating parts, 41 overlaps. The exterior is recognizable and the wall openings, door, porch, and windows are visible. The roof is boxy and several fascia, sill, handle, and chimney pieces are structurally flagged as floating. One eval exhausted the 500K budget.
- dragon: 11 rounds, 198,057 input tokens, 8 edits, 85 parts, 7 floating parts, 88 overlaps. The pedestal is grounded, but the head is visibly detached above the body and several limb, tail, wing, pillar, and flame pieces are disconnected. The dark material/lighting makes the anatomy difficult to judge.

No visual judge ran. Human screenshot review is the current verdict: execution succeeded, but this smoke does not justify the full ten-eval run.

## follow-up results

`primitives_0709_1347` and `primitives_0709_1353` were infrastructure failures before model construction. `primitives_0709_1402` was a diagnostic run that exposed an over-escaped primitive trace regex. They are not quality data.

`primitives_0709_1405` was the first clean dragon-only run after fixing that regex:

- primitive usage was confirmed: `block=5`, `limb=17`, `ball=4`, `wedge=4`
- 58 total parts, 15 floating parts, 33 overlaps
- `--no-gate` execution passed, but `passed_cons=false`; no visual quality promotion

The smallest demonstrated API fix added explicit `P.limb` origin-face anchors. `primitives_0709_1411` used the new API:

- primitive usage: `floor=1`, `block=7`, `limb=10`, `wedge=5`, `ball=2`
- 49 total parts, 12 floating parts, 71 overlaps
- one harness `execute_luau` error was recovered without aborting the run
- screenshots remained too dark and structurally cluttered for a quality pass

## deterministic anchor calibration

`anchor_calibration_0709_160219` tested the API without an LLM. The returned positions show exact face joins:

- body top is `y=7.5`; `CalNeck_1` bottom is `y=7.5`
- body bottom is `y=2.5`; `CalLeg_1` top is `y=2.5`
- body left/right faces are `x=-5/+5`; the first wing inner faces land on those values
- body back face is `z=-6`; `CalTail_1` starts at that face
- subsequent segments continue from the previous segment endpoint

The generic structural checker reported six floating parts, but all six were horizontal side/tail segments. The checker only recognizes vertical top support, so these are false positives for this calibration. The two floor/leg overlaps are intentional contact with the floor. The screenshot framing was partial, so the coordinate dump is the authoritative calibration result.

The latest clean-model-error run `primitives_0709_1621` had zero model tool errors and `primitive_duplicate_names=0`. It produced 32 primitive links from 10 limb calls, 54 total parts, ground contact, 14 generic floating flags, and 77 generic overlaps. The screenshots still show an almost-black cuboid statue with a weak silhouette, long stick-like limbs/tail, floating fragments, and no convincing dragon readability. `passed_cons=false` under the run's execution-only `--no-gate` mode.

The near-clean run `primitives_0709_1616` was visually better and also had no duplicate primitive names, but it still had one model execute error and remained crude. The clean run removes the partial-execution explanation without rescuing the visual result.

## cottage replicate

The matched cottage-only replicate completed with zero model tool errors on both sides:

- vanilla `vanilla_0709_1644`: 128 parts, 8 generic floating flags, 274 overlaps, 8 edits, 14 rounds, 292,763 input tokens
- primitives `primitives_0709_1648`: 71 parts, 4 generic floating flags, 53 overlaps, 5 edits, 25 rounds, 493,206 input tokens

The primitive screenshot is materially more recognizable, with a roof, chimney, porch, and wall framing. It still has a malformed upper roof block and costs substantially more context, so this is a narrow positive signal, not a promotion.

`vanilla_0709_1631` used the same model and matched two-eval settings without primitive injection. It is the first useful directional control, although the cottage had three model tool errors and both runs used `--no-gate`.

- cottage: 113 parts, 10 generic floating flags, 231 overlaps, 11 edits
- dragon: 60 parts, 13 generic floating flags, 58 overlaps, 1 edit, zero model tool errors

Compared with `primitives_0709_1321`, the primitive cottage used fewer parts and had far fewer generic overlaps, and its front facade was clearer in the reviewed screenshot. Its roof was still detached/boxy. The primitive dragon was not better: the final clean run `primitives_0709_1621` had 54 parts, 14 generic floating flags, 77 overlaps, and a worse silhouette than vanilla despite zero model tool errors and zero duplicate primitive names.

This is evidence for a possible architecture-only benefit, not a general construction win.

## architecture smoke result

`primitives_0709_1653` tested cottage, watchtower, and market stall with primitive injection. It did not justify an architecture-only arm:

- cottage: hit the 500,000 input-token budget at 20 rounds, leaving only 8 parts and a wall-only partial build
- watchtower: 35 parts, 4 generic floating flags, 23 overlaps; the screenshot was almost entirely black and not visually judgeable
- market stall: 35 parts, 2 generic floating flags, 29 overlaps, one model tool error; the screenshot was black and incomplete-looking

All three used `--no-gate`, all had `passed_cons=false`, and no visual judge ran. The smoke is execution data, not a quality pass.

The matched cottage-only replicate was a real but non-repeatable positive signal: primitives used 71 parts versus vanilla's 128 and produced a clearer screenshot, but used 493K input tokens and 25 rounds. The subsequent three-eval architecture smoke hit the token cap on cottage and produced unreadable watchtower and market stall screenshots. This does not support an architecture-only benchmark arm.

## current verdict

Reject `PartPrimitives` as a benchmark intervention. Do not run the full ten-building experiment or more prompt/geometry iterations on this API. Keep the code, calibration, primitive-link report, and artifacts for historical reproduction. The next useful work must target decomposition or model behavior directly, or pause the construction benchmark.
