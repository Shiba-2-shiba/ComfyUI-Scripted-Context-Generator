# R43-04 — Clothing trace and reconstruction

State: PASS (R43-04 acceptance only, 2026-09-11 JST).
Start source: `9e11acec3b8d16f280bbec453d8f0d3506baaa3a892fe565a9ee0beecbdcd6c7`.
The accepted evidence-base snapshot and all earlier work are preserved.

## Cleanup plan before code

1. Lock current item/candidate/selector output, signature, decision and RNG behavior
   before extracting shared assembly/trace helpers. Keep all existing tuple APIs.
2. Produce immutable selected-part traces from the same item/candidate rendering
   helper, including drawn-but-suppressed material/state values. Expose selected
   attempt trace through an optional internal selector sink, without serializing it.
3. Add a history-bound Clothing adapter using only received Builder context.
   The latest ContextClothingExpander history has pack/type/variant/signature but
   deliberately removes prompt; bind current extras.clothing_prompt by uniquely
   reconstructing selected-pack parts and verifying the existing signatures.
4. Reuse current nominal/attachment rules for the existing single-garment boundary.
   Missing/stale/ambiguous history, ambiguous source fields, unsupported multiple
   garment/outerwear ownership, and unproved detail grammar stay unknown. Do not
   search unrelated packs or add new grammar to improve coverage.
5. Keep exact producer trace/replay with complete actual renderer inputs separate
   from runtime bound-constructor proof. History does not contain outfit_mode,
   outerwear_chance or original full state; never guess those to claim exact replay.
6. Connect only the common evidence factory's Clothing component. Extend its
   cached source identity to actual clothing code/catalogs. Keep legacy direct
   realization, family selection, public I/O and existing audit definitions intact.
7. Verify real512 output/debug parity, selected-attempt trace replay, grammar and
   negative cases, source/contract protection, root/package/hashseed determinism.
   Record new typed proof counts separately from unchanged ordinary v2 coverage.

Scope: clothing_candidate_renderer/selector, additive clothing provenance adapter,
common evidence factory, bounded tests and docs. clothing_builder/public nodes do
not need new metadata or inputs. No dependency, vocabulary, semantic selection,
family permission or A1.6 change. Next task after acceptance: R43-05.
Adoption remains BLOCKED; no main merge/push or N2.8/D3.

## Implemented result

The item renderer now uses one private selection helper and one shared
`_assemble_item_description` for text/signature assembly. The legacy API still
returns two values; `build_item_description_with_trace` additionally returns an
immutable ProducerTrace when RNG state is available. Source hashes retain raw
selected values, including list-shaped garment choices. Emitted order, palette
overrides, drawn-but-suppressed material and location-disallowed states are explicit.
RNGs without state do not receive an exact-replay trace.

`render_clothing_candidate(..., trace_sink=...)` preserves its existing tuple and
decision keys, and captures base/outerwear parts plus raw/sanitized hashes.
`select_clothing_candidate(..., trace_sink=...)` emits only the chosen attempt
after the unchanged scoring/selection loop. No trace enters history or extras,
and clothing_builder/public nodes needed no changes. Character-palette colors
have catalog_key=None, rather than claiming membership in the selected pack.

The additive history adapter reads the latest ContextClothingExpander entry only.
It verifies pack/type/theme/variant/signature and reconstructs the current text
from that pack through shared assembly. It does not decode variant strings into
invented original inputs or search other packs. Existing nominal/attachment code
is shared with the legacy materializer; no new noun/grammar table was introduced.
Both duplicate field origins and different raw choices that normalize/render to
the same signature are rejected before grammar filtering.

The common evidence factory now supplies a Clothing component from received
context. Runtime traces use `bound_constructor`, not exact historical node replay:
history lacks original outfit_mode, outerwear_chance and complete prior state.
Complete actual renderer arguments are available only to direct source callers
or the audit runner; those exact replays are counted separately. Multiple garments,
outerwear attachment, unsupported grammar and missing/ambiguous binding stay unknown.
No common family authorization or legacy family selection was enabled/changed.

Cached source identity now covers direct clothing code, sanitizer/location/seed
dependencies and relevant loaded catalogs. Catalog iteration order is retained
because choices/theme ordering affects RNG behavior. This still describes a fixed
imported source snapshot, with whole-source guards at audit boundaries.

## Fresh512 measurements

| Observation | Result |
|---|---:|
| Selected-attempt trace equals direct candidate replay | 512/512 |
| Runtime-available history-bound constructor proof | 102/512 |
| Runtime exact historical renderer replay | 0; required old settings absent |
| Audit-only complete-input renderer replay | 512/512 |
| Multiple-garment owner unknown | 182 |
| Outerwear attachment unknown | 134 |
| Nominal grammar unknown | 71 |
| Source ambiguity | 7 |
| Stale/incomplete selection history | 16 |

All102 bound constructors' emitted source fields/raw hashes/text match the actual
producer trace. The410 remaining cases do not receive a trace-based permission.
These are new typed component proofs, not102 ordinary v2 applications or an update
to the R43-02 audit definition. Existing ordinary v2 remains9/512 across3 families;
all prior reachability domains/families/routes/blockers remain unchanged.

Chosen attempt distribution:0=465,1=29,2=8,3=8,4=2. Runtime binding uses actual
selection records and does not assume that attempt0 won. All512 stale-history
binding mutations were rejected. The exact complete-input replay observations
were not passed into the runtime history adapter.

## Verification and source identity

Final source-tree SHA-256:
`69870cf195583d3cc50ae765c2761754f9a5eedeb2f42cbd16181000b5bc1876`.
Runtime evidence identity (bounded imported-source scope):
`bcc0feba90d7aa9f8943763cb746db4cb00c0287587a966ac85404fc088cb58f`.
Tracked receipt inventory: [r43_clothing_summary.json](./r43_clothing_summary.json).
Ignored evidence beneath original main:
`assets/results/diversity_refactor/r43/clothing-final-01/`.
Read-only source: `assets/results/diversity_refactor/r43/clothing-base-20260911/`.

- Focused259 tests/1,963 subtests and regression87 tests/33 subtests pass, exit0.
  There are23 added test IDs, none removed, no exclusions/skips.
- Pre-extraction golden hashes match for624 item and576 candidate outputs.
  Item trace/plain checks retain caller RNG state; an additional384 candidate
  comparisons retain internal RNG post-state, prompt and decision exactly.
- Actual512 raw/cleaned prompts, upstream context, Builder debug and whole records
  match R43-03 byte-for-byte. Existing reachability counters/blockers also match.
- Live trace/plain selector results and selected-attempt replay match all512,
  including nonzero attempts, history bytes and global RNG state.
- Root/ascending/hashseed0 and separate read-only package/reverse/hashseed123 runs
  produce identical trace/runtime-Clothing evidence bytes.
- Public signatures/default serialization, V150 protected120 files, A1.6 lock,
  metric contract, saved previous source and original main/user files are unchanged.
- Python3.10 AST, diff check and independent review pass; execution is Python3.12.10.
  Review corrected override source references and expanded fingerprint dependencies.

Clothing evidence SHA-256:
`a6f88a6731239c05ecf1b209ba76062088a5f3fa70e7d50650b391d91d4f5bb7`.
Tests cover multiple attempts, palette override and ambiguous origins, material
suppression, detail/state policies, outerwear, malformed/latest-stale history,
no all-pack scan, explicit null current text, and forged owner rejection.

Changed source: clothing_candidate_renderer.py, clothing_candidate_selector.py,
v2_clothing_provenance.py, realization_evidence.py, and three new
`assets/test_r43_clothing_{trace,selector_trace,binding}.py` files. Plan/result/JSON
summary and progress entry documents complete the scope.

All R43-04 acceptance conditions are satisfied. General multi-garment/outerwear
grammar remains unproved; typecheck is unconfigured; full suite, frontend/browser
and formal8192/2048/fixed80/release gates are NOT_RUN. Overall R4.3 architecture/
development acceptance remains NOT_RUN and adoption BLOCKED. Next: R43-05 Scene
trace/reconstruction. No commit/merge/push or N2.8/D3 was started.
