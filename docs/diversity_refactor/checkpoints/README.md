# N2.7-R4 checkpoint

`n27-r4-candidate04-07.zip` preserves the isolated implementation through
N2.7-R4.2 without applying it to the active runtime. It contains candidate04-07
source snapshots, candidate05-07 development evidence/harnesses, the fixed
intake512 and the candidate04 observations needed by those harnesses.
It does not contain all historical candidate04 formal evaluation artifacts.
OMX state, caches and unrelated local results are excluded.

The adjacent JSON records the archive SHA256, base commit and four candidate
source hashes. `CHECKPOINT-MANIFEST.json` inside the archive records every file
hash. Creation verification extracted all files into a temporary directory,
checked their hashes and rebuilt all four source manifests successfully.

Restore from the repository root in a fresh checkout, where the candidate
directories do not already exist:

```powershell
python -m zipfile -e docs/diversity_refactor/checkpoints/n27-r4-candidate04-07.zip .
```

The original `assets/results/diversity_refactor/` paths are restored. These paths
remain ignored by Git; the archive is the committed checkpoint. Candidate07
verification can then be repeated from the repository root:

```powershell
python assets/results/diversity_refactor/n27-candidate-07/verify_candidate.py
```

Latest result: 9/512 actual v2 applications; four observed syntax families.
Development preservation checks passed. Adoption remains **BLOCKED**; formal
8192/2048/fixed80 gates were not run. See the canonical progress log for details.
