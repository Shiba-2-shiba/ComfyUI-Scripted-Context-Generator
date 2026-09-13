# R45 development comparison receipts

Development verdict: **BLOCKED_CAPABILITY_MODEL**. Ordinary output is preserved
at 11/512 across three families with 501 fallbacks. The 131 capability hashes
produce 50 qualifying candidates (top 12 displayed); every single-capability
rescue upper bound is zero. This is development evidence, with no formal adoption
or runtime grammar expansion.

The final verified source is commit
`8a1977116e64c1d8bfd135b1a1376854b67cfa48`, source-tree SHA-256
`db45a5e058ec2ee1c2de2cd22d59b3f97bc7133ffa26315f972b14b91b27641f`.
`tools.prompt_quality_loop.build_source_manifest` defines the source scope;
documentation commits preserve this source identity. Large raw evidence remains
local under `assets/results/diversity_refactor/r45/final-development-02/`.
Every JSON receipt records its source commit/tree and SHA-256 of the local
artifacts it summarizes.

| Receipt | Meaning |
|---|---|
| [registry.json](./registry.json) | Recoverable source, receipt hashes and pending R45-06 boundary |
| [baseline-identity.json](./baseline-identity.json) | Historical R45-00/R44 baseline, published immutable tags |
| [post-scene-reachability.json](./post-scene-reachability.json) | Historical R45-03 result; original invocation and recoverable source differ explicitly |
| [final-reachability.json](./final-reachability.json) | Fresh final-source fixed512 and root/package replay preservation |
| [capability-summary.json](./capability-summary.json) | Descriptive groups, qualifying candidates and deterministic repeat audit |
| [candidate-ranking.json](./candidate-ranking.json) | Top-12 ranking, bounded examples, exact readiness rule and top-three unions |
| [protected-inputs.json](./protected-inputs.json) | 120 explicit V150 and 166 broader R44 protected-input comparisons |
| [development-verification.json](./development-verification.json) | Focused/regression/all-R45, validators, AST and corrected obsolete test evidence |
| [reproduction.json](./reproduction.json) | Final artifact/source hashes and deterministic comparison results |

R45-03 source-tree hash `a50a4c01ec95664426e14c7723a79b566aa53cb46fd6a336d993d306bb3eceba`
is recoverable at commit `7ee02172f13d2e7a92ef2d3060ff0479e69d6cc5`.
Its audit recorded the pre-commit invocation `659c4e7dcebf29ac7e4567fcb3c58e0683be63ba`;
those records are historical and do not claim to verify the final source.
The parent independently compared every historical manifest entry with a Git
archive of the recoverable R45-03 commit.

The top-three hashes have complete occurrence counts 470/416/416 and a union of
497, as required by R45-05 Step 3. Their qualifying affected counts are 451/399/398
and union 474. The rescue-upper-bound sum is 0. The six target families include
three already ordinary and three not yet ordinary. These work-scope counts do not
predict 64/512 coverage. Tracked examples are capped at eight per candidate;
complete seed lists are never tracked or used as runtime allowlists.

For R45-06, restore the final source commit with `git archive`, verify every
manifest entry, and run the replay tools from the restored source using the fresh
fixed512 pairs. The existing receipt hashes identify the original local
invocation artifacts; retain the restored invocation's own provenance separately.
The exact executed verification/audit/replay commands are in the
[R45 ledger](../../r45_progress.md); local `commands.json` retains argv, exit codes
and log hashes. Recompute manifests with the existing helper, not Git's tree ID.
Use new output directories for regenerated audits/replays.

The R45-05 verdict commit contains documentation and compact receipts only;
the separately reviewed expectation correction preserves all ten negative Scene
cases, exact source binding, UNKNOWN grammar, mandatory deferred blockers and
rejection by all four rendering constructors. Full final verification was rerun
after that correction. All 14 changed Python files pass Python 3.10 AST parsing.

R45-06 archive restore, final handoff/checkpoint, tag and publication are pending.
Formal reference8192, gate2048, paired formal comparison, fixed80, blind review,
fresh confirmations, frontend/browser and release8192 remain **NOT_RUN**.
N2.8/adoption remains **BLOCKED**; D3 remains **DEFERRED**. Published R44 comparison
tags must not be force-updated or deleted.
