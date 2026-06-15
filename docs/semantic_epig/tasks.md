# EPIG的 Semantic Enrichment 実装タスク

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev`
関連仕様: `implementation_spec.md`
関連進捗: `progress.md`

---

## 0. Codex 用共通指示

Codex セッション開始時に貼る共通指示:

```text
You are working on Shiba-2-shiba/ComfyUI-Scripted-Context-Generator on the dev branch.
Implement the EPIG-like semantic enrichment plan in small, testable steps.
Follow these constraints:
- Do not change public Context* node inputs/outputs unless explicitly requested.
- Keep context_json compatibility.
- Preserve seed determinism.
- Preserve semantic-only policy: no camera, quality, render effects, or body-type descriptors.
- Start each domain in passive mode: compute rankings and DebugInfo but do not change prompt output.
- Add or update tests in the same change as runtime/data changes.
- Update asset_validator.py when adding new vocab/data JSON files.
- Run the relevant unittest and validation commands before finishing.
```

---

## 1. M0: Baseline と作業準備

### Task M0.1: ブランチ作成

```bash
git checkout dev
git pull
git checkout -b feature/semantic-epig-extension
```

Acceptance:

- [ ] dev 最新から作業ブランチを作成した
- [ ] 作業前の差分が空である

### Task M0.2: baseline verification

Run:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print('issues', len(issues)); print(issues[:20])"
```

Acceptance:

- [ ] 結果を `progress.md` に記録した
- [ ] 既存 failure がある場合は今回作業由来かどうかを分離した

### Task M0.3: docs 配置

推奨配置:

```text
docs/semantic_epig/implementation_spec.md
docs/semantic_epig/progress.md
docs/semantic_epig/tasks.md
```

Acceptance:

- [ ] この 3 文書を repo 内 docs にコピーした
- [ ] README からはまだリンクしなくてよい

---

## 2. M1: 共通 semantic space 基盤

### Task M1.1: `vocab/semantic_space.py` を追加

実装:

- [x] `clamp01()`
- [x] `normalize_vector()`
- [x] `weighted_distance()`
- [x] `relevance_from_distance()`
- [x] `rank_candidates()`
- [x] `top_window()`
- [x] `validate_axis_payload()`

Codex prompt:

```text
Add vocab/semantic_space.py with generic axis-vector ranking utilities. Keep it dependency-light and deterministic. Add unit tests in assets/test_semantic_space.py. Do not touch runtime prompt generation yet.
```

Acceptance:

- [x] 同じ target/candidates で ranking が deterministic
- [x] score は distance 昇順と整合する
- [x] vector 欠損は 0.5 補完または validator warning
- [x] `python -m unittest assets.test_semantic_space` passes

### Task M1.2: `pipeline/semantic_epig.py` と config を追加

追加:

```text
pipeline/semantic_epig.py
vocab/data/semantic_epig_config.json
```

Config 初期値:

```json
{
  "schema_version": "1.0",
  "default_mode": "passive",
  "gamma": 2.0,
  "top_k": 3,
  "top_window": 3,
  "domains": {
    "action": {"mode": "passive"},
    "object_relation": {"mode": "passive"},
    "location_scene": {"mode": "passive"},
    "clothing_tpo": {"mode": "passive"},
    "personality_behavior": {"mode": "passive"}
  }
}
```

Acceptance:

- [x] config missing 時も safe fallback する
- [x] unknown domain は `off` or `passive` として安全に扱う
- [x] DebugInfo に `semantic_epig` payload を merge する helper がある

### Task M1.3: asset validator 拡張

変更:

```text
asset_validator.py
```

追加チェック:

- [x] 新規 semantic JSON の banned term scan
- [x] `schema_version` / `axes` / vector range validation
- [x] camera / quality / body-type domain 語彙を検出

Acceptance:

- [x] `validate_assets()` が新規 config を読む
- [x] invalid vector value の test がある
- [x] `python -m unittest assets.test_asset_validator` passes
- [x] `python -c "from asset_validator import validate_assets; print(validate_assets())"` returns `[]`

---

## 3. M2: Action EPIG

### Task M2.1: action semantic data を追加

追加:

```text
vocab/data/action_semantic_profiles.json
vocab/data/action_slot_descriptors.json
```

初期 coverage:

- [x] `study`
- [x] `work`
- [x] `commute`
- [x] `rest`
- [x] `shop`
- [x] `wait`

Slot coverage:

- [x] `posture`
- [x] `hand_action`
- [x] `gaze_target`
- [x] `purpose_clause`
- [x] `optional_micro_action`

Acceptance:

- [x] 既存 `POSTURE_BY_PURPOSE` 等の文言を一部 mirror し、出力語彙が急に変わらない
- [x] banned term scan に通る

### Task M2.2: `pipeline/action_semantics.py` を追加

実装:

- [x] `load_action_semantic_profiles()`
- [x] `build_action_target_vector()`
- [x] `rank_action_slot_options()`
- [x] `semantic_slot_weights()`
- [x] `semantic_action_debug_payload()`

Codex prompt:

```text
Implement pipeline/action_semantics.py. It should rank action slot candidates by semantic axis vectors but not change action_generator behavior yet. Include tests for study vs commute ranking.
```

Acceptance:

- [x] `study` target で precision/object_coupling 系が上位
- [x] `commute` target で time_pressure/motion_energy 系が上位
- [x] data missing 時は空 ranking で落ちない

### Task M2.3: passive mode を `action_generator.py` に接続

変更:

```text
pipeline/action_generator.py
```

やること:

- [x] `build_action_slots()` 内で target vector を作る
- [x] 各 `choose_slot()` の候補 ranking を DebugInfo 用に計算
- [x] `passive` mode では既存選択を維持
- [x] decision に `semantic_epig.action` を追加

Acceptance:

- [x] 既存 prompt output が変わらない
- [x] `ContextSceneVariator` history に semantic debug が入る
- [x] `python -m unittest assets.test_action_semantics assets.test_context_pipeline` passes

### Task M2.4: active mode を有効化

やること:

- [x] `semantic_epig_config.json` で `action.mode = active`
- [x] `_weighted_slot_choice()` の weight に semantic score を掛ける
- [x] top_window 内から既存 rng で選ぶ
- [x] output change の snapshot を確認

Acceptance:

- [x] 同じ seed で deterministic
- [x] `study` / `commute` の before/after を progress に記録
- [x] `python -m unittest discover -s assets -p "test_*.py"` passes or expected snapshot update is committed

---

## 4. M3: Object Relation EPIG

### Task M3.1: object relation data を追加

追加:

```text
vocab/data/object_relation_profiles.json
```

初期 relation:

- [x] `book:reading`
- [x] `phone:checking`
- [x] `coffee:sipping_or_holding`
- [x] `drink:sipping`
- [x] `screen:typing_or_reviewing`
- [x] `microphone:singing_or_speaking`
- [x] `surfboard:carrying_or_balancing`

Acceptance:

- [x] 各 relation に `required_roles` がある
- [x] descriptor が role-bound である
- [x] forbidden pattern は出力用ではなく validation / documentation 用に保持

### Task M3.2: `object_focus_service.py` を拡張

実装:

- [x] `load_object_relation_profiles()`
- [x] `infer_object_relation_key()`
- [x] `relation_slots_for_action()`
- [x] `summarize_object_relation_focus()`

Codex prompt:

```text
Extend object_focus_service.py with object relation profile loading and relation inference. Keep existing object concentration APIs backward compatible. Add tests for book/reading and phone/checking.
```

Acceptance:

- [x] 既存関数の戻り値を壊さない
- [x] relation unknown の場合は `{}` を返す
- [x] test passes

### Task M3.3: action slots へ relation を追加

変更:

```text
pipeline/action_generator.py
```

やること:

- [x] slots に `object_relation` と `object_state` を許可
- [x] `render_action_slots()` の order に追加
- [x] passive mode では debug のみ
- [x] active mode では relation slot を追加
- [x] 既存 `summarize_slot_object_focus()` に relation slot を含める

Acceptance:

- [x] `reading a book` で `open book` / `pages` / `gaze` 系が追加される
- [x] relation が既存 hand_action と矛盾する場合は上書きしない
- [x] prompt が過剰に長くならない

---

## 5. M4: Location / Scene Axis EPIG

### Task M4.1: scene axis data を追加

追加:

```text
vocab/data/location_axis_profiles.json
vocab/data/staging_axis_descriptors.json
```

初期 location coverage:

- [x] `school_library`
- [x] `modern_office`
- [x] `commuter_transport`
- [x] `rainy_bus_stop`
- [x] `street_cafe`
- [x] `cozy_living_room`
- [x] `shopping_mall_atrium`
- [x] `picnic_park`

Acceptance:

- [x] axis values are 0.0〜1.0
- [x] camera/quality/effect terms are not included

### Task M4.2: `pipeline/location_semantics.py` を追加

実装:

- [x] `load_location_axis_profiles()`
- [x] `build_scene_target_vector()`
- [x] `rank_location_segment_options()`
- [x] `semantic_location_weights()`

Codex prompt:

```text
Implement pipeline/location_semantics.py. It should compute scene-axis target vectors from location key plus lightweight action/mood adjustments. Do not change location_builder output yet. Add tests for library/study and commuter/waiting.
```

Acceptance:

- [x] `school_library + study` は orderliness/low activity に寄る
- [x] `commuter_transport + waiting` は crowd/time_pressure に寄る
- [x] mood text を直接 emotion label として過剰に使わない

### Task M4.3: passive mode を `location_builder.py` に接続

変更:

```text
pipeline/location_builder.py
```

やること:

- [x] `expand_location_prompt()` に optional `action_text` / `mood_text` を追加
- [x] `apply_location_expansion()` から `ctx.action` / `ctx.meta.mood` を渡す
- [x] segment ranking debug を decision に追加
- [x] passive mode では選択を変えない

Acceptance:

- [x] 既存 output は変わらない
- [x] decision に `semantic_epig.location_scene` が入る
- [x] `lighting_mode=off` の test が通る

### Task M4.4: active mode を有効化

やること:

- [x] `location_scene.mode = active`
- [x] `_weighted_choice()` / `_weighted_sample()` の重みに semantic score を掛ける
- [x] FX deny / lighting off / recent object guard を維持

Acceptance:

- [x] commuter 系で crowd/time_pressure が増える
- [x] library 系で orderly/quiet が増える
- [x] banned fx が出ない

---

## 6. M5: Clothing TPO EPIG

### Task M5.1: clothing axis data を追加

追加:

```text
vocab/data/clothing_axis_profiles.json
```

初期 coverage:

- [x] common themes in `clothing_theme_map.json`
- [x] key outerwear packs
- [x] location targets: office / school / rainy / winter / gym / beach / home
- [x] action targets: commute / study / work / rest / shop

Acceptance:

- [x] body-type descriptors are absent
- [x] weather/activity fit is represented

### Task M5.2: `pipeline/clothing_semantics.py` を追加

実装:

- [x] `build_clothing_target_vector()`
- [x] `score_clothing_decision()`
- [x] `semantic_clothing_penalty()`
- [x] `clothing_semantic_debug_payload()`

Codex prompt:

```text
Implement clothing TPO scoring as a soft candidate penalty. Do not replace existing clothing generation; only score rendered candidates first. Add tests for rainy_bus_stop and modern_office.
```

Acceptance:

- [x] rainy target has high weather_fit
- [x] office target has medium/high formality and low visual_prominence
- [x] data missing does not crash

### Task M5.3: passive mode を `clothing_builder.py` に接続

やること:

- [x] `_render_clothing_candidate()` decision に semantic score を入れる
- [x] `expand_clothing_prompt()` の candidate list に semantic debug を保持
- [x] passive mode では existing repeat penalty のみで選ぶ

Acceptance:

- [x] output unchanged in passive mode
- [x] decision has candidate scores

### Task M5.4: active mode を有効化

やること:

- [x] `clothing_tpo.mode = active`
- [x] final penalty = repeat penalty + semantic penalty
- [x] state detail hard filter は維持

Acceptance:

- [x] rainy/winter/gym/office examples が自然化する
- [x] repeat guard regression がない
- [x] tests pass

---

## 7. M6: Personality Behavior EPIG

### Task M6.1: personality behavior data を追加

追加:

```text
vocab/data/personality_behavior_profiles.json
```

初期 personality:

- [x] `shy`
- [x] `confident`
- [x] `energetic`
- [x] `gloomy`
- [x] `faithful`
- [x] `aggressive`
- [x] `mysterious`
- [x] `cheerful`
- [x] `serious`
- [x] `gentle`
- [x] `neutral`

Acceptance:

- [x] 既存 `PERSONALITY_GARNISH_BIAS` の意味を data に mirror している
- [x] prefer_category が保持される

### Task M6.2: `vocab/personality_semantics.py` を追加

実装:

- [x] `load_personality_profiles()`
- [x] `personality_vector()`
- [x] `prefer_category_for_personality()`
- [x] `rank_personality_descriptors()`
- [x] `pick_personality_descriptor()`

Codex prompt:

```text
Add data-driven personality behavior semantic ranking. Keep the existing inline personality bias as fallback. Add tests for shy, confident, serious, and neutral.
```

Acceptance:

- [x] shy ranking returns away/down/close/restraint descriptors
- [x] confident ranking returns direct/upright/open descriptors
- [x] neutral returns no forced descriptor

### Task M6.3: passive mode を `vocab/garnish/logic.py` に接続

やること:

- [x] semantic personality ranking を debug に出す
- [x] passive mode では既存 `PERSONALITY_GARNISH_BIAS` behavior を維持
- [x] data load failure fallback を追加

Acceptance:

- [x] existing personality tests pass
- [x] debug contains `semantic_epig.personality_behavior`

### Task M6.4: active mode を有効化

やること:

- [x] `personality_behavior.mode = active`
- [x] semantic descriptor を personality preferred tag として使う
- [x] `_is_out_of_context()` を必ず通す
- [x] emotion VAD descriptor と重複・矛盾しないよう `_dedupe()` と face budget を維持

Acceptance:

- [x] shy / confident / serious examples が expected behavior へ寄る
- [x] action context と矛盾する posture が落ちる
- [x] existing garnish tests pass

---

## 8. M7: 統合監査と仕上げ

### Task M7.1: integration samples を記録

Progress の sample A〜D を埋める。

- [x] study / book / library
- [x] commute / station-like scene
- [x] rainy bus stop / clothing TPO
- [x] shy personality

### Task M7.2: full verification

Run:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print('issues', len(issues)); print(issues[:20])"
python assets/calc_variations.py --json
```

Acceptance:

- [x] すべて pass または既知差分が progress に記録されている
- [x] unexpected warning がない

### Task M7.3: docs 更新

候補:

```text
CURRENT_STATUS.md
README.md
docs/semantic_epig/progress.md
```

Acceptance:

- [x] active domain と config mode を記録
- [x] 新規 data files を Source Of Truth に追記
- [x] verification snapshot を更新

---

## 9. PR 分割案

推奨 PR:

1. `semantic-space-passive-foundation`
2. `action-epig-passive`
3. `action-epig-active`
4. `object-relation-epig-passive`
5. `object-relation-epig-active`
6. `location-scene-epig-passive`
7. `location-scene-epig-active`
8. `clothing-tpo-epig-passive`
9. `clothing-tpo-epig-active`
10. `personality-behavior-epig-passive`
11. `personality-behavior-epig-active`
12. `semantic-epig-docs-and-audit`

小さく進める場合は、M2 と M3 を統合しない。  
`action_generator.py` はリスクが中程度なので、Action と Object Relation の変更を分ける。

---

## 10. 完了チェック

- [x] 1〜5 の domain が実装済み
- [x] 各 domain に passive/active mode がある
- [x] DebugInfo に ranking / selected / skipped reason が出る
- [x] semantic-only policy を維持
- [x] public node spec を壊していない
- [x] seed determinism を維持
- [x] new data assets are validated
- [x] unit tests are added
- [x] full verification passes
