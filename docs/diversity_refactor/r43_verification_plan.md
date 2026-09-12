# R43-09 — Portable development verification

State: PASS (R43-09 acceptance, 2026-09-12 JST).
Start source: `1eaca58955044461c335702ea0a398bab8fb9958f0a82fcb01a312d7f979d79a`.

## Cleanup plan before code

1. Preserve the accepted source and run focused baseline.
2. Move the existing replay/expansion evidence logic from ignored drivers into
   portable tracked tools, reusing the canonical runner, existing audit, common
   proof engine and semantic projections. Add no new metric or workflow runner.
3. Extend the thin verifier with intake and bounded adoption-preflight stages.
   Run dependent checks in order and bind all receipts to unchanged source,
   cohort, lock and actual test collections/outcomes. Invalid/missing evidence
   fails closed; existing output directories and dependencies are untouched.
4. Record tests/subtests/skips/deselections/xfail/xpass/errors separately. Keep
   canonical verdicts free of absolute paths, time and nondeterministic log hashes.
5. Require a source-bound prose review receipt for development acceptance; do not
   infer ownership/naturalness from semantic signatures or test counts alone.
6. Compare old/current source in separate processes and replay current inputs in
   fresh root/package interpreters with actual hashseed/order changes. Verify the
   new commands from a clean copied checkout with no ignored-driver imports.
7. Report architecture, development and adoption separately. The64/512 and5-family
   guide controls automatic formal handoff, not the section13.2 development verdict.
   Formal/full-suite/frontend/browser results stay NOT_RUN.

Scope: verifier/replay/preservation support tools, their contract tests and
source-bound verification/review documentation. Runtime, data, A1.6, selection,
public contracts and grammar remain unchanged. No new dependency or main/N2.8/D3.

## Portable verification interface

Run from the development source root, using a new output directory each time:

```powershell
python tools/verify_realizer_v2_candidate.py --stage focused --output-dir assets/results/r43-focused-01
python tools/verify_realizer_v2_candidate.py --stage regression --output-dir assets/results/r43-regression-01
python tools/verify_realizer_v2_candidate.py --stage intake --baseline-root <frozen-nine-case-source> --output-dir assets/results/r43-intake-01
python tools/verify_realizer_v2_candidate.py --stage adoption-preflight --intake-root assets/results/r43-intake-01 --v150-baseline-root <stable-v150-preservation-source> --output-dir assets/results/r43-preflight-01
```

The intake baseline must be a distinct saved development source whose unchanged
512 cohort has9 v2 cases. It is not the original V150 formal baseline. Source,
protected/public/data inputs and A1.6 must match the appropriate comparison
contract. No ZIP, ignored helper import, hardcoded developer path or dependency
installation is used. Source and output paths are ordinary CLI arguments.

Intake composes existing focused/regression validators, the existing audit,
isolated baseline_pairs, portable expansion preservation, and root/package
replay of received Builder inputs. It validates actual constructor results and
new ordinary text against a source/input/prose-bound review receipt. A future
runtime/input/output change invalidates that review rather than inheriting PASS.
The default scoped review is r43_development_review.json; it is not a blinded
formal quality review. An explicit --review-receipt may provide another current review.

Test accounting records selected/executed IDs, setup/call/teardown, tests and
subtests, runtime/collection skips, deselections, xfail/xpass and collection errors.
Unexecuted tests or exceptional outcomes cannot masquerade as a clean pass.
Exit codes:0 pass,1 measured verification failure,2 missing/invalid/error evidence.
Adoption-preflight returns2/BLOCKED while prerequisites remain unmet.

Canonical verdicts reference canonical child artifacts only. Commands, elapsed
time, log hashes and absolute paths are separate records. Source changes are
INVALID. Replay uses actual PYTHONHASHSEED0/123 without -I/-E and checks the
interpreter flags/hash sentinel; package replay excludes the source root from
flat sys.path. Existing output directories are never overwritten.

## Verified judgments

| Judgment | Result |
|---|---|
| architecture_status | PASS |
| development_status | PASS |
| adoption_status | BLOCKED |
| ordinary v2 /512 | 10 (baseline9, new1) |
| ordinary executed families | 3 |
| forced unchanged-real-graph families | 6 |
| development guide64/512 and5 ordinary families | NOT MET |
| formal reference8192/gate2048/fixed80/release8192 | NOT_RUN |

The section13.2 development conditions pass: new ordinary application, preservation
of old successes/fallbacks and semantic/upstream choices, six-family real proof,
zero constructor mismatch and scoped final-prose review. The64/5 guide is separate;
it prevents automatic heavy formal evaluation and remains an improvement target.

Adoption-preflight identified the supplied stable V150 main source and matching
protected inputs, verified the saved intake/source/supplemental/lock identities,
then returned BLOCKED for the unmet guide and required R43-10 formal baseline/
quality receipt validation. It neither ran nor certified any formal gate.

The supplied stable source is not the sealed original pre-N2 formal baseline.
The subsequent [R43-10 handoff](./r43_handoff.md) verifies that exact original
source separately and clarifies the preserved preflight receipt's source label.
The current CLI source check is a preservation prerequisite; original formal
comparison also needs the handoff's explicit allowed N2 metadata/config differences.

## Evidence and validation

Final source:
`1678a635b03d8e6e18e6a797b395511a51cc04c3f245f96c7c5a38e9ca17cf23`.
Summary and parent/child artifact hashes:
[r43_verification_summary.json](./r43_verification_summary.json).
Evidence relative to original main:
`assets/results/diversity_refactor/r43/verification-20260912-01/`.

- Pre-edit423 focused tests pass. Corrected intake runs492 focused tests and1,990
  subtests,87 regressions and33 subtests, all PASS;69 tests added, none removed.
  All skip/deselect/xfail/xpass/collection/setup/teardown failure counters are0.
- Existing validators, V150 sizing/assets/full flow and fresh baseline/current512
  expansion preservation pass. Original9 successes and502 remaining fallbacks
  remain unchanged; new ordinary prose is bound to the independently reviewed text.
- All6 real-graph families are forced, with current source/proof/constructor checks.
  Common evidence and final prose replay in independent root/package processes,
  reversed order and differing actual hash seeds. Runtime/source files are unchanged.
- The entire new intake CLI was rerun from a separate clean source copy containing
  only manifest and required supplemental inputs. Its canonical verdict is
  byte-identical to the development-root run; all referenced canonical hashes match.
- Adoption-preflight was also run from that clean copy, with stable V150 main
  explicitly supplied. BLOCKED/exit2 is the expected prerequisite outcome.
- Public/V150/A1.6, original main and previous user files preserved. Python3.10 AST
  and whitespace checks pass. Runtime/grammar/selection/data and dependencies unchanged.
- Independent review found three false-PASS/staleness gaps; failing regressions
  reproduced them, fixes passed re-review. accounting-probe/intake-01 remain
  unsuccessful historical probes; intake-02/fresh-intake are authoritative.

Changed tools: verify_realizer_v2_candidate.py and new realizer_candidate_intake.py,
realizer_candidate_replay.py, realizer_candidate_preservation.py. Changed tests:
test_r43_candidate_verifier.py and new candidate intake/replay/preservation and
test accounting suites. The scoped prose review is stored as a normal document.
Simplification: replace ignored session drivers with reusable thin tracked
wrappers over existing runner/grammar/projection logic, with explicit receipts.

No unrestricted full suite/frontend/browser/formal evaluation was performed;
typecheck remains unconfigured. Next: R43-10 conditional handoff. No automatic
formal execution, main merge/push, N2.8 or D3. Changes remain uncommitted.
