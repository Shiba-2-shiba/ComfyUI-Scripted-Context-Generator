# R45 handoff

## Verdict

**BLOCKED_CAPABILITY_MODEL**. Grouping and provenance diagnostics improved, but
all 50 qualifying candidates have zero single-capability rescue upper bounds.
R46 runtime work is not justified by this measurement. Formal evaluation and
adoption remain blocked; no readiness threshold was relaxed.

## Source identities

- Branch: `refactor/realizer-v2-r45`.
- Immutable checkpoint target: `8861ceaedcf50b5803fdb7f3afa52a96a093caac`.
- Final verified source commit: `8a1977116e64c1d8bfd135b1a1376854b67cfa48`.
- Source-manifest SHA-256: `db45a5e058ec2ee1c2de2cd22d59b3f97bc7133ffa26315f972b14b91b27641f`.
  This is the diagnostic source-manifest hash, not Git's tree object ID.
- Annotated tag: `realizer-v2-r45-blocked-20260913`; published and remote source identity verified.
- [Registry](./comparison_sources/r45/registry.json) distinguishes the verified
  source, checkpoint commit and later handoff documentation. Never move a tag to
  include later documentation; the final documentation SHA belongs in Git history
  and the local task report, avoiding self-referential hash churn.
- R44 baseline tag `realizer-v2-r44-baseline-11`: tag object
  `eb0600409b463a578e47f55cf6d696fdf2654397`, commit
  `b16a4dbca7d91d6d1cdefbfd521fd6a44787765a`.
- R44 diagnostic tag `realizer-v2-r44-blocked-20260913`: tag object
  `0f4d49af59d8e679a9471e4c982acb5534e35f79`, commit
  `98a8ef33ab9a851240cf678864b0ed65879228e4`. Both remain immutable.

## Preservation

Ordinary v2 remains **11/512**, **3 families**, **501 fallback**, zero errors.
All prior successes, normal output/context records and all 3,072 real-input
seed/family eligibility and forced-version states match the baseline. Six
real-input common-forced families remain positive. Protected V150 inventory
120/120 and broader R44 inventory 166/166 match independently. Runtime
`family_capabilities.py`, `prompt_realizer.py`, `v2_candidate_bridge.py` and
`natural_language_realizer_v2.json` have no diff against R44. No public node I/O
or context contract changed.

## Provenance separation

Scene source-bound count increased **16 -> 479**. Of those 479 source-bound
cases, **16** retain known grammar and **463** remain grammar-unknown with
explicit deferred-permission blockers. Source evidence never grants permission:
current-input `FamilyProof` remains the sole runtime authority and UNKNOWN stays
UNKNOWN. Exact text/catalog binding is preserved without treating unsupported
Scene grammar as absent source evidence.

## Capability measurement

There are **8,684 occurrences**, **131 capabilities**, **50 qualifying
candidates**, with the top **12** displayed. Repeated unknown-grammar groups of
at least four seeds number **8 action / 11 Scene**.

| Rank | Capability class | Complete occurrence seeds | Qualifying affected seeds | Single-capability rescue upper bound |
|---|---|---:|---:|---:|
| 1 | Action `primary_action`, `action_slots`, unknown grammar/owner/attachment | 470 | 451 | 0 |
| 2 | Scene `environment`, `scene.r45_source_bound_unproved` | 416 | 399 | 0 |
| 3 | Scene `core`, `scene.r45_source_bound_unproved` | 416 | 398 | 0 |

The complete occurrence seed union of the top three is **497**; their qualifying
affected union is **474**. Neither is a rescue forecast. The rescue-upper-bound
sum is zero. The top-three family union contains all six target families,
including three already ordinary and three not yet ordinary. Exact hashes and
bounded examples are in [candidate-ranking.json](./comparison_sources/r45/candidate-ranking.json).
Complete occurrence sets, rather than capped examples, determine these counts.

## What R45 did not do

No runtime grammar expansion, syntax family, Scheduler or N2.8 activation, new
dependency, output domain, seed/phrase allowlist or threshold relaxation.
Formal reference8192, gate2048, paired formal comparison, fixed80, blind review,
fresh confirmations, frontend/browser and release8192 are **NOT_RUN**.
N2.8/adoption is **BLOCKED**; D3 is **DEFERRED**.

## R46 boundary

The next action is diagnostic model/design review, starting with the three
classes above one at a time. Investigate why source-bound unknown primary
Action and unproved Scene environment/core capabilities still have independent
co-blockers across Action, Scene, clothing, template and subject. Any proposed
capability refinement must explain the complete blocker intersections and retain
text-free identities and fail-closed proof boundaries. R45 does not authorize
runtime implementation or a hand-selected rescue list. A new reviewed design
and preserved gates are required before any runtime wave; 64/512 and five-family
goals remain unchanged.

## Reproduce

Local restore status: **PASS**. Exact commit `8861cea` was archived into a new
ignored directory; its 640-entry manifest matches the final verified source
before and after replay. All 13 canonical result files match final-development-02
byte-for-byte; three metadata artifacts differ only at four listed Git/path
fields. Both 512-input replays pass with 3,072 family rows, zero output/context,
proof and RNG mismatches, and 512 stale-binding rejections each. See the
[restore receipt](./comparison_sources/r45/restore-verification.json).
The immutable tag peels to that exact commit. From a new archive
extraction, using a fresh sibling evidence directory:

```text
git archive --format=zip --output=<new-source.zip> 8861ceaedcf50b5803fdb7f3afa52a96a093caac
python tools/audit_realizer_reachability.py --profile intake --force-families all --output-dir ../reachability
python tools/audit_realizer_capabilities.py --rows ../reachability/rows.jsonl --output-dir ../capabilities
# Set PYTHONHASHSEED=29 for the root command and PYTHONHASHSEED=101 for package.
python tools/realizer_candidate_replay.py --source-root . --pairs ../reachability/normal-pairs.jsonl --output-dir ../replay-root --import-mode root --order ascending
python tools/realizer_candidate_replay.py --source-root . --pairs ../reachability/normal-pairs.jsonl --output-dir ../replay-package --import-mode package --order reverse
```

Use `tools.prompt_quality_loop.build_source_manifest` before and after; compare
with `final-development-02/source-manifest.json`. Compare canonical rows,
records, normal pairs, capability occurrences/summary/intersections/candidates,
and both replay summary/evidence/family rows byte-for-byte. Only explicitly
recorded checkout Git metadata and environment/input paths may differ.
Compact receipts are in [comparison_sources/r45](./comparison_sources/r45/registry.json);
large restored artifacts and command logs remain local under
`assets/results/diversity_refactor/r45/restore-06/`. Task06 source publication and handoff are complete. Remote identities are
recorded in [publication.json](./comparison_sources/r45/publication.json).
