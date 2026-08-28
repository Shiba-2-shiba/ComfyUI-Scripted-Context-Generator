# Test Specification: Female Protagonist Natural Prompts

## 1. Test dimensions

評価fixtureは最低でも次を直交的に含める。

- source: JSON / prompts.jsonl / character profile
- subject: named profile / generic female role / ambiguous role / legacy subject
- location: indoor / outdoor / work / school / retail / fantasy / sci-fi
- action: object-free / object-bound / posture-heavy / social / fallback-generated
- mood: positive / neutral / negative / high-arousal / low-arousal
- seed: fixed representative set + larger audit range
- history: empty / repeated verb / repeated object / repeated location / repeated template

## 2. Unit tests

### Identity

- `ProtagonistState` adapter preserves entity id, female presentation, count=1, pronouns and profile traits.
- unknown legacy extras survive round-trip.
- ambiguous subject follows documented fallback without inventing age or appearance.
- male pronouns or additional people are rejected in default solo mode.
- explicit/legacy non-female payload remains readable and round-trippable, but natural rendering returns a stable unsupported-identity reason and uses the documented fallback.
- recognized namespaced GenerationModel takes precedence over legacy fields; unknown schema versions follow the documented fallback without data loss.

### Constraint engine

- hard conflicts are rejected and include stable reason codes.
- soft conflicts alter ranking but do not make all candidates unreachable.
- diversity penalties depend only on bounded relevant history.
- fallback candidates pass the same constraints.
- ConstraintResult reason codes, total penalty and survivor count are stable and serializable, while domain candidate types remain domain-specific.

### Action frame and realization

- parser maps legacy strings to stable slots.
- renderer preserves subject-verb agreement.
- duplicate semantic roles are emitted once.
- missing optional slots do not create fragments or dangling punctuation.
- lexical and syntax choices are deterministic by seed.
- persisted ActionFrame equals the debug slot payload after legacy-string parsing and generation.
- identity / scene / action / lexical / syntax / template named seed streams are individually reproducible.

### Selection memory

- verb/object/location histories are independently bounded.
- legacy debug history is used only for one-time migration into SelectionMemory.
- selection behavior no longer depends on unrelated DebugInfo fields or trace length.
- template/syntax selection is not persisted because PromptBuilder does not return updated context; its reproducibility and diversity are verified as named-seed distributions.

## 3. Integration tests

- Full ContextSource → Character → Scene → Clothing → Location → Mood → Garnish → PromptBuilder flow.
- Every stage preserves protagonist identity.
- location/action/object/clothing/emotion combinations satisfy hard constraints.
- history produces measurable variation without changing fixed-seed replay.
- source/runtime action pool and compatibility CSV remain synchronized.
- PromptCleaner does not remove required subject/action semantics.
- `composition_mode=False` remains on the legacy renderer; `composition_mode=True` can shadow-generate legacy/new results and roll back without changing the public node contract.
- Phase 7B verifies the updated recommended workflow and the expected widget-default change to natural mode while retaining explicit False as rollback.

## 4. Statistical quality audits

For a versioned stratified corpus, report:

- female protagonist coverage
- other-person / pronoun / subject drift rate
- hard and soft contradiction counts by reason code
- exact duplicate and normalized duplicate rate
- repeated 2/3/4-gram concentration
- action verb, action object, location, semantic family entropy
- intro/body/end and syntax family coverage
- fallback rate and candidate exhaustion rate
- survivor count distribution and hard/soft/diversity penalty counts
- mean/p95 prompt length and context JSON size

Initial numeric thresholds must be derived from the Phase 0 baseline. Absolute invariants are:

- female protagonist coverage = 100%
- hard contradiction count = 0
- deterministic replay mismatch = 0
- invalid workflow round-trip = 0

All other metrics require non-regression first, then a separately recorded improvement target.

## 5. Human evaluation

Use blind paired comparison on a stratified sample. Score 1-5 for:

- protagonist clarity
- internal consistency
- grammatical naturalness
- redundancy
- semantic variety
- suitability as an image-generation prompt

Record evaluator count, sample ids, seed, pipeline version and disagreement. Do not promote a phase solely on automated lexical diversity if human consistency or naturalness regresses.

Phase 0 must publish a versioned quality contract containing a fixed stratified sample size, minimum evaluator count, paired-preference promotion threshold, and non-regression thresholds for protagonist attribute retention and image-prompt suitability. Later phases may not redefine these thresholds without a reviewed plan change.

## 6. Compatibility tests

- `PromptContext` JSON old → new → old-readable round-trip.
- public node `INPUT_TYPES`, `RETURN_TYPES`, `RETURN_NAMES`, `FUNCTION`, widget order unchanged.
- Phase 7B permits only the reviewed `composition_mode` default-value expected-diff; field order, field type and socket contract remain unchanged.
- hidden legacy arguments remain accepted/no-op where currently promised.
- frontend schema validation passes.
- LGraph configure/serialize snapshot passes.
- browser import/save/reload snapshot passes.

## 7. Stop conditions

Stop the current rollout phase when any of the following occurs:

- fixed-seed output changes outside the phase's approved expected-diff fixture;
- hard contradiction appears;
- public node or workflow contract changes unexpectedly;
- source/runtime generated data diverges;
- diversity improves only by increasing contradiction, fragment, or fallback rates;
- no candidate survives normal constraints for a supported location/action family.
- a named seed stream changes outside the stage being intentionally switched.
