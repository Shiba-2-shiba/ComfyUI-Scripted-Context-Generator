# R45 Progress

## Baseline
- branch: refactor/realizer-v2-r45
- parent_branch: refactor/realizer-v2-r44
- start_head: 8c0dce2a6a2f485d683c306736b76a114bae3165
- source_tree_hash: a113f9908fd53be35ff0e457445c4a6717f2d32bbaefb36cc95da1728c76a778
- ordinary_v2: 11 / 512
- ordinary_families: 3
- forced_families: 6 (real-input common proof and forced rendering)

## Task ledger
| Task | State | Commit | Evidence | Notes |
|---|---|---|---|---|
| R45-00 | PASS | 24d902b8099c433def50f87ac80536c05773a123 | baseline/baseline-verification.json | baseline lock |
| R45-01 | PASS | 2a328547e81bf26f16b22b83014bf1a9ccafd608 | r45-01-verification.json | taxonomy; selector []; pairs unchanged |
| R45-02 | PASS | 659c4e7dcebf29ac7e4567fcb3c58e0683be63ba | r45-02-reachability | capability projection; pairs unchanged |
| R45-03 | PASS | 7ee02172f13d2e7a92ef2d3060ff0479e69d6cc5 | r45-03-verification.json | Scene source-bound 479; ordinary pairs unchanged |
| R45-04 | PASS | d59b1fc2272acd5094571578fcee0b1f7dee7032 | r45-04-capabilities | 131 capabilities; 50 candidates; rescue max 0 |
| R45-05 | PASS | this change; SHA in R45-05-report.md | comparison_sources/r45/registry.json | BLOCKED_CAPABILITY_MODEL; preservation PASS |
| R45-06 | PENDING | | | handoff/checkpoint |

## Formal scope
Formal N2.7/N2.8/D3 evaluation: NOT_RUN / BLOCKED / DEFERRED.

## R45-05 execution record

2026-09-13: IN_PROGRESS before documentation/receipt edits. Prior approved source
commit: `d59b1fc2272acd5094571578fcee0b1f7dee7032`. Only the three progress/task
documents, compact R45 comparison receipts and ignored final-development evidence
are in scope. Final-source checks use fresh directories; historical R45-00 and
R45-03 evidence retain their original source identities. Zero single-capability
rescue is a measured blocked verdict, not a reason to weaken the readiness rule.

### Focused-suite expectation correction

The first final-development focused run at `d59b1fc2272acd5094571578fcee0b1f7dee7032`
failed ten cases in one parametrized Scene coverage test (524 passed / 2,020
subtests passed). Like the two tests corrected in R45-03, it still required
absent provenance for exact catalog-matched but grammatically unsupported input.
The parent approved a narrow scope extension to that test in
`assets/test_r43_coverage_scene.py`. All ten cases now require exact source
field/catalog/raw binding, UNKNOWN grammar and unproved ownership, both
grammar-unknown and deferred-permission blockers, and rejection by all four
Scene rendering constructors. No runtime source or other rejection case changed.

The complete Scene coverage file passes **31 tests** with no skips or errors:
`python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -p tools.verify_realizer_v2_candidate -q assets/test_r43_coverage_scene.py`.
Initial failure and correction logs remain in `final-development/`; complete
final verification will restart in fresh `final-development-02/` directories
after this correction is committed. This is a diagnostic expectation correction,
not a relaxation of the ordinary/protected/determinism preservation gates.

## Final development verdict
- development_verdict: BLOCKED_CAPABILITY_MODEL

R45-05 verification passes. Ordinary/protected/determinism preservation has no
regression, and the largest capability spans 470 distinct seeds. However, all
50 qualifying candidates have `single_capability_rescue_upper_bound == 0`.
The exact readiness rule therefore returns `BLOCKED_CAPABILITY_MODEL`.
No threshold is relaxed; R46 runtime implementation is not authorized by this
measurement. Source-only Scene binding still grants no grammar permission.

### Final-source evidence

- Recoverable source commit: `8a1977116e64c1d8bfd135b1a1376854b67cfa48`
  (the separately committed Scene test expectation correction).
- Source-tree hash: `db45a5e058ec2ee1c2de2cd22d59b3f97bc7133ffa26315f972b14b91b27641f`.
- Evidence root: `assets/results/diversity_refactor/r45/final-development-02/`.
  Source manifests use `tools.prompt_quality_loop.build_source_manifest` and
  match before/after every check. Documentation is outside that source scope,
  so the following receipt/documentation commit preserves these verified bytes.
- Focused **534 tests / 2,020 subtests PASS**; regression **87 / 33 PASS**;
  all R45 suites **40 / 33 PASS**. All failure, skip, xfail/xpass, deselection,
  collection and setup/teardown counters are zero. Data, scope, action-pool and
  compatibility build checks, full flow, and all **14 changed Python files**
  parsed with Python 3.10 AST all PASS. No standalone lint/typecheck is configured;
  authored diff hygiene also passes.
- Fixed512: ordinary v2 **11**, ordinary families **3**, fallback **501**, errors
  **0**. Normal pairs and records are byte-identical to R45-00. Root/ascending
  hashseed 17 and package/reverse hashseed 73 replay all 512 inputs; their canonical
  summary/evidence/family rows match byte-for-byte. All **3,072** baseline
  `(seed, family)` eligibility and forced-version states are unchanged; all six
  real-input common-forced families remain positive. Output/context, proof and
  RNG mismatches are zero; stale bindings rejected **512** in each fresh replay.
- Exact R45-00 Step 6 inventory: **120/120** protected V150 hashes match, with
  identical manifest bytes. Broader R44 inventory: **166/166** hashes match.
  These are separate inventories. No runtime authorization or protected data
  source changed in R45-05.
- Fresh capability audit: **8,684** occurrences, **131** capability hashes,
  **50** qualifying candidates before the top-12 display cap. Maximum descriptive
  distinct-seed count **470**, maximum qualifying affected count **451**, maximum
  single-capability rescue upper bound **0**. Repeated unknown-grammar groups
  with at least four seeds: action **8**, Scene **11**. All six repeat-audit
  artifacts match byte-for-byte.

| Final artifact | SHA-256 |
|---|---|
| reachability/rows.jsonl | 3d164a865a7d44f16236c7cedcd479f7bbe48fbddcb1cb453ef78ae1f0edc7af |
| reachability/normal-pairs.jsonl | a3b8a28e873bb4cbcfbd338125eef6165e809f228cd5d7cafa73d1589255b87d |
| capabilities/capability-occurrences.jsonl | c763b831726db37cdfa4ba8819a6dfe23792e2501d6d9b7303afa8178804e9e3 |
| capabilities/capability-summary.json | 2f097f1efa1975a635e9fe1f6df8ee076c18090fe8ac41fb491c753bbc45b06b |
| capabilities/r46-candidates.json | 2662eda0b772624b47c14309c9431dc708dc1ef51e403d69d7f0d7aa134966f5 |

### Top-three planning bound

- top3_affected_seed_union: **497** (the complete occurrence seed sets required
  by Step 3, including descriptive occurrences outside candidate qualification).
- top3_qualifying_affected_seed_union: **474** (reported separately).
- top3_single_capability_rescue_upper_bound_sum: **0**.
- top3_domains: **action, scene, scene**.
- top3_family_union: all six target families, including three not yet ordinary:
  `action_lead_subject_scene`, `scene_lead_subject_action`,
  `subject_action__scene_tail`, `subject_action_scene`,
  `subject_action_scene_insert`, `subject_scene_action`.

| Rank | Domain | Complete occurrence seeds | Qualifying affected seeds | Rescue upper bound |
|---|---|---:|---:|---:|
| 1 | action | 470 | 451 | 0 |
| 2 | scene | 416 | 399 | 0 |
| 3 | scene | 416 | 398 | 0 |

The candidate hashes and at most eight examples per candidate are in the compact
[candidate receipt](./comparison_sources/r45/candidate-ranking.json). Counts use
complete occurrence sets, never the capped examples. These are development-work
bounds, not a forecast of 64/512 or a permission to activate runtime grammar.

### Reproduction and remaining boundary

Executed from the isolated worktree, all exit zero on the final source:

```text
python tools/verify_realizer_v2_candidate.py --stage focused --output-dir assets/results/diversity_refactor/r45/final-development-02/focused
python tools/verify_realizer_v2_candidate.py --stage regression --output-dir assets/results/diversity_refactor/r45/final-development-02/regression
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -p tools.verify_realizer_v2_candidate -q assets/test_r45_blocker_taxonomy.py assets/test_r45_capability_projection.py assets/test_r45_scene_provenance_separation.py assets/test_r45_capability_audit.py
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python tools/verify_full_flow.py
python tools/audit_realizer_reachability.py --profile intake --force-families all --output-dir assets/results/diversity_refactor/r45/final-development-02/reachability
python tools/audit_realizer_capabilities.py --rows assets/results/diversity_refactor/r45/final-development-02/reachability/rows.jsonl --output-dir assets/results/diversity_refactor/r45/final-development-02/capabilities
python tools/audit_realizer_capabilities.py --rows assets/results/diversity_refactor/r45/final-development-02/reachability/rows.jsonl --output-dir assets/results/diversity_refactor/r45/final-development-02/capabilities-repeat
python tools/realizer_candidate_replay.py --source-root . --pairs assets/results/diversity_refactor/r45/final-development-02/reachability/normal-pairs.jsonl --output-dir assets/results/diversity_refactor/r45/final-development-02/replay-root --import-mode root --order ascending
python tools/realizer_candidate_replay.py --source-root . --pairs assets/results/diversity_refactor/r45/final-development-02/reachability/normal-pairs.jsonl --output-dir assets/results/diversity_refactor/r45/final-development-02/replay-package --import-mode package --order reverse
```

The local driver records full argv, exit codes, log hashes, Python 3.10 AST files,
protected comparisons and source guards. [Compact receipts and registry](./comparison_sources/r45/README.md)
retain every summarized local artifact SHA-256 plus source commit/tree identity.
Historical baseline and post-Scene receipts are labeled separately from final
source. The parent independently restored the task03 commit archive and verified
all entries against its historical source manifest. No full seed lists or raw
prompt/rows/log artifacts are tracked.

R45-06 archive restore, handoff/checkpoint and publication remain pending.
Formal reference8192, gate2048, paired formal comparison, fixed80, blind review,
fresh confirmations, frontend/browser and release8192 are all **NOT_RUN**.
N2.8/adoption remains **BLOCKED**; D3 remains **DEFERRED**.

## R45-04 execution record

2026-09-13: IN_PROGRESS before source edits. Prior approved commit:
`7ee02172f13d2e7a92ef2d3060ff0479e69d6cc5`. Input is the final R45-03
reachability artifact at
`assets/results/diversity_refactor/r45/r45-03-reachability-final/rows.jsonl`.
Ownership is limited to the capability audit CLI, its focused tests, this ledger,
task report, and generated R45-04 receipts.

The audit keeps the typed capability identity and its canonical hash unchanged,
then adds only occurrence context. Descriptive blocker counts also consume the
raw reachability rows, so components without projected capabilities remain in
the graph. Candidate count, floor and order use the union of source-bound,
ordinary-v1 seeds with a repairable domain blocker after row/error and all-family
hard exclusions. A hard sibling family excludes the complete row. Ranking uses
all co-blocker classes before capping the displayed top eight. Counts deduplicate
repeated atoms and `(seed, family)` edges; examples are capped independently.

Required commands from the isolated worktree all exited zero:

```text
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_capability_audit.py
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_capability_projection.py assets/test_r45_capability_audit.py
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_blocker_taxonomy.py assets/test_r45_capability_projection.py assets/test_r45_scene_provenance_separation.py assets/test_r45_capability_audit.py
python tools/audit_realizer_capabilities.py --rows assets/results/diversity_refactor/r45/r45-03-reachability-final/rows.jsonl --output-dir assets/results/diversity_refactor/r45/r45-04-capabilities-final-a
python tools/audit_realizer_capabilities.py --rows assets/results/diversity_refactor/r45/r45-03-reachability-final/rows.jsonl --output-dir assets/results/diversity_refactor/r45/r45-04-capabilities-final-b
python -m py_compile tools/audit_realizer_capabilities.py assets/test_r45_capability_audit.py
git -c safe.directory=<absolute R45 worktree> diff --check
```

- RED: expected missing audit-module collection error (exit 1); the focused
  correction cycle then produced three expected adversarial failures. GREEN:
  corrected focused audit suite **15 passed**. Before the final corrections, the
  required projection/audit suite passed 21 tests and all R45 suites passed 37
  tests plus 33 subtests, with zero failures/skips/errors.
- Final R45-03 input: 512 rows, SHA-256
  `69deea7151bc39d9d6a699ca548f701adc089637cd9dab1710bcc8146045fdd4`;
  embedded source-tree hash
  `a50a4c01ec95664426e14c7723a79b566aa53cb46fd6a336d993d306bb3eceba`.
  The receipt records this separately from the audit invocation commit and audit
  tool hash.
- Audit: 8,684 occurrences, **131** unique capability hashes, largest
  descriptive distinct-seed count **470**; action unknown-grammar groups with
  at least four seeds **8**, Scene unknown-grammar groups **11**.
- Candidate accounting: **50** qualifying hashes before the top-12 output cap,
  maximum `affected_seed_count` **451**, maximum
  `single_capability_rescue_upper_bound` **0**. Per-hash affected/rescue counts
  exactly match the independent oracle. R45-04 passes because reusable groups
  exist; the zero rescue result is preserved for the R45-05 verdict rather than
  weakening accounting.
- Both audit runs match byte-for-byte for all six artifacts. Primary hashes:
  occurrences `c763b831726db37cdfa4ba8819a6dfe23792e2501d6d9b7303afa8178804e9e3`,
  summary `2f097f1efa1975a635e9fe1f6df8ee076c18090fe8ac41fb491c753bbc45b06b`,
  intersections `cd227861a6be602869fddaef2ffca431e4090fdbc0c74fd6d1468443a81d5d2e`,
  candidates `2662eda0b772624b47c14309c9431dc708dc1ef51e403d69d7f0d7aa134966f5`.
- No runtime authorization, protected source, dependency, public I/O, threshold,
  full-clause allowlist or seed allowlist changed. Formal evaluations remain
  **NOT_RUN**.

## R45-03 execution record

2026-09-13: IN_PROGRESS before edits. Ownership: `pipeline/v2_scene_provenance.py`,
`assets/test_r45_scene_provenance_separation.py`, this ledger and task receipts.
Plan: lock known Scene evidence, preserve the R44 combined parser unchanged,
add exact source-only binding and grammar classification with unconditional
deferred permission, then run focused tests, fixed512 parity and fresh replays.

Approved scope correction: two existing R43 tests equated unknown grammar with
absent provenance, contradicting the governing R45 separation requirement. The
leader authorized only those expectations in `assets/test_r43_scene_binding.py`
and `assets/test_r43_reviewed_scene_binding.py` to change. Source/raw order,
unknown grammar, mandatory deferred blocker and blocked constructors are now
asserted; all ambiguity, stale binding and antecedent rejection controls remain.

Evidence root: `assets/results/diversity_refactor/r45/`.

```text
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_scene_provenance_separation.py
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -p tools.verify_realizer_v2_candidate -q assets/test_r45_scene_provenance_separation.py assets/test_r43_scene_binding.py assets/test_r43_scene_trace.py assets/test_r43_reviewed_scene_binding.py assets/test_r43_family_capabilities.py assets/test_r43_evidence_contract.py assets/test_r43_real_graph_placement.py
python tools/audit_realizer_reachability.py --profile intake --force-families all --output-dir assets/results/diversity_refactor/r45/r45-03-reachability-final
python tools/realizer_candidate_replay.py --source-root . --pairs assets/results/diversity_refactor/r45/baseline/reachability/normal-pairs.jsonl --output-dir assets/results/diversity_refactor/r45/r45-03-replay-root --import-mode root --order ascending
python tools/realizer_candidate_replay.py --source-root . --pairs assets/results/diversity_refactor/r45/baseline/reachability/normal-pairs.jsonl --output-dir assets/results/diversity_refactor/r45/r45-03-replay-package --import-mode package --order reverse
python .superpowers/sdd/R45_IMPLEMENTATION_PLAN/verify_r45_03.py
git -c safe.directory=<absolute R45 worktree> diff --check
```

- RED: five expected failures / two passes; rule-attribution regression also
  reproduced (one failure / eight passes). GREEN: **125 tests PASS**, zero
  failures/skips/errors. Logs: `r45-03-red.log`, `r45-03-rule-red.log`,
  `r45-03-green-final.log`. Initial focused run exposed the two corrected old
  expectations above. Preliminary audit preceded final test/rule changes;
  final acceptance uses only `r45-03-reachability-final` and the fresh replays.
- Fixed512 Scene source traces **479**, runtime-bound **479**, all-atom grammar
  known **16**, grammar unknown **496** including unavailable scenes. The **463**
  recovered scenes all retain grammar-unknown and deferred-permission blockers;
  32 source-unavailable scenes and one invalid antecedent remain unavailable.
- Ordinary v2 **11/512**, **3** families, **501** fallbacks, zero errors.
  `normal-pairs.jsonl` is byte-identical to R45-00, SHA-256
  `a3b8a28e873bb4cbcfbd338125eef6165e809f228cd5d7cafa73d1589255b87d`.
- Root ascending/hashseed 17 and package reverse/hashseed 73 both PASS:
  512 inputs / 3,072 seed-family rows, zero output/context/proof/RNG mismatches,
  512 stale bindings rejected. Summary/evidence/family-row bytes match exactly;
  hashes are in `r45-03-verification.json`. Source guards unchanged during runs,
  final source-tree hash `a50a4c01ec95664426e14c7723a79b566aa53cb46fd6a336d993d306bb3eceba`.
- Parent independently verified all **3,072** eligibility/forced-version pairs
  unchanged against R45-00, plus output and replay byte parity. AST extraction
  confirms the R44 combined parser and four rendering entry points unchanged.
- Simplification: source topology and grammar proof now have separate private
  stages; no dependency, runtime authorization file or protected data changed.
  Known recovered atoms keep their actual grammar rule provenance. No standalone
  lint/typecheck configuration exists; focused tests and diff hygiene passed.
  Formal evaluations remain **NOT_RUN**; this diagnostic gain grants no adoption.


## R45-00 execution record

2026-09-13: Isolated worktree at `assets/results/r45-worktree` on
`refactor/realizer-v2-r45`. The parent fetched origin/tags and created this branch
at the exact approved remote HEAD. This existing ignored results-directory
convention stays within the writable workspace. No parent-source reconciliation
was needed. The ledger was created IN_PROGRESS before baseline verification;
no runtime, diagnostic, public I/O or protected data source was edited.

Local Git uses command-scoped `safe.directory` for this worktree because the
sandbox identity differs from the owner. Verifier processes inherited equivalent
`GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=safe.directory`,
`GIT_CONFIG_VALUE_0=<absolute worktree path>` settings. No global Git configuration
was changed. The audit records the exact starting commit above.

### Source and approved-input identities

Both annotated tag object IDs and peeled commits match the published R44 registry:

| Role | Tag | Peeled commit | Tag object |
|---|---|---|---|
| pre-R44 baseline | realizer-v2-r44-baseline-11 | b16a4dbca7d91d6d1cdefbfd521fd6a44787765a | eb0600409b463a578e47f55cf6d696fdf2654397 |
| R44 diagnostics | realizer-v2-r44-blocked-20260913 | 98a8ef33ab9a851240cf678864b0ed65879228e4 | 0f4d49af59d8e679a9471e4c982acb5534e35f79 |

Registry assertions returned `R44 registry PASS`; neither tag was changed.
Approved design and implementation plan were copied verbatim:

- `R45_DESIGN.md` SHA-256: `b9d4260baeaeae27199fc65d3251ce84816dded74c05aa2b7ddb08bc5b5d97cf`
- `R45_IMPLEMENTATION_PLAN.md` SHA-256: `ae49f92d727755c516000f19b312e235fea7ef0280eae8ceb2c575df6b82e944`

### Exact verification commands

All commands ran from the isolated R45 worktree; all four exited 0.

```text
python tools/verify_realizer_v2_candidate.py --stage focused --output-dir assets/results/diversity_refactor/r45/baseline/focused
python tools/verify_realizer_v2_candidate.py --stage regression --output-dir assets/results/diversity_refactor/r45/baseline/regression
python tools/audit_realizer_reachability.py --profile intake --force-families all --output-dir assets/results/diversity_refactor/r45/baseline/reachability
python tools/realizer_candidate_replay.py --source-root . --pairs assets/results/diversity_refactor/r45/baseline/reachability/normal-pairs.jsonl --output-dir assets/results/diversity_refactor/r45/baseline/replay-root --import-mode root
```

- Focused: PASS, 534 tests / 2,020 subtests.
- Regression: PASS, 87 tests / 33 subtests; variations, prompt data, variation
  scope, action pools, compatibility, full flow and asset validation all PASS.
- All failure, skip, xfail/xpass, deselection and collection/error counters: zero.
- Intake: PASS, ordinary v2 11/512, three executed families, 501 fallbacks;
  errors zero. Fresh rows, records and pairs match the R44 preservation hashes.
- Replay: PASS, 512 inputs / 3,072 real-input seed-family rows; zero ordinary
  output/context, proof/constructor or RNG mismatches; 512 stale bindings rejected.
  Canonical summary bytes match the tracked R44 replay receipt exactly.
- Real-input forced proof uses replay `families[*].common_forced_v2`, as in R44:
  action_lead_subject_scene 1, scene_lead_subject_action 2,
  subject_action__scene_tail 7, subject_action_scene 2,
  subject_action_scene_insert 2, subject_scene_action 2. All six are positive.
  Audit `forced_render_v2` only measures equivalence to ordinary output and is
  not the six-family proof criterion; raw constructor presence is insufficient.
- Focused/regression/audit/replay source guards remain at the R44 source-tree hash.

### Receipt hashes and protected inputs

Local evidence root: `assets/results/diversity_refactor/r45/baseline/`.
Compact receipts: `preflight.json` and `baseline-verification.json`; raw commands,
environment, source guards and test outcomes remain in their stage directories.

| Artifact | SHA-256 |
|---|---|
| reachability/normal-pairs.jsonl | a3b8a28e873bb4cbcfbd338125eef6165e809f228cd5d7cafa73d1589255b87d |
| reachability/records.jsonl | a821d0264957ee602f0e9a80d2f112c213b9f88df839f258e7a6fb483290026c |
| reachability/rows.jsonl | 00fe4ca13dbf1f0b2e5739fc017114600b2f5d50ea76247e295df1b8b8e280c1 |
| replay-root/summary.json | ccd938dff5f46c6683fb907c4cfbd331fb1558a294143cc4950c012552a9e08d |
| protected-inputs.sha256 | 6a2b8e61eec69d768d682786dc464967ec5cc33854015f4250f646866237e00b |

The exact R45-00 Step 6 path/glob inventory contains **120 protected V150 files**.
Its UTF-8/LF manifest stores `sha256 path` rows sorted by path, followed by
`protected_count 120`. Additionally, all **166 broader protected development
inputs** in the existing R44 receipt were checked and are unchanged; these are
different inventories, not a reduction in protection.

Git diff hygiene is checked for authored documentation. Supplied design/plan
bytes remain verbatim; the six existing Markdown hard-break lines in the design and final blank line
in the plan are excluded only from the scoped authored-file check. No new test,
runtime code, dependency, lint/typecheck configuration or active runtime claim
was introduced by this documentation baseline task.

Formal candidate reference8192, gate2048, paired formal comparison, fixed80,
blind review, fresh confirmations, frontend/browser and release8192: **NOT_RUN**.
N2.8/adoption: **BLOCKED**. D3: **DEFERRED**.

## R45-02 execution record

2026-09-13: Marked IN_PROGRESS before source edits. Added a diagnostic-only,
typed atomic capability projection that resolves each atom through its declared
`source_part_ids`, rebuilds current evidence only after R44 common-input binding
validation, and attaches canonical projection bytes without changing the R44
signature schema or runtime authorization.

Commands from the R45 worktree (evidence under `assets/results/diversity_refactor/r45/`):

```text
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_capability_projection.py
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_capability_projection.py assets/test_r43_common_diagnostics.py assets/test_r44_coverage_signatures.py assets/test_r44_reachability_accounting.py
python tools/audit_realizer_reachability.py --profile intake --force-families all --sample-count 16 --output-dir assets/results/diversity_refactor/r45/r45-02-repeat16-a
python tools/audit_realizer_reachability.py --profile intake --force-families all --sample-count 16 --output-dir assets/results/diversity_refactor/r45/r45-02-repeat16-b
python tools/audit_realizer_reachability.py --profile intake --force-families all --output-dir assets/results/diversity_refactor/r45/r45-02-reachability
```

- RED: expected missing `tools.realizer_capability_projection` collection error
  (exit 1).
- GREEN: 37 tests / 17 subtests PASS; no failures, skips or errors.
- Repeat16: both complete rows are equal. Projection payloads and hashes match
  for 16/16 seeds; after removing only the two additive capability fields, all
  pre-R45 diagnostic fields match. The same comparisons match the first 16
  fixed512 rows exactly.
- Fixed512: 512 AVAILABLE projections; 6,466 capability identities; 112 unique
  capability hashes; largest repeated capability count 470. These are
  measurement facts only and grant no runtime permission.
- Preservation: ordinary v2 remains 11/512 across three families with 501
  fallbacks and zero errors. `normal-pairs.jsonl` is byte-equal to the R45-00
  baseline, SHA-256
  `a3b8a28e873bb4cbcfbd338125eef6165e809f228cd5d7cafa73d1589255b87d`.
  The fixed512 source manifests before/after are equal.
- R44 `realizer-coverage-signature/v1` code and tests are unchanged. Capability
  identity excludes source text, selected-text hashes, exact catalog keys,
  evidence/input bindings and unrelated domains; invalid part references fail
  closed. No runtime/protected source, dependency, threshold or public I/O changed.
- Formal candidate reference8192, gate2048, paired formal comparison, fixed80,
  blind review, fresh confirmations, frontend/browser and release8192 remain
  **NOT_RUN**.

## R45-01 execution record

2026-09-13: Marked IN_PROGRESS before code. Centralized diagnostic blocker
normalization, hard exclusions and domain ownership; selector retains the
four-distinct-seed floor and leaves forensic signatures untouched.

Commands from the R45 worktree (evidence under `assets/results/diversity_refactor/r45/`):

```text
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_blocker_taxonomy.py
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_blocker_taxonomy.py assets/test_r44_packet_selection.py
python tools/select_r44_coverage_packets.py --rows assets/results/diversity_refactor/r45/baseline/reachability/rows.jsonl --output assets/results/diversity_refactor/r45/r45-01-r44-selector.json --max-packets 3
python tools/audit_realizer_reachability.py --profile intake --force-families all --output-dir assets/results/diversity_refactor/r45/r45-01-reachability
git -c safe.directory=<absolute R45 worktree> diff --check
```

- RED: missing taxonomy import (exit 2), then both selector regressions fail
  while five taxonomy tests pass (exit 1). Logs: `r45-01-red.log`,
  `r45-01-selector-red.log`.
- GREEN: 30 tests / 69 subtests PASS; no failures, skips or errors.
  Log: `r45-01-green.log`.
- Preserved selector input returns `[]` (exit 0).
- Fresh512: exit 0; ordinary 11/512, three families, 501 fallbacks, zero errors;
  source manifests before/after equal. Python `read_bytes()` equality against
  baseline pairs PASS; SHA-256
  `a3b8a28e873bb4cbcfbd338125eef6165e809f228cd5d7cafa73d1589255b87d`.
  Receipt: `r45-01-verification.json`.
- Approved adaptation: package-first import with sibling fallback supports
  existing `spec_from_file_location` consumers as well as package/CLI use.
  The plan's relative-first import failed existing tests; old tests are unchanged.
- Self-review: scope and diff hygiene PASS; no runtime/protected source edits,
  dependency changes, signature rehashing or threshold changes. No standalone
  lint/typecheck configuration is present. Formal evaluations remain NOT_RUN.
