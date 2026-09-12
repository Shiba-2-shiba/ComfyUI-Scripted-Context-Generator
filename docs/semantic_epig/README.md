# Semantic EPIG

Last verified: 2026-08-31

このファイルは Semantic EPIG の canonical index です。現在地、次に変更する
対象、検証契約はまずここで確認します。個別の `*_spec.md`、`*_progress.md`、
`*_tasks.md` は各 wave の設計・実績記録であり、この index より新しい
source of truth にはなりません。

## Current State

- Current branch baseline: `main`
- Public `Context*` node I/O: unchanged
- Runtime config: `vocab/data/semantic_epig_config.json`
- Active domains: `action`, `object_relation`, `location_scene`,
  `clothing_tpo`, `personality_behavior`
- Shared ranking: `vocab/semantic_space.py`
- Config/debug helpers: `pipeline/semantic_epig.py`
- Asset validation: `asset_validator.py`
- Prompt-level audit: `tools/audit_semantic_epig_outputs.py`

The June 2026 R0-R7 refactor is complete. The relation-key descriptor matcher
and its dedicated regression test are present. The implemented builder split is:

- action: `action_parser.py`, `action_relation_binder.py`, `action_renderer.py`
- location: `location_policy.py`, `location_segment_selector.py`
- clothing: `clothing_candidate_renderer.py`, `clothing_candidate_selector.py`

## Document Authority

| Purpose | Canonical document | Status |
|---|---|---|
| Current state and navigation | `docs/semantic_epig/README.md` | Active |
| Initial implementation rollout | `implementation_spec.md`, `progress.md`, `tasks.md` | Completed history |
| R0-R7 maintainability refactor | `refactor_spec.md`, `refactor_progress.md`, `refactor_tasks.md` | Completed history |
| External reference evaluation | `reference_refresh_*` | Completed research history |
| Curated descriptor adoption | `curated_reference_adoption_*` | Completed adoption history |
| Solo duplicate suppression | `solo_duplicate_refactor_*` | Completed focused-refactor history |

For documentation, this file is the single source of truth.
`CURRENT_STATUS.md` is a repository-level summary/mirror and must be updated from
this index; it does not have equal authority. When evidence disagrees, use this
order:

1. runtime code, data schemas, and current tests for actual behavior
2. this canonical index for documentation status and routing
3. the active wave's locked experiment contract and append-only state
4. `CURRENT_STATUS.md` as a summary/mirror
5. completed wave documents as historical evidence

## Loop Engineering Contract

Future Semantic EPIG changes use the same loop discipline as
`docs/prompt_quality/`:

```text
DRAFT
  -> HYPOTHESIS_LOCKED
  -> BASELINE_READY
  -> CANDIDATE_SNAPSHOT_LOCKED
  -> GENERATED
  -> ANALYZED
  -> COMPARED
  -> REVIEWED
  -> VERIFIED
  -> PROMOTED | REJECTED
```

Any non-terminal state may become `ABORTED`. Rejected and aborted evidence is
preserved; a retry creates a new iteration instead of rewriting prior records.

Each active experiment must freeze:

- hypothesis, target metric, and guard metrics
- owned files and non-goals
- config/policy/cohort versions
- baseline source and data hashes
- deterministic seeds or fixture cohort
- promotion and rejection thresholds

Tracked decision evidence belongs under
`docs/semantic_epig/experiments/<experiment-id>/`. Large generated audits may
remain under `assets/results/semantic_epig/<experiment-id>/`, but tracked state
must bind them by path and SHA-256. Local generated artifacts alone are not
decision authority.

## Change Gate

Before changing an active domain:

1. Lock one hypothesis and one bounded ownership surface.
2. Capture the passive/current baseline with deterministic fixtures and hashes.
3. Lock the candidate snapshot before generation.
4. Compare prompt-level output and debug decisions.
5. Review target improvements and semantic-only, determinism, repetition, and
   cross-domain guard metrics.
6. Run focused tests, asset validation, full-flow verification, then broader
   regression tests in proportion to impact.
7. Record `PROMOTED`, `REJECTED`, or `ABORTED`; never silently replace evidence.

Minimum focused verification:

```bash
python -m unittest assets.test_semantic_space assets.test_semantic_epig assets.test_action_semantics assets.test_location_semantics assets.test_clothing_semantics assets.test_personality_semantics assets.test_action_generator assets.test_object_focus_service assets.test_personality_garnish
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

## Next Work

No item from the completed R0-R7 task board is currently open. A new Semantic
EPIG change starts as a new experiment/wave linked from this index; it does not
reopen `refactor_tasks.md`.
