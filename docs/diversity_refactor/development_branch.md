# Realizer v2 development branch

`main` contains V150 stable. `refactor/realizer-v2` contains candidate07 at ordinary
repository paths, including its tests and fixtures. Future development should
commit changes here directly. Candidate source no longer requires ZIP extraction.
Adoption remains **BLOCKED**; do not merge this branch into stable until the
unchanged formal 8192/2048/fixed80 gates and required family evidence pass.

## Checkpoint lineage

| Snapshot | Source commit |
| --- | --- |
| candidate04 | `b2d1261c46e9796e5f2b399cfa281b47990ccdfb` |
| candidate05 | `c0822f55a3ffb19368bdfeca5ebde66b0f56e006` |
| candidate06 | `f67798b791a0742b8918614495171414fa1663bb` |
| candidate07 | `24bbbfbfb7ef7a66d2997f47149d870dfb84e79a` |

These are consecutive commits on the same paths. For example:

```sh
git diff c0822f5 f67798b -- pipeline assets
git diff f67798b 24bbbfb -- pipeline assets
git diff main...refactor/realizer-v2
```

All 2510 archived file hashes were verified before migration. Every committed
source-manifest file and the additional runtime support files match the original
snapshot bytes for all four candidates. Candidate07's source hash remains
`b8a99c2fa84cc59e2ade7378d6614527a3bfe672d42e474d0dbaca6078c57472`.
Explicit `.gitattributes` entries preserve the checkpoint's CRLF files across
checkouts; changes to those attributes require rechecking source hashes.
Current documentation is retained instead of restoring stale snapshot documents.

The [checkpoint manifest](checkpoints/n27-r4-candidate04-07.json) records all four
source hashes. Historical observations, harnesses and ZIP recovery instructions
remain available through [checkpoints/README.md](checkpoints/README.md). The old
`verify_candidate.py` requires a stable root plus isolated candidates; it cannot
validate this development branch unchanged.

## Development verification

Run from the branch root with the existing Python test environment. No new
dependencies or source behavior changes were introduced by this migration.

```powershell
$candidateTests = Get-ChildItem assets/test_n27*.py | Select-Object -ExpandProperty FullName
python -m pytest -q $candidateTests assets/test_syntax_family_selector.py assets/test_prompt_realizer_v2.py -k 'not test_actual_v1_family_metadata_and_seed_replay'
python -m unittest assets.test_context_codec assets.test_context_state_adapter assets.test_context_nodes assets.test_context_ops assets.test_vocab_lint
python tools/validate_prompt_data.py
python -c "from asset_validator import validate_assets; issues = validate_assets(); print(issues); assert not issues"
python tools/verify_full_flow.py
git diff --check main
```

Migration verification: 151 focused tests and 1888 subtests passed; 29 related
regressions passed; data/asset validation and full flow passed. The single excluded
test, `test_actual_v1_family_metadata_and_seed_replay`, is the previously recorded
candidate failure concerning v1 family aliases. It still needs resolution during
development; these results do not claim an unrestricted full-suite pass.
No typecheck configuration is present. Formal adoption gates were not rerun for
this storage-only migration, and no CI workflow was added.
