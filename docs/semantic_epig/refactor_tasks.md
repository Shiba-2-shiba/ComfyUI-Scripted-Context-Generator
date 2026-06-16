# Semantic EPIG Refactor Tasks

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-16
関連仕様: `refactor_spec.md`
関連進捗: `refactor_progress.md`

---

## 0. Common Instructions

Use these rules for every task in this refactor wave.

- Do not change public `Context*` node inputs or outputs.
- Do not add dependencies.
- Preserve seed determinism.
- Preserve semantic-only policy.
- Add or update tests with behavior changes.
- Keep `selected_by_semantic` backward-compatible until downstream docs/tests stop relying on it.
- Run focused tests after each pass.
- Do not begin builder split before R1-R5 are complete.

Focused verification:

```bash
python -m unittest assets.test_semantic_space assets.test_semantic_epig assets.test_action_semantics assets.test_location_semantics assets.test_clothing_semantics assets.test_personality_semantics assets.test_action_generator assets.test_object_focus_service assets.test_personality_garnish
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## R0. Refactor Docs Setup

### R0.1 Add refactor documentation

Files:

```text
docs/semantic_epig/refactor_spec.md
docs/semantic_epig/refactor_progress.md
docs/semantic_epig/refactor_tasks.md
```

Acceptance:

- [x] Next-wave refactor scope is documented
- [x] Current baseline verification is recorded
- [x] Task order puts debug/audit before builder split

---

## R1. Debug Meaning Cleanup

### R1.1 Define shared debug fields

Files:

```text
pipeline/semantic_epig.py
assets/test_semantic_epig.py
```

Add helper or documented contract for:

```json
{
  "semantic_scoring_enabled": true,
  "selection_changed_by_semantic": false,
  "baseline_candidate": "",
  "semantic_candidate": "",
  "semantic_top_candidate": "",
  "selected_candidate_rank": null
}
```

Acceptance:

- [x] Existing debug payloads remain valid
- [x] New fields have documented meaning
- [x] Tests cover default values or helper output

### R1.2 Update Action debug

Files:

```text
pipeline/action_generator.py
pipeline/action_semantics.py
assets/test_action_generator.py
assets/test_action_semantics.py
```

Requirements:

- Compute baseline slot choice without semantic scores
- Compute semantic slot choice with semantic scores
- Record slot-level changes
- Keep actual selected value deterministic

Acceptance:

- [x] `semantic_scoring_enabled` distinguishes passive/active scoring from final change
- [x] `selection_changed_by_semantic` is true only when a slot choice differs
- [x] `selected_by_semantic` remains present for compatibility

### R1.3 Update Location debug

Files:

```text
pipeline/location_builder.py
pipeline/location_semantics.py
assets/test_location_semantics.py
assets/test_context_content_pipeline.py
```

Requirements:

- Record section-level baseline and semantic selected values
- Report `section_changes`

Acceptance:

- [x] active mode with no changed section is representable
- [x] changed sections are visible in debug

### R1.4 Update Clothing debug

Files:

```text
pipeline/clothing_builder.py
pipeline/clothing_semantics.py
assets/test_clothing_semantics.py
assets/test_context_content_pipeline.py
```

Requirements:

- Record repeat-only selected attempt
- Record repeat + semantic selected attempt
- Report whether semantic penalty changed selected attempt

Acceptance:

- [x] `baseline_selected_attempt_index` exists
- [x] `semantic_selected_attempt_index` exists
- [x] changed flag is based on attempt index difference

### R1.5 Update Personality debug

Files:

```text
vocab/personality_semantics.py
vocab/garnish/logic.py
assets/test_personality_semantics.py
assets/test_personality_garnish.py
```

Requirements:

- Record `fallback_used`
- Record `rejected_candidates`
- Record selected candidate rank

Acceptance:

- [x] semantic candidate reject is visible
- [x] fallback use is visible
- [x] existing personality behavior remains deterministic

---

## R2. Prompt-Level Semantic EPIG Audit

### R2.1 Add audit fixtures

Files:

```text
assets/fixtures/semantic_epig_audit_cases.json
```

Include cases:

- `study_book_library`
- `commute_station_wait`
- `rainy_bus_stop_commute`
- `shy_classroom_door`
- `office_document_review`

Acceptance:

- [x] Fixture is small enough for unit tests
- [x] Cases exercise all five domains where possible

### R2.2 Add audit tool

Files:

```text
tools/audit_semantic_epig_outputs.py
```

CLI:

```bash
python tools/audit_semantic_epig_outputs.py --samples assets/fixtures/semantic_epig_audit_cases.json --seed-start 0 --seed-count 8 --output assets/results/semantic_epig_audit.json
```

Requirements:

- Temporarily compare passive vs active config without permanently editing config file
- Run same input/seed in both modes
- Output JSON summary
- Include policy issue scan

Acceptance:

- [x] JSON output includes `passive_prompt`, `active_prompt`, `changed_domains`, `prompt_length_delta`
- [x] Policy issues are reported
- [x] Tool does not mutate repo config

### R2.3 Add audit tests

Files:

```text
assets/test_semantic_epig_audit.py
```

Acceptance:

- [x] Fixture can be loaded
- [x] Audit returns deterministic results for same seed
- [x] Output schema is tested

---

## R3. Object Relation Validator

### R3.1 Add dedicated validator

Files:

```text
asset_validator.py
assets/test_asset_validator.py
```

Function:

```python
def validate_object_relation_profiles(payload: Any | None = None) -> list[str]:
    ...
```

Acceptance:

- [x] Current `object_relation_profiles.json` returns no warnings
- [x] Unknown object returns warning
- [x] Malformed relation key returns warning
- [x] Empty verbs returns warning
- [x] Unknown role returns warning
- [x] Empty descriptor list returns warning
- [x] Banned term returns warning

### R3.2 Connect validator to `validate_assets()`

Files:

```text
asset_validator.py
```

Acceptance:

- [x] `validate_assets()` includes object relation structure validation
- [x] Duplicate warnings are de-duplicated as current behavior expects

---

## R4. Action Descriptor Candidate Supply

### R4.1 Extend descriptor schema

Files:

```text
vocab/data/action_slot_descriptors.json
assets/test_asset_validator.py
assets/test_action_semantics.py
```

Optional descriptor fields:

```json
{
  "text": "holding a tilted teapot",
  "action_keys": ["pouring"],
  "object_tokens": ["drink"],
  "relation_keys": ["drink:sipping"],
  "roles": ["hand_action"],
  "vector": {}
}
```

Acceptance:

- [x] Existing descriptors remain valid
- [x] New optional fields are validated if present
- [x] No banned terms introduced

### R4.2 Add descriptor candidate function

Files:

```text
pipeline/action_semantics.py
assets/test_action_semantics.py
```

Function:

```python
def semantic_descriptor_options_for_slot(
    slot_name: str,
    purpose: str = "",
    action_verb: str = "",
    object_flags: set[str] | None = None,
    relation_key: str = "",
) -> list[str]:
    ...
```

Acceptance:

- [x] Matching action key returns descriptors
- [ ] Matching relation key returns descriptors
- [x] Unknown slot/action returns empty list

### R4.3 Integrate descriptor options into action slot selection

Files:

```text
pipeline/action_generator.py
assets/test_action_generator.py
```

Requirements:

- Merge runtime options and semantic descriptor options
- Dedupe by normalized text
- Limit added semantic descriptors per slot
- Preserve slot overrides

Acceptance:

- [x] Representative action can select descriptor not originally in runtime options
- [x] Prompt length does not grow unexpectedly
- [x] Seed determinism remains
- [x] Object relation slots are not duplicated

---

## R5. Personality Context-Aware Top-K

### R5.1 Add ranked candidate stream

Files:

```text
vocab/personality_semantics.py
assets/test_personality_semantics.py
```

Function:

```python
def ranked_personality_candidate_stream(personality: str) -> list[dict]:
    ...
```

Acceptance:

- [x] Merges gaze/posture/hands rankings
- [x] Sorts by score descending with deterministic tie-break
- [x] Includes role/source/rank

### R5.2 Add reject callback support

Files:

```text
vocab/personality_semantics.py
vocab/garnish/logic.py
assets/test_personality_garnish.py
```

Requirements:

- `pick_personality_descriptor()` accepts `reject_fn`
- Try candidates in ranked order
- Fallback only after all semantic candidates fail

Acceptance:

- [x] Top1 rejected then top2 accepted case is tested
- [x] All rejected case falls back
- [x] Debug records rejected candidates

---

## R6. Builder Responsibility Split

Do not start R6 until R1-R5 are done and verified.

### R6.1 Split action parser

Files:

```text
pipeline/action_parser.py
pipeline/action_generator.py
assets/test_action_generator.py
```

Move:

- action text normalization
- action verb parsing
- pool action slot parsing
- contextual clause splitting

Acceptance:

- [x] `action_generator.py` re-exports or imports without breaking callers
- [x] Action parser tests pass unchanged

### R6.2 Split action relation binder

Files:

```text
pipeline/action_relation_binder.py
pipeline/action_generator.py
assets/test_action_generator.py
assets/test_object_focus_service.py
```

Move:

- object relation slot application
- relation debug assembly

Acceptance:

- [x] Object relation debug unchanged except intentional R1 fields
- [x] Existing slots are still not overwritten

### R6.3 Split action renderer

Files:

```text
pipeline/action_renderer.py
pipeline/action_generator.py
assets/test_action_generator.py
```

Move:

- `render_action_slots()`
- clause append/dedupe helpers

Acceptance:

- [x] Prompt snapshots remain expected
- [x] Public import compatibility preserved

### R6.4 Split location selector/policy

Files:

```text
pipeline/location_segment_selector.py
pipeline/location_policy.py
pipeline/location_builder.py
assets/test_location_semantics.py
assets/test_context_content_pipeline.py
```

Acceptance:

- [x] `lighting_mode=off` behavior unchanged
- [x] FX deny behavior unchanged
- [x] Scene semantic rankings unchanged

### R6.5 Split clothing candidate selector

Files:

```text
pipeline/clothing_candidate_renderer.py
pipeline/clothing_candidate_selector.py
pipeline/clothing_builder.py
assets/test_clothing_semantics.py
assets/test_context_content_pipeline.py
```

Acceptance:

- [x] Repeat penalty behavior unchanged
- [x] TPO penalty behavior unchanged
- [x] State detail hard filters unchanged

---

## R7. Final Verification And Docs

### R7.1 Run full verification

Commands:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python assets/calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Acceptance:

- [x] All commands pass, or known ignored artifact gaps are documented

### R7.2 Update docs

Files:

```text
docs/semantic_epig/refactor_progress.md
CURRENT_STATUS.md
README.md
```

Acceptance:

- [x] Completed milestones are marked
- [x] New audit tool is documented
- [x] Verification snapshot is current
- [x] Remaining risks are listed
