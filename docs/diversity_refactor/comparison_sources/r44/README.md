# R44 recoverable development sources

The [registry](./registry.json) pins full annotated-tag, commit, tree and source-guard identities. R44 adds diagnostic tools; ordinary output remains11/512 with3 families and6 common-forced families. The bounded selection gate found no eligible packet. Formal evaluation is NOT_RUN.

Use new destination directories. Do not overwrite another checkout or move existing tags.

```powershell
git fetch origin tag realizer-v2-r44-baseline-11
git fetch origin tag realizer-v2-r44-blocked-20260913
git worktree add --detach ../scg-r44-baseline realizer-v2-r44-baseline-11
git worktree add --detach ../scg-r44-diagnostics realizer-v2-r44-blocked-20260913
```

Compare `git rev-parse <tag>`, `<tag>^{commit}`, and `<tag>^{tree}` to the registry before using the source. From the checkout containing this registry, verify the guards:

```powershell
python -B -c "import json; from pathlib import Path; from tools.realizer_candidate_intake import source_guard; base=Path('docs/diversity_refactor/comparison_sources/r44'); assert source_guard(Path('../scg-r44-baseline')) == json.loads((base/'baseline/source-guard.json').read_text()); assert source_guard(Path('../scg-r44-diagnostics')) == json.loads((base/'diagnostics/source-guard.json').read_text()); print('source guards PASS')"
```

From the restored diagnostic root, run the commands in [the handoff](../../r44_handoff.md). Then verify forced proof in both import modes:

```powershell
python tools/realizer_candidate_replay.py --source-root . --pairs assets/results/r44-recheck/reachability/normal-pairs.jsonl --output-dir assets/results/r44-recheck/replay-root --import-mode root
python tools/realizer_candidate_replay.py --source-root . --pairs assets/results/r44-recheck/reachability/normal-pairs.jsonl --output-dir assets/results/r44-recheck/replay-package --import-mode package --order reverse
```

All six `summary.json` family entries must have positive `common_forced_v2`; summary/evidence/family-row files should match across import modes. Audit forced_render_v2 is only exact ordinary-output equality and must not substitute for this common proof.

Tracked receipts describe the current environment and exact source, not a historical environment lock. Absolute paths in command receipts identify this execution; use your restored paths instead. The source tar hashes identify local Git archives, not GitHub-generated ZIP files. Large raw audit/replay logs are not tracked; regenerate them from the pinned source. The diagnostic snapshot tag precedes final handoff documentation; the registry lives on the R44 development branch.
