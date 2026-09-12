# R43-02 — Reachability audit

State: PASS (R43-02 acceptance only, 2026-09-11 JST).
Start source: `e44157bdbf706465d3f9f8531aad7f5d3e4281c108429fada51535ce51de1be1`.
R43-00/01 changes and evidence are preserved. No new grammar or family permission.

## Pre-code cleanup and verification plan

1. Freeze the accepted R43-01 source and reuse the sealed candidate07 baseline.
   Lock sink-free output/debug/context and RNG behavior with regression tests.
2. Add an internal optional, keyword-only diagnostic sink through the existing
   Builder call chain. Capture detached bridge inputs/decisions; keep diagnostics
   out of public node inputs and serialized context/history. Share existing final
   postprocessing so forced diagnostics use the actual normalizer/cleaner path.
3. Diagnose existing component constructors using their current helpers, retaining
   UNKNOWN for unproved source binding/ownership. Source membership is not grammar.
   Record route ceilings and required-fact failures separately from common fallback.
4. Implement a development-only audit that reuses build_canonical_record and exact
   Builder trace inputs, distinguishes run/Builder seeds, and separates six stages.
   Forced construction is off the ordinary path. Raw constructor success is not
   semantic certification: unavailable atom/ownership proof stays explicitly unknown
   and is excluded from certified forced-success counts.
5. Pin the cohort/diagnostic definitions in r43_metric_contract.json. Record source,
   supplemental files, catalog, workflow/config and A1.6 identities. Report domains,
   family/route counts, overlapping blockers, only-blocker counts, sets/pairs/triples
   and deterministic examples; do not count audit-only replay as runtime evidence.
6. Run tests/validators and paired512 against candidate07, with/without sink and
   forcing. Repeat canonical reports/rows for hash equality. Preserve an immutable
   R43-AUDIT-BASE snapshot. Mark any source mutation/replay mismatch as an error;
   do not overwrite earlier receipts or treat a changed cohort as regression.

Scope: internal sink/finalizer in prompt_renderer, prompt_orchestrator and bridge;
diagnostic helper and CLI under tools; contract JSON, bounded tests and documents.
Source-atom/owner constructor expansion belongs to later R43 tasks. No dependency,
vocabulary, public API, selection, alias mapping, A1.6 or schema changes.
Adoption remains BLOCKED. Only R43-02 is active; next task is R43-03 after acceptance.

## Result and evidence

R43-02 acceptance is complete. The optional sink follows only existing Builder
inputs through the orchestrator/renderer/bridge. It emits detached JSON outside
the returned context. Public nodes have no diagnostic inputs. Final substitution,
staging and normalization now use one shared `_finalize_prompt` implementation;
ordinary and forced output receive the same processing. No grammar, selection,
producer source, alias or safety permission changed.

`tools/audit_realizer_reachability.py` reuses the canonical workflow runner and
replays the exact resolved Builder seed/context from its trace. It records six
stages, seven domains, per-family blockers, singleton/full-set/pair/triple counts,
normal/fallback routes and input/source identity. `tools/realizer_reachability_diagnostics.py`
uses existing constructors and selector results; captured selectable membership is
authoritative, including a genuinely selectable baseline family on simple inputs.
Old R4 structural traces remain `legacy_direct`, not the future common-evidence route.

The diagnostic contract is [r43_metric_contract.json](./r43_metric_contract.json).
Audit-only upstream producer replay is NOT_RUN. Source binding, constructor
recognition and runtime evidence availability are distinct; unavailable binding
stays null even if a source-like phrase has recognized grammar. Forced output is
certified only when both final raw/cleaned text equal ordinary output. Changed
forced output retains NOT_AVAILABLE semantic parity; lexical comparisons are
auxiliary. Ordinary or forced proof/constructor mismatches are explicit errors.

Final source-tree SHA-256:
`0cfe1bf8a508e83d7c93e853b526826e8326cebf11260d49b5ab3883d6432808`.
Tracked receipt inventory: [r43_audit_summary.json](./r43_audit_summary.json).
Ignored evidence beneath the original main checkout:
`assets/results/diversity_refactor/r43/audit-final-02/`.
Read-only R43-AUDIT-BASE:
`assets/results/diversity_refactor/r43/audit-base-20260911-02/`.
The accepted R43-01 source was separately preserved in `audit-start-20260911/`.
Earlier smoke/final-01 outputs are superseded; final-02 is the final-source evidence.

### Fresh fixed512 result

| Family | Runtime eligible | Forced constructor v2 | Exact ordinary-output matches | Normal selected / executed v2 |
|---|---:|---:|---:|---:|
| subject_action_scene | 0 | NOT_RUN | NOT_RUN | 0 / 0 |
| subject_action__scene_tail | 9 | 9 | 7; 2 changed outputs UNKNOWN | 7 / 7 |
| scene_lead_subject_action | 4 | 4 | 1; 3 changed outputs UNKNOWN | 1 / 1 |
| action_lead_subject_scene | 0 | NOT_RUN | NOT_RUN | 0 / 0 |
| subject_scene_action | 4 | 4 | 1; 3 changed outputs UNKNOWN | 1 / 1 |
| subject_action_scene_insert | 0 | NOT_RUN | NOT_RUN | 0 / 0 |

All six families are declared and implemented, but only three are eligible on
this real workflow. Ordinary actual v2 remains **9/512**. Fallback structures:
subject_action_scene374 and subject_action__scene_tail129. Four structure names
are observed when fallback is included; this is not six-family execution.
Eligibility distribution:503 seeds with0,5 with1,4 with3 eligible families.
Routes: legacy_direct9, fallback503, simple_legacy_compatible0, common_evidence0.

There are17 successful forced constructor attempts:9 exact ordinary-output
matches and8 changed outputs with semantic parity UNKNOWN. No changed output was
promoted to a semantic success by word counting. The three ineligible families
were not forced around their safety/route guards.

Action current-text/slot-renderer replay binds512/512; recognized complete action
grammar is14/512 under this new diagnostic definition, not the historical primary
leaf count. Constructor grammar recognition counts are clothing124, scene16,
subject264, template208, garnish386 and mood312. The latter source bindings remain
unknown except the208 exact template topologies; recognition is not runtime coverage.

Blocker counts use **seed-family rows**, with overlapping IDs. Leading blockers
include unknown scene overlap3033, global frame proof3018 and action grammar3013.
Only `family.legacy_route_ceiling` appears alone, in11 seed-family rows; these are
not11 newly rescued seeds. The leading pair is global frame proof + unknown scene
overlap3018. Counts reflect current route constraints and intersecting component
failures, not a prediction that any single edit will produce those gains.

### Verification

- Focused:202 tests /1,922 subtests passed; no exclusions/skips, exit0.
- Regression:87 tests /33 subtests passed, exit0. Existing validators, V150 sizing,
  vocabulary/asset validation and full-flow all exit0.
- All512 raw/cleaned prompts, upstream context, existing Builder debug/context and
  whole canonical records match the sealed candidate07 start source in a separate
  interpreter. Original9 successful seeds retained; new/regressed successes0.
- Sink/plain context and prompt parity holds for all512. Global RNG is unchanged;
  tests also cover rollback, callback mutation and root/package identity.
- Repeated forced intake512 has byte-identical report/rows/records/normal pairs.
  The16-seed no-force run has identical normal records to the forced prefix.
- A fresh read-only source snapshot executes the new CLI without historical ZIPs
  or developer paths and matches current-source smoke rows/records.
- Public node signatures/default serialization, V150 protected120 files, A1.6 lock,
  original main/user files and saved comparison sources remain unchanged.
- Changed Python parses with Python3.10 grammar; execution used Python3.12.10.
  Diff check and independent bounded code review pass.

Rows SHA-256: `24707d73c2e9d7f235080694eb7df0a427f35c8d5f0d8dd2b799208dc841b307`.
Records SHA-256: `c384f01d708a546ac4a1b08ef1b9fd46bd1e8bb97d886032a56f616148a13bef`.
Exact collections and27 added test IDs (none removed) are retained in the receipts.

Changed runtime: `prompt_renderer.py`, `pipeline/prompt_orchestrator.py`,
`pipeline/v2_candidate_bridge.py`. New tools: audit CLI and diagnostics module.
New tests: `test_r43_runtime_transport.py`, `test_r43_reachability_diagnostics.py`,
`test_r43_reachability_audit.py`. Contract, this report/JSON summary and progress
entry documents complete the scope.

Typecheck is unconfigured. Full suite, frontend/browser, formal8192/2048/fixed80
and audit-only producer replay are NOT_RUN. All-R4.3 architecture/development
acceptance remains NOT_RUN and adoption BLOCKED. R43-03 common evidence/binding
is next; no new producer coverage, main merge/push or N2.8/D3 was started here.
