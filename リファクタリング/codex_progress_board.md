# Codex Progress Board

## How to use this board

Use this as the single board for the post-M13 maintenance refactor.
The repository is already green; this board tracks cleanup that improves operational safety and maintainability without reopening large feature work.

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
| `python -m pytest assets -q` | 210 passed / 161 subtests / 1 warning | 222 passed / 161 subtests / 0 warnings | pass | Latest full run on 2026-03-21 after `TASK-M17-01` |
| `asset_validator.validate_assets()` warnings | 0 | 0 | 0 | Must stay clean during this refactor |
| official workflow analyzer warning count | 0 / 32 runs | 0 / 32 runs | 0 / 32 runs | `python tools/analyze_context_workflow_diversity.py --runs 32 --seed-start 0` |
| default prompt-renderer file logging | on | off | off | `prompt_renderer.py` now requires explicit opt-in to attach a file handler |
| repo-local pytest cache warning count | 1 | 0 | 0 | Stabilized via repo `pytest.ini` |
| repo-owned imports using `pipeline.content_pipeline` | 1 | 1 | 1 | Compatibility guard only; keep stable |

---

## Milestone dashboard

### M14. Runtime side-effect and hygiene cleanup
- [x] Remove default prompt-renderer file logging
- [x] Stabilize pytest cache behavior
- [x] Add regression coverage and update repo config

### M15. Registry and service-boundary cleanup
- [x] Reduce implementation ownership inside `registry.py`
- [x] Guard the intended compatibility surface with focused tests

### M16. Shared heuristic consolidation
- [x] Centralize object-focus helpers and policy access
- [x] Reduce duplicated runtime classification logic

### M17. Text normalization boundary cleanup
- [x] Clarify sanitization vs final cleaning ownership
- [x] Add regression coverage for the cleaned boundary

---

## Task board

### Backlog
- _(empty)_

### Ready
- _(empty)_

### In Progress
- _(empty)_

### Review
- _(empty)_

### Done
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

- M14: default import/logging behavior checks plus full `assets` pytest run
- M15: focused registry/service tests plus full `assets` pytest run
- M16: focused helper tests plus full `assets` pytest run
- M17: focused normalization tests plus full `assets` pytest run

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
- Current milestone: M17 Text normalization boundary cleanup
- Current task: `TASK-M17-01 Clarify shared sanitization versus final cleaning`
- Dependencies cleared: `TASK-M16-01` centralized duplicated object-focus helpers, so the next cleanup target was the overlapping text-normalization logic across `semantic_policy`, prompt assembly, and `PromptCleaner`
- Risk level: medium
- Expected file set: `core/semantic_policy.py`, `prompt_renderer.py`, `nodes_prompt_cleaner.py`, focused tests under `assets/`, `リファクタリング/codex_progress_board.md`, `リファクタリング/codex_temporary_exceptions.md`, `リファクタリング/codex_operating_notes.md`
- Test plan for this session: centralize shared fragment sanitization in `semantic_policy`, make prompt assembly delegate to that shared cleanup, keep `PromptCleaner` focused on final user-facing polish, add focused regression tests, then rerun focused pytest, the full `assets` suite, `asset_validator`, and the workflow diversity analyzer

End:
- Status moved to: Done
- What passed: `python -m py_compile core/semantic_policy.py prompt_renderer.py nodes_prompt_cleaner.py assets/test_semantic_policy.py assets/test_prompt_renderer.py assets/test_prompt_cleaner.py`, `python -m pytest assets/test_semantic_policy.py assets/test_prompt_renderer.py assets/test_prompt_cleaner.py assets/test_policy_alignment.py assets/test_policy_drift.py assets/test_fx_cleanup.py -q`, `python -m pytest assets -q`, `python -c "from asset_validator import validate_assets; print(validate_assets())"`, and `python tools/analyze_context_workflow_diversity.py --runs 32 --seed-start 0`
- What failed: none
- New findings: the text cleanup boundary is easier to maintain when `semantic_policy` owns compact fragment sanitization and banned-term removal, prompt assembly only delegates to that shared cleanup after composition, and `PromptCleaner` stays responsible for final user-facing polish such as article fixes, deduplication, and sentence shaping. That split removed overlapping punctuation cleanup without changing policy behavior.
- Follow-up task created: none

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
