# Realizer v2 development branch

`main` contains V150 stable. `refactor/realizer-v2` contains candidate07 plus the
R43-01 import repair, R43-02 diagnostics, R43-03 evidence, R43-04/05 Clothing/Scene
reconstruction, R43-06 support adapters, R43-07 family proof and a limited R43-08
runtime integration at ordinary repository paths. Future development should
commit changes here directly. Candidate source no longer requires ZIP extraction.
Adoption remains **BLOCKED**; do not merge this branch into stable until the
unchanged formal 8192/2048/fixed80 gates and required family evidence pass.

## Checkpoint lineage

| Snapshot | Source commit |
| --- | --- |
| candidate04 | `b2d1261c46e9796e5f2b399cfa281b47990ccdfb` |
| candidate05 | `c0822f55a3ffb19368bdfeca5ebde66b0f56e006` |
| candidate06 | `f67798b791a0742b8918614495171414fa1663bb` |
| candidate07 | `24bbbfbfb7ef7a66d2997f47149d870dfb84e79a` |

These are consecutive commits on the same paths. For example:

```sh
git diff c0822f5 f67798b -- pipeline assets
git diff f67798b 24bbbfb -- pipeline assets
git diff main...refactor/realizer-v2
```

All 2510 archived file hashes were verified before migration. Every committed
source-manifest file and the additional runtime support files match the original
snapshot bytes for all four candidates. Candidate07's source hash remains
`b8a99c2fa84cc59e2ade7378d6614527a3bfe672d42e474d0dbaca6078c57472`.
Explicit `.gitattributes` entries preserve the checkpoint's CRLF files across
checkouts; changes to those attributes require rechecking source hashes.
Current documentation is retained instead of restoring stale snapshot documents.

The [checkpoint manifest](checkpoints/n27-r4-candidate04-07.json) records all four
source hashes. Historical observations, harnesses and ZIP recovery instructions
remain available through [checkpoints/README.md](checkpoints/README.md). The old
`verify_candidate.py` requires a stable root plus isolated candidates; it cannot
validate this development branch unchanged.

## Development verification

Run from the branch root with the existing Python test environment. Each command
requires a new output directory; replace the example directory for subsequent runs.
No dependency is installed by the verifier. Only focused/regression stages are
implemented; neither is a formal adoption gate.

```powershell
python tools/verify_realizer_v2_candidate.py --stage focused --output-dir assets/results/diversity_refactor/r43/local-focused-01
python tools/verify_realizer_v2_candidate.py --stage regression --output-dir assets/results/diversity_refactor/r43/local-regression-01
git diff --check main
```

Historical migration verification: 151 focused tests and 1888 subtests passed; 29 related
regressions passed; data/asset validation and full flow passed. The single excluded
test, `test_actual_v1_family_metadata_and_seed_replay`, is the previously recorded
candidate failure concerning v1 family aliases. R43-01 resolves that exclusion by
separating the plan-only v1 contract from Builder fallback metadata. Current
verification includes both contracts without exclusions. The import repair also
supports package-mode Builder execution without a flat repository-root import.
Results and source-bound paired512 evidence are in
[r43_import_plan.md](./r43_import_plan.md) and [progress.md](./progress.md).
Focused/regression results do not claim an unrestricted full-suite pass.
No typecheck configuration is present. Formal adoption gates were not rerun for
this storage-only migration, and no CI workflow was added.

## Development reachability (R43-02)

Use a new output directory on each invocation:

```powershell
python tools/audit_realizer_reachability.py --profile smoke --output-dir assets/results/diversity_refactor/r43/smoke-01
python tools/audit_realizer_reachability.py --profile intake --force-families all --output-dir assets/results/diversity_refactor/r43/intake-01
```

Smoke defaults to16, intake to512; these are not Effective Diversity profiles.
Optional `--baseline-root <saved-source-root>` compares ordinary output/debug in
a separate interpreter; a source without the sink has reachability NOT_AVAILABLE.
Unknown forcing/semantic proof is never reported as certified success. Existing
output directories and source changes fail closed. Full evidence and remaining
proof gaps: [r43_audit_plan.md](./r43_audit_plan.md). Adoption remains BLOCKED.

R43-03 adds immutable common evidence and an Action adapter, without connecting new
family authorization. Binding validation reconstructs current evidence; receipt
JSON/checksums are not trusted proof. Runtime fingerprints describe an imported
source snapshot, while audit runs guard full source before/after. Details and
512-case preservation: [r43_evidence_plan.md](./r43_evidence_plan.md).

R43-04 shares item assembly and selected-attempt traces, and binds Clothing from
received history without guessing historical renderer settings. Complete-input
audit replay stays separate from102 runtime-available bound constructors; ordinary
v2 coverage is unchanged. Verification and remaining ownership gaps:
[r43_clothing_plan.md](./r43_clothing_plan.md).

R43-05 retains Scene source/default origins and original selected hashes through
shuffle, text dedupe and repeat-risk suppression. Ten runtime-bound constructors
preserve known owners/references; missing historical renderer inputs are not
guessed. Existing output and family permission remain unchanged. Details:
[r43_scene_plan.md](./r43_scene_plan.md).

R43-06 adapts selected Template/Subject/Garnish/Mood through existing source and
grammar rules. Common evidence is captured within the Builder audit sink, separately
from locked legacy reachability counts.299 focused tests and87 regressions pass;
paired512 output/context/debug is unchanged and common receipts reproduce across
fresh root/package processes. Unknown grammar/source stays blocked. Details:
[r43_support_plan.md](./r43_support_plan.md). Next: R43-07 family proof/constructors.

R43-07 provides one common family proof/constructor engine and explicit selector/
realizer adapters. The six-layout formatter is shared while ordinary selection
remains unchanged.348 focused tests and87 regressions pass; paired512 and fresh
root/package receipts match. Recombination6-family success is separate from
common real-graph eligible0/512. See [r43_family_plan.md](./r43_family_plan.md).
Next R43-08 owns integration and real-graph proof; adoption remains BLOCKED.

R43-08's limited runtime integration and Garnish post-policy reconstruction are
verified:374 focused tests and87 regressions pass; ordinary512 is unchanged.
Common standalone proof reaches4 prior success inputs, but five families remain
unreached and new ordinary applications remain0. **R43-08 acceptance is BLOCKED**;
do not proceed to R43-09 or infer adoption from these tests. Details:
[r43_integration_plan.md](./r43_integration_plan.md).

The subsequent [owned-placement pass](./r43_placement_plan.md) reaches all six
families on unchanged real-graph inputs (14 forced seed-family rows), with exact
source binding and scoped semantic review.409 focused tests/87 regressions and
paired512 pass. Ordinary v2 remains9/512; new ordinary application is the remaining
R43-08 blocker. Do not start R43-09 or claim formal adoption from forced reachability.
