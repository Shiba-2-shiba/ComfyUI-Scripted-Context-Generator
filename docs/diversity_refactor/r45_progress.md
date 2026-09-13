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
| R45-00 | PASS | baseline commit (this change; exact SHA in task report) | baseline/baseline-verification.json | baseline lock |
| R45-01 | PENDING | | | blocker taxonomy |
| R45-02 | PENDING | | | capability projection |
| R45-03 | PENDING | | | Scene provenance separation |
| R45-04 | PENDING | | | capability audit graph |
| R45-05 | PENDING | | | R46 readiness verdict |
| R45-06 | PENDING | | | handoff/checkpoint |

## Formal scope
Formal N2.7/N2.8/D3 evaluation: NOT_RUN / BLOCKED / DEFERRED.


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
