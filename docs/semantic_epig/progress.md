# EPIG的 Semantic Enrichment 実装進捗

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev`
関連仕様: `implementation_spec.md`
関連タスク: `tasks.md`

---

## 1. 現在地

### 1.1 Repo baseline

- Runtime surface: `Context*` nodes and `PromptCleaner`
- Transport: `context_json: STRING`
- Main runtime logic: `pipeline/`
- Schema / context operations / policy: `core/`
- Data source of truth: `vocab/data/`
- Action authoring source: `vocab/source/action_pools/`
- 方針: semantic-only
- public prompt surface で扱わないもの: camera / quality / body-type / render effects

### 1.2 既存 EPIG 的処理

現状では感情表現に対して以下が実装済み。

- `vocab/emotion_vad.py`
  - category VAD
  - nuance VAD
  - load arousal bias
  - Euclidean distance
  - relevance
  - descriptor ranking
- `vocab/garnish/logic.py`
  - `emotion_role_mode = subject_only`
  - `subject_role`, `stimulus_role`, `context_role` を DebugInfo に記録
  - expression / gaze / behavior / extra を VAD ranking で選択
  - action / location / costume と矛盾する候補を filter

今回の拡張は、これを以下へ横展開する。

| Domain | 目的 | 状態 |
|---|---|---|
| Action EPIG | 動詞を posture / hand / gaze / progress へ分解 | Active complete |
| Object Relation EPIG | object を使用関係として bind | Active complete |
| Location / Scene Axis EPIG | 場所を scene axis で制御 | Active complete |
| Clothing TPO EPIG | 衣装を場所・動作適合で rank | Active complete |
| Personality Behavior EPIG | personality を視線・姿勢・手へ変換 | Active complete |

---

## 2. Milestone 状態

| Milestone | 内容 | 状態 | PR / commit | メモ |
|---|---|---|---|---|
| M0 | baseline verification and docs setup | Done |  | docs copied to `docs/semantic_epig/`; baseline rechecked |
| M1 | generic semantic_space + config + validator | Done |  | passive foundation only; no runtime prompt connection |
| M2 | Action EPIG | Active complete |  | semantic score now adjusts slot weights; other domains remain passive |
| M3 | Object Relation EPIG | Active complete |  | relation `object_state`/empty role slots render; existing slots are not overwritten |
| M4 | Location / Scene Axis EPIG | Active complete |  | scene-axis score now adjusts location segment weights |
| M5 | Clothing TPO EPIG | Active complete |  | final penalty now combines repeat and semantic penalties |
| M6 | Personality Behavior EPIG | Active complete |  | semantic ranking now selects personality preferred garnish with inline fallback |
| M7 | integration audit / docs / cleanup | Done |  | samples A-D recorded; final verification and status docs updated |

Status values:

- `Not started`
- `In progress`
- `Passive complete`
- `Active complete`
- `Blocked`
- `Done`

---

## 3. Decision log

| Date | Decision | Reason | Impact |
|---|---|---|---|
| 2026-06-15 | `semantic_epig_config.json` で mode 管理する | public node UI を変えずに段階導入するため | low-risk rollout |
| 2026-06-15 | 初期は `passive` mode から実装する | snapshot 破壊を避け、debug payload を先に確認するため | implementation safety |
| 2026-06-15 | 共通 ranking は `vocab/semantic_space.py` に集約する | emotion 以外でも同じ距離・relevance・validator を使うため | duplication reduction |
| 2026-06-15 | semantic-only policy を維持する | repo 方針に合わせるため | camera / quality / body-type を除外 |

---

## 4. Baseline verification log

Codex 作業前に実行する。

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print('issues', len(issues)); print(issues[:20])"
```

結果記録:

| Command | Result | Notes |
|---|---|---|
| `python -m unittest discover -s assets -p "test_*.py"` | Pass | 290 tests OK after regenerating ignored audit artifacts |
| `python tools/validate_prompt_data.py` | Pass | `ERROR: []`, `WARNING: []` |
| `python tools/verify_full_flow.py` | Pass | OK |
| `python tools/check_widgets_values.py` | Pass | no widget value issues |
| `asset_validator.validate_assets()` | Pass | `issues 0` |

---

## 5. Domain progress

### 5.1 M1: Generic semantic space

Status: Done

Expected files:

```text
vocab/semantic_space.py
pipeline/semantic_epig.py
vocab/data/semantic_epig_config.json
assets/test_semantic_space.py
```

Checklist:

- [x] distance / relevance / ranking utility added
- [x] axis payload validator added
- [x] config loader added
- [x] passive / active mode helper added
- [x] unit tests added
- [x] asset validator updated
- [x] no prompt output change in passive mode

Notes:

```text
Implemented as foundation only:
- vocab/semantic_space.py
- pipeline/semantic_epig.py
- vocab/data/semantic_epig_config.json
- assets/test_semantic_space.py
- assets/test_semantic_epig.py

Focused verification:
- python -m unittest assets.test_semantic_space assets.test_semantic_epig assets.test_asset_validator
- python -m py_compile vocab/semantic_space.py pipeline/semantic_epig.py asset_validator.py assets/test_semantic_space.py assets/test_semantic_epig.py assets/test_asset_validator.py
```

---

### 5.2 M2: Action EPIG

Status: Active complete

Expected files:

```text
pipeline/action_semantics.py
vocab/data/action_semantic_profiles.json
vocab/data/action_slot_descriptors.json
assets/test_action_semantics.py
```

Expected modified files:

```text
pipeline/action_generator.py
pipeline/context_pipeline.py
asset_validator.py
```

Checklist:

- [x] action axes defined
- [x] purpose target vectors added
- [x] slot descriptor ranking added
- [x] `build_action_slots()` semantic debug added
- [x] passive mode keeps output unchanged
- [x] active mode changes slot selection deterministically
- [x] unit tests added
- [x] integration tests pass

Before / after examples:

```text
Active mode enabled for `action` only. Slot selection now applies:

```text
final_weight = existing_weight * (0.50 + semantic_score)
```

Representative debug payload now appears under:
decision.semantic_epig.action = {
  "mode": "active",
  "target_vector": {...},
  "slot_rankings": {...},
  "selected_by_semantic": true
}

Focused verification:
- python -m unittest assets.test_action_semantics assets.test_action_generator assets.test_semantic_epig assets.test_context_pipeline assets.test_asset_validator
- python -m py_compile pipeline/action_semantics.py pipeline/action_generator.py vocab/semantic_space.py pipeline/semantic_epig.py asset_validator.py assets/test_action_semantics.py assets/test_action_generator.py
```

---

### 5.3 M3: Object Relation EPIG

Status: Active complete

Expected files:

```text
vocab/data/object_relation_profiles.json
assets/test_object_relation_semantics.py
```

Expected modified files:

```text
object_focus_service.py
pipeline/action_generator.py
asset_validator.py
```

Checklist:

- [x] relation profile loader added
- [x] relation key inference added
- [x] relation slots `object_relation` / `object_state` added
- [x] render order updated
- [x] passive mode debug added
- [x] active mode applies relation descriptors
- [x] unit tests added
- [x] no forbidden relation text emitted

Before / after examples:

```text
Active mode enabled for `object_relation`.

Representative debug payload now appears under:
decision.semantic_epig.object_relation = {
  "mode": "active",
  "detected_objects": ["book"],
  "relation_key": "book:reading",
  "required_roles": {...},
  "applied_slots": {"object_state": "open pages visible"},
  "skipped_slots": {"hand_action": "existing slot already set", ...}
}

Focused verification:
- python -m unittest assets.test_object_focus_service assets.test_action_generator assets.test_semantic_epig assets.test_action_semantics assets.test_asset_validator
```

---

### 5.4 M4: Location / Scene Axis EPIG

Status: Active complete

Expected files:

```text
pipeline/location_semantics.py
vocab/data/location_axis_profiles.json
vocab/data/staging_axis_descriptors.json
assets/test_location_semantics.py
```

Expected modified files:

```text
pipeline/location_builder.py
pipeline/mood_builder.py
asset_validator.py
```

Checklist:

- [x] scene axes defined
- [x] location base vector profiles added
- [x] action/mood lightweight target adjustment added
- [x] segment ranking added
- [x] `lighting_mode=off` respected
- [x] FX deny list respected
- [x] passive mode keeps output unchanged
- [x] active mode segment choice becomes scene-axis aware

Before / after examples:

```text
Active mode enabled for `location_scene`.

Section selection now applies:

```text
final_weight = existing_weight * (0.50 + semantic_score)
```

Representative debug payload now appears under:
decision.semantic_epig.location_scene = {
  "mode": "active",
  "target_vector": {...},
  "segment_rankings": {...},
  "selected_by_semantic": true
}

Focused verification:
- python -m unittest assets.test_location_semantics assets.test_context_content_pipeline assets.test_semantic_epig assets.test_asset_validator
- python -m py_compile pipeline/location_semantics.py pipeline/location_builder.py assets/test_location_semantics.py assets/test_context_content_pipeline.py
```

---

### 5.5 M5: Clothing TPO EPIG

Status: Active complete

Expected files:

```text
pipeline/clothing_semantics.py
vocab/data/clothing_axis_profiles.json
assets/test_clothing_semantics.py
```

Expected modified files:

```text
pipeline/clothing_builder.py
asset_validator.py
```

Checklist:

- [x] clothing axes defined
- [x] location/action target vectors added
- [x] candidate semantic score added
- [x] repeat penalty preserved
- [x] state detail hard filters preserved
- [x] passive mode debug added
- [x] active mode uses final penalty
- [x] body-type terms not introduced

Before / after examples:

```text
Active mode enabled for `clothing_tpo`.

Candidate selection now applies:

```text
final_penalty = repeat_penalty + semantic_penalty
```

Representative debug payload now appears under:
decision.semantic_epig.clothing_tpo = {
  "mode": "active",
  "target_vector": {...},
  "candidate_scores": [...],
  "selected_attempt_index": 0,
  "selected_by_semantic": true
}

Focused verification:
- python -m unittest assets.test_clothing_semantics assets.test_context_content_pipeline assets.test_semantic_epig assets.test_prompt_snapshots
- python -m py_compile pipeline/clothing_semantics.py pipeline/clothing_builder.py assets/test_clothing_semantics.py assets/test_context_content_pipeline.py
```

---

### 5.6 M6: Personality Behavior EPIG

Status: Active complete

Expected files:

```text
vocab/personality_semantics.py
vocab/data/personality_behavior_profiles.json
assets/test_personality_semantics.py
```

Expected modified files:

```text
vocab/garnish/logic.py
asset_validator.py
```

Checklist:

- [x] personality axes defined
- [x] existing inline bias moved or mirrored to data
- [x] fallback to inline bias retained
- [x] personality descriptor ranking added
- [x] `_is_out_of_context()` filter reused
- [x] `prefer_category` behavior preserved
- [x] passive mode debug added
- [x] active mode chooses semantic personality descriptors

Before / after examples:

```text
Active mode enabled for `personality_behavior`.

Semantic ranking now selects the preferred personality garnish first. If no semantic
descriptor is available or the context filter rejects it, selection falls back to
the existing `PERSONALITY_GARNISH_BIAS` list.

Representative debug payload now appears under:
decision.semantic_epig.personality_behavior = {
  "mode": "active",
  "personality": "shy",
  "target_vector": {...},
  "prefer_category": "care",
  "slot_rankings": {...},
  "selected": "semantic descriptor tag",
  "selected_by_semantic": true
}

Focused verification:
- python -m unittest assets.test_personality_semantics assets.test_personality_garnish assets.test_emotion_vad_alignment assets.test_semantic_epig assets.test_prompt_snapshots
- python -m py_compile vocab/personality_semantics.py vocab/garnish/logic.py assets/test_personality_semantics.py assets/test_personality_garnish.py
```

---

## 6. Risk register

| Risk | Level | Mitigation |
|---|---:|---|
| Existing prompt snapshots change unexpectedly | High | passive mode first, active mode in separate PR |
| Public node UI / workflow widget breaks | High | no `nodes_context.py` public spec change initially |
| New descriptors violate semantic-only policy | High | asset validator + banned term scan |
| Action output becomes too verbose | Medium | max new relation slots = 2, dedupe, top_k limit |
| Clothing TPO overfits location stereotypes | Medium | use soft score, preserve theme and repeat guard |
| Location axis produces mood-like drift | Medium | use concrete scene axes, not emotion words |
| Personality and emotion garnish conflict | Medium | reuse `_is_out_of_context()` and existing face-forward budget |
| Data files become hard to maintain | Medium | schema_version, notes, tests, minimal initial coverage |

---

## 7. Integration audit log

After each active domain, record the output of representative contexts.

### Sample A: study / book / library

Input:

```json
{"subj":"a student","loc":"school_library","action":"reading a book","costume":"school_uniform","meta":{"mood":"focus"}}
```

Result:

```text
a student in navy cotton layered collar academy pleated dress, with contrast piping, soft knit cardigan, right where her attention settles, reading a book, upright composed posture, composed face, attention locked forward, in quiet library filled with rows of books, intricate background details, filled with return cart waiting by the aisle and labeled study folders, smell of old paper visualized, during quiet afternoon, focus
```

Audit notes:

- Inspector summary: `subj=a student; costume=school_uniform; loc=school_library; action=reading a book; mood=focus; history=5`
- Runtime semantic domains observed: `clothing_tpo`, `location_scene`, `personality_behavior`

### Sample B: commute / station-like scene

Input:

```json
{"subj":"a commuter","loc":"commuter_transport","action":"waiting for the next train","costume":"casual","meta":{"mood":"tense"}}
```

Result:

```text
a commuter in casual, generic outfit, moving with the next part of the day, waiting for the next train, upright composed posture, uneasy face, quick darting glance, the moment staying with her, with the scene around her staying in crowded commuter train interior, featuring large glass windows reflecting interior, lived-in atmosphere, during quiet midday, crowded claustrophobic feel, hard plastic seats, tense
```

Audit notes:

- Inspector summary: `subj=a commuter; costume=casual; loc=commuter_transport; action=waiting for the next train; mood=tense; history=5`
- Runtime semantic domains observed: `clothing_tpo`, `location_scene`, `personality_behavior`

### Sample C: rainy bus stop / clothing TPO

Input:

```json
{"subj":"a woman","loc":"rainy_bus_stop","action":"commuting","costume":"casual","meta":{"mood":"calm"}}
```

Result:

```text
a woman in casual, generic outfit, caught in a brief pause, open posture, playful expression, teasing look while commuting, the rest of the moment opening into rural bus shelter at night, featuring puddle reflecting the street light, during stormy evening, adorned with wet schedule timetable, calm
```

Audit notes:

- Inspector summary: `subj=a woman; costume=casual; loc=rainy_bus_stop; action=commuting; mood=calm; history=5`
- Runtime semantic domains observed: `clothing_tpo`, `location_scene`, `personality_behavior`

### Sample D: shy personality

Input:

```json
{"subj":"a student","loc":"school_classroom","action":"standing near the classroom door","extras":{"personality":"shy"},"meta":{"mood":"focus"}}
```

Result:

```text
a student in navy academy pleated dress, with soft knit cardigan, wearing a forest green warm wool coat over it, standing near the classroom door, looking slightly away, still posture, and the room around her staying in nostalgic after-school classroom with golden light, sunny blue sky outside, with leather school bags hanging heavily on hooks, during early morning, rich surface variation, featuring dark green blackboard covered in chalk equations plus rows of wooden desks with scratches, full of chatting students, focus
```

Audit notes:

- Inspector summary: `subj=a student; costume=school_uniform; loc=school_classroom; action=standing near the classroom door; mood=focus; history=5`
- Runtime semantic domains observed: `clothing_tpo`, `location_scene`, `personality_behavior`

### Action / Object Relation active path

`ContextSceneVariator` uses `action` and `object_relation` debug when action generation is refreshed.

```text
school_library: semantic domains action, object_relation; modes active, active
commuter_transport: semantic domains action, object_relation; modes active, active
school_classroom: semantic domains action, object_relation; modes active, active
```

---

## 8. Final verification checklist

- [x] `python -m unittest discover -s assets -p "test_*.py"` passes
- [x] `python tools/validate_prompt_data.py` passes
- [x] `python tools/verify_full_flow.py` passes
- [x] `python tools/check_widgets_values.py` passes
- [x] `python -c "from asset_validator import validate_assets; print(validate_assets())"` returns `[]`
- [x] `python assets/calc_variations.py --json` has no unexpected metric break
- [x] `ContextInspector` summary still works
- [x] No public node I/O spec changes unless explicitly accepted
- [x] README / CURRENT_STATUS are updated after final active rollout

Final verification snapshot:

| Command | Result | Notes |
|---|---|---|
| `python -m unittest discover -s assets -p "test_*.py"` | Pass | 315 tests OK |
| `python tools/validate_prompt_data.py` | Pass | `ERROR: []`, `WARNING: []` |
| `python tools/verify_full_flow.py` | Pass | OK |
| `python tools/check_widgets_values.py` | Pass | no widget value issues |
| `python -c "from asset_validator import validate_assets; issues=validate_assets(); print('issues', len(issues)); print(issues[:20])"` | Pass | `issues 0`, `[]` |
| `python assets/calc_variations.py --json` | Pass | base variations remain `105,612`; no missing pools |
| `python -m unittest assets.test_context_nodes assets.test_workflow_samples` | Pass | 12 tests OK; ContextInspector covered |
| `python tools/check_variation_scope.py` | Pass | `ERROR: []`, `WARNING: []` |
| `python tools/build_compatibility_review.py --check` | Pass | `ERROR: []`, `WARNING: []` |
| `python tools/build_action_pools.py --check` | Pass | `ERROR: []`, `WARNING: []` |
