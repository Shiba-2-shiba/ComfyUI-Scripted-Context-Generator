# Codex Progress Board

## How to use this board

Use this as the single board for the prompt-repetition refactor.
The repository baseline is green; this board tracks work that reduces repeated semantics without regressing prompt safety, determinism, or workflow compatibility.

States:
- Backlog
- Ready
- In Progress
- Review
- Done
- Blocked

---

## Project KPIs

Track these after each merged PR.

| KPI | Baseline | Current | Target | Notes |
|---|---:|---:|---:|---|
| `python -m pytest assets -q` | 222 passed / 161 subtests / 0 warnings | 240 passed / 161 subtests / 0 warnings | pass | Latest full run on 2026-03-21 after `TASK-M20-02` |
| `asset_validator.validate_assets()` warnings | 0 | 0 | 0 | Must stay clean during this refactor |
| official workflow analyzer warning count | 0 / 32 runs | 0 / 32 runs | 0 / 32 runs | `python tools/analyze_context_workflow_diversity.py --runs 32 --seed-start 0` |
| active prompt rows with breath-family language in end-to-end reconstruction | 62 / 105 | 8 / 105 | lower than baseline | Recomputed with the current runtime at 1 sample per active-source row on 2026-03-21 after the `mood_map` rebalance |
| active prompt rows with `calm breathing` | 27 / 105 | 0 / 105 | 0 forced by construction | `quiet_focused` no longer carries the phrase in high-frequency staging |
| active prompt rows with `slow breath` | 28 / 105 | 1 / 105 | 0 forced by construction | The remaining occurrence is no longer coming from `peaceful_relaxed` staging |
| dominant calm-heavy moods in prompt source | `quiet_focused = 27`, `peaceful_relaxed = 28` | source data unchanged, but no longer bonus-weighted by default source selection | review and reduce only if still needed after runtime controls | `prompts.jsonl` distribution stays the same, but `pipeline/source_pipeline.py` no longer promotes these moods above brighter defaults |
| fixed staging mode | full list appended | sampled deterministic subset | sampled deterministic subset | `apply_mood_expansion()` now uses the staged subset helper |
| moods with forced staging tags in repetition audit | 9 / 9 moods | 0 / 9 moods | 0 / 9 moods | Refreshed artifact `prompt_repetition_active_source_8.json` remains clean after `TASK-M19-02` |

---

## Milestone dashboard

### M18. Repetition observability and guardrails
- [x] Add repetition audit for staging, garnish, and final prompts
- [x] Add deterministic staging-selection regression coverage

### M19. Runtime repetition controls
- [x] Sample `staging_tags` instead of appending full fixed lists
- [x] Add cross-layer semantic-family dedupe and budgets

### M20. Vocabulary and source-data rebalance
- [x] Rework high-frequency `mood_map` staging and descriptions
- [x] Review calm-heavy source defaults outside `mood_map`

---

## Task board

### Backlog
- TASK-M21-01 Revisit template-catalog weighting only if repetition remains template-driven

### Ready
- _(empty)_

### In Progress
- _(empty)_

### Review
- _(empty)_

### Done
- TASK-M20-02 Review calm-heavy source defaults outside `mood_map`
- TASK-M20-01 Rework high-frequency `mood_map` staging and descriptions
- TASK-M19-02 Add cross-layer semantic-family dedupe and budgets
- TASK-M19-01 Sample `staging_tags` instead of appending full fixed lists
- TASK-M18-02 Add focused regression coverage for deterministic staging selection
- TASK-M18-01 Add a repetition audit for staging, garnish, and final prompts
- TASK-M17-01 Clarify shared sanitization versus final cleaning
- TASK-M16-01 Centralize object-focus helpers and policy access
- TASK-M15-02 Add regression coverage for service-boundary expectations
- TASK-M15-01 Slim `registry.py` into a real compatibility facade
- TASK-M14-02 Stabilize pytest cache behavior and ignore transient artifacts
- TASK-M14-01 Make prompt-renderer debug logging opt-in
- TASK-M13-01 Broader vocabulary expansion
- TASK-M12-02 Reduce recent-window costume-signature repetition
- TASK-M12-01 Add explicit clothing repetition observability
- TASK-M11-02 Document and guard the remaining intentional facade surface
- TASK-M11-01 Replace avoidable internal imports of `pipeline.content_pipeline`
- TASK-M10-02 Add prompt-surface regression coverage and refresh baselines
- TASK-M10-01 Introduce non-gerund action-surface variation
- TASK-M9-02 Add regression coverage for verb-metric edge cases
- TASK-M9-01 Improve action verb normalization

### Blocked
- _(empty)_

---

## Validation checklist

Minimum checks for touched work:

- `python -m py_compile ...` on touched modules
- `python -m pytest` for touched tests
- `python -m pytest assets -q`
- `python -c "from asset_validator import validate_assets; print(validate_assets())"`

Additional checks by milestone:

- M18: run the new repetition audit and capture the baseline
- M19: rerun the repetition audit after runtime controls and compare against baseline
- M20: rerun the repetition audit, full `assets` pytest, and the workflow diversity analyzer

---

## Weekly / per-session check-in

At the start of each Codex session, update:

- Current milestone:
- Current task:
- Dependencies cleared:
- Risk level: low / medium / high
- Expected file set:
- Test plan for this session:

At the end of each session, update:

- Status moved to:
- What passed:
- What failed:
- New findings:
- Follow-up task created:

### Latest session

Start:
- Current milestone: M20 Vocabulary and source-data rebalance
- Current task: `TASK-M20-02 Review calm-heavy source defaults outside mood_map`
- Dependencies cleared: `TASK-M20-01` already removed the highest-frequency breath cues from `mood_map`, so this pass could focus on the remaining calm-heavy defaults in `garnish`, `action_pools`, and source selection
- Risk level: medium
- Expected file set: `vocab/garnish/logic.py`, `vocab/data/action_pools.json`, `pipeline/source_pipeline.py`, focused tests and fixtures under `assets/`, refreshed audit artifacts under `assets/results/`, and `リファクタリング/codex_progress_board.md`
- Test plan for this session: reduce calm-heavy source weighting outside `mood_map`, cap calm-load garnish face-forward stacking, neutralize the most explicit body-cue action-pool entries, refresh audit/snapshot artifacts, then rerun full `assets`, asset validation, and the workflow diversity analyzer

End:
- Status moved to: Done
- What passed: `python -m py_compile vocab/garnish/logic.py pipeline/source_pipeline.py assets/test_calm_bias_controls.py assets/test_source_pipeline.py`, `python -m pytest assets/test_calm_bias_controls.py assets/test_source_pipeline.py assets/test_personality_garnish.py assets/test_prompt_repetition_audit.py assets/test_determinism.py -q`, `python tools/audit_prompt_repetition.py --samples-per-row 8 --enforce-thresholds`, `python tools/audit_template_diversity.py --seed-count 32 --seed-start 0 --output assets/results/template_diversity_32.json`, `python -m pytest assets -q`, `python -c "from asset_validator import validate_assets; print(validate_assets())"`, and `python tools/analyze_context_workflow_diversity.py --runs 32 --seed-start 0`
- What failed: full `assets` initially surfaced snapshot and template-diversity artifact drift after the runtime changes; expectations were refreshed and the final validation pass was green
- New findings: calm-heavy defaults outside `mood_map` were being amplified by three places at once: `source_pipeline` bonus-weighted `quiet_focused` and `peaceful_relaxed`, calm-load garnish always emitted multiple face-forward tags, and several common action-pool entries baked in `focused/gaze/breath` cues. Removing those bonuses and neutralizing the most explicit action/garnish defaults kept workflow warnings at `0 / 32`, moved the workflow analyzer toward more playful/energetic moods, and preserved a green full `assets` suite.
- Follow-up task created: none; M20 is complete and only deferred `TASK-M21-01` remains in backlog if repetition still proves template-driven later

---

## Definition of Ready
A task may move to Ready only if:
- scope fits in one PR
- expected files are named
- acceptance criteria are explicit
- validation commands are listed
- rollback is obvious

## Definition of Done
A task may move to Done only if:
- code merged or patch accepted
- listed tests all passed
- compatibility impact documented
- board and KPI row updated
