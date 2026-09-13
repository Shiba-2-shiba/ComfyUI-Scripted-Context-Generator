# R45 Capability Projection and Provenance Separation Design

**Repository:** `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`  
**Input branch:** `refactor/realizer-v2-r44`  
**Planning baseline HEAD:** `8c0dce2a6a2f485d683c306736b76a114bae3165`  
**R44 runtime/diagnostic source checkpoint:** `98a8ef33ab9a851240cf678864b0ed65879228e4`  
**R44 immutable diagnostic tag:** `realizer-v2-r44-blocked-20260913`  
**Planned implementation branch:** `refactor/realizer-v2-r45`  
**Date:** 2026-09-13

## 1. Problem statement

R44 successfully implemented source-bound diagnostic signatures and deterministic packet selection without changing runtime output. It then stopped at the viability gate because the fixed 512-seed cohort produced 511 full structural signatures: 510 singleton signatures and one two-seed signature. No group met the four-distinct-seed packet floor, so no runtime coverage packet was attempted.

This is not evidence that the development thresholds are too strict. It shows that the R44 grouping key is an excellent forensic fingerprint but is too specific to answer the development question:

> Which recurring producer capability, if proved once, could remove the same class of blocker across many independent seeds?

The second R44 finding is equally important. Common evidence still reports `action.leaf_grammar_unknown` for 498/512 cases and `scene.source_or_grammar_unknown` for 496/512. In Scene, source provenance and grammar recognition are still coupled closely enough that grammar failure often prevents a useful source trace from surviving into diagnostics.

R45 therefore changes the measurement abstraction, not the runtime language model.

## 2. Goal

R45 shall build a diagnostic layer that identifies recurring, source-bound producer capabilities across otherwise different prompts while preserving the R44 full signature for forensic replay.

R45 shall also separate Scene source binding from Scene grammatical proof so a current source can be known while its grammar remains explicitly `UNKNOWN`.

At the end of R45, the repository must be able to answer, for the preserved 512-seed cohort:

1. Which producer capabilities recur across distinct seeds?
2. Which blocker IDs co-occur with each capability?
3. Which syntax families are affected?
4. How many distinct seeds are represented by each capability and blocker intersection?
5. Which bounded capability implementations are rational candidates for R46?

R45 does **not** need to increase ordinary v2 execution above 11/512.

## 3. Non-goals

R45 must not:

- activate new Realizer v2 runtime cases;
- add a seventh or eighth syntax family;
- implement the Deterministic Diversity Scheduler;
- lower the `64/512` or `5 ordinary families` development guide;
- add new action/location/character vocabulary for coverage;
- modify V150 protected variation data;
- add an LLM, embedding model, parser package, or NLP dependency;
- change public `Context*` node I/O;
- change the `context_json` contract/version;
- run candidate reference8192, gate2048, fixed80, blind review, confirmation, frontend/browser, or release8192 formal gates;
- treat diagnostic capability data as runtime authorization;
- use seed IDs, complete prompt text, complete action text, or complete scene text as a capability key;
- create seed allowlists or phrase allowlists to manufacture coverage.

## 4. Approaches considered

### 4.1 Rejected: make the R44 full signature less detailed

Removing a few fields from `realizer-coverage-signature/v1` would create larger groups, but the resulting equivalence relation would be difficult to interpret. A single composite hash would still mix Action, Scene, Clothing, Template, Mood and family blockers. It would also weaken an already useful forensic artifact.

The R44 signature remains unchanged and continues to mean “this exact diagnostic structural state.”

### 4.2 Rejected: group only by blocker ID

Grouping `action.leaf_grammar_unknown` alone would produce large counts but would not identify whether the same producer construction is involved. A single blocker can cover many unrelated grammatical forms. Blocker-only groups would overstate reuse potential.

### 4.3 Selected: atomic capability projection plus blocker graph

R45 adds domain-scoped capability records. One seed may produce several capability records. A capability describes one producer-origin structural unit without incorporating unrelated domains.

The full R44 signature remains available for replay and debugging. Capability records are a second projection for development prioritization only.

## 5. Architectural model

```text
Current Builder inputs
        |
        v
RealizationEvidence
        |
        +------------------------------+
        |                              |
        v                              v
FamilyProof                     R44 full signature
(runtime authority)             (forensic fingerprint)
        |                              |
        |                              v
        |                       R45 capability projection
        |                              |
        |                              v
        |                    capability/blocker graph
        |                              |
        |                              v
        |                      R46 candidate ranking
        |
        +--> runtime realization only when existing proof is eligible
```

R45 diagnostic modules must never be imported by runtime authorization paths.

## 6. Blocker taxonomy normalization

R44 revealed a delimiter mismatch in the diagnostic selector contract. `family_capabilities.py` emits identifiers such as:

```text
family.required_fact_not_true:scene_lead_safe
family.forbidden_fact_not_false:scene_action_overlap
family.missing_slot:scene
```

while the R44 selector's repairable prefix list also contains dot-form prefixes. R45 shall introduce one canonical diagnostic normalization helper.

Canonical family blocker form is colon-delimited:

```text
family.required_fact_not_true:{fact}
family.forbidden_fact_not_false:{fact}
family.missing_slot:{slot}
```

Legacy dot-form diagnostic input may be accepted and normalized, but new output must use colon form. This helper remains diagnostic-only and does not alter `FamilyProof` production.

## 7. Capability projection schema

Schema ID:

```text
realizer-capability-projection/v1
```

Capability projection must use the typed `RealizationEvidence` graph, not parallel indexing of the R44 diagnostic arrays. This is required because some domains are not one-part/one-atom: for example a Clothing `ClauseEvidence` can own several `ProducerPart` values. `ClauseEvidence.source_part_ids` is the authoritative relation.

Each capability identity represents one source-bound `ClauseEvidence` atom plus the producer parts it explicitly references. It contains structural categories only, never complete source text.

Required fields:

```json
{
  "schema_version": "realizer-capability-projection/v1",
  "domain": "action",
  "capability_kind": "clause_atom",
  "producer_class": "pipeline.action_renderer",
  "constructor_class": "action_slots",
  "source_field_classes": ["primary_action"],
  "catalog_source_classes": ["producer"],
  "form_class": "unknown",
  "attachment_class": "unknown",
  "owner_class": "unknown",
  "grammar_state": "unknown",
  "source_bound": true
}
```

For Clothing, one atom can legitimately contain multiple source fields, for example `palette.colors` plus `choices.dresses`. Their order follows the atom's `source_part_ids` resolved against the current trace; no array-position guess is allowed.

The canonical capability hash is SHA-256 of canonical JSON for these fields only.

The hash must not include:

- seed;
- prompt/action/scene/source text;
- selected catalog key;
- selected vocabulary text hash;
- unrelated domains;
- all-family blocker sets;
- execution outcome.

`diagnose_snapshot()` attaches the projection to each reachability row only after the current R44 binding check reports `proof_basis=common_reconstructed`. A separate audit occurrence row later binds the capability hash to seed/family/blocker measurement context:

```json
{
  "run_seed": 42,
  "capability_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "domain": "action",
  "family": "subject_action_scene",
  "blocker_ids": ["action.leaf_grammar_unknown"]
}
```

Seed appears only in the occurrence/evidence layer, never in the capability identity.

## 8. Domain projection rules

### 8.1 Typed atom projection

For every `EvidenceComponent` with a current `ProducerTrace`, iterate `component.atoms`. For each atom:

1. resolve every `atom.source_part_ids` entry against `trace.parts`;
2. preserve the atom-declared source-part order;
3. project each referenced `SourceRef.field` to `source_field_classes`;
4. project each catalog origin to a bounded category (`producer`, `location_pack`, `background_defaults`, `selected_clothing_pack`, `character_palette`, `character_profile`, `template_catalog`, `mood_catalog`, or `catalog`);
5. use the atom's typed `form`, `attachment`, owner/subject relationship and `grammar_known` state;
6. ignore `source_text`, `ProducerPart.text`, and `selected_text_sha256`.

If a `source_part_id` cannot be resolved in the current trace, the projection is invalid and must fail closed rather than invent an identity.

Components with no trace or no atoms produce no capability identity. Their blockers remain available to the blocker audit from the reachability row.

### 8.2 Action

Action atoms naturally project source slots such as `primary_action`, `posture`, `hand_action`, `gaze_target`, and related structural ownership. Do not parse final prose again.

### 8.3 Scene

After R45 source/grammar separation, source-bound Scene atoms are projected even when `grammar_known=UNKNOWN`. Keep field classes such as `environment`, `core`, `texture`, `details`, `fx`, `weather`, `crowd`, `props`, and `time`, plus bounded `location_pack` / `background_defaults` origins. Discard the exact location pack key and selected text.

### 8.4 Other domains

Subject, Clothing, Garnish, Mood and Template use the same typed atom/source-part relation. R45 does not redesign their runtime adapters. The purpose is to expose cross-seed recurrence, not to authorize them.

## 9. Scene source provenance / grammar separation

Current Scene reconstruction can return `scene.source_or_grammar_unknown`, losing the distinction between:

1. current text cannot be bound to its producer source; and
2. source is exactly known but grammatical construction is unsupported.

R45 shall split these stages inside `pipeline/v2_scene_provenance.py`.

### 9.1 Source-binding stage

The source-binding stage may use:

- current `location_prompt`;
- current location key;
- `ContextLocationExpander` history;
- selected props;
- section changes;
- `background_packs` and `background_defaults` membership;
- exact assembly order and dedupe behavior;
- current action-frame location consistency.

It must not require a noun/attachment grammar rule to create a `ProducerTrace`.

### 9.2 Grammar stage

Each bound part is then passed to the existing closed grammar recognizers.

If recognized:

```text
grammar_known = TRUE
form / attachment / owner = proved values
```

If unrecognized:

```text
grammar_known = UNKNOWN
form = unknown
attachment = unknown
owner = null/unknown
```

The component may still be `runtime_available=True` in the same sense as Action: exact current producer provenance exists. `FamilyProof` remains blocked because `_prepare()` separately rejects any atom whose grammar is not `TRUE`.

### 9.3 Runtime-permission preservation guard

R45 must not accidentally widen runtime authorization even if the new source-only path recovers a Scene whose individual constituents happen to be recognized by the existing grammar.

Preserve the current combined source+grammar path as the R44 compatibility oracle. If that existing path accepts the Scene, keep its current behavior. If it rejects the Scene but the new source-only binder succeeds, the component must include:

```text
scene.r45_source_only_permission_deferred
```

in its blockers. Per-part grammar facts may still be recorded for diagnostics, but the deferred blocker remains until an explicit R46 capability task proves and adopts that source class. This guard is diagnostic-development debt, not a permanent public contract.

The refactor must prove by test that no Scene recovered only by the new source-only path can make a previously ineligible family eligible during R45.

## 10. Capability/blocker graph

R45 shall materialize a diagnostic graph as flat canonical records rather than introduce a graph dependency.

The graph has three logical node types:

- capability hash;
- canonical blocker ID;
- syntax family.

Measurement edges are keyed by `(run_seed, family)`.

Required summaries:

- capability distinct-seed count;
- capability seed-family-row count;
- blocker distinct-seed count;
- capability × blocker intersection count;
- capability × family count;
- blocker-pair distinct-seed count;
- top co-blockers for each capability;
- example seeds, capped separately from the complete internal seed set.

Counts named `distinct_seed_count` must be computed from set union and never from family-row counts.

## 11. R46 candidate ranking

R45 ranking is diagnostic only. A candidate is a recurring capability that:

- occurs on ordinary v1 fallback rows;
- is source-bound;
- has at least four distinct seeds;
- is associated with at least one repairable blocker;
- is not contaminated by hard binding/policy/transport failures;
- does not depend on exact prompt text or exact seed identity.

Rank by:

1. descending distinct seed count;
2. descending number of affected not-yet-ordinary syntax families;
3. ascending number of common co-blocker classes;
4. stable capability hash tie-break.

The report shall expose both:

- `affected_seed_count`: seeds that contain the capability;
- `single_capability_rescue_upper_bound`: seeds for which, for at least one family, every remaining blocker belongs to the same repairable domain/capability class after hard exclusions.

The second number is still an upper bound, not a promise of runtime success.

No runtime edit is automatically triggered by ranking.

## 12. Development verdict

R45 final status is one of:

### `READY_FOR_R46`

All preservation checks pass, Scene source/grammar separation is verified, and the capability audit finds reusable bounded candidates suitable for one-at-a-time runtime work.

Minimum readiness evidence:

- at least one capability group with `distinct_seed_count >= 4`;
- at least one candidate with nonzero `single_capability_rescue_upper_bound`;
- no ordinary output/context regression;
- no new family eligibility caused solely by diagnostic/provenance separation.

### `BLOCKED_CAPABILITY_MODEL`

The diagnostic model still fragments or cannot produce reusable candidate groups. Stop and redesign the abstraction. Do not lower the four-seed floor and do not begin runtime grammar expansion.

### `REJECTED_REGRESSION`

Any existing ordinary v2 success, fallback output, context, determinism, proof binding, protected input, or validation contract regresses.

## 13. Formal evaluation boundary

R45 is not an adoption candidate. Even `READY_FOR_R46` means only that the next bounded runtime capability work is justified.

The existing sequence remains:

```text
R45 capability diagnosis
    -> R46 bounded capability implementation
    -> >=64/512 ordinary v2 and >=5 ordinary families
    -> formal N2.7 candidate evaluation
    -> N2.8 activation decision
    -> D3 Deterministic Diversity Scheduler
```

## 14. File boundaries

New diagnostic files:

```text
tools/realizer_blocker_taxonomy.py
tools/realizer_capability_projection.py
tools/audit_realizer_capabilities.py
assets/test_r45_blocker_taxonomy.py
assets/test_r45_capability_projection.py
assets/test_r45_capability_audit.py
assets/test_r45_scene_provenance_separation.py
docs/diversity_refactor/R45_DESIGN.md
docs/diversity_refactor/R45_IMPLEMENTATION_PLAN.md
docs/diversity_refactor/r45_progress.md
docs/diversity_refactor/r45_handoff.md
```

Existing files expected to change:

```text
tools/select_r44_coverage_packets.py
tools/realizer_reachability_diagnostics.py
pipeline/v2_scene_provenance.py
assets/test_r43_common_diagnostics.py
docs/diversity_refactor/tasks.md
docs/diversity_refactor/progress.md
CURRENT_STATUS.md
```

Do not move runtime authorization into any new `tools/` module.

## 15. Testing strategy

Every implementation task uses red/green TDD.

Required test classes:

- delimiter normalization and hard-exclusion preservation;
- capability identity ignores text/seed but changes on structural role changes;
- capability grouping is independent of input row order and dict insertion order;
- complete seed union is separate from capped examples;
- Scene source trace survives unknown grammar;
- unknown Scene grammar remains `Truth.UNKNOWN` and does not grant a family proof;
- R44 full signature remains deterministic and available;
- ordinary 11/512 successes and 501 fallbacks remain byte-identical;
- focused/regression/R45 suites all pass;
- root/package/hashseed/order replay remains deterministic;
- protected V150 input hashes remain unchanged.

## 16. Decision summary

R44 correctly demonstrated that full-state equality is the wrong abstraction for selecting reusable coverage work. R45 keeps that evidence intact but adds a second, domain-local capability view. The critical runtime-facing refactor is limited to preserving Scene source provenance when grammar is unknown; authorization remains fail-closed.

R45 succeeds when the repository can identify high-yield, source-bound capability work for R46 without changing a single ordinary prompt.
