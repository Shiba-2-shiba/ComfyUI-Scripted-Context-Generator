# R43-01 — Import and metadata contracts

State: PASS (R43-01 acceptance only, 2026-09-11 JST).
Start HEAD: `9a2aa32c1e3a48d1d7ea51eb91aee42843dba021`.
Existing R43-00 documentation changes and all historical evidence are preserved.

## Cleanup plan before code

1. Lock the two distinct metadata contracts: plan-only v1 retains legacy aliases
   and text; Builder fallback retains the current canonical mapping, v1 version,
   origin, fallback reason and deterministic replay. Do not alter family mapping.
2. Reproduce package-mode failure in a fresh process without repository-root
   sys.path access. Compare root/package Builder output, JSON context transport,
   public node execution and module identity across independent source copies.
3. Repair only the function-local candidate bridge import using the existing
   package/non-package convention in `prompt_renderer.py`. Keep import lazy if
   that preserves existing module initialization behavior.
4. Add the minimal `tools/verify_realizer_v2_candidate.py` wrapper for existing
   focused/regression checks: sorted collection, commands/logs, source integrity,
   explicit failure statuses and no overwrite or dependency installation.
   Intake/adoption stages remain later work and must not report success here.
5. Run focused tests without exclusions, related regressions, validators/full
   flow, baseline output comparison and diff/static checks. Record actual source,
   collection hash, test-set delta and limits; update progress at task completion.

Smells: incorrect import boundary; one test conflating legacy and bridge metadata;
missing process/import transport coverage and reproducible validation entry point.
Scope: prompt_renderer.py, assets/test_prompt_realizer_v2.py, new bounded R43
import/transport and verifier tests, the minimal verifier, and progress documents.
No new dependencies, producer grammar, audit mapping, selection or public API
changes. Candidate07 raw/cleaned prompt and serialized debug remain the baseline.
Adoption remains BLOCKED. Next task after acceptance: R43-02.

## Result

The runtime diff is the lazy candidate bridge import's package/root selection in
`prompt_renderer.py`. A clean package import previously raised
`ModuleNotFoundError: No module named 'pipeline'`; both new process-boundary tests
reproduced this before the change. The import follows the existing package
convention and retains lazy initialization. No producer grammar or selector changed.

The existing alias test now strictly covers plan-only v1 text, aliases, empty
fallback reason and replay. A separate Builder test strictly preserves canonical
mapping, original alias, `realizer_version=v1`, `candidate_v2_applied=False`,
fallback reason, debug/context replay and input immutability. No assertion was
relaxed to accept both contracts interchangeably and no mapping was changed.

Fresh-process tests cover root/package output, received JSON with Builder history,
composition-mode rollback, actual public-node output, and independent runtime
source copies. Each process verifies module paths and ActionFrame/function
identity; package mode has no flat repository-root path or flat runtime modules.

The thin verifier provides `focused` and `regression` stages, exact sorted pytest
IDs/hash, explicit exit statuses, separated canonical receipts and timing/logs,
and no-overwrite behavior. It hashes supplemental inputs omitted by the existing
source manifest, including `assets/calc_variations.py`. Independent review found
that last omission; a mutation test now proves it returns INVALID/2. The earlier
run is retained as superseded evidence, and final checks were rerun after repair.
Intake/adoption stages remain unimplemented, not successful empty stages.

Final source-tree SHA-256:
`e44157bdbf706465d3f9f8531aad7f5d3e4281c108429fada51535ce51de1be1`.
Receipts: [r43_import_summary.json](./r43_import_summary.json).
Local evidence beneath the original main checkout:
`assets/results/diversity_refactor/r43/import-20260911-02/`.
The unchanged fresh baseline512 is explicitly reused from `import-20260911-01/`.

| Final check | Result |
|---|---|
| Focused, no exclusions/skips | 175 tests / 1,888 subtests passed; exit 0 |
| Context/schema/renderer/snapshot/vocab regression | 87 tests / 33 subtests passed; exit 0 |
| Existing validators, sizing, asset validation, full flow | All exit 0 |
| Whole workflow + existing Builder context, paired512 | Byte-identical records; raw/cleaned/context/debug mismatches 0 |
| Package replay of exact received inputs | All512 match root-mode results; includes existing9 actual v2 cases |
| Public I/O/serialization, V150 protected120, A1.6 lock | Unchanged |
| Changed Python AST (Python3.10 grammar), diff check | PASS; runtime executed on Python3.12.10 |
| Independent bounded code review | PASS after supplemental-source fix |
| Typecheck / full suite / frontend/browser / formal gates | Unconfigured / NOT_RUN / NOT_RUN / NOT_RUN |

Focused collection increased from152 to175: one Builder fallback test, two import
tests and20 verifier cases, with no removed IDs. The existing alias ID now covers
the low-level contract. The old exclusion is gone. Regression now pins the broader
context/schema/renderer/snapshot/vocab group; do not compare87 to the previous29
as if the test sets were identical. Exact IDs and set differences are retained.

Fresh ordinary v2 count remains9/512 across3 executed families; observed structure
names including fallback remain4 (fallback itself uses2). This task fixes import
and validation boundaries; it does not claim coverage or quality improvement.
Architecture/development acceptance for all of R4.3 remains NOT_RUN; adoption is
BLOCKED and N2.8/D3 remain unstarted. R43-01 acceptance is complete.

Changed source files: `prompt_renderer.py`, `assets/test_prompt_realizer_v2.py`,
`assets/test_r43_import_transport.py`, `assets/fixtures/r43_import_probe.py`,
`tools/verify_realizer_v2_candidate.py`, `assets/test_r43_candidate_verifier.py`.
Documentation: this plan/result, its JSON summary, progress/tasks, CURRENT_STATUS
and development_branch.md. Existing R43-00 artifacts and main/user files remain
unchanged. No commit, merge or push was made.
