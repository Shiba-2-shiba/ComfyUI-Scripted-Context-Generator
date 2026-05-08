# ComfyUI-Scripted-Context-Generator

LLM に依存せず、ルールベース + seed 再現で自然言語プロンプトを組み立てる ComfyUI カスタムノード集です。

現在の公開面は `context_json` を中心に扱う context-first 構成で、active surface は `Context*` ノード群と `PromptCleaner` のみです。

## 現在地の把握

毎回全スクリプトを読み直さずに状態を確認する入口として、[`CURRENT_STATUS.md`](./CURRENT_STATUS.md) を参照してください。

- active runtime surface
- semantic-only 方針
- 現在の variation metrics
- 直近の検証コマンドと結果
- リファクタ時のリスクマップ

## 概要

- ノード間の正式な受け渡しは `context_json: STRING`
- 乱択は `seed` ベースで再現可能
- 生成ロジックは `pipeline/`、スキーマと変換は `core/`、語彙データは `vocab/data/` に分離
- legacy / bridge ノードは退役済み
- 検証資産は `assets/` `tools/` `verification/` に集約

## 現在の公開ノード

### Primary

- `ContextSource`
  - `json_string` と `source_mode` から `context_json` を生成
  - `source_mode` は `auto` / `json_only` / `prompts_only`
- `ContextCharacterProfile`
  - キャラクタープロファイルを `context_json` に反映
- `ContextSceneVariator`
  - シーンと action の整合を調整
- `ContextClothingExpander`
  - 衣装展開
- `ContextLocationExpander`
  - 場所展開
- `ContextMoodExpander`
  - `mood_map.json` を使った mood 展開
- `ContextGarnish`
  - 仕草や補助描写を追加
- `ContextPromptBuilder`
  - `context_json` から最終 prompt を組み立て
  - `composition_mode=true` の場合は `vocab/data/template_catalog.json` と `vocab/templates_*.txt` を使って template part を選択
- `ContextInspector`
  - `context_json` の pretty print と summary を返す

### Utility

- `PromptCleaner`
  - 句読点、重複、空白、禁止語混入をルールベースで整理

## 推奨フロー

同梱の推奨サンプルは [`ComfyUI-workflow-context.json`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/ComfyUI-workflow-context.json) です。

基本の流れ:

1. `ContextSource`
2. `ContextCharacterProfile`
3. `ContextSceneVariator`
4. `ContextClothingExpander`
5. `ContextLocationExpander`
6. `ContextMoodExpander`
7. `ContextGarnish`
8. `ContextPromptBuilder`
9. `PromptCleaner`
10. `ContextInspector`

補足:

- サンプル workflow には preview 用の外部ノードが入ることがありますが、このリポジトリの必須ノードではありません
- downstream ノードの `context_json` は optional input として設計されており、段階的な接続や差し替えをしやすくしています

## 現在の方針

このリポジトリは semantic-only 寄りの出力に整理されています。

- `meta.style` は legacy read-only metadata として保持されますが、prompt 生成には使いません
- `ContextGarnish.include_camera` は旧 workflow 復元用の hidden legacy arg としてのみ残り、実行時は no-op です
- public prompt surface では camera / quality / body-type を前提にしません
- 新規機能追加先は `Context*` ノードと `pipeline/` です

## Source Of Truth

### Character

- `vocab/data/character_profiles.json`
- `vocab/data/scene_compatibility.json`
- 統合責務: [`character_service.py`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/character_service.py)

### Location

- `vocab/data/background_packs.json`
- `vocab/data/background_alias_overrides.json`
- `vocab/data/loc_aliases_canonical.json`
- `vocab/data/loc_aliases_legacy.json`
- `vocab/data/loc_aliases_fallback.json`
- legacy fallback: `vocab/data/background_loc_tag_map.json`
- 解決責務: [`location_service.py`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/location_service.py)

### Clothing

- `vocab/data/clothing_theme_map.json`
- `vocab/data/clothing_packs.json`

### Policy / banned terms

- `vocab/data/policy_terms.json`
- 共有先:
  - [`core/semantic_policy.py`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/core/semantic_policy.py)
  - [`nodes_prompt_cleaner.py`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/nodes_prompt_cleaner.py)
  - [`asset_validator.py`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/asset_validator.py)

## リポジトリ構成

ランタイムの入口は次です。

- [`__init__.py`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/__init__.py)
- [`nodes_context.py`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/nodes_context.py)
- [`nodes_prompt_cleaner.py`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/nodes_prompt_cleaner.py)

主要ディレクトリ:

- `core/`: schema, codec, context 操作, semantic policy
- `pipeline/`: source, scene, clothing, location, mood, garnish, prompt orchestration
- `vocab/`: 語彙ローダーと JSON データ
- `assets/`: Python テスト、baseline、測定、検証スクリプト
- `tools/`: workflow / data / audit 系ユーティリティ
- `verification/`: frontend / browser round-trip 検証

詳しくは以下を参照してください。

- [`REPO_STRUCTURE.md`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/REPO_STRUCTURE.md)
- [`assets/ARCHITECTURE.md`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/assets/ARCHITECTURE.md)
- [`docs/context_refactor/README.md`](/C:/Users/inott/Downloads/test2/ComfyUI-Scripted-Context-Generator/docs/context_refactor/README.md)
- [`codex_refactor_spec_ja.md`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/codex_refactor_spec_ja.md)

## バリエーション規模

`2026-05-08` 時点で `python assets/calc_variations.py --json` を実行した値です。

- unique subjects: `58`
- unique locations: `58`
- base variations: `11,916`
- actions per location: `min 4 / median 8 / mean 7.6 / max 12`
- missing action pools: `0`
- mood keys: `9`
- unique mood tags: `172`
- unique micro actions: `280`
- unique background context tags: `771`
- semantic units: `1,223`
- semantic garnish universe: `11,007`
- theoretical max: `131,159,412`

camera / effect 系は semantic-only ランタイムでは active variation に含めません。
監査用の legacy-disabled 指標として `camera_configs=120`, `effect_tags=22` は残しています。

この数値は語彙データ更新で変わるため、必要なら再計測してください。

## インストール

```bash
cd /path/to/ComfyUI/custom_nodes
git clone <repo-url> ComfyUI-Scripted-Context-Generator
```

1. `ComfyUI/custom_nodes/ComfyUI-Scripted-Context-Generator` に配置
2. ComfyUI を再起動
3. ノード一覧で `prompt_builder/context` と `prompt_builder/utility` を確認

## 検証コマンド

最小確認:

```bash
python -m unittest assets.test_context_nodes assets.test_workflow_samples
python tools/verify_full_flow.py
python -c "from asset_validator import validate_assets; print(validate_assets())"
```

追加の確認:

```bash
python tools/validate_prompt_data.py
python assets/calc_variations.py --json
python tools/check_widgets_values.py
```

frontend / browser round-trip は `verification/` と `tools/run_*.ps1` を使って実行できます。

## データ編集ポイント

- `prompts.jsonl`: `ContextSource` の入力ソース
- `mood_map.json`: mood 展開データ
- `templates.txt`: 単一テンプレート入力向け資産
- `vocab/templates_intro.txt`
- `vocab/templates_body.txt`
- `vocab/templates_end.txt`
- `vocab/data/template_catalog.json`: composition mode 用 template catalog
- `vocab/data/action_pools.json`: location ごとの action 候補
- `vocab/data/background_packs.json`: location pack 定義
- `vocab/data/clothing_packs.json`: clothing pack 定義
- `vocab/data/garnish_base_vocab.json`
- `vocab/data/garnish_micro_actions.json`

asset 編集後は `asset_validator.py` と該当テストを必ず確認してください。

## 注意事項

- 同梱語彙は作者用途寄りの初期セットです。必要に応じて JSON 資産を編集してください
- 生成結果の最終確認と利用判断は利用者側で行ってください
- README は current active surface を基準にしています。退役済みフローは `docs/context_refactor/archive/` や `tools/archive/` を参照してください

## ライセンス

Apache License 2.0。詳細は [`LICENSE`](/C:/Users/inott/Downloads/ComfyUI-Scripted-Context-Generator/LICENSE) を参照してください。
