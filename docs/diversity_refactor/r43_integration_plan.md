# R43-08 — Runtime integration and real-graph evidence

State: BLOCKED (R43-08 acceptance; limited integration verified, 2026-09-12 JST).

This is the first limited-integration checkpoint. The subsequent
[placement pass](./r43_placement_plan.md) proves all six families on real inputs;
new ordinary applications remain the unresolved R43-08 acceptance condition.

That condition is satisfied by the subsequent [ordinary-application pass](./r43_ordinary_plan.md).
This document retains the earlier checkpoint evidence and limitations.
Start source: `2bf39ee99bcc5fa9010891c2ddf8451cc9194cb8647887d099870e9e021d4faf`.

## Cleanup plan before code

1. Preserve the full accepted R43-07 source and run pre-edit focused tests.
2. Inspect actual seven-domain intersections, including only-Garnish blockers.
   Repair received-context reconstruction using existing producer/Builder policy
   functions before adding grammar. Record omissions without restoring suppressed
   facts or counting audit-only inputs as runtime proof.
3. Preserve the legacy accepted path first. Only its fallback inputs may enter
   common evidence/proof and existing sorted seed-based family selection.
   Keep complete proof/trace in detached audit receipts, not serialized context.
4. Ensure the normal and diagnostic paths share current Builder input assembly.
   Update diagnostics to identify common selection/forcing without changing the
   meaning of existing metrics or weakening unknown semantic parity.
5. Add real-graph fixture receipts and negative binding/ownership/transport tests
   before runtime changes. Preserve upstream choices, existing9 successes, all
   unchanged fallbacks, semantic frame, public I/O, V150 and A1.6.
6. Run paired512, per-family forcing, source-atom checks and fresh root/package/
   reversed-order/hashseed replay alongside focused/regression/validators/full
   flow and independent review. Record unattained families as BLOCKED; never
   substitute recombinations for real-graph evidence or start R43-09 prematurely.

Scope: support/source reconstruction justified by measured blockers, common
family materialization if existing grammar permits it, Builder/bridge plumbing,
read-only reachability diagnostics, integration tests/fixtures and docs.
No seed/full-action allowlists, semantic reselection, broad vocabulary expansion,
new dependencies, public schema changes, favorable audit edits or N2.8/D3.

Baseline and evidence relative to original main:
`assets/results/diversity_refactor/r43/integration-20260912-01/`.
Adoption remains BLOCKED; no main merge/push.

## Implemented and verified scope

The normal Builder now supplies its received context, current component strings,
selected entries and explicit composition_mode to the common route. The bridge
tries existing compatibility rendering first and returns all accepted outputs
unchanged. Only an actual fallback considers new proof and the existing sorted
mix_seed-based selection. Common input fields/frame/seed must match the current
bridge invocation. Full proof and transforms stay in detached audit receipts.

Garnish reconstruction reuses _arbitrate_prompt_cues, subject normalization and
the solo-support budget. Latest final_tags must reproduce raw received garnish.
If current text differs, all original Builder policy inputs are required; the
existing functions must reproduce that exact current text. Selected raw parts,
emitted IDs and exact/semantic-budget/solo-budget omissions are recorded separately.
Unknown emitted grammar remains UNKNOWN; omitted facts are not restored.
No grammar rule, complete-action list or source vocabulary was added.

Read-only diagnostics recognize actual common selection and reconstruct forced
families from the source plan and current evidence. Existing metric definitions
remain unchanged: changed text does not earn semantic parity from word counts,
and only exact ordinary raw/cleaned equality earns that existing certificate.
Legacy diagnostics are unchanged.

Optional noncanonical context values such as NaN cannot grant common evidence.
The strict factory still rejects them; the optional runtime/diagnostic boundary
preserves the previous fallback and records invalid_inputs outside context.
Proof/constructor mismatches remain errors rather than being swallowed.

## Real-graph measurements

| Measurement, fixed512 inputs | R43-07 | This pass |
|---|---:|---:|
| Garnish source binding | 122 | 512 |
| All emitted Garnish atoms grammar-known | 65 | 386 |
| Common eligible standalone-scene inputs | 0 | 4 |
| Common eligible inputs for each other family | 0 | 0 |
| Ordinary v2 applications | 9 | 9 |
| Ordinary executed v2 families | 3 | 3 |
| Structures including v1 fallback | 4 | 4 |

390 post-policy garnish reconstructions succeeded. Each of512 raw garnishes
already matched its recorded final_tags; the old failure was comparing raw
selection directly with the post-policy string.

Common standalone proof now succeeds on four unchanged inputs (88/190/234/482).
All four forced results match their existing raw and cleaned outputs exactly.
They are prior compatibility successes, so compatibility priority intentionally
preserves their usual execution. They are not new ordinary applications.
Source-valid recombination tests exercise fallback-to-common runtime integration,
but are labelled synthetic and never counted as new real-graph successes.

## Acceptance remains BLOCKED

- New ordinary success count:0. All9 previous successes and503 fallbacks remain
  byte-identical; upstream context and semantic core/frame are unchanged.
- Five common families still have no eligible/forced real-graph example.
- Inputs88/190/482 have unproved place overlap and/or temporal/bedroom placement.
  UNKNOWN cannot become non-overlap. Input234 has an owned-finite room wrapper
  restricted to standalone and body-owned brows garnish; actor fronting cannot
  relabel that body subject or discard the wrapper.
- Complete Action grammar remains12/512, and Scene source/grammar10/512. Many
  remaining inputs need multiple source/grammar proofs, not a family-label change.

The implementation plan's section18 A/C/D applies: source trace is not grammar,
missing family constructors need attachment/owner proof, and incremental rescue
of individual strings/seeds must not replace a reusable design. This pass stops
before broad or unsupported grammar additions. Further R43-08 work should design
the exact owned-wrapper/actor-garnish placements and choose producer grammar work
from measured intersections. No six-family claim or R43-09 handoff is made.

## Verification and source

Final source:
`e4742266368e68aaee3e3aa82fe03850c8186f4267f0c7cb9f77d80bf84663ec`.
Summary/receipt inventory: [r43_integration_summary.json](./r43_integration_summary.json).
Final evidence relative to original main:
`assets/results/diversity_refactor/r43/integration-20260912-01/final-02/`.
The previous final-01 receipts are retained and superseded after the NaN regression fix.

- Pre-edit348 focused tests/1,963 subtests passed against the exact R43-07 snapshot.
- Final374 focused tests/1,963 subtests and87 regressions/33 subtests passed.
  27 test IDs added and1 renamed/updated: the old sink-only evidence contract is
  replaced by runtime-fallback evidence plus rollback isolation. No skipped or
  excluded tests. New tests include9 unchanged real-graph success receipts.
- All validators, V150 sizing, assets and full-flow checks exit0.
- Paired512 ordinary raw/cleaned/upstream/context/debug/whole records and legacy
  reachability metrics match R43-07. Four common forced raw/cleaned outputs also match.
- Common evidence,3,072 family rows and recombination receipts reproduce exactly
  across root/ascending/hashseed0 and separate snapshot/package/reverse/hashseed123.
  RNG/context and public contracts are unchanged;512 stale input mutations rejected.
- Protected120 V150 files, A1.6 lock, metric contract, stable main and existing user
  files are intact. Python3.10 AST and git diff whitespace checks pass.
- Independent review approved the limited integration after the malformed-input
  regression correction. Constructor errors remain visible.

Changed source: `pipeline/v2_support_provenance.py`,
`pipeline/v2_candidate_bridge.py`, `pipeline/prompt_orchestrator.py`,
`pipeline/realization_evidence.py`, `prompt_renderer.py`,
`tools/realizer_reachability_diagnostics.py`.
Tests: new `assets/test_r43_garnish_reconstruction.py`,
`assets/test_r43_runtime_integration.py`, `assets/test_r43_common_diagnostics.py`,
updated `assets/test_r43_support_transport.py`, and new
`assets/fixtures/r43_real_graph_cases.json`.
Simplification: reuse existing cue policies and the common proof engine instead
of recreating policy or granting source membership blanket grammar permission.

Full suite/frontend/browser/formal gates remain NOT_RUN; typecheck unconfigured.
Architecture/development acceptance NOT_RUN; adoption BLOCKED. No commit/merge/push
or N2.8/D3. Next: remaining R43-08 proof work; R43-09 has not started.
