# R43-06 — Template / Subject / Garnish / Mood adapters

State: PASS (R43-06 acceptance only, 2026-09-12 JST).
Start source: `0781fb1204b07bba7dc97af26711f6a989d7334f0118651099b5b4f81fa3143c`.

## Cleanup plan before code

1. Preserve all uncommitted R43-00..05 work in a hash-verified source snapshot;
   run the existing focused regression collection before runtime edits.
2. Adapt exact selected template entries (key/text/roles/topology), using existing
   direct and owned-finite recognition. Catalog membership alone proves no grammar.
3. Adapt received subject/profile and current garnish/mood through existing bounded
   rules. Keep origin, grammatical subject and owner separate; missing, changed or
   unsupported input remains UNKNOWN with its original text retained.
4. Pass selected entries and current post-policy inputs inside the same Builder
   call to common evidence diagnostics. Do not serialize evidence into context,
   change semantic selection, RNG, family permission or existing metric definitions.
5. Add positive/negative binding tests before adapter edits; measure all seven
   common components separately from the locked legacy reachability counters.
6. Verify focused/regression/validators/full-flow, source-bound paired512, common
   evidence repeatability across fresh root/package interpreters and hash seeds,
   protected V150 data, public contracts and unchanged A1.6.

Scope: common evidence, template/direct provenance helpers as needed, a bounded
support adapter module, renderer/bridge diagnostic input plumbing, tests and docs.
No grammar/lexicon expansion, dependency, public API, family authorization or formal
evaluation. Large-blocker constructor decision: measure existing support rules
first. Future extensions require single/pair blocker evidence and R43-07/08 proof.

Adoption BLOCKED. Main is untouched. Next task after acceptance: R43-07.

## Implemented result

All seven common evidence components now have adapters. The four support domains
reuse the existing profile constructor, closed support rules and direct/owned-finite
template classifier. They introduce no new grammar or family permission.

Template binding compares the complete normalized selected entry, including
key/text/roles and selection metadata, with the current catalog. Unsupported or
changed fragments retain UNKNOWN atoms. Exact attention-suffix removal is recorded
as an observed omission, with pruning-condition UNKNOWN; it grants no topology.
Owned room/scene wrappers keep their grammatical subject and the protagonist
reference separate from ownership.

Subject binding requires the received current subject and named profile constructor
to match, including available appearance/palette metadata. Garnish requires the latest
received final_tags to reproduce the current text. Changed post-policy garnish
remains unbound; filtered-away selections are not invented. Mood binds the recorded
raw key and current description while independently checking the existing grammar.
Explicit empty garnish selection differs from missing selection.

The renderer builds common evidence only when its existing audit sink is requested.
Its inputs are the received context and current post-policy values plus entries
selected in that same call. The receipt is detached and JSON-serializable; no
evidence enters public debug/history/context. Normal execution and rollback incur
no evidence construction. This diagnostic path does not enable family selection.

## Fresh512 evidence

| Component | Source bound from runtime inputs | All current atoms grammar-known |
|---|---:|---:|
| Subject | 491 | 243 |
| Garnish | 122 | 65 |
| Mood | 512 | 312 |
| Template | 512 | 208 |

Counts are out of512; source-bound counts include grammar UNKNOWN. They are not
eligible-family counts or exact historical producer replays. All seven domains
are recorded in the separate common-evidence receipt. Locked legacy reachability
metrics and their definitions remain unchanged.

The largest new support blockers are garnish source binding390, unknown template
topology304, subject grammar248 and mood grammar200. Four inputs have garnish as
their sole blocked common component. The complete common view also reports
Action/Scene as a blocked-domain pair on494 inputs. These intersections are
diagnostics, not estimates of recoverable v2 cases; family-specific proof is still
required. No new wrapper/lexicon was added to rescue individual seeds.

## Verification

Final source hash:
`72988cdef49384d5d61ead709280497af59e2ab400a3f85dc1cad0ecf358deaf`.
Receipt inventory: [r43_support_summary.json](./r43_support_summary.json).
Evidence relative to original main:
`assets/results/diversity_refactor/r43/support-20260912-01/final-02/`.
Pre-edit snapshot: the sibling `baseline/` under `support-20260912-01/`.

- Before edits:278 focused tests/1,963 subtests passed against the exact R43-05 hash.
- Final:299 focused tests/1,963 subtests and87 regression tests/33 subtests passed;
  21 test IDs added, none removed, no skips or exclusions.
- All existing data/asset validators, V150 sizing and full-flow checks passed.
- Paired512 raw/cleaned/upstream/context/debug/whole records match the saved R43-05
  source exactly; all legacy reachability counters are unchanged. Ordinary v2
  remains9/512 across3 families,4 structures including fallback.
- Common evidence reproduces byte-for-byte in fresh root/ascending/hashseed0 and
  separate snapshot/package/reverse/hashseed123 processes. All512 stale-input
  mutations are rejected; RNG and received contexts are unchanged.
- Public signatures/default serialization, protected120 V150 files, A1.6,
  metric contract, original main and existing user files match preserved evidence.
- Python3.10 AST and git diff whitespace checks pass. Independent review approved
  the final correction separating attachment categories from owner IDs.

Changed source/tests: `pipeline/realization_evidence.py`,
`pipeline/v2_template_provenance.py`, new `pipeline/v2_support_provenance.py`,
`pipeline/prompt_orchestrator.py`, `prompt_renderer.py`, and new
`assets/test_r43_{support_binding,template_binding,support_transport}.py`.
Source simplification: reuse the existing constructors/rules and replace four
adapter-not-implemented placeholders with common typed components; no new dependency.

The earlier final-01 run is retained but superseded after the review correction.
Full suite/frontend/browser/formal8192/2048/fixed80/release gates remain NOT_RUN;
typecheck is unconfigured. Overall architecture/development acceptance remains
NOT_RUN and adoption BLOCKED. Next R43-07 owns family-specific proof/constructors.
