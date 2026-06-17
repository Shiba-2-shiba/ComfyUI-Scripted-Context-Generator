# Curated Reference Adoption Tasks

対象リポジトリ: `ComfyUI-Scripted-Context-Generator`  
対象ブランチ: `dev2`  
作成日: 2026-06-17 JST  
関連仕様: `curated_reference_adoption_spec.md`  
関連進捗: `curated_reference_adoption_progress.md`

---

## 0. Common Rules

- Do not change public `Context*` node inputs or outputs.
- Do not add dependencies.
- Do not commit `参考/`.
- Do not commit generated `assets/results/` score-bearing overlays.
- Do not load raw EPIG / NRC / EmotionDynamics data at runtime.
- Do not use `llm_expanded_prompts.csv` as prompt source.
- Keep semantic-only policy: no style / quality / camera / render / body-type descriptors.
- Preserve seed determinism.
- Start runtime-facing changes in passive/debug-only mode.
- Add tests before active behavior changes.
- Keep generated reference data as local audit input unless explicitly transformed into repo-authored curated data.

Focused verification:

```bash
python -m unittest assets.test_action_semantics assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_policy
python tools/validate_prompt_data.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## C0. Planning Docs Setup

### C0.1 Add planning docs

Files:

```text
docs/semantic_epig/curated_reference_adoption_spec.md
docs/semantic_epig/curated_reference_adoption_progress.md
docs/semantic_epig/curated_reference_adoption_tasks.md
```

Acceptance:

- [x] Main scope covers items 1〜3 from the current implementation direction.
- [x] Runtime adoption remains deferred until audit/passive gates are satisfied.
- [x] Extensibility path is documented.

---

## C1. Reference Path Cleanup

### C1.1 Replace stale absolute path examples

Files:

```text
docs/semantic_epig/reference_refresh_spec.md
docs/semantic_epig/reference_refresh_progress.md
docs/semantic_epig/reference_refresh_tasks.md
docs/semantic_epig/reference_refresh_handoff.md
```

Requirements:

- Replace old examples that hardcode:

```text
C:\Users\inott\Downloads\新しいフォルダー (3)\参考
```

- Prefer:

```text
<REFERENCE_ROOT>
..\参考
```

- If a current local absolute path is useful, label it as an example only.

Acceptance:

- [x] No command example depends on `(3)\参考`.
- [x] Docs still state that `参考/` is external and must not be committed.
- [x] Regeneration commands remain copy/paste friendly from repo root.

### C1.2 Verify path cleanup

Run:

```bash
rg -n "新しいフォルダー \(3\)|<REFERENCE_ROOT>|\.\.\\参考" docs/semantic_epig -g "reference_refresh_*.md"
```

Acceptance:

- [x] Old path appears only in historical notes if intentionally preserved.
- [x] New command examples use `<REFERENCE_ROOT>` or `..\参考`.

---

## C2. Relation-Key-Specific Descriptor Test

### C2.1 Add direct relation key match test

Files:

```text
assets/test_action_semantics.py
```

Target function:

```text
pipeline.action_semantics.semantic_descriptor_options_for_slot
```

Test requirements:

- Use a tiny descriptor payload or monkeypatch loader.
- Include a descriptor with:

```json
{
  "roles": ["hand_action"],
  "relation_keys": ["drink:sipping"],
  "text": "keeping the cup steady near her hands"
}
```

- Assert it is returned for `relation_key="drink:sipping"`.
- Assert it is not returned for unrelated relation key.

Acceptance:

- [x] Relation-key matching is covered by a focused unit test.
- [x] Runtime prompt output is not changed.
- [x] No external reference data is used in the test.

### C2.2 Optional asset validator coverage

Only if data file changes are needed.

Files:

```text
asset_validator.py
assets/test_asset_validator.py
vocab/data/action_slot_descriptors.json
```

Acceptance:

- [ ] `relation_keys` remains optional.
- [ ] malformed `relation_keys` values are reported.
- [ ] `validate_assets()` still returns 0 issues.

### C2.3 Verify relation-key test

Run:

```bash
python -m unittest assets.test_action_semantics assets.test_action_generator
```

Acceptance:

- [x] Tests pass.

---

## C3. Local Report Regeneration

### C3.1 Regenerate current reference reports

Run from repo root:

```bash
python tools\audit_epig_reference_alignment.py --reference-root "..\参考" --output assets\results\epig_reference_alignment.json
python tools\extract_epig_reference_overlay.py --reference-root "..\参考" --output assets\results\epig_reference_overlay.local.json
python tools\audit_subject_centric_descriptors.py --reference-root "..\参考" --output assets\results\subject_centric_descriptor_candidates.json
python tools\audit_reference_dimension_projection.py --reference-root "..\参考" --output assets\results\reference_dimension_projection.json
python tools\audit_llm_expanded_prompt_policy.py --reference-root "..\参考" --output assets\results\llm_expanded_prompt_policy_audit.json
python tools\review_reference_refresh_adoption.py --results-dir assets\results --output assets\results\reference_refresh_adoption_decision.json
```

Acceptance:

- [x] Reports are generated under `assets/results/`.
- [x] Reports are not tracked.
- [x] Optional missing sources are warnings, not blockers.

### C3.2 Record current summary

Files:

```text
docs/semantic_epig/curated_reference_adoption_progress.md
```

Acceptance:

- [x] Record key counts for overlay, subject candidates, LLM policy, dimension projection.
- [x] Record any missing optional sources.
- [x] Keep runtime adoption decision unchanged unless evidence requires a new plan.

---

## C4. Subject-Centric Candidate Triage

### C4.1 Review `needs_phrase` candidates

Input:

```text
assets/results/subject_centric_descriptor_candidates.json
```

Requirements:

- Review only `needs_phrase` and `direct` categories first.
- Do not copy reference terms directly into prompt data.
- Rewrite candidates into repo style when useful.
- Reject anything near camera / view / quality / style / render / body type.

Acceptance:

- [x] Candidate review notes distinguish `direct`, `needs_phrase`, `reject`, and `unmatched`.
- [x] Candidate notes include target slot and risk note.
- [x] No runtime data is changed in this task.

### C4.2 Create curated candidate shortlist

Candidate output options:

```text
docs/semantic_epig/curated_reference_candidate_shortlist.md
```

or a section in:

```text
docs/semantic_epig/curated_reference_adoption_progress.md
```

Required fields:

```text
candidate_id
source_classification
target_slot
proposed_repo_phrase
source_hint
rewrite_reason
risk_note
decision
```

Acceptance:

- [x] Shortlist contains a small number of candidates, not all `needs_phrase`.
- [x] Each accepted candidate has repo-authored phrase text.
- [x] Rejected candidates include reason.

---

## C5. Curated Data Schema Decision

### C5.1 Decide whether to add a new curated data file

Options:

1. Add new file:

```text
vocab/data/subject_centric_descriptor_overrides.json
```

2. Fold small descriptors into existing:

```text
vocab/data/personality_behavior_profiles.json
```

Decision criteria:

- Choose new file if provenance / passive mode / future extension need a separate boundary.
- Choose existing file if candidate count is tiny and behavior is already personality-only.

Acceptance:

- [x] Decision is recorded in progress.
- [x] Rejected option and reason are recorded.
- [x] No data is added until validator/test requirements are clear.

### C5.2 Define schema and validation rules

If new file is chosen, schema must include:

```text
schema_version
descriptors[].id
descriptors[].slot
descriptors[].text
descriptors[].source_hint
descriptors[].rewrite_reason
descriptors[].risk_note
descriptors[].mode
```

Acceptance:

- [x] Missing / malformed fields have validator coverage.
- [x] semantic-only policy scan covers descriptor text.
- [x] score-bearing copied fields are not allowed.

---

## C6. Passive Runtime Integration Plan

Do not start C6 implementation until C1〜C5 are complete.

### C6.1 Add passive loader

Candidate files:

```text
vocab/personality_semantics.py
vocab/garnish/logic.py
```

Requirements:

- Missing curated data file is safe.
- Passive mode records candidate availability/debug only.
- Prompt output is unchanged in passive mode.
- Context rejection logic remains active.

Acceptance:

- [x] Passive mode does not change prompt snapshots.
- [x] Debug includes selected/available/rejected candidate metadata.
- [x] Existing personality tests pass.

### C6.2 Add tests for passive behavior

Candidate files:

```text
assets/test_personality_semantics.py
assets/test_personality_garnish.py
assets/test_semantic_epig_audit.py
```

Acceptance:

- [x] Passive candidate availability is visible.
- [x] Passive output equals baseline.
- [x] Reject/fallback behavior is deterministic.

### C6.3 Verify passive integration

Run:

```bash
python -m unittest assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig_audit
python tools\validate_prompt_data.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Acceptance:

- [x] Tests pass.
- [x] Validator has 0 issues.

---

## C7. Active Adoption Gate

C7 is intentionally deferred until C6 evidence exists.

### C7.0 Add active gate infrastructure

Files:

```text
vocab/data/semantic_epig_config.json
vocab/personality_semantics.py
asset_validator.py
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
```

Acceptance:

- [x] Subject-centric overrides have a nested config gate under `personality_behavior`.
- [x] Config has an explicit gate; current gate is active with only one active descriptor.
- [x] Active selector behavior is covered by test-only fixture data.
- [x] Audit output exposes subject-centric override debug.
- [x] Current curated data keeps all but `sc_gaze_downcast_01` at `mode=passive`.

### C7.1 Capture active/passive prompt audit

Run:

```bash
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_adoption.json
```

Acceptance:

- [x] Changed prompts are explainable for the current all-active Semantic EPIG baseline.
- [x] policy issue count is 0.
- [x] prompt length delta is available in generated audit records.
- [x] subject-centric overrides remain debug-visible and passive.

### C7.2 Active enablement decision

Acceptance:

- [x] If active adoption is rejected/deferred, reason is recorded.
- [x] If active adoption is accepted, update snapshots/tests in the same change.
- [x] Full verification passes before completion.

Full verification:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools\validate_prompt_data.py
python tools\verify_full_flow.py
python tools\check_widgets_values.py
python assets\calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## C8. Active Adoption Wave 2

### C8.1 Add extensibility filters before broadening active descriptors

Files:

```text
vocab/personality_semantics.py
vocab/garnish/logic.py
assets/test_personality_semantics.py
```

Requirements:

- Runtime selection respects optional `mood_keys`.
- Runtime selection respects optional `reject_context_terms`.
- Current garnish mood/action/context are passed into subject-centric override selection.
- Existing descriptor mode and config mode gates remain required.

Acceptance:

- [x] `mood_keys` matching is covered by a focused unit test.
- [x] `reject_context_terms` rejection is covered by a focused unit test.
- [x] Existing active `sc_gaze_downcast_01` behavior remains intact.

### C8.2 Activate one second descriptor only

Files:

```text
vocab/data/subject_centric_descriptor_overrides.json
assets/fixtures/prompt_snapshot_cases.json
docs/semantic_epig/curated_reference_candidate_shortlist.md
docs/semantic_epig/curated_reference_adoption_progress.md
```

Accepted descriptor:

```text
sc_expression_reassuring_01 -> small reassuring smile
```

Acceptance:

- [x] Only one additional descriptor changed from `passive` to `active`.
- [x] Prompt snapshots are updated only for intentional active-selection changes.
- [x] Semantic audit has `policy_issue_count=0`.
- [x] Full verification passes.

Verification:

```bash
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
python -m unittest discover -s assets -p "test_*.py"
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave2.json
python tools\validate_prompt_data.py
python tools\verify_full_flow.py
python tools\check_widgets_values.py
python assets\calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## C9. Active Adoption Wave 3

### C9.1 Activate one third descriptor only

Files:

```text
vocab/data/subject_centric_descriptor_overrides.json
assets/fixtures/semantic_epig_audit_cases.json
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
tools/audit_semantic_epig_outputs.py
```

Accepted descriptor:

```text
sc_gaze_curious_01 -> curious eyes
```

Acceptance:

- [x] Only one additional descriptor changed from `passive` to `active`.
- [x] A standard semantic audit fixture exercises the new descriptor.
- [x] The audit context manager does not leak forced passive/active modes into later same-process tests.
- [x] Semantic audit has `policy_issue_count=0`.
- [x] Full verification passes.

Verification:

```bash
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
python -m unittest discover -s assets -p "test_*.py"
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave3.json
python tools\validate_prompt_data.py
python tools\verify_full_flow.py
python tools\check_widgets_values.py
python assets\calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## C10. Active Adoption Wave 4

### C10.1 Activate one mood-gated hands descriptor only

Files:

```text
vocab/data/subject_centric_descriptor_overrides.json
vocab/personality_semantics.py
assets/fixtures/semantic_epig_audit_cases.json
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
```

Accepted descriptor:

```text
sc_hands_touching_lips_01 -> fingers resting near her lips
```

Requirements:

- Descriptor remains scoped to `shy` and `moved`.
- Matching mood-specific active candidates take priority over generic active candidates.
- Non-moved `shy` still selects `sc_gaze_downcast_01`.
- Context reject terms are present before active adoption.

Acceptance:

- [x] Only one additional descriptor changed from `passive` to `active`.
- [x] A standard semantic audit fixture exercises the new descriptor.
- [x] Mood-specific priority is covered by focused tests.
- [x] Semantic audit has `policy_issue_count=0`.
- [x] Full verification passes.

Verification:

```bash
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
python -m unittest discover -s assets -p "test_*.py"
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave4.json
python tools\validate_prompt_data.py
python tools\verify_full_flow.py
python tools\check_widgets_values.py
python assets\calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## C11. Active Adoption Wave 5

### C11.1 Activate one calm mood-gated expression descriptor only

Files:

```text
vocab/data/subject_centric_descriptor_overrides.json
assets/fixtures/semantic_epig_audit_cases.json
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
```

Accepted descriptor:

```text
sc_expression_calm_01 -> calm expression
```

Requirements:

- Descriptor remains scoped to `neutral` / `gentle`.
- Descriptor remains gated by calm/relieved mood keys.
- Tense/high-motion contexts are rejected before active selection.
- All previously active descriptors remain covered by standard semantic audit fixtures.

Acceptance:

- [x] Only one additional descriptor changed from `passive` to `active`.
- [x] A standard semantic audit fixture exercises the new descriptor.
- [x] Existing `sc_expression_reassuring_01` remains covered by another fixture.
- [x] Semantic audit has `policy_issue_count=0`.
- [x] Full verification passes.

Verification:

```bash
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
python -m unittest discover -s assets -p "test_*.py"
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave5.json
python tools\validate_prompt_data.py
python tools\verify_full_flow.py
python tools\check_widgets_values.py
python assets\calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## C12. Active Adoption Wave 6

### C12.1 Activate one joy/relax mood-gated expression descriptor only

Files:

```text
vocab/data/subject_centric_descriptor_overrides.json
assets/fixtures/semantic_epig_audit_cases.json
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
```

Accepted descriptor:

```text
sc_expression_contented_01 -> contented mouth
```

Requirements:

- Descriptor remains scoped to `gentle` / `cheerful`.
- Descriptor remains gated by joy/relieved mood keys.
- Tense/high-motion contexts are rejected before active selection.
- Non-matching cheerful cases continue to select `sc_gaze_curious_01`.

Acceptance:

- [x] Only one additional descriptor changed from `passive` to `active`.
- [x] A standard semantic audit fixture exercises the new descriptor.
- [x] Existing active descriptors remain covered by standard semantic audit fixtures.
- [x] Semantic audit has `policy_issue_count=0`.
- [x] Full verification passes.

Verification:

```bash
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
python -m unittest discover -s assets -p "test_*.py"
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave6.json
python tools\validate_prompt_data.py
python tools\verify_full_flow.py
python tools\check_widgets_values.py
python assets\calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## C13. Active Adoption Wave 7

### C13.1 Activate one awkward/mysterious mood-gated expression descriptor only

Files:

```text
vocab/data/subject_centric_descriptor_overrides.json
assets/fixtures/semantic_epig_audit_cases.json
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
```

Accepted descriptor:

```text
sc_expression_wry_01 -> wry grin
```

Requirements:

- Descriptor remains scoped to `mysterious` / `serious`.
- Descriptor remains gated by awkward/playful/mysterious mood keys.
- Tense/high-motion contexts are rejected before active selection.
- Non-matching serious cases do not select `wry grin`.

Acceptance:

- [x] Only one additional descriptor changed from `passive` to `active`.
- [x] A standard semantic audit fixture exercises the new descriptor.
- [x] Existing active descriptors remain covered by standard semantic audit fixtures.
- [x] Semantic audit has `policy_issue_count=0`.
- [x] Full verification passes.

Verification:

```bash
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
python -m unittest discover -s assets -p "test_*.py"
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave7.json
python tools\validate_prompt_data.py
python tools\verify_full_flow.py
python tools\check_widgets_values.py
python assets\calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## C14. Completion Scope Freeze

### C14.1 Do not adopt remaining posture descriptor in this pass

Remaining passive descriptor:

```text
sc_posture_relaxed_01 -> relaxed posture
```

Decision:

- [x] Keep `sc_posture_relaxed_01` at `mode=passive`.
- [x] Do not add an eighth active descriptor in this wave.
- [x] Record final active set as 7 descriptors.
- [x] Record that future posture adoption needs a posture-specific priority/gate.

Reason:

- `relaxed posture` overlaps with calm/relieved expression choices.
- Posture descriptors need stronger action-load gating than gaze/expression descriptors.
- The current active set is already policy-clean and full-suite verified.

---

## Completion Checklist

- [x] Planning docs created.
- [x] Reference path cleanup completed.
- [x] Relation-key descriptor test added.
- [x] Local report regeneration commands verified.
- [x] Subject-centric candidate shortlist created.
- [x] Curated data schema decision recorded.
- [x] Passive runtime integration plan approved by evidence.
- [x] Active adoption remains narrow and is backed by full audit and verification.
- [x] Wave 2 active descriptor added with mood/context extensibility filters.
- [x] Wave 3 active descriptor added with standard audit fixture coverage.
- [x] Wave 4 mood-gated active descriptor added with context rejects.
- [x] Wave 5 calm mood-gated active descriptor added while preserving audit coverage for earlier active descriptors.
- [x] Wave 6 joy/relax mood-gated active descriptor added while preserving audit coverage for earlier active descriptors.
- [x] Wave 7 awkward/mysterious mood-gated active descriptor added while preserving audit coverage for earlier active descriptors.
- [x] Remaining posture descriptor intentionally left passive; final active set frozen at 7 descriptors.
