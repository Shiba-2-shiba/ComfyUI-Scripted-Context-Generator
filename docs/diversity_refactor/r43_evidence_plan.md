# R43-03 — Common runtime evidence and binding

State: PASS (R43-03 acceptance only, 2026-09-11 JST).
Start source: `0cfe1bf8a508e83d7c93e853b526826e8326cebf11260d49b5ab3883d6432808`.
The read-only R43-AUDIT-BASE and earlier changes/receipts are preserved.

## Cleanup plan before code

1. Lock immutable tri-state contracts and stale/forged/version-mismatch rejection
   in focused tests. Binding covers every supplied semantic Builder input, exact
   action/frame bytes, selected template data and producer context/palette.
2. Add minimal frozen internal types in pipeline/realization_evidence.py. Keep
   unknown references as None, not empty tuples, and distinguish grammatical
   subject from owner. Explicit audit serialization stays outside PromptContext.
3. Adapt the existing ActionStructuralEvidence and legacy leaf/aggregate facts
   using the unchanged renderer/grammar. Preserve original ActionFrame semantic
   head separately from a clause's grammatical head; no new grammar inference.
4. Build and validate evidence by reconstructing current expected evidence, not
   by trusting a caller's checksum or booleans. Runtime source identity is a
   cached fingerprint of bounded code/loaded catalogs, not a per-prompt repo scan.
   It is named separately from the audit's complete source_tree_hash.
5. Expose the new internal API without connecting it to family authorization or
   changing the R43-02 metric contract. Other producer adapters remain explicitly
   unavailable until their owning tasks. FamilyProof/constructors belong to R43-07.
6. Verify all512 ordinary prompts/debug/context and existing reachability results
   against the saved source; test JSON transport, hashseed/process/import stability,
   public serialization, protected V150 data and A1.6. Save external typed-evidence
   receipts, then record acceptance and the remaining proof limits.

Scope: new common evidence module, an additive Action adapter in
v2_structural_evidence.py, bounded contract/adapter tests and documentation.
No source membership promotion, new dependency, public I/O, selection, family
permission or serialized context metadata. No R43-04 clothing work is started.
Adoption remains BLOCKED. Next task after acceptance: R43-04.

## Implemented boundary

`pipeline/realization_evidence.py` provides Truth, SourceRef, ProducerPart,
ProducerTrace, ClauseEvidence, EvidenceComponent and RealizationEvidence. Frozen
values reject mutable child containers. Truth requires explicit identity tests;
`bool(Truth.UNKNOWN)` raises rather than becoming a positive safety condition.
Place/antecedent/omission uncertainty remains None. FamilyProof and family
authorization are deferred to R43-07, where they acquire actual consumers.

`build_realization_evidence(builder_inputs, producer_context=...)` hashes all
supplied JSON-compatible semantic inputs without dropping unknown fields or
coercing keys. Explicit `action` and `action_frame` feed the Action adapter.
Selected template keys/text, context/history, palette and seed participate in the
binding when supplied. Missing/empty values differ. The factory does not infer
missing producer settings or read runner-only inputs. Non-Action components are
explicitly unavailable with adapter_not_implemented blockers.

`validate_evidence_binding()` rebuilds current expected evidence and compares both
typed values and canonical bytes. A matching digest cannot authorize changed
atoms, owner IDs, trace parts or runtime flags. It rejects old schema/source
identities, changed inputs and Python bool/int equality collisions. A valid
binding says the evidence matches its inputs; it does not say any family is safe.
External receipt dictionaries are not accepted as trusted runtime evidence.

The cached runtime source identity hashes a bounded list of source files and
loaded catalogs once at import, with relative names only. It represents the
imported process snapshot, not a live hot-reload detector or full repository tree.
Changed source requires a fresh process; the existing audit separately checks
whole-source and supplemental identities before/after each run. No Builder call
scans the repository, and no node-to-node trace cache was introduced.

The additive `adapt_action_component()` in `v2_structural_evidence.py` preserves
the original functions and their whitespace-normalized legacy behavior. New
common traces require exact current/frame/rendered bytes. SourceRef hashes the
original selected slot bytes even when the renderer strips whitespace. Only
emitted parts are inventoried; omitted parts/rules remain unknown. All three
existing replay cases (activity-first, legacy ordering, both modes yielding the
same unique trace) have distinct constructor IDs.

Legacy leaf and aggregate grammar facts are copied without widening recognition.
They remain grammar projections, not complete family proofs. Body eyes/hands/
fingers retain their grammatical subject separately from protagonist ownership;
external events have a distinct subject and unknown owner. Unknown leaves do not
acquire an actor or empty reference set. Compound grammatical heads are recorded
without overwriting the ActionFrame semantic main verb.

## Verification and result

Final full source-tree SHA-256:
`9e11acec3b8d16f280bbec453d8f0d3506baaa3a892fe565a9ee0beecbdcd6c7`.
Runtime evidence identity (different scope):
`7a3a721c800df92e3b4e0ed74c8ce2dc205a9662818335198be89232b87ab6a8`.
Tracked receipt inventory: [r43_evidence_summary.json](./r43_evidence_summary.json).
Ignored artifacts beneath original main:
`assets/results/diversity_refactor/r43/evidence-final-01/`.
Read-only source snapshot: `assets/results/diversity_refactor/r43/evidence-base-20260911/`.

| Check | Result |
|---|---|
| Focused, no exclusions/skips | 236 tests /1,931 subtests; exit0 |
| Regression | 87 tests /33 subtests; exit0 |
| Existing validators, V150 sizing, asset validation, full flow | All exit0 |
| Source-bound paired512 ordinary records/debug/context | All bytes unchanged from R43-02 |
| Existing reachability domains/families/routes/blockers | Unchanged; ordinary v2 remains9/512 across3 families |
| Typed inputs built and revalidated | 512/512; changed-action bindings rejected512/512 |
| Exact Action renderer replay | 512/512; this is source reconstruction, not full grammar permission |
| Evidence across root/package, forward/reverse order, hashseeds0/123/7, separate source snapshot | Identical canonical bytes |
| Public I/O/default serialization, protected120, A1.6 and metric contract | Unchanged |
| Changed Python AST with Python3.10 grammar, diff check, bounded independent review | PASS |

The new type contains2,818 Action atoms:994 with recognized legacy grammar and
1,824 UNKNOWN. Unknown omissions/antecedents remain null. Trace availability is
not the R43-02 aggregate runtime-eligibility metric and does not increase coverage.
Clothing/Scene/Template/Subject/Garnish/Mood adapters remain unavailable here.

Typed evidence SHA-256:
`41d5837308d75a399640df1d677e3646b6f21cda7069fba6c9ef56f122115966`.
34 focused test IDs were added, none removed. Tests include forged facts with an
unchanged digest, missing fields, raw whitespace/version changes, source/palette/
template/history changes, ownership and immutable input isolation. The initial
Action-adapter tests were RED before the shared module existed. Review independently
ran all34 new tests and9 subtests; full verification followed on frozen source.

Source changes: `pipeline/realization_evidence.py`, additive adapter in
`pipeline/v2_structural_evidence.py`, `assets/test_r43_evidence_contract.py`,
`assets/test_r43_action_evidence.py`. No selector, bridge, renderer, public schema,
data, audit metric or ordinary serialization changes were required for this task.
Plan/result/summary and progress entry documents complete the scope.

R43-03 acceptance is PASS. Overall R4.3 architecture/development acceptance remains
NOT_RUN; family authorization is not connected. Typecheck is unconfigured; full
suite, frontend/browser and formal8192/2048/fixed80/release gates are NOT_RUN.
Adoption remains BLOCKED. Next: R43-04 Clothing trace/reconstruction, with the
same conservative transport boundary. No commit/merge/push or N2.8/D3 was started.
