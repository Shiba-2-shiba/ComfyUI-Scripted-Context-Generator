# R43-05 — Scene trace and reconstruction

State: PASS (R43-05 acceptance only, 2026-09-11 JST).
Start source: `69870cf195583d3cc50ae765c2761754f9a5eedeb2f42cbd16181000b5bc1876`.
The accepted Clothing snapshot and all prior work are preserved.

## Cleanup plan before code

1. Lock current simple/detailed and auto/off output/debug/RNG before moving
   selected segments into internal text+source records. Keep original filtering,
   probabilities, draw order, shuffle length and text-based dedupe semantics.
2. Add optional internal Scene producer trace with atomic field references,
   pack/default origins, final emitted order and dedupe suppression. Reuse the
   actual final join/sanitize helper; no public/context trace fields.
3. Share existing scene grammar/constituent parsing with a history-bound adapter.
   Use latest LocationExpander pack/mode/selected_props and available section_changes;
   absent optional semantic history is not fabricated. Compare current/raw/frame
   location identities and reject conflicts instead of choosing a favorable one.
4. Preserve gallery-owned predicates and each-work -> works references explicitly.
   Only existing bounded grammar is allowed. Unsupported weather/crowd, source
   ambiguity and unproved ownership remain unknown with original text retained.
5. Connect the common evidence Scene component only. Runtime proof is a bound
   constructor; complete exact replay requires earlier lighting/action/mood/recent
   inputs and remains a separate audit-only measurement. Do not change family gates.
6. Verify whole512 output/debug parity, producer trace/source order, RNG post-state,
   default mixing/dedupe, negative bindings and root/package fresh-process replay.
   Extend cached source identity to relevant Scene code/catalogs; keep V150/A1.6,
   public I/O, the R43 metric contract and existing reachability results unchanged.

Scope: location_builder.py, v2_scene_provenance.py, common evidence factory,
bounded Scene tests and docs. No new vocabulary, dependencies, public nodes,
semantic selection or family permissions. Next task after acceptance: R43-06.
Adoption remains BLOCKED; no main merge/push or N2.8/D3.

## Implemented result

`expand_location_prompt(..., trace_sink=...)` keeps its existing output/debug
contract. Internal text/source records follow the original choices and shuffle;
dedupe still compares text, even when fields differ. Atomic environment/core/
props/texture/details/time/weather/crowd/fx parts retain source field, original
pre-normalization value hash and pack/default origin. Trace-only candidate
identities distinguish duplicate normalized text and pack/default duplicates.
Existing FX first-occurrence behavior is preserved; public debug stays plain JSON.

Post-shuffle duplicate segments and sampled cores rejected by the existing repeat
risk budget retain explicit omission rules. Accepted/emitted order and random
draws are unchanged. `_assemble_location_prompt` shares final join/sanitization
between producer and bound reconstruction. No trace is serialized into context.

The common Scene adapter uses the latest LocationExpander pack/mode/selected_props
and available section_changes. Missing optional semantic diagnostics are not
filled with defaults. Contradictory current/raw/frame location identities are
rejected. Runtime proof is `bound_constructor`: historical lighting, action,
mood and recent-object settings are not available in full at the Builder.

Existing scene grammar is shared with raw source components, without changing
the legacy parser/family path. Runtime binding additionally rejects competing
normalized source origins, including bare weather/crowd that resembles a prefixed
core segment, single joined catalog values versus multiple cores, and ambiguous
environment/segment boundaries. Unknown source/grammar retains the whole original
scene text in an UNKNOWN atom instead of discarding the unsupported clauses.

Gallery predicates remain attached to the scene head. Works/plaques predicates
retain their own grammatical subjects and scene owner; each-work references
require exactly one earlier works atom. Wrong/missing/forward references remain
unknown. No new grammar lexicon or family permission was introduced.

## Fresh512 measurements

| Observation | Result |
|---|---:|
| Complete-input producer trace/direct replay | 512/512, audit-only |
| Local RNG post-state comparisons | 512/512 match |
| Runtime-available bound Scene constructors | 10/512 |
| Runtime exact historical replay | 0; required earlier settings absent |
| Unproved source/grammar, original text retained | 502 |
| Defaults-origin selected parts | 232 |
| Sampled cores omitted by repeat-risk budget | 9 |
| Post-shuffle text duplicates in this cohort | 0; covered by controlled fixtures |
| Bound each-work reference atoms | 1 |

The nine source fields are all measured. Six environments use the existing
loc_tag fallback; their origin is explicitly input-derived, not falsely marked
as pack environment text. All10 bound constructors' emitted field/origin/raw hash/
text sequences match actual producer traces. All512 mutated-history bindings are
rejected. Source-available proof counts are separate from ordinary generation:
v2 remains9/512 across3 families and all previous audit counters/blockers match.

## Verification and source identity

Final full source-tree SHA-256:
`0781fb1204b07bba7dc97af26711f6a989d7334f0118651099b5b4f81fa3143c`.
Bounded runtime source identity:
`8c8151d9ada97fb23c520e7a1f01fb36e4907c8348290b8b477eee50fe783d4e`.
Receipt inventory: [r43_scene_summary.json](./r43_scene_summary.json).
Ignored final evidence beneath original main:
`assets/results/diversity_refactor/r43/scene-final-03/`.
Read-only source: `assets/results/diversity_refactor/r43/scene-base-20260911-03/`.
Earlier scene-final-01/02 outputs remain stored and are superseded.

- Focused278 tests/1,963 subtests and regression87 tests/33 subtests pass, exit0;
  19 test IDs added, none removed, no exclusions/skips.
- The pre-edit2,736-row baseline (114 packs x6 seeds xsimple/detailed xauto/off)
  retains identical prompt, debug and local RNG post-state hashes. Trace/plain
  coverage additionally checks all packs, semantic off/passive/active, defaults,
  raw normalization collisions, suppressed draws, shuffle and cross-field dedupe.
- Ordinary512 raw/cleaned/upstream/Builder debug/context/whole records are identical
  to R43-04; existing reachability domains/families/routes/blockers are unchanged.
- Full renderer replay and runtime Scene evidence match across root/ascending/
  hashseed0 and separate read-only package/reverse/hashseed123 runs without a side
  channel. Exact audit-only inputs are never passed to the runtime history adapter.
- V150 protected120 files, public signatures/default serialization, A1.6 lock,
  metric contract, saved sources and original main/user files remain intact.
- Python3.10 AST and diff checks pass; execution used Python3.12.10. Independent
  review approved origin-ambiguity, antecedent-order and omission corrections.

Scene evidence SHA-256:
`92a35c91246f63408071be898fdc470852d4b2650d0c4f2c4419f9eff2423f06`.
Changed source: `pipeline/location_builder.py`, `pipeline/v2_scene_provenance.py`,
`pipeline/realization_evidence.py`, `assets/test_r43_scene_trace.py`,
`assets/test_r43_scene_binding.py`; result/summary and progress entry documents.

All R43-05 acceptance conditions are satisfied. Unsupported weather/crowd and
other source/grammar gaps remain unknown. Overall R4.3 architecture/development
acceptance remains NOT_RUN; full suite/frontend/browser/formal8192/2048/fixed80/
release gates are NOT_RUN and typecheck unconfigured. Adoption remains BLOCKED.
Next: R43-06 Template/Subject/Garnish/Mood adapters. No commit/merge/push or N2.8/D3.
