# Post-R43 coverage AS01: source-bound Action and Scene grammar

## Scope and preservation

Continue the conditional R43 handoff with one bounded Action+Scene pass. The
accepted source is `1678a635b03d8e6e18e6a797b395511a51cc04c3f245f96c7c5a38e9ca17cf23`.
Its complete source snapshot and passing pre-edit focused run are retained under
`assets/results/diversity_refactor/r43/coverage-as01-20260912-01` in original main.
Preserve all ten ordinary successes, unchanged fallbacks, upstream semantic choices,
V150 data, legacy grammar defaults, and compatibility-first dispatch.

## Cleanup and implementation plan (written before code)

The boundary gap is complete producer-bound constituents that common proof cannot
yet express. Extend existing grammar helpers; add no dependencies or new layer.

1. Lock the received recording-booth case and adversarial variants in regression
   tests before implementation. Independent review checks the proof boundaries.
2. Action: bounded abstract turning/manner, leaning/manner, clicking a count noun,
   and explicit nonprimary time-or-weather event clauses. Derive a distinct common
   dependent-event marker; retain nonhuman owner and `same_subject=False`. Generic
   external clauses and Action-leading remain rejected. Insert only licensed
   articles, retaining raw producer evidence.
3. Scene: common-only source-bound booth/pads/atmosphere noun grammar. Preserve
   exact history, catalog and field ownership before grammar; keep the pads'
   `on wall` modifier attached to pads and insert its licensed definite article.
4. Reuse existing construction and proof paths. Test full consumption, wrong
   roles/owners, unsupported subjects/tails, stale proof and legacy defaults.
5. Run focused/regression/static checks and fixed development512. Compare against
   both the original nine-case baseline and this ten-case snapshot. Independently
   review all newly emitted ordinary prose and refresh source-bound receipts.
6. Run portable intake/replay; document measured reachability and remaining gaps.

No seed or full-clause allowlists, generation vocabulary edits, threshold changes,
formal evaluation, main promotion, merge/push, N2.8 or D3. Formal adoption stays
blocked until its separate prerequisites pass. Typecheck is not configured.

## Status

Complete, 2026-09-12. [Source-bound result](./coverage_as01_summary.json).

The nine-case intake baseline, ten-case immediate baseline and eleven-case
candidate are now recoverable through [fixed source tags and restore instructions](./comparison_sources/README.md).
Their full Git identities, source guards and preserved receipts are in the registry.

- Ordinary v2: **10 to 11/512**, still three ordinary families. All ten earlier
  successes and501 remaining fallbacks retain their exact output/context and
  upstream choices. Original nine-case baseline preservation also passes.
- All six families retain real-input forced proof. New input91 uses standalone;
  its temporal event remains nonhuman and cannot authorize Action-leading.
- Focused534 tests/2,020 subtests; regression87 tests/33 subtests; validators,
  sizing, assets and full flow PASS. No skipped/deselected/xfail/xpass or errors.
- Portable intake PASS for architecture/development. Root and clean-copy package
  replay agree on canonical evidence/final prose for all512 inputs, reversed
  ordering and different actual hash seeds; proof/constructor mismatches are0.
- Independent code and raw/Cleaner review PASS for this scope. Previous seven
  reviewed texts retain exact hashes; the source-bound receipt now has eight cases.
- Python3.10 AST checks pass. V150120 protected files, stable main and existing
  user files are unchanged. No dependency or generation vocabulary changes.

Source: `53a4fe8048cfd71cdcd9f3a7cb414e0b96ec6c0450b96795c465470d6963b56e`.
The first audit was invalidated by final source/test edits and is historical only;
`audit-final` and `intake` under the evidence directory are authoritative.

Changed runtime files: v2_common_action_grammar.py, v2_leaf_grammar.py,
v2_scene_provenance.py, v2_structural_evidence.py and family_capabilities.py.
Added three coverage test modules and one minimal real-graph input projection.
Existing aggregation, rendering, source binding and family construction are reused.
No additional runtime layer is introduced.

The64/5 development guide remains unmet. Existing template/mood phrasing remains
cumbersome; this review does not establish formal naturalness acceptance.
Formal evaluation/adoption remain BLOCKED; formal and frontend/browser gates are
NOT_RUN, typecheck NOT_CONFIGURED. Next: further bounded Action+Scene coverage
from the remaining intersections, preserving this eleven-case checkpoint.
