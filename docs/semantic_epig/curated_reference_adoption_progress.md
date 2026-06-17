# Curated Reference Adoption Progress

対象リポジトリ: `ComfyUI-Scripted-Context-Generator`  
対象ブランチ: `dev2`  
作成日: 2026-06-17 JST  
関連仕様: `curated_reference_adoption_spec.md`  
関連タスク: `curated_reference_adoption_tasks.md`

---

## 1. Current State

この wave は、reference refresh 後の次段階として、次の 1〜3 を主対象にする。

1. 低リスクな整備
   - reference docs の path cleanup
   - relation-key-specific action descriptor test
2. 採用前の候補選定
   - subject-centric candidate report の triage 方針化
   - generated/local artifact と tracked curated data の境界整理
3. 小さな runtime 採用計画
   - subject-centric personality / garnish descriptor の repo-authored 小規模採用計画
   - passive/debug-first の integration path

現在は、C7 で narrow active adoption を開始している。runtime prompt output の変更は
small curated descriptors に限定し、各 wave ごとに snapshot / audit / full verification を通す。

---

## 2. Baseline

直近確認済み:

```text
branch=dev2
working_tree=active implementation changes present
runtime_surface=Context* nodes + PromptCleaner
semantic_epig_domains=all-active
reference_refresh_decision=no_raw_reference_runtime_adoption
```

Verification snapshot from current analysis:

| Command | Result |
|---|---|
| `python -m unittest assets.test_reference_refresh_adoption assets.test_llm_expanded_prompt_policy assets.test_reference_dimension_projection assets.test_subject_centric_descriptor_audit assets.test_epig_reference_alignment assets.test_epig_reference_overlay assets.test_emotion_vad_profiles assets.test_emotion_vad_alignment assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig_audit assets.test_semantic_policy` | Pass: 50 tests OK |
| `python tools\validate_prompt_data.py` | Pass: `ERROR: []`, `WARNING: []` |
| `asset_validator.validate_assets()` | Pass: `0` issues |
| `python assets\calc_variations.py --json` | Pass: base variations `105,612`, missing pools `0` |

Current reference-root observation:

```text
reference_root=C:\Users\inott\Downloads\新しいフォルダー (4)\参考
available=EPIG, NRC-VAD-Lexicon-v2.1, 2606.13247v1.pdf
optional_missing=EmotionDynamics, lexicons.html, WorryWords, Words of Warmth
```

Notes:

- Some existing docs still mention `C:\Users\inott\Downloads\新しいフォルダー (3)\参考`.
- Current scripts support `--reference-root`, so implementation should prefer `..\参考` or `<REFERENCE_ROOT>` in docs.
- `EmotionDynamics`-related hooks should remain optional.

---

## 3. Reference metrics

Current local runs against the current `参考` folder produced these representative values:

| Audit | Metric | Value |
|---|---|---:|
| reference alignment | `source_count` | 4 |
| reference alignment | `emotion_profile_matched_count` | 15 |
| reference alignment | `exact_reference_match_count` | 3003 |
| overlay | `extracted_term_count` | 8728 |
| overlay | `matched_term_count` | 7700 |
| overlay | `unmatched_term_count` | 1028 |
| subject-centric descriptors | `descriptor_count` | 809 |
| subject-centric descriptors | `direct_count` | 7 |
| subject-centric descriptors | `needs_phrase_count` | 80 |
| subject-centric descriptors | `reject_count` | 595 |
| subject-centric descriptors | `unmatched_count` | 127 |
| LLM expanded policy audit | `row_count` | 44 |
| LLM expanded policy audit | `policy_issue_count` | 83 |
| dimension projection | `projection_comparison_count` | 99 |
| dimension projection | `high_risk_count` | 15 |
| dimension projection | `runtime_axis_adoption` | deferred |

Interpretation:

- The reference data is useful as audit/calibration signal.
- `needs_phrase=80` is the main candidate pool for human/repo-authored rewrite.
- Dominance remains audit-only.
- LLM expanded prompts remain negative corpus only.
- Optional reference gaps should not block low-risk stabilization or curated candidate planning.

---

## 4. Milestone Status

| Milestone | Title | Status | Notes |
|---|---|---|---|
| C0 | Planning docs setup | Done | This spec/progress/tasks set created |
| C1 | Reference path cleanup | Done | Old `(3)\参考` command examples replaced with `<REFERENCE_ROOT>` / `..\参考` guidance |
| C2 | Relation key descriptor test | Done | Focused relation-key matcher coverage added without runtime output changes |
| C3 | Candidate report regeneration docs | Done | Local reports regenerated under ignored `assets/results/` |
| C4 | Subject-centric triage | Done | `curated_reference_candidate_shortlist.md` added |
| C5 | Curated data schema | Done | New curated file boundary selected for future passive integration |
| C6 | Passive runtime integration | Done | Curated data, validator, and passive debug loader added without output adoption |
| C7 | Narrow active adoption gate | Done | `sc_gaze_downcast_01` active |
| C8 | Active adoption wave 2 | Done | `sc_expression_reassuring_01` active with mood/context extensibility gates |
| C9 | Active adoption wave 3 | Done | `sc_gaze_curious_01` active with audit fixture coverage; audit patch no longer leaks forced modes |
| C10 | Active adoption wave 4 | Done | `sc_hands_touching_lips_01` active behind `moved` mood gate and context rejects |
| C11 | Active adoption wave 5 | Done | `sc_expression_calm_01` active behind calm mood gate; all active descriptors remain audit-covered |
| C12 | Active adoption wave 6 | Done | `sc_expression_contented_01` active behind joy/relax mood gate; all active descriptors remain audit-covered |
| C13 | Active adoption wave 7 | Done | `sc_expression_wry_01` active behind awkward/mysterious mood gate; all active descriptors remain audit-covered |
| C14 | Completion scope freeze | Done | Remaining `sc_posture_relaxed_01` is not adopted in this wave; final active set is 7 descriptors |

Status vocabulary:

- `Not started`
- `In progress`
- `Blocked`
- `Deferred`
- `Done`

---

## 5. Decision Log

| Date | Decision | Reason | Impact |
|---|---|---|---|
| 2026-06-17 | Start with docs/test-only stabilization | It removes uncertainty without prompt output drift | C1/C2 before runtime planning |
| 2026-06-17 | Use `<REFERENCE_ROOT>` / `..\参考` in docs | Absolute `(3)` path is stale and environment-specific | Better reproducibility |
| 2026-06-17 | Keep generated overlays local | They can contain reference-derived scores | Avoid redistribution risk |
| 2026-06-17 | Treat `needs_phrase` as rewrite hints | Direct adoption risks weak or copied descriptors | Candidate triage required |
| 2026-06-17 | First runtime target is subject-centric personality/garnish | Narrowest useful adoption lane | Lower risk than emotion/action/dominance changes |
| 2026-06-17 | Active behavior remains deferred | Need passive debug and prompt audit first | No prompt snapshot churn in planning/docs phase |
| 2026-06-17 | Use a new curated descriptor file for future passive work | Keeps provenance / mode / validation separate from broad personality profiles | Candidate file remains planned, not implemented in this pass |
| 2026-06-17 | Keep curated descriptors passive/debug-only | Initial curated data is useful as availability signal but not yet prompt selection input | No prompt output adoption in C6 |
| 2026-06-17 | Add an explicit subject-centric override gate under `personality_behavior` | Active use must require both config mode and descriptor mode to be active | The gate now allows one narrow active descriptor while keeping the rest passive |
| 2026-06-17 | Activate only `sc_gaze_downcast_01` first | It is narrow, subject-centric, and covered by audit with no policy issues | Shy/gloomy can select `downcast eyes`; all other curated descriptors stay passive |
| 2026-06-17 | Add mood/context filters before the second active descriptor | Future descriptors need safe optional narrowing before active expansion | `mood_keys` and `reject_context_terms` are now runtime-respected and test-covered |
| 2026-06-17 | Activate `sc_expression_reassuring_01` as wave 2 | Audit showed policy issue count 0 and selection is limited to gentle/faithful personality matches | Gentle/faithful can select `small reassuring smile`; prompt snapshots updated intentionally |
| 2026-06-17 | Activate `sc_gaze_curious_01` as wave 3 | It is low-risk subject gaze wording and is isolated to mysterious/cheerful personalities | Mysterious/cheerful can select `curious eyes`; default prompt snapshots did not change |
| 2026-06-17 | Fix audit-mode patch import order | Importing modules after patching `pipeline.semantic_epig` could leave `vocab.garnish.logic` restored to a forced mode in same-process tests | Audit context manager now imports modules before patching and clears garnish facade cache after use |
| 2026-06-17 | Activate `sc_hands_touching_lips_01` as wave 4 | It exercises the real `mood_keys` gate and remains scoped to `shy` + `moved` | Shy/moved cases can select `fingers resting near her lips`; non-moved shy keeps `downcast eyes` |
| 2026-06-17 | Prefer mood-specific active overrides when mood matches | Otherwise broad shy gaze overrides can starve narrower mood-gated descriptors | Selection now prioritizes matched mood-specific candidates before generic candidates |
| 2026-06-17 | Activate `sc_expression_calm_01` as wave 5 | It is low-arousal semantic expression wording and can be safely constrained to calm/relieved moods | Neutral/gentle calm cases can select `calm expression`; tense neutral remains ungated/fallback |
| 2026-06-17 | Preserve audit coverage for all active descriptors | Wave 5 calm priority superseded the previous gentle/calm `small reassuring smile` fixture | Added `faithful_library_note` so `sc_expression_reassuring_01` remains covered by standard audit |
| 2026-06-17 | Activate `sc_expression_contented_01` as wave 6 | It is concise subject expression wording and can be safely constrained to joy/relieved moods | Cheerful/gentle joy-relax cases can select `contented mouth`; non-matching cheerful still uses `curious eyes` |
| 2026-06-17 | Activate `sc_expression_wry_01` as wave 7 | It is restrained subject expression wording and can be safely constrained to awkward/playful/mysterious moods | Serious/mysterious awkward-like cases can select `wry grin`; non-matching serious remains ungated/fallback |
| 2026-06-17 | Do not adopt `sc_posture_relaxed_01` in this wave | It overlaps with active calm expression and needs a clearer posture-specific gate before active use | Keep it passive/debug-only for future posture lane work |
| 2026-06-17 | Freeze final active set at 7 descriptors for this adoption pass | The current set is policy-clean, audit-covered, and verified by full test suite | Completion cleanup can proceed without broadening prompt behavior further |

---

## 6. Implementation Notes

### 6.1 Path cleanup target

Known stale path examples occur in:

```text
docs/semantic_epig/reference_refresh_spec.md
docs/semantic_epig/reference_refresh_progress.md
docs/semantic_epig/reference_refresh_tasks.md
docs/semantic_epig/reference_refresh_handoff.md
```

Expected replacement pattern:

```text
<REFERENCE_ROOT>
..\参考
```

Do not remove the explanation that `参考/` is repo-external and untracked.

### 6.2 Relation-key test target

Known open follow-up:

```text
R4 relation-key-specific descriptor fixture/test remains open
```

Likely files:

```text
pipeline/action_semantics.py
assets/test_action_semantics.py
```

Expected test shape:

- Build a tiny descriptor payload or monkeypatch loader.
- Call `semantic_descriptor_options_for_slot(slot_name, relation_key="drink:sipping")`.
- Assert relation-specific descriptor appears.
- Assert unrelated relation does not match.
- Assert no runtime prompt generation is changed.

### 6.3 Candidate triage target

Generated input:

```text
assets/results/subject_centric_descriptor_candidates.json
```

This file remains ignored/local. Curated adoption, if any, must be a new repo-authored data file or a small edit to existing repo-owned descriptor data.

Initial triage fields to record:

```text
candidate_text
classification
target_slot
proposed_repo_phrase
source_hint
rewrite_reason
risk_note
decision
```

### 6.4 Runtime adoption planning target

Likely future files:

```text
vocab/data/subject_centric_descriptor_overrides.json
vocab/personality_semantics.py
vocab/garnish/logic.py
asset_validator.py
assets/test_personality_semantics.py
assets/test_personality_garnish.py
assets/test_asset_validator.py
```

Initial integration mode:

```text
passive/debug-only
```

Active adoption remains future work.

---

## 7. Implementation Log

### 7.1 C1 Reference path cleanup

Updated:

```text
docs/semantic_epig/reference_refresh_spec.md
docs/semantic_epig/reference_refresh_progress.md
docs/semantic_epig/reference_refresh_tasks.md
docs/semantic_epig/reference_refresh_handoff.md
```

Changes:

- Replaced stale `(3)\参考` absolute command examples with `..\参考`.
- Replaced hardcoded "do not commit from `(3)\参考`" wording with `<REFERENCE_ROOT>` / repo-external `参考` wording.
- Kept the rule that reference material is local and untracked.

### 7.2 C2 Relation-key descriptor test

Updated:

```text
assets/test_action_semantics.py
```

Changes:

- Added focused coverage for `semantic_descriptor_options_for_slot(..., relation_key="drink:sipping")`.
- Test uses an in-test descriptor lookup, so no runtime data or external reference data changed.

Verification:

```text
python -m unittest assets.test_action_semantics assets.test_action_generator
```

Result:

```text
27 tests OK
```

### 7.3 C3 Local report regeneration

Generated local ignored reports:

```text
assets/results/epig_reference_alignment.json
assets/results/epig_reference_overlay.local.json
assets/results/subject_centric_descriptor_candidates.json
assets/results/reference_dimension_projection.json
assets/results/llm_expanded_prompt_policy_audit.json
assets/results/semantic_epig_audit_reference_refresh_baseline.json
assets/results/reference_refresh_adoption_decision.json
```

Summary:

```text
reference_alignment.source_count=4
reference_alignment.warning_count=1
overlay.extracted_term_count=8728
overlay.matched_term_count=7700
overlay.unmatched_term_count=1028
subject_descriptor.descriptor_count=809
subject_descriptor.direct_count=7
subject_descriptor.needs_phrase_count=80
subject_descriptor.reject_count=595
subject_descriptor.unmatched_count=127
subject_descriptor.warning_count=0
llm_policy.policy_issue_count=83
semantic_baseline.record_count=40
semantic_baseline.policy_issue_count=0
adoption_decision.overall_decision=no_runtime_adoption_now
adoption_decision.missing_count=0
```

Notes:

- `warning_count=1` is expected in the current reference folder because optional EmotionDynamics data is absent.
- Generated report files remain ignored and should not be committed.

### 7.4 C4 Subject-centric shortlist

Added:

```text
docs/semantic_epig/curated_reference_candidate_shortlist.md
```

Shortlist result:

- Future passive/debug candidates: 8.
- Direct reference matches kept as validation signal only.
- High-intensity / action-specific / body-risk candidates rejected for this wave.

### 7.5 C5 Curated data schema decision

Decision:

```text
Use a new future file: vocab/data/subject_centric_descriptor_overrides.json
```

Reason:

- Keeps repo-authored subject-centric overrides separate from broad `personality_behavior_profiles.json`.
- Makes passive/active mode, provenance hints, and validator checks explicit.
- Avoids mixing local audit provenance into existing runtime data before passive evidence exists.

Rejected:

```text
Fold directly into vocab/data/personality_behavior_profiles.json
```

Reason:

- Too easy to blur existing authored personality profiles with reference-audit-derived rewrite candidates.
- Harder to keep passive/debug-only behavior isolated.

### 7.6 C6 Passive runtime integration

Added:

```text
vocab/data/subject_centric_descriptor_overrides.json
```

Updated:

```text
asset_validator.py
vocab/personality_semantics.py
assets/test_asset_validator.py
assets/test_personality_semantics.py
assets/test_personality_garnish.py
```

Behavior:

- Curated subject-centric descriptors are loaded from a repo-authored data file.
- Initial C6 descriptors used `mode=passive`.
- `personality_behavior` debug now includes `subject_centric_overrides`.
- Existing personality selection does not consume these candidates for prompt output.
- Active adoption was deferred until the C7 gate pass below.

Validator coverage:

- schema_version
- descriptor id / duplicate id
- allowed slot
- non-empty text
- source_hint / rewrite_reason / risk_note
- mode
- optional list fields
- forbidden score-bearing fields
- semantic-only banned term scan

Verification:

```text
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish
```

Result:

```text
36 tests OK
```

Expanded verification:

```text
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig_audit assets.test_prompt_snapshots
python -m py_compile asset_validator.py vocab\personality_semantics.py
python tools\validate_prompt_data.py
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_passive.json
```

Result:

```text
41 tests OK
py_compile OK
validate_prompt_data.py -> ERROR: [], WARNING: []
semantic audit -> record_count=40, changed_count=40, policy_issue_count=0
```

Asset validator:

```text
asset_validator.validate_assets() -> 0 issues
```

### 7.7 C7 gate infrastructure

Updated:

```text
vocab/data/semantic_epig_config.json
vocab/personality_semantics.py
asset_validator.py
assets/test_asset_validator.py
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
```

Config gate:

```json
{
  "domains": {
    "personality_behavior": {
      "mode": "active",
      "subject_centric_overrides": {
        "mode": "passive",
        "max_candidates_per_slot": 1
      }
    }
  }
}
```

Behavior:

- Subject-centric override adoption now has a nested config gate.
- Current gate mode is `active`, but only descriptors with `mode=active` can be selected.
- Active selection code is test-covered with an in-test active fixture.
- Real curated data has one active descriptor: `sc_gaze_downcast_01`.
- Other curated descriptors remain `mode=passive`.

Verification:

```text
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
python -m py_compile asset_validator.py vocab\personality_semantics.py
python tools\validate_prompt_data.py
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_gated.json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Result:

```text
48 tests OK
py_compile OK
validate_prompt_data.py -> ERROR: [], WARNING: []
semantic audit -> record_count=40, changed_count=40, policy_issue_count=0
asset_validator.validate_assets() -> 0 issues
```

### 7.8 C7 narrow active adoption

Activated:

```text
vocab/data/semantic_epig_config.json
  domains.personality_behavior.subject_centric_overrides.mode = active

vocab/data/subject_centric_descriptor_overrides.json
  sc_gaze_downcast_01.mode = active
```

Effect:

- `shy` / `gloomy` can use `downcast eyes` through the subject-centric override gate.
- Semantic audit selected the override in 8 records, all from `shy_classroom_door`.
- Policy issue count remained 0.
- Other curated descriptors remain passive/debug-only.

Verification:

```text
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
python -m unittest discover -s assets -p "test_*.py"
python tools\verify_full_flow.py
python tools\check_widgets_values.py
python tools\validate_prompt_data.py
python assets\calc_variations.py --json
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active.json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Result:

```text
focused tests -> 49 tests OK
full asset unittest discovery -> 359 tests OK
verify_full_flow.py -> OK
check_widgets_values.py -> OK
validate_prompt_data.py -> ERROR: [], WARNING: []
calc_variations.py -> base_variations=105612, missing_pools=0
semantic audit -> record_count=40, changed_count=40, policy_issue_count=0, override_selected_count=8
asset_validator.validate_assets() -> 0 issues
```

### 7.9 C8 active adoption wave 2 and extensibility gates

Updated:

```text
vocab/data/subject_centric_descriptor_overrides.json
vocab/personality_semantics.py
vocab/garnish/logic.py
assets/test_personality_semantics.py
assets/fixtures/prompt_snapshot_cases.json
```

Implementation:

- Added optional `mood_key` filtering for subject-centric overrides.
- Added optional `reject_context_terms` filtering before a descriptor can be selected.
- Passed the current garnish mood/action/context into subject-centric override selection.
- Kept `max_candidates_per_slot=1` and descriptor-level `mode=active` as the hard active gate.
- Activated one additional descriptor: `sc_expression_reassuring_01` -> `small reassuring smile`.

Audit result:

```text
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave2.json
-> record_count=40, changed_count=40, policy_issue_count=0
override selections:
  shy_classroom_door / sc_gaze_downcast_01 / downcast eyes = 8
  rainy_bus_stop_commute / sc_expression_reassuring_01 / small reassuring smile = 8
prompt_length_delta: min=-67, max=72, avg=8.05
```

Verification:

```text
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
-> 52 tests OK

python -m unittest discover -s assets -p "test_*.py"
-> 362 tests OK

python tools\validate_prompt_data.py
-> ERROR: [], WARNING: []

python tools\verify_full_flow.py
-> OK

python tools\check_widgets_values.py
-> OK

python assets\calc_variations.py --json
-> base_variations=105612, missing_pools=0

asset_validator.validate_assets()
-> 0 issues
```

### 7.10 C9 active adoption wave 3 and audit isolation fix

Updated:

```text
vocab/data/subject_centric_descriptor_overrides.json
assets/fixtures/semantic_epig_audit_cases.json
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
tools/audit_semantic_epig_outputs.py
```

Implementation:

- Activated one additional descriptor: `sc_gaze_curious_01` -> `curious eyes`.
- Added `mysterious_bookstore_corner` to the semantic audit fixture so this active descriptor is exercised by the standard audit.
- Added unit coverage that `mysterious` active override options expose only `curious eyes`.
- Added audit coverage that the new fixture selects `sc_gaze_curious_01` and remains policy-clean.
- Fixed `semantic_epig_mode()` in the audit tool so modules are imported before forced-mode patching; this prevents same-process tests from restoring `vocab.garnish.logic.semantic_mode` to a forced passive/active function.
- The audit tool also clears the cached garnish facade after forced-mode runs.

Audit result:

```text
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave3.json
-> case_count=6, record_count=48, changed_count=48, policy_issue_count=0
override selections:
  shy_classroom_door / sc_gaze_downcast_01 / downcast eyes = 8
  rainy_bus_stop_commute / sc_expression_reassuring_01 / small reassuring smile = 8
  mysterious_bookstore_corner / sc_gaze_curious_01 / curious eyes = 8
prompt_length_delta: min=-67, max=72, avg=5.90
```

Verification:

```text
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
-> 53 tests OK

python -m unittest discover -s assets -p "test_*.py"
-> 363 tests OK

python tools\validate_prompt_data.py
-> ERROR: [], WARNING: []

python tools\verify_full_flow.py
-> OK

python tools\check_widgets_values.py
-> OK

python assets\calc_variations.py --json
-> base_variations=105612, missing_pools=0

asset_validator.validate_assets()
-> 0 issues
```

### 7.11 C10 active adoption wave 4 and mood-specific priority

Updated:

```text
vocab/data/subject_centric_descriptor_overrides.json
vocab/personality_semantics.py
assets/fixtures/semantic_epig_audit_cases.json
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
```

Implementation:

- Activated one additional descriptor: `sc_hands_touching_lips_01` -> `fingers resting near her lips`.
- Kept this descriptor scoped by `personality=["shy"]` and `mood_keys=["moved"]`.
- Added `reject_context_terms` for intimate/high-motion/high-tension contexts (`kissing`, `cuddling`, `bed`, `bath`, `soaking`, `fighting`, `running`, `sprinting`).
- Updated active selection so mood-specific candidates take priority over generic candidates when the current mood matches.
- Added `shy_moved_station_reunion` to the semantic audit fixture so the real mood-gated descriptor is exercised.
- Added tests proving `moved` selects `sc_hands_touching_lips_01` while non-moved shy still selects `sc_gaze_downcast_01`.

Audit result:

```text
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave4.json
-> case_count=7, record_count=56, changed_count=56, policy_issue_count=0
override selections:
  shy_classroom_door / sc_gaze_downcast_01 / downcast eyes = 8
  rainy_bus_stop_commute / sc_expression_reassuring_01 / small reassuring smile = 8
  mysterious_bookstore_corner / sc_gaze_curious_01 / curious eyes = 8
  shy_moved_station_reunion / sc_hands_touching_lips_01 / fingers resting near her lips = 8
prompt_length_delta: min=-67, max=72, avg=5.14
```

Verification:

```text
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
-> 55 tests OK

python -m unittest discover -s assets -p "test_*.py"
-> 365 tests OK

python tools\validate_prompt_data.py
-> ERROR: [], WARNING: []

python tools\verify_full_flow.py
-> OK

python tools\check_widgets_values.py
-> OK

python assets\calc_variations.py --json
-> base_variations=105612, missing_pools=0

asset_validator.validate_assets()
-> 0 issues
```

### 7.12 C11 active adoption wave 5 and calm mood gate

Updated:

```text
vocab/data/subject_centric_descriptor_overrides.json
assets/fixtures/semantic_epig_audit_cases.json
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
```

Implementation:

- Activated one additional descriptor: `sc_expression_calm_01` -> `calm expression`.
- Scoped the descriptor to `personality=["neutral", "gentle"]` and `mood_keys=["calm", "peaceful_relaxed", "relieved"]`.
- Added reject terms for high-tension/high-motion contexts (`fighting`, `arguing`, `battle`, `danger`, `running`, `sprinting`, `jumping`, `dancing`).
- Added `neutral_calm_balcony_pause` to exercise the calm mood-gated descriptor.
- Added `faithful_library_note` to keep `sc_expression_reassuring_01` covered after calm-specific priority took over the previous gentle/calm audit case.
- Added tests proving neutral/calm selects `sc_expression_calm_01` while neutral/tense does not.

Audit result:

```text
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave5.json
-> case_count=9, record_count=72, changed_count=72, policy_issue_count=0
override selections:
  faithful_library_note / sc_expression_reassuring_01 / small reassuring smile = 8
  mysterious_bookstore_corner / sc_gaze_curious_01 / curious eyes = 8
  neutral_calm_balcony_pause / sc_expression_calm_01 / calm expression = 8
  rainy_bus_stop_commute / sc_expression_calm_01 / calm expression = 8
  shy_classroom_door / sc_gaze_downcast_01 / downcast eyes = 8
  shy_moved_station_reunion / sc_hands_touching_lips_01 / fingers resting near her lips = 8
prompt_length_delta: min=-67, max=69, avg=6.17
```

Verification:

```text
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
-> 58 tests OK

python -m unittest discover -s assets -p "test_*.py"
-> 368 tests OK

python tools\validate_prompt_data.py
-> ERROR: [], WARNING: []

python tools\verify_full_flow.py
-> OK

python tools\check_widgets_values.py
-> OK

python assets\calc_variations.py --json
-> base_variations=105612, missing_pools=0

asset_validator.validate_assets()
-> 0 issues
```

### 7.13 C12 active adoption wave 6 and joy/relax mood gate

Updated:

```text
vocab/data/subject_centric_descriptor_overrides.json
assets/fixtures/semantic_epig_audit_cases.json
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
```

Implementation:

- Activated one additional descriptor: `sc_expression_contented_01` -> `contented mouth`.
- Scoped the descriptor to `personality=["gentle", "cheerful"]` and `mood_keys=["joy", "peaceful_relaxed", "relieved"]`.
- Added reject terms for high-tension/high-motion or incompatible contexts (`fighting`, `arguing`, `battle`, `danger`, `crying`, `rage`, `running`, `sprinting`).
- Added `cheerful_joy_market_chat` to exercise the joy mood-gated descriptor.
- Added tests proving cheerful/joy selects `sc_expression_contented_01` while cheerful/focus still selects `sc_gaze_curious_01`.

Audit result:

```text
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave6.json
-> case_count=10, record_count=80, changed_count=80, policy_issue_count=0
override selections:
  cheerful_joy_market_chat / sc_expression_contented_01 / contented mouth = 8
  faithful_library_note / sc_expression_reassuring_01 / small reassuring smile = 8
  mysterious_bookstore_corner / sc_gaze_curious_01 / curious eyes = 8
  neutral_calm_balcony_pause / sc_expression_calm_01 / calm expression = 8
  rainy_bus_stop_commute / sc_expression_calm_01 / calm expression = 8
  shy_classroom_door / sc_gaze_downcast_01 / downcast eyes = 8
  shy_moved_station_reunion / sc_hands_touching_lips_01 / fingers resting near her lips = 8
prompt_length_delta: min=-67, max=69, avg=5.31
```

Verification:

```text
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
-> 60 tests OK

python -m unittest discover -s assets -p "test_*.py"
-> 370 tests OK

python tools\validate_prompt_data.py
-> ERROR: [], WARNING: []

python tools\verify_full_flow.py
-> OK

python tools\check_widgets_values.py
-> OK

python assets\calc_variations.py --json
-> base_variations=105612, missing_pools=0

asset_validator.validate_assets()
-> 0 issues
```

### 7.14 C13 active adoption wave 7 and awkward/mysterious mood gate

Updated:

```text
vocab/data/subject_centric_descriptor_overrides.json
assets/fixtures/semantic_epig_audit_cases.json
assets/test_personality_semantics.py
assets/test_semantic_epig_audit.py
```

Implementation:

- Activated one additional descriptor: `sc_expression_wry_01` -> `wry grin`.
- Scoped the descriptor to `personality=["mysterious", "serious"]` and `mood_keys=["awkward", "mysterious_curious", "playful"]`.
- Added reject terms for high-tension/high-motion or incompatible contexts (`crying`, `fighting`, `arguing`, `battle`, `danger`, `rage`, `running`, `sprinting`).
- Added `serious_awkward_office_paperwork` to exercise the awkward mood-gated descriptor.
- Added tests proving serious/awkward selects `sc_expression_wry_01` while serious/focus does not.

Audit result:

```text
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-count 8 --output assets\results\semantic_epig_audit_subject_centric_active_wave7.json
-> case_count=11, record_count=88, changed_count=88, policy_issue_count=0
override selections:
  cheerful_joy_market_chat / sc_expression_contented_01 / contented mouth = 8
  faithful_library_note / sc_expression_reassuring_01 / small reassuring smile = 8
  mysterious_bookstore_corner / sc_gaze_curious_01 / curious eyes = 8
  neutral_calm_balcony_pause / sc_expression_calm_01 / calm expression = 8
  rainy_bus_stop_commute / sc_expression_calm_01 / calm expression = 8
  serious_awkward_office_paperwork / sc_expression_wry_01 / wry grin = 8
  shy_classroom_door / sc_gaze_downcast_01 / downcast eyes = 8
  shy_moved_station_reunion / sc_hands_touching_lips_01 / fingers resting near her lips = 8
prompt_length_delta: min=-67, max=69, avg=3.06
```

Verification:

```text
python -m unittest assets.test_asset_validator assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig assets.test_semantic_epig_audit assets.test_prompt_snapshots
-> 62 tests OK

python -m unittest discover -s assets -p "test_*.py"
-> 372 tests OK

python tools\validate_prompt_data.py
-> ERROR: [], WARNING: []

python tools\verify_full_flow.py
-> OK

python tools\check_widgets_values.py
-> OK

python assets\calc_variations.py --json
-> base_variations=105612, missing_pools=0

asset_validator.validate_assets()
-> 0 issues
```

### 7.15 C14 completion scope freeze

Final decision for this adoption pass:

```text
Do not activate sc_posture_relaxed_01 in this wave.
```

Reason:

- `relaxed posture` overlaps with the newly active calm/relieved expression lane.
- Posture descriptors can conflict with action load more easily than facial/gaze descriptors.
- Although `reject_context_terms` are already present, a future posture-specific gate should define when posture can outrank expression/gaze before active use.

Final active descriptor set:

| id | text | gate summary |
|---|---|---|
| `sc_gaze_downcast_01` | `downcast eyes` | `shy` / `gloomy` |
| `sc_gaze_curious_01` | `curious eyes` | `mysterious` / `cheerful` |
| `sc_expression_reassuring_01` | `small reassuring smile` | `gentle` / `faithful` |
| `sc_hands_touching_lips_01` | `fingers resting near her lips` | `shy` + `moved`, with context rejects |
| `sc_expression_calm_01` | `calm expression` | `neutral` / `gentle` + calm/relieved moods, with context rejects |
| `sc_expression_contented_01` | `contented mouth` | `gentle` / `cheerful` + joy/relieved moods, with context rejects |
| `sc_expression_wry_01` | `wry grin` | `mysterious` / `serious` + awkward/playful/mysterious moods, with context rejects |

Remaining passive descriptor:

| id | text | reason not adopted now |
|---|---|---|
| `sc_posture_relaxed_01` | `relaxed posture` | Needs a posture-specific priority/gate to avoid low-pressure posture overriding richer expression/gaze choices |

No additional verification was required for this docs-only scope freeze beyond the wave 7 verification already recorded above.

---

## 8. Risks

| Risk | Level | Mitigation |
|---|---:|---|
| Docs path cleanup accidentally removes useful local examples | Low | Replace with `<REFERENCE_ROOT>` and keep one labeled local example if needed |
| Relation-key test requires data mutation | Low/Medium | Prefer tiny in-test payload / monkeypatch before data changes |
| Candidate triage slips into direct copying | Medium | Require `rewrite_reason` and repo-authored phrase |
| Score-bearing overlay gets tracked | Medium | Keep `assets/results/` ignored and docs explicit |
| Subject-centric descriptors introduce camera/view/body language ambiguity | Medium | Validator + semantic-only policy scan + review |
| Passive integration unexpectedly changes output | High | Test passive output unchanged before active |
| Active adoption causes snapshot churn | Medium | Final active set frozen at 7 descriptors; update snapshots only for a future explicitly audited wave |
| Optional reference source missing causes false blocker | Low | Treat as warning unless the task explicitly targets that source |

---

## 9. Next Actions

Immediate next actions:

1. Treat the current 7-descriptor active set as complete for this adoption pass.
2. Keep `sc_posture_relaxed_01` passive until a future posture-specific gate is planned.
3. If a future adoption pass resumes, add at most one descriptor per pass and repeat audit/full verification.
4. Continue keeping generated `assets/results/*` artifacts ignored/untracked.

Do not broaden active prompt changes further in this wave.
