# ComfyUI-Scripted-Context-Generator

LLM に依存せず、**ルールベース + シード再現**で自然言語プロンプトを構築する ComfyUI カスタムノード集です。  
This custom-node pack generates natural-language prompts via deterministic/rule-based logic (no LLM required).

---

## 重要な前提 / Important Notice

- 本リポジトリは、作者の用途（女性主人公・SFW寄り）向けに設計された語彙セットを同梱しています。
- 収録語彙はあくまで初期実装です。運用用途に合わせて `vocab/data/*.json` や `templates.txt` を編集してください。
- 生成結果の最終確認・利用判断は利用者自身の責任で行ってください。

---

## このノードの現在地（強化ポイント）

従来の「テンプレート置換」中心から、以下のように強化されています。

- **構造化フロー化**: `PackParser` → `SceneVariator` → `GarnishSampler` → `SimpleTemplateBuilder` → `PromptCleaner` の段階処理で文生成を安定化。
- **語彙モジュール分離**: `vocab/` 配下に衣装・背景・ガーニッシュ語彙を分割し、データ差し替えで拡張しやすい構成。
- **検証資産の整備**: `assets/` にユニットテスト、整合性検証、分布検証、ベースライン生成を集約。
- **再現性の担保**: 各ノードの seed 入力により、同条件で同一出力を再現可能。

---

## バリエーション規模（検証スクリプト計測値）

`assets/calc_variations.py` による計測結果（現行データ時点）は次の通りです。

- **ベース組み合わせ（Char × Loc × Action）**: **6,070**
- **対象サブジェクト数**: **58**
- **対象ロケーション数**: **45**
- **不足 Action Pool**: **0**
- **ガーニッシュ空間（推定）**: **471,120**
- **理論上限（Base × Garnish Universe）**: **2,859,698,400**

> 算出コマンド例:
>
> ```bash
> python assets/calc_variations.py --project_root .
> ```

※ 上記「理論上限」は、各要素の組み合わせ可能性を積算した上限指標です。実運用では互換ルール・テンプレート条件で絞り込まれます。

---

## 主なノード

- `PackParser`  
  `prompts.jsonl`（または入力 JSON）から `subj / costume / loc / action / meta_*` を抽出。

- `SceneVariator`  
  `scene_compatibility.json` と `action_pools.json` を使ってロケーション・行動候補の整合性を補強。

- `ThemeClothingExpander` / `ThemeLocationExpander`  
  テーマキー・場所キーを詳細表現へ展開（`vocab/data` を参照）。

- `GarnishSampler` / `ActionMerge`  
  ムード・ポーズ・微動作などの補助描写を生成し、既存 action と統合。

- `SimpleTemplateBuilder`  
  プレースホルダを使って自然文を構築。未指定時は `templates.txt` を利用。

- `PromptCleaner`  
  句読点、空白、不要区切りなどをルールベースで整形。

- `CharacterProfileNode`  
  キャラプロファイルから外見・性格・カラーパレットを取り出し、文生成に供給。

---

## 基本フロー（推奨）

1. `PackParser` でベース要素を抽出（空入力時は `prompts.jsonl`）
2. `SceneVariator` でシーン整合性を調整
3. `ThemeClothingExpander` / `ThemeLocationExpander` で描写を具体化
4. `GarnishSampler` で補助描写を追加
5. `SimpleTemplateBuilder` で自然言語文に組み立て
6. `PromptCleaner` で最終整形

---

## 検証スクリプト（抜粋）

`assets/` には以下の検証系スクリプトがあります。

- 単体テスト: `test_schema.py`, `test_composition.py`, `test_prompt_cleaner.py` など
- 整合性検証: `verify_integrated_flow.py`, `verify_consistency.py`, `verify_location_quality.py`
- 分布確認: `test_roulette_distribution.py`, `verify_color_distribution.py`
- KPI/規模評価: `evaluate_kpi.py`, `calc_variations.py`

必要に応じて CI に組み込むことで、語彙拡張時の破壊的変更を早期検出できます。

---

## インストール

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/<your-account>/ComfyUI-Scripted-Context-Generator.git
```

1. `ComfyUI/custom_nodes/` に配置
2. ComfyUI を再起動
3. ノード一覧で `prompt_builder` 系カテゴリを確認

---

## データ編集ポイント

- `templates.txt`: 文テンプレート
- `prompts.jsonl`: ベースシーン候補
- `mood_map.json`: ムード辞書
- `vocab/data/character_profiles.json`: キャラ設定
- `vocab/data/scene_compatibility.json`: シーン互換ルール
- `vocab/data/action_pools.json`: ロケーション別アクション
- `vocab/data/garnish_*.json`: ガーニッシュ語彙

---

## ライセンス

このプロジェクトは **Apache License 2.0** の下で公開されています。詳細は `LICENSE` を参照してください。
