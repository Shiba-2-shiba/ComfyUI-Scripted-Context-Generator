# R43-08 continued — Owned placement and reviewed Scene binding

State: PASS (placement pass); R43-08 acceptance BLOCKED (2026-09-12 JST).

Historical placement checkpoint. The subsequent [ordinary-application pass](./r43_ordinary_plan.md)
adds a new source-proved ordinary v2 case and completes R43-08 acceptance.
Start source: `e4742266368e68aaee3e3aa82fe03850c8186f4267f0c7cb9f77d80bf84663ec`.

## Cleanup plan before code

1. Preserve accepted limited integration and run focused baseline.
2. Reuse existing reviewed legacy Scene grammar with exact selected-field/default/
   history binding in the common adapter. Keep the existing legacy runtime path
   unchanged, reject ambiguous origins and do not add vocabulary.
3. Use the existing relative Scene constructor only on this source-bound reviewed
   route; preserve its exact order/attachment and leading-temporal rejection.
   Do not use it to bypass modern producer-owned Scene restrictions.
4. Separate actor-controlled fronted action from protagonist-owned Garnish.
   Move proved Garnish into the subject parenthetical, preserve its grammatical
   body subject/owner, map it to the actual destination and keep every atom once.
   An independent/body Action atom still prevents action-leading.
5. Add an owned with-absolute template constructor for non-action-leading
   placements. Preserve the room/scene owner and her reference. Keep standalone
   finite rendering unchanged; never use with-absolute as an is-locative predicate.
6. Add negative and recombination tests before changes, then force all families
   on unchanged real-graph inputs, checking final output, source-atom retention,
   owner/reference, normal compatibility preservation and fresh-process replay.
7. Record ordinary expansion separately. If no new ordinary success remains,
   R43-08 remains BLOCKED even when six-family real-graph forcing is attained.

Scope: common Scene adapter/constructor access, common family construction and
proof, template helper, minimal shared formatter option and regression fixtures.
No source vocabulary, seed allowlists, semantic reselection, public schema,
metric thresholds, new dependency or main/N2.8/D3 changes.

Independent design review permits exact legacy temporal-constructor reuse only
on its existing reviewed grammar route, not a general temporal-safe fact.
Evidence relative to original main:
`assets/results/diversity_refactor/r43/placement-20260912-01/`.

## Implemented result

Common Scene binding now reuses the existing reviewed legacy grammar in addition
to the previous nominal constructors. The adapter still checks current pack,
raw/default origin, selected fields, history, frame and normalized-source
ambiguities. The public legacy constructor path is unchanged. The new reviewed
trace is explicitly identified; only that route may reuse the exact legacy
relative constructor, including its existing temporal order and leading-time
rejection. It supplies no generic temporal-safe fact.

Action-leading fronts only proved actor-controlled Action atoms. Independently
proved protagonist-owned Garnish moves into the subject parenthetical. Body
grammatical subjects remain body subjects; source-atom mappings follow the actual
destination. The formatter restores the closing comma after normalization.
Body/external Action atoms still reject action-leading.

Owned room/scene templates now have a with-absolute constructor for four additional
layouts. The owner and her-reference remain explicit. Standalone finite wording
is preserved, and action-leading still rejects the absolute wrapper as an invalid
locative predicate. These additions do not change template selection or vocabulary.

## Unchanged real-graph proof

| Family | Runtime-common eligible /512 | Forced actual v2 /512 |
|---|---:|---:|
| subject_action_scene | 2 | 2 |
| subject_action__scene_tail | 5 | 5 |
| scene_lead_subject_action | 2 | 2 |
| action_lead_subject_scene | 1 | 1 |
| subject_scene_action | 2 | 2 |
| subject_action_scene_insert | 2 | 2 |

All six families now reach unmodified real-graph input, not just recombinations.
There are14 successful seed-family rows across5 inputs. Actual input51 proves all
six through its bound reviewed Scene; input234 proves five with its owned wrapper.
The three other common successes remain standalone only. These fixture identifiers
describe observed evidence; runtime has no seed conditions.

Scene source/grammar binding increases10→13/512. Garnish binding512 and known
emitted grammar386 are unchanged. Ordinary output remains9/512 v2 across3 families
and4 structures including fallback. All new common eligible inputs are already
accepted by the compatibility path, whose output is intentionally retained.
New ordinary success count remains0, so R43-08 acceptance is still BLOCKED.

## Semantic and regression evidence

Real-graph tests exercise the complete finalizer and PromptCleaner for all six
actual51 outputs. They check each emitted action/scene/mood/garnish source part,
separately named hair and eye attributes, clothing retention, output order and
the parenthetical boundary. Owner and antecedent tests cover the room wrapper,
gallery siblings, wrong body owners and source ambiguity. Extra controlled cases
are explicitly recombinations and not added to real-graph counts.

Independent review printed and read all six actual51 surfaces and ran35 new
tests. The exact legacy relative clause retains its source order and temporal
attachment. Changed forced wording is not marked exact ordinary parity in the
locked audit; source-atom tests and scoped semantic review are separate evidence.
Formal global quality/semantic certification has not been run.

Final verification, all commands exit0:

- Pre-edit374 focused tests/1,963 subtests.
- Final409 focused tests/1,963 subtests,87 regressions/33 subtests.
  36 test IDs added and1 renamed/updated for the new owned-wrapper contract;
  another existing diagnostics assertion now checks the five proved alternatives
  while retaining action-leading rejection. No skips or exclusions.
- Existing validators, V150 sizing, assets and full flow PASS.
- Paired512 ordinary raw/cleaned/upstream/context/debug/whole records and all
  legacy reachability counters are byte-identical to the pre-edit source.
- Common evidence,3,072 family rows and recombination receipts are byte-identical
  in fresh root/ascending/hashseed0 and separate snapshot/package/reverse/hashseed123.
  No proof/constructor mismatch or RNG mutation;512 stale inputs rejected.
- Public node/default serialization,120 protected V150 files, A1.6/metric
  contract, stable main and previous user files preserved. Python3.10 AST and
  git diff whitespace checks PASS. No dependency added; typecheck unconfigured.

Final source:
`0c8c421de459f62afa8731d60994d23a4409165b726095e5b24c13d363ebd281`.
Source-bound summary and SHA-256 inventory:
[r43_placement_summary.json](./r43_placement_summary.json).
Final evidence relative to original main:
`assets/results/diversity_refactor/r43/placement-20260912-01/final-02/`.
final-01 is retained with its obsolete diagnostics expectation failure; it is
superseded by the corrected final-02 collection.

Changed source: `pipeline/v2_scene_provenance.py`,
`pipeline/family_capabilities.py`, `pipeline/v2_template_provenance.py`,
`pipeline/prompt_realizer.py`. New tests:
`assets/test_r43_reviewed_scene_binding.py`, `assets/test_r43_owned_placement.py`,
`assets/test_r43_real_graph_placement.py`; updated family/diagnostic contract tests.
Simplification: reuse reviewed Scene grammar and the shared formatter; separate
actual fronted Action from owned Garnish rather than conflate their subjects.

Remaining R43-08 condition: a new safely proved ordinary application. The remaining
fallback inputs require producer grammar/binding work beyond placement alone;
use the measured domain intersections, not individual complete-string additions.
Architecture/development and formal/full-suite/frontend/browser gates remain
NOT_RUN; adoption BLOCKED. R43-09, main merge/push and N2.8/D3 remain unstarted.
