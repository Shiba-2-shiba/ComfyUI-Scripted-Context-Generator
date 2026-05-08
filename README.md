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

subject / location / base variations を増やす作業では、[`EXPANSION_GUIDE.md`](./EXPANSION_GUIDE.md) を先に参照してください。
日常系 location / action pool の拡張計画と進捗は [`docs/variation_expansion/`](./docs/variation_expansion/README.md) にあります。
現在は 100k base variations gate を通過済みで、次の大きな計画対象は 500k へ向けた段階拡張です。

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

同梱の推奨サンプルは [`ComfyUI-workflow-context.json`](./ComfyUI-workflow-context.json) です。

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
- 統合責務: [`character_service.py`](./character_service.py)

### Location

- `vocab/data/background_packs.json`
- `vocab/data/background_alias_overrides.json`
- `vocab/data/loc_aliases_canonical.json`
- `vocab/data/loc_aliases_legacy.json`
- `vocab/data/loc_aliases_fallback.json`
- legacy fallback: `vocab/data/background_loc_tag_map.json`
- 解決責務: [`location_service.py`](./location_service.py)

### Clothing

- `vocab/data/clothing_theme_map.json`
- `vocab/data/clothing_packs.json`

### Action / variation sizing

- `vocab/data/variation_scope.json`
- `vocab/data/action_pools.json`
- authoring source: `vocab/source/action_pools/*.json` and shared families in `vocab/source/action_pools/_shared_families.json`
- `assets/compatibility_review.csv`
- 計測責務: [`assets/calc_variations.py`](./assets/calc_variations.py)
- scope 検証: [`tools/check_variation_scope.py`](./tools/check_variation_scope.py)
- scoped CSV 生成チェック: [`tools/build_compatibility_review.py`](./tools/build_compatibility_review.py)

`assets/calc_variations.py` は `assets/compatibility_review.csv` を base variation sizing の入力として使います。
location を追加しても、この CSV に反映されなければ `base variations` には加算されません。
`vocab/data/variation_scope.json` は、現在 variation sizing に含める subject / location の境界を明示します。
action pool は source 側で編集し、`tools/build_action_pools.py --write` で runtime の
`vocab/data/action_pools.json` へ展開します。

### Policy / banned terms

- `vocab/data/policy_terms.json`
- 共有先:
  - [`core/semantic_policy.py`](./core/semantic_policy.py)
  - [`nodes_prompt_cleaner.py`](./nodes_prompt_cleaner.py)
  - [`asset_validator.py`](./asset_validator.py)

## リポジトリ構成

ランタイムの入口は次です。

- [`__init__.py`](./__init__.py)
- [`nodes_context.py`](./nodes_context.py)
- [`nodes_prompt_cleaner.py`](./nodes_prompt_cleaner.py)

主要ディレクトリ:

- `core/`: schema, codec, context 操作, semantic policy
- `pipeline/`: source, scene, clothing, location, mood, garnish, prompt orchestration
- `vocab/`: 語彙ローダーと JSON データ
- `assets/`: Python テスト、baseline、測定、検証スクリプト
- `tools/`: workflow / data / audit 系ユーティリティ
- `verification/`: frontend / browser round-trip 検証

詳しくは以下を参照してください。

- [`REPO_STRUCTURE.md`](./REPO_STRUCTURE.md)
- [`CURRENT_STATUS.md`](./CURRENT_STATUS.md)
- [`EXPANSION_GUIDE.md`](./EXPANSION_GUIDE.md)
- [`docs/variation_expansion/README.md`](./docs/variation_expansion/README.md)
- [`assets/ARCHITECTURE.md`](./assets/ARCHITECTURE.md)
- [`docs/context_refactor/README.md`](./docs/context_refactor/README.md)
- [`codex_refactor_spec_ja.md`](./codex_refactor_spec_ja.md)

## バリエーション規模

`2026-05-08` 時点で `python assets/calc_variations.py --json` を実行した値です。

- unique subjects: `120`
- unique locations: `91`
- base variations: `105,612`
- actions per location: `min 12 / median 16 / mean 15.6 / max 20`
- missing action pools: `0`
- mood keys: `9`
- unique mood tags: `172`
- unique micro actions: `280`
- unique background context tags: `835`
- semantic units: `1,287`
- semantic garnish universe: `11,583`
- theoretical max: `1,223,303,796`

camera / effect 系は semantic-only ランタイムでは active variation に含めません。
監査用の legacy-disabled 指標として `camera_configs=120`, `effect_tags=22` は残しています。

この数値は語彙データ更新で変わるため、必要なら再計測してください。

直近の拡張では、100k target planning、P10 compatibility taxonomy expansion、P11 action authoring refactor を実施し、base variations を `105,612` まで増やしました。
100k stabilization gate の主要検証も通過済みです。
詳細と実績差分は [`docs/variation_expansion/progress.md`](./docs/variation_expansion/progress.md) を参照してください。

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
python tools/check_variation_scope.py
python tools/check_widgets_values.py
```

`python tools/build_compatibility_review.py --check` は scoped CSV 再生成の差分確認用です。
現状は `ERROR: []`, `WARNING: []` が期待値です。

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
- `vocab/source/action_pools/*.json`: action pool の location 別 authoring source
- `vocab/source/action_pools/_shared_families.json`: action pool の共有 authoring family
- `vocab/data/background_packs.json`: location pack 定義
- `vocab/data/clothing_packs.json`: clothing pack 定義
- `vocab/data/garnish_base_vocab.json`
- `vocab/data/garnish_micro_actions.json`

asset 編集後は `asset_validator.py` と該当テストを必ず確認してください。

variation 拡張時は次も確認してください。

- `python tools/validate_prompt_data.py`
- `python tools/plan_variation_target.py --target 100000`
- `python assets/calc_variations.py --json`
- `python tools/check_variation_scope.py`
- `python tools/build_compatibility_review.py --check`
- `python tools/build_action_pools.py --check`

## 注意事項

- 同梱語彙は作者用途寄りの初期セットです。必要に応じて JSON 資産を編集してください
- 生成結果の最終確認と利用判断は利用者側で行ってください
- README は current active surface を基準にしています。退役済みフローは `docs/context_refactor/archive/` や `tools/archive/` を参照してください

## ライセンス

Apache License 2.0。詳細は [`LICENSE`](./LICENSE) を参照してください。
