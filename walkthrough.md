# リファクタリング実装 ウォークスルー

## 概要

ComfyUI-Scripted-Context-Generatorのリファクタリングが完了しました。  
**全4フェーズ**を実装し、`assets/runner.py all` で **Unit Tests PASS / Integrity Checks PASS** を達成しました。

---

## 実装フェーズ別 変更内容

### Phase 0: 検証基盤の整備

| ファイル | 変更内容 |
|---|---|
| [test_personality_garnish.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/test_personality_garnish.py) | personality→garnish連動のユニットテスト（新規作成） |
| [verify_personality_variation.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/verify_personality_variation.py) | personality別tag分布の整合性チェック（新規作成） |
| [verify_mood_staging.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/verify_mood_staging.py) | staging_tagsフィールド検証（新規作成、Phase 2向け） |
| [verify_lighting_axis.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/verify_lighting_axis.py) | 光源軸の検証（新規作成、Phase 3向け） |
| [test_roulette_distribution.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/test_roulette_distribution.py) | APIシグネチャ変更への対応（meta_mood引数追加）、旧rouletteテストを実態に合わせて更新 |

**既存問題の修正:**
- [test_roulette_distribution.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/test_roulette_distribution.py) のインポートエラー（`test_bootstrap` → `sys.path`直接追加）
- [verify_mood_staging.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/verify_mood_staging.py) の cp932 エンコードエラー（em dash文字を除去）

---

### Phase 1: personality → garnish 実接続

**変更ファイル:** [logic.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/vocab/garnish/logic.py)

`PERSONALITY_GARNISH_BIAS` 定数を追加し、[sample_garnish()](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/vocab/garnish/logic.py#322-461) の Step 9 でバイアスを適用:

```python
PERSONALITY_GARNISH_BIAS = {
    "shy": {"prefer": ["looking away", "fidgeting", ...], "avoid_pools": ["POSE_DYNAMIC"]},
    "confident": {"prefer": ["looking at viewer", "chin up", ...], ...},
    ...  # 10 personalities defined
}
```

**検証結果:**
- [shy](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/test_personality_garnish.py#124-153) top-5: `fidgeting, looking down, cheeks flushed, ...`
- [confident](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/test_personality_garnish.py#124-153) top-5: `pumping fist, bright smile, dynamic pose, ...`
- `verify_personality_variation.py --phase1` → **PASS**

---

### Phase 2: mood_map staging_tags 分離

**変更ファイル:**

| ファイル | 変更内容 |
|---|---|
| [mood_map.json](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/mood_map.json) | 全9ムードキーを新フォーマット `{description: [...], staging_tags: [...]}` に変換 |
| [nodes_dictionary_expand.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/nodes_dictionary_expand.py) | [DictionaryExpand](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/nodes_dictionary_expand.py#37-109) を2出力対応に拡張（`expanded_text` + `staging_tags`）、旧フォーマット（リスト）後方互換 |

**例（quiet_focused）:**
```json
{
  "description": ["soft natural lighting, calm atmosphere, ..."],
  "staging_tags": ["soft light", "downcast gaze", "still posture", ...]
}
```

---

### Phase 3: 独立した光源・時間帯軸

**変更ファイル:**

| ファイル | 変更内容 |
|---|---|
| [background_packs.json](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/vocab/data/background_packs.json) | 全58パックにカテゴリ別 [lighting](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/verify_lighting_axis.py#105-131) フィールドを追加（indoor/outdoor/night/nature/commercial/fantasy/industrial） |
| [nodes_dictionary_expand.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/nodes_dictionary_expand.py) | `ThemeLocationExpander.expand_location()` に `lighting_mode=auto/off` パラメータを追加 |

`lighting_mode=auto`（デフォルト）の場合、パックの[lighting](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/verify_lighting_axis.py#105-131)リストからランダムに1タグを出力プロンプトに追加します。

---

### Phase 4: emotion_nuance の活用

**変更ファイル:**

| ファイル | 変更内容 |
|---|---|
| [logic.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/vocab/garnish/logic.py) | [sample_garnish()](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/vocab/garnish/logic.py#322-461) に `emotion_nuance` パラメータを追加（Step 2a で [scene_axis.json](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/vocab/data/scene_axis.json) の `garnish_bias` タグを pool に追加） |
| [nodes_garnish.py](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/nodes_garnish.py) | [GarnishSampler](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/nodes_garnish.py#24-135) に `emotion_nuance` オプション入力（STRING）を追加、[sample_garnish()](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/vocab/garnish/logic.py#322-461) に渡す |

**[scene_axis.json](file:///c:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/vocab/data/scene_axis.json) の `emotion_nuance` 構造:**
- `tense`: `garnish_bias`: `["biting lip", "clenched jaw", "stiff posture", ...]`
- `absorbed`: `garnish_bias`: `["leaning forward", "chin on palm", ...]`
- `relieved`, `awkward`, `content`, `bored` の計6状態

---

## 最終検証結果

```
  Unit Tests      : PASS
  Integrity Checks: PASS
  [SUCCESS] All checks passed.
```

### Integrity Checks 内訳

| スクリプト | 結果 |
|---|---|
| verify_color_distribution.py | PASS |
| verify_consistency.py | PASS |
| verify_integrated_flow.py | PASS |
| verify_lighting_axis.py | **PASS** (Phase 3完了後) |
| verify_location_quality.py | PASS |
| verify_mood_staging.py | **PASS** (Phase 2完了後) |
| verify_personality_action.py | PASS |
| verify_personality_variation.py | **PASS** (Phase 1完了後) |
| verify_phase1.py | PASS |
| verify_refactoring.py | PASS |

---

## 視覚的バリエーション向上の見込み

| 改善軸 | 改善前 | 改善後 |
|---|---|---|
| キャラ性格 | personality 未使用 | shy/confident/gloomy等でガーニッシュタグが変化 |
| ムード演出 | descriptionのみ | staging_tagsで追加の演出情報が利用可能 |
| 光源表現 | なし | 全58ロケーションに lighting タグ（indoor/outdoor/night等で異なる） |
| 感情的文脈 | なし | emotion_nuance (tense/absorbed 等) でキャラポーズが変化 |
