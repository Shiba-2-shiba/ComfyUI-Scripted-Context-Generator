# Semantic EPIG Refactor Specification

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-16
関連文書:

- `docs/semantic_epig/implementation_spec.md`
- `docs/semantic_epig/progress.md`
- `docs/semantic_epig/tasks.md`
- `docs/semantic_epig/refactor_progress.md`
- `docs/semantic_epig/refactor_tasks.md`

---

## 1. 目的

`dev2` では Semantic EPIG の5 domainが all-active で統合されている。
このリファクタの目的は、機能を大きく作り替えることではなく、次の順序で安全性と検証性を上げることにある。

```text
debug meaning を正す
  ↓
active/passive 差分を監査可能にする
  ↓
asset schema を強くする
  ↓
Action / Personality の実効性を上げる
  ↓
builder を小さく分割する
```

この順序を守る。先に builder を分割すると、Semantic EPIG が実際に選択を変えたのか、単に構造変更で出力が変わったのかを切り分けにくくなる。

---

## 2. 現状評価

### 2.1 良い状態

- `vocab/semantic_space.py` に共通 ranking utility がある
- `pipeline/semantic_epig.py` に config / debug helper がある
- `semantic_epig_config.json` で `off` / `passive` / `active` を切り替えられる
- public `Context*` node I/O は変更されていない
- semantic-only 方針は維持されている
- Semantic EPIG 直結テストは通る
- `asset_validator.validate_assets()` は clean

### 2.2 リファクタ対象

| Area | 現状 | 問題 |
|---|---|---|
| Debug meaning | `selected_by_semantic` が広く使われる | 多くの箇所で active mode と実選択変化が混ざっている |
| Audit | active/passive 比較 tool がない | all-active の効果と副作用を定量的に追えない |
| Object relation validation | banned term scan 中心 | relation key, object, role, verbs の構造崩れを検出しにくい |
| Action EPIG | runtime候補の重み付け中心 | descriptorを新規 slot 候補として供給できていない |
| Personality EPIG | context引数を受けるが内部で活用が浅い | top1 reject 後に次点候補を試さず fallback しやすい |
| Builder modules | action/location/clothing builder が肥大 | 今後の変更で責務境界がさらに曖昧になる |

---

## 3. Refactor Principles

### 3.1 Behavior lock first

リファクタ前に、対象挙動をテストまたは audit で固定する。

最低限:

```bash
python -m unittest assets.test_semantic_space assets.test_semantic_epig assets.test_action_semantics assets.test_location_semantics assets.test_clothing_semantics assets.test_personality_semantics assets.test_action_generator assets.test_object_focus_service assets.test_personality_garnish
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

`assets/results/` は gitignore されている。全 unittest で audit baseline が不足する場合は、実装 failure と baseline artifact 不足を分けて記録する。

### 3.2 Public node I/O を変えない

このリファクタでは `nodes_context.py` の public input/output spec を変更しない。

### 3.3 Semantic-only を維持する

新規 descriptor / audit / debug field は camera, quality, render effect, body-type を出力面へ持ち込まない。

### 3.4 Diff を段階化する

1 pass で複数の smell を混ぜない。

推奨順:

1. debug contract
2. prompt-level audit
3. validator
4. Action descriptor candidate supply
5. Personality top-k selection
6. builder split

---

## 4. Target Debug Contract

### 4.1 問題

現状の `selected_by_semantic` は domain により意味が揺れている。

例:

- `action`: `semantic_mode("action") == "active"`
- `location_scene`: `location_semantic_mode == "active"`
- `clothing_tpo`: `clothing_tpo_active`
- `personality_behavior`: semantic candidate が context filter を通ったか

つまり、同じ field が「activeだった」「semantic scoreを使った」「実際にsemantic候補が採用された」を混在して表す。

### 4.2 新 contract

各 domain debug payload に次を追加する。

```json
{
  "mode": "active",
  "semantic_scoring_enabled": true,
  "selection_changed_by_semantic": false,
  "baseline_candidate": "...",
  "semantic_candidate": "...",
  "semantic_top_candidate": "...",
  "selected_candidate_rank": 1
}
```

`selected_by_semantic` は当面 backward compatibility のため残してよいが、新規 test は上記 fields を見る。

### 4.3 Domain別定義

#### action

- `baseline_candidate`: semantic score なしで同じ候補集合から選ぶ候補
- `semantic_candidate`: semantic score ありで選ぶ候補
- `selection_changed_by_semantic`: slot ごとに baseline と semantic が異なるか

slot別 debug:

```json
{
  "slot_changes": {
    "hand_action": {
      "baseline": "hands staying precise and controlled",
      "semantic": "fingers keeping her notes in order",
      "changed": true,
      "semantic_top_candidate": "fingers keeping her notes in order",
      "selected_candidate_rank": 1
    }
  }
}
```

#### location_scene

section別に baseline/semantic を記録する。

```json
{
  "section_changes": {
    "core": {
      "baseline": "rows of wooden desks",
      "semantic": "quiet study tables",
      "changed": true
    }
  }
}
```

#### clothing_tpo

- `baseline_selected_attempt_index`: repeat penalty のみ
- `semantic_selected_attempt_index`: repeat + semantic penalty
- `selection_changed_by_semantic`: index が異なるか

#### personality_behavior

- `semantic_scoring_enabled`: domain が passive/active で ranking されたか
- `selection_changed_by_semantic`: inline fallback first candidate と semantic selected が異なるか
- `fallback_used`: semantic候補が全滅したか
- `rejected_candidates`: context filter で落ちた候補

---

## 5. Prompt-Level Audit

### 5.1 目的

画像生成前に active/passive の prompt 差分を比較する。

### 5.2 CLI

追加候補:

```text
tools/audit_semantic_epig_outputs.py
assets/fixtures/semantic_epig_audit_cases.json
assets/test_semantic_epig_audit.py
```

想定コマンド:

```bash
python tools/audit_semantic_epig_outputs.py \
  --samples assets/fixtures/semantic_epig_audit_cases.json \
  --seed-start 0 \
  --seed-count 8 \
  --output assets/results/semantic_epig_audit.json
```

### 5.3 Output

```json
{
  "case_id": "study_book_library",
  "seed": 42,
  "input": {
    "subj": "a student",
    "loc": "school_library",
    "action": "reading a book",
    "costume": "school_uniform",
    "mood": "focus"
  },
  "passive_prompt": "...",
  "active_prompt": "...",
  "changed": true,
  "changed_domains": ["location_scene", "clothing_tpo"],
  "prompt_length_delta": 18,
  "semantic_debug": {},
  "policy_issues": []
}
```

### 5.4 Metrics

- changed domain count
- prompt length delta
- semantic top-1 adoption rate
- selection changed rate
- context filter reject rate
- object relation application rate
- banned term count
- camera / quality / body-type policy issue count

---

## 6. Object Relation Validator

### 6.1 Target

`object_relation_profiles.json` は axis asset ではないため、専用 validator を持つ。

### 6.2 Function

```python
ALLOWED_OBJECT_RELATION_ROLES = {
    "posture",
    "hand_action",
    "gaze_target",
    "object_relation",
    "object_state",
    "optional_micro_action",
}

def validate_object_relation_profiles(payload: Any | None = None) -> list[str]:
    ...
```

### 6.3 Checks

- `schema_version` がある
- `relations` が dict
- relation key が `object:relation` 形式
- relation key の object と payload `object` が一致する
- object が `OBJECT_TOKENS` に含まれる
- `verbs` が non-empty `list[str]`
- `required_roles` が dict
- role key が許可済み
- role values が non-empty `list[str]`
- descriptor が空文字ではない
- `forbidden_patterns` が `list[str]`
- banned terms を含まない

---

## 7. Action Descriptor Candidate Supply

### 7.1 問題

現状は runtime options に存在する候補を semantic score で重み付けしている。
これは安全だが、抽象動詞を視覚証拠へ展開する EPIG としては弱い。

### 7.2 方針

`action_slot_descriptors.json` を metadata だけでなく候補供給源として使う。

```text
runtime options
  + semantic descriptor options
  + object relation derived options
  ↓
rank
  ↓
context / object policy
  ↓
choose
```

### 7.3 Guardrails

- descriptor追加は slot ごとに最大 1-2 個
- existing slot override は上書きしない
- prompt length delta を audit で見る
- object relation と重複する descriptor は dedupe
- seed determinism を維持

---

## 8. Personality Context-Aware Top-K

### 8.1 問題

`pick_personality_descriptor()` は context引数を受け取るが、現状では内部で破棄している。
外側で top1 を `_is_out_of_context()` に通し、reject されたら inline fallback に戻りやすい。

### 8.2 方針

slot横断の ranked stream を作り、context filter を上から順に通す。

```text
gaze / posture / hands rankings
  ↓
merge by score
  ↓
reject_fn(candidate)
  ↓
first accepted candidate
  ↓
fallback only when all semantic candidates fail
```

### 8.3 Debug

```json
{
  "selected": "looking slightly away",
  "selected_candidate_rank": 2,
  "fallback_used": false,
  "rejected_candidates": [
    {"text": "open posture", "reason": "out_of_context"}
  ]
}
```

---

## 9. Builder Split

Builder split は最後に行う。

### 9.1 `pipeline/action_generator.py`

分割候補:

```text
pipeline/action_parser.py
pipeline/action_slot_selector.py
pipeline/action_relation_binder.py
pipeline/action_renderer.py
```

Public compatibility:

- `generate_action_for_location()`
- `parse_pool_action_to_slots()`
- `render_action_slots()`
- `action_verb()`
- `action_object_flags()`

既存 import を壊さないため、必要なら `action_generator.py` は facade として残す。

### 9.2 `pipeline/location_builder.py`

分割候補:

```text
pipeline/location_segment_selector.py
pipeline/location_policy.py
pipeline/location_renderer.py
```

### 9.3 `pipeline/clothing_builder.py`

分割候補:

```text
pipeline/clothing_candidate_renderer.py
pipeline/clothing_candidate_selector.py
pipeline/clothing_tpo_adapter.py
```

---

## 10. Verification Gates

### 10.1 Per-pass

各 pass 後に最低限:

```bash
python -m unittest assets.test_semantic_space assets.test_semantic_epig assets.test_action_semantics assets.test_location_semantics assets.test_clothing_semantics assets.test_personality_semantics assets.test_action_generator assets.test_object_focus_service assets.test_personality_garnish
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

### 10.2 Before builder split

```bash
python tools/audit_semantic_epig_outputs.py --samples assets/fixtures/semantic_epig_audit_cases.json --seed-count 8 --output assets/results/semantic_epig_audit_before_split.json
python -m unittest discover -s assets -p "test_*.py"
```

### 10.3 After builder split

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python assets/calc_variations.py --json
```

---

## 11. Definition of Done

- `selected_by_semantic` の意味揺れが解消または後方互換扱いに限定される
- active/passive prompt diff を JSON audit できる
- object relation asset の構造崩れを validator が検出する
- Action descriptor が候補供給源として使える
- Personality descriptor が context-aware top-k で選ばれる
- builder split 後も public API と node I/O が変わらない
- seed determinism が維持される
- semantic-only policy violation がない
- verification commands が pass するか、既知の ignored baseline artifact 不足として記録される
