# BloxBench knowledge boundary

BloxBench evaluates construction ability, not access to a hidden corpus or undocumented API trivia.

## what generation consumes

Comparable generation arms receive the same versioned public Roblox context from:

```text
scripts/benchmark/knowledge/<profile>.txt
```

The active profile is `roblox-core-v1`. Its content and SHA-256 digest are recorded in generation manifests and propagated into evaluation bundles and pairwise packets.

A fixture may also declare task provenance, such as a hand-authored origin, a real-world atlas record, or a corpus-derived design reference. Provenance identifies where the task idea came from. It is not evidence that the candidate is correct, licensed, or high quality.

## what generation does not consume

The benchmark does not feed these directly to a model:

- raw files from `/root/roblox-corpus-analysis`
- copied source trees such as `crosswalk/mined/src/`
- Roblox asset IDs, mesh IDs, sound IDs, or image IDs extracted from corpus data
- `roblox-brain` skill files as hidden task context
- reference fixtures or evaluator implementation source
- corpus-derived code examples that have not passed an explicit release review

The corpus and `roblox-brain` repositories remain read-only research inputs. BloxBench should consume any future derived material through a checked-in, versioned knowledge release with input hashes and provenance, not by reading those repositories at generation time.

## contamination policy

A task-set or knowledge release must record:

- source repository or archive identity
- source commit, archive hash, or equivalent immutable digest
- source record or artifact identifiers
- license and permission status, using `unknown` when it cannot be established
- the transformation that produced the released abstraction
- the release version and generation date
- exclusions used to keep held-out evaluation tasks from leaking into model context

Unknown licensing is not treated as permission. Static corpus frequency is not treated as a quality claim. Raw source and third-party assets are not copied into the benchmark merely because they are useful examples.

## current status

- `roblox-core-v1` is a hand-maintained public API/context profile.
- A corpus/atlas-derived knowledge release has not yet been generated.
- The checked-in suite is still the three-task diagnostic pilot.
- The planned v1 suite is 25 balanced tasks with a frozen suite manifest.

Until that release exists, corpus and atlas material may inform task selection and author research, but it must not silently change the shared model context or enter a generation arm without a new versioned profile and hash.
