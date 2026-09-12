# R44 handoff

R44 development verdict: **BLOCKED_DEVELOPMENT_GUIDE**. Diagnostic signatures and deterministic selection are implemented and verified. No runtime coverage packet was selected or attempted.

The final ordinary512 profile contains **511 full structural signatures**, with at most **2 distinct seeds** in a signature. The minimum is four seeds per packet, so the selector returns `[]`; the selected seed union is zero and the bounded upper bound is **11/512**, below 64. Task 2 Step 7 explicitly directs this result to handoff. Tasks 3-5 and the runtime coverage portion of Task 6 were skipped. Handoff verification still ran focused/regression/validators and independent replay.

## Source identities

- R44 branch: `refactor/realizer-v2-r44`
- R44 source: `98a8ef33ab9a851240cf678864b0ed65879228e4`; annotated tag `realizer-v2-r44-blocked-20260913`
- R44 source-tree hash: `a113f9908fd53be35ff0e457445c4a6717f2d32bbaefb36cc95da1728c76a778`
- Baseline: `b16a4dbca7d91d6d1cdefbfd521fd6a44787765a`; annotated tag `realizer-v2-r44-baseline-11`
- Baseline source-tree hash: `53a4fe8048cfd71cdcd9f3a7cb414e0b96ec6c0450b96795c465470d6963b56e`
- Registry: [comparison_sources/r44/registry.json](./comparison_sources/r44/registry.json)
- Remote source publication: both annotated tags and peeled commit IDs verified against GitHub; registry and handoff are on `refactor/realizer-v2-r44`.

## Measured results

| Check | Result |
|---|---|
| Ordinary v2 | 11/512; three executed families |
| Real-input forced common proof/render | All six families |
| Prior v2 successes | All 11 preserved exactly |
| Remaining fallback | All 501 raw/cleaned outputs and context preserved exactly |
| All512 records / Builder context | Canonical pair bytes identical to pre-R44 |
| Upstream semantic core/frame/context | All512 unchanged |
| Original diagnostic fields | All512 unchanged; only structural signature fields added |
| Focused verifier | 534 tests / 2,020 subtests PASS |
| Regression verifier | 87 tests / 33 subtests PASS |
| R44 tests | 45 tests / 53 subtests PASS |
| Test skips, xfail/xpass, errors, deselection | Zero |
| Data/scope/build validators, full flow, asset validation | PASS |
| Protected development input files | All 166 hashes unchanged; V150 base variations remain150,184 |
| Python3.10 AST / diff hygiene | PASS for eight changed Python files |
| Root vs restored-package512 replay | Summary, evidence, family-proof rows byte-identical |
| Restored512 audit | Rows, records and pairs byte-identical |

The archive's audit report has no checkout Git commit. Its full report equals the worktree report after removing only `identity.git_commit`; source/configuration identity and every diagnostic/outcome field match. Replay summary bytes themselves match exactly. Forced-family evidence uses the existing AS01 replay `common_forced_v2`, because audit `forced_render_v2` certifies only exact ordinary-output equivalence and observes three families.

## Changes and boundaries

`tools/realizer_coverage_signatures.py` projects freshly reconstructed producer evidence into text-free structure. `tools/realizer_reachability_diagnostics.py` attaches the signature; `tools/audit_realizer_reachability.py` counts ordinary seed-family diagnostic rows. `tools/select_r44_coverage_packets.py` ranks distinct-seed groups with hard exclusions and bounded ROI. Existing evidence/proof and canonical JSON helpers are reused. Runtime authorization never imports these new tools.

Tests add real-input, stale-current-state, source-category, ordering, confidentiality and selector coverage. The existing common-diagnostics regression now protects all old fields separately from the new signature. No new dependency, runtime grammar, public node I/O/schema, semantic selection, protected variation data, family scheduling or default activation changed.

Accepted packets: none. Rejected runtime packets: none. A/B/C execution: skipped by the viability gate; no empty packet manifests or unused packet tests were created.

Final independent whole-branch review: **APPROVE**, no Important findings remaining.

Formal evaluation = **NOT_RUN** for candidate reference8192, gate2048, paired formal comparison, fixed80, blind review, fresh confirmations, frontend/browser and release8192. Adoption/N2.8 = **BLOCKED**. D3 = **DEFERRED**. Stable main remains separate.

## Next task

R45: redesign diagnostic packet grouping around recurring domain capabilities and measured blocker intersections; full cross-domain signatures currently split 512 seeds into 511 groups. Preserve the existing runtime proof and exclusions; do not invent a fourth R44 packet or start formal evaluation.

This is a measured grouping limitation, not evidence that runtime thresholds should be relaxed. The current all-domain signature combines source-slot order, atom forms/ownership, template/support shape and family blockers; recurring local capabilities can therefore land in distinct full-signature groups. A new design should test a domain-level grouping/overlap strategy against these preserved512 rows before selecting runtime changes.

## Reproduce

Use the [checkpoint restoration instructions](./comparison_sources/r44/README.md), then:

```text
python tools/verify_realizer_v2_candidate.py --stage focused --output-dir assets/results/r44-recheck/focused
python tools/verify_realizer_v2_candidate.py --stage regression --output-dir assets/results/r44-recheck/regression
python -m unittest assets.test_r44_coverage_signatures assets.test_r44_reachability_accounting assets.test_r44_packet_selection -v
python tools/audit_realizer_reachability.py --profile intake --force-families all --output-dir assets/results/r44-recheck/reachability
python tools/select_r44_coverage_packets.py --rows assets/results/r44-recheck/reachability/rows.jsonl --output assets/results/r44-recheck/packets.json --max-packets 3
```

The fresh post-fix `signature-intake-02` audit is also the selector input: no source change occurred between diagnostic verification and selection. Large raw logs remain local; source identities, file hashes and compact receipts are tracked under `comparison_sources/r44/`.
