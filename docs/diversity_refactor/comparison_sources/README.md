# Recoverable comparison sources

From AS01 onward, every source used as a development comparison baseline must be
recoverable from the remote repository before relying on its results. A local
directory and a SHA-256 alone are insufficient.

## Publication policy

1. Before changing a baseline, capture its source manifest, supplemental inputs,
   review/config files and the A1.6 lock. Preserve all files needed to execute it.
2. Commit the exact source and create an annotated comparison tag. An existing
   commit may be tagged if its restored bytes match. For an uncommitted historical
   snapshot, use an independent snapshot commit without inventing development
   ancestry. Do not merge snapshot commits into the development branch.
3. Pin the full commit, tree and annotated-tag object IDs in a registry. Never
   force-update or delete a published comparison tag; corrections get new names.
   Tag names alone are not an integrity check.
4. Restore into a fresh directory and compare both the source manifest and
   supplemental/A1.6 checks. Verify checkout preserves fixture and receipt bytes.
5. Publish source tags and the registry, verify the remote IDs, and record the
   exact baseline role in the experiment. A moving branch is not a baseline.
6. Preserve compact verification/environment receipts. Large regenerated logs
   may stay local if their reproducible source references and limitations are
   explicit. Record dependencies when running future experiments; do not label a
   later environment observation as the historical environment.

This policy applies to future comparisons. It does not retroactively publish
every historical R43 intermediate directory or certify any formal evaluation.

## AS01 source set

The [registry](as01/registry.json) pins full Git identities and source-guard files.
All three are **development** sources, not the original formal V150 baseline.

| Role | Fixed tag | Commit | Ordinary v2 /512 |
|---|---|---|---|
| Intake comparison baseline | `r43-baseline-nine-20260912` | `273c153dfe3651b56a91fdac08fab24ee6132c46` | 9 |
| AS01 immediate previous baseline | `r43-baseline-ten-20260912` | `2a8ffebfc68125ba7cbb1d8245516d48aff7511b` | 10 |
| Verified AS01 candidate | `r43-coverage-as01-20260912` | `d548cc4d4ca9bc127086cdc281aaa846079c0f41` | 11 |

The nine/ten snapshot commits were created on publication day from saved source;
they are not claims about when those sources were developed. Their only storage
adjustment appends `* -text` to `.gitattributes` so Git preserves all file bytes.
Original attribute files and complete original file-hash inventories are saved
here. Every other archived source file matches the original bytes. The source
manifest and supplemental/A1.6 checks are identical, including the absence of the
later prose-review file in the nine-case baseline.

The eleven-case tag points to the already published commit without modification.
Source tags contain source/configuration, not historical output directories.

## Restore without changing your current branch

Run in a clone of this repository with Git, Python and the test environment ready.
Use new destination directories; existing directories must not be overwritten.

```powershell
git fetch origin tag r43-baseline-nine-20260912
git fetch origin tag r43-baseline-ten-20260912
git fetch origin tag r43-coverage-as01-20260912
git worktree add --detach ../scg-baseline-nine refs/tags/r43-baseline-nine-20260912
git worktree add --detach ../scg-baseline-ten refs/tags/r43-baseline-ten-20260912
git worktree add --detach ../scg-as01 refs/tags/r43-coverage-as01-20260912
```

Before running a comparison, check the tag-object, peeled commit and tree IDs
against the registry (`git rev-parse <tag>`, `<tag>^{commit}`, `<tag>^{tree}`).
From the current development checkout, verify the three source guards:

```powershell
python -B -c "import json,sys; from pathlib import Path; from tools.realizer_candidate_intake import source_guard; base=Path('docs/diversity_refactor/comparison_sources/as01'); roots={'nine':'../scg-baseline-nine','ten':'../scg-baseline-ten','candidate':'../scg-as01'}; checks={role:source_guard(Path(root),require_contract=False)==json.loads((base/(role+'-source-guard.json')).read_text(encoding='utf-8')) for role,root in roots.items()}; print(checks); sys.exit(0 if all(checks.values()) else 1)"
```

For the unchanged AS01 candidate, run the existing portable intake from its
restored root. Intake deliberately uses the **nine-case** baseline:

```powershell
Set-Location ../scg-as01
python tools/verify_realizer_v2_candidate.py --stage intake --baseline-root ../scg-baseline-nine --output-dir assets/results/restored-as01-intake
```

The ten-case source is the additional preservation comparison for AS01. From
`scg-as01`, after the intake above completes, run:

```powershell
python -B -c "from pathlib import Path; from tools.audit_realizer_reachability import baseline_pairs; out=Path('assets/results/restored-ten-pairs'); out.mkdir(parents=True,exist_ok=False); baseline_pairs(Path('../scg-baseline-ten').resolve(),out.resolve(),0,512)"
python -B -c "import json,sys; from pathlib import Path; from tools.realizer_candidate_preservation import compare_pairs; rows=lambda name:[json.loads(line) for line in Path(name).read_text(encoding='utf-8').splitlines()]; result=compare_pairs(rows('assets/results/restored-ten-pairs/baseline-pairs.jsonl'),rows('assets/results/restored-as01-intake/reachability/normal-pairs.jsonl'),require_baseline_v2=10); print(json.dumps(result,ensure_ascii=False)); sys.exit(0 if result['status']=='PASS' else 1)"
```

The preservation CLI's nine-case contract is unchanged. The
[publication replay receipt](as01/publication-replay.json) records the separate
ten-case check and exact historical-pair hashes. Both restored baselines replayed
all512 inputs with byte-identical historical pair records at publication.

## Evidence scope

The AS01 directory includes the original intake verdict, both preservation
reports, source guards, protected-input hashes, reviewed prose/input receipts,
independent review and historical commands/environment records. Their embedded
absolute paths identify the old machine; use the restored paths above to run
again. Full raw evidence files referenced by the historical verdict are not all
included here. A new intake regenerates its own complete evidence directory.

The old environment record identifies Python/platform but is not a full package
lockfile. `environment-observation.json` is explicitly a new observation at source
publication time. These tags restore source; they do not reconstruct an entire
historical Python installation or establish formal quality acceptance.

Each `archive_sha256` identifies the local publication-time `git archive
--format=tar <commit>` artifact, not GitHub's generated ZIP or an archive produced
by an arbitrary Git version. The commit/tree and source-guard checks are the
cross-environment restoration checks.
