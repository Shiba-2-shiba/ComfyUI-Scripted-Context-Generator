# V150 resume: bounded cleanup and release

Continue the approved PRD and test specification for V150. Preserve existing edits.
Active source at entry: 2419bb4ef2498dc850cc6f7b185146232f3beb90f19cca1028c573ca23bbdf6e.

Scope: existing V150 preparation, verification and transactional promotion paths.
No speculative refactor. Investigate only concrete gate failures or independently
confirmed boundary defects. Before each code fix, run or add a focused regression
that protects the affected behavior, then apply the smallest correction. Remove
duplication or unnecessary indirection only in that affected path; no dependencies.

1. Freeze existing source into a fresh resume output; independently review promotion.
2. Run all six Python gates and actual frontend/browser gates against that snapshot.
3. Generate fresh automatic and semantic comparisons, two independent blind lanes,
   and three objective confirmation runs. Preserve failed and interrupted evidence.
4. Bind eleven gates, preflight against actual active data, independently review the
   completed evidence, then apply with rollback-protected postchecks.
5. Verify PROMOTED, exact 135/109/8227/150184 counts, full tests and runtime replay;
   update current docs after successful promotion and report remaining limitations.

If code changes, create a new snapshot and corresponding evidence. Existing v7
quality thresholds and all historical results remain intact. Do not stage or commit.

Confirmed cleanup pass: upstream oxlint reports two it.each uses and one inline
type import in verification/frontend/customNodeWorkflow*.test.ts. Existing real
Vitest 4 tests and 872 Python tests pass before editing. Replace it.each with
it.for for the same object cases and move ComfyWorkflowJSON to import type.
Retain cases, callbacks and assertions; rerun Vitest, scoped lint and typecheck
before freezing again. The first resume output remains historical evidence.

Second confirmed pass: preserve action-owned visual direction in
vocab/garnish/logic.py. Formal first-resume review rejected the candidate for
"checking the skyline beyond the tables" combined with "downcast eyes".
Two tests in assets/test_personality_garnish.py reproduced 22 failing subcases
before the narrow target/optional-gaze filter; 23 related tests pass after it.
Independent read-only comparison verified identical RNG state in 16 changed
cases and identical outputs/RNG for five unaffected controls. Fresh experiment:
v150-gaze-release-20260905. Retain the original review as rejected, never rerate.

Frontend validation after cleanup: real Vitest 4 pass, scoped oxlint pass,
vue-tsc --noEmit --incremental false pass. Object-case it.for behavior checked
against https://vitest.dev/api/test#test-for; callbacks/assertions unchanged.
