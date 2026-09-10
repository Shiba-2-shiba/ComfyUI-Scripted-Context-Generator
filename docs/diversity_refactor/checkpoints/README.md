# N2.7-R4 checkpoint

`main` remains the V150 stable runtime. Candidate development continues on
`refactor/realizer-v2`, with candidate04, 05, 06 and 07 recorded as consecutive
ordinary source commits at the repository root. Review changes on that branch;
do not merge them into `main` until the unchanged adoption gates pass.

This directory retains the checkpoint manifest and recovery instructions. The
original `n27-r4-candidate04-07.zip` remains available in commit
`5edea779206cdbcdf4e756012561a137d3ff0c3f`. It preserves the implementation through
N2.7-R4.2 and contains candidate04-07
source snapshots, candidate05-07 development evidence/harnesses, the fixed
intake512 and the candidate04 observations needed by those harnesses.
It does not contain all historical candidate04 formal evaluation artifacts.
OMX state, caches and unrelated local results are excluded.

The adjacent JSON records the archive SHA256, archive commit, base commit and four candidate
source hashes. `CHECKPOINT-MANIFEST.json` inside the archive records every file
hash. Creation verification extracted all files into a temporary directory,
checked their hashes and rebuilt all four source manifests successfully.

For normal development, check out `refactor/realizer-v2`. Its source, fixtures
and tests are tracked directly; no archive extraction is required.

For historical evidence recovery, run the following from the repository root
in a fresh **stable** checkout where the candidate directories do not already
exist. Python preserves the ZIP bytes on all supported PowerShell versions:

```powershell
python -c "import pathlib, subprocess; p = pathlib.Path('assets/results/n27-r4-candidate04-07.zip'); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(subprocess.check_output(['git', 'show', '5edea779206cdbcdf4e756012561a137d3ff0c3f:docs/diversity_refactor/checkpoints/n27-r4-candidate04-07.zip']))"
python -m zipfile -e assets/results/n27-r4-candidate04-07.zip .
```

The original `assets/results/diversity_refactor/` paths are restored. These paths
remain ignored by Git. Candidate07 historical evidence verification can then be
repeated from the stable repository root. This verifier intentionally asserts
that the root runtime is still V150, so it must not run on the development branch:

```powershell
python assets/results/diversity_refactor/n27-candidate-07/verify_candidate.py
```

Latest result: 9/512 actual v2 applications; four observed syntax families.
Development preservation checks passed. Adoption remains **BLOCKED**; formal
8192/2048/fixed80 gates were not run. See the canonical progress log for details.
