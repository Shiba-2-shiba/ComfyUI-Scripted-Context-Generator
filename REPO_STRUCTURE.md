# Repository Structure

このメモは、M5 まで完了した現行リポジトリを次の2軸で見るためのものです。

- 実際に ComfyUI カスタムノードとして稼働する部分
- スクリプトや workflow の検証に使う部分

## 1. 実際にカスタムノードとして稼働する部分

`__init__.py` から公開されているのは、現在 `nodes_context.py` と `nodes_prompt_cleaner.py` の 2 系統です。  
その下で `core/`、`pipeline/`、service/helper モジュール、`vocab/`、各種 JSON データがランタイムとして使われます。

```text
.
├── __init__.py                              # ComfyUI 読み込み用エントリポイント
├── nodes_context.py                         # Context* ノード群の公開面
├── nodes_prompt_cleaner.py                  # PromptCleaner ノード
├── registry.py                              # location / clothing / action 関連の互換 facade
├── location_service.py                      # location alias / canonical key 解決
├── character_service.py                     # named profile / compatibility archetype 統合解決
├── history_service.py                       # PromptContext.history 参照 helper
├── prompt_renderer.py                       # 最終 prompt clause 組み立て
├── asset_validator.py                       # policy / asset 不整合の静的検査
├── core/
│   ├── schema.py                            # PromptContext schema
│   ├── context_codec.py                     # context_json の入出力
│   ├── context_ops.py                       # patch / history / note / warning 操作
│   ├── context_state.py                     # PromptContext -> internal typed state adapter
│   └── semantic_policy.py                   # 文字列 sanitization / policy
├── pipeline/
│   ├── source_pipeline.py                   # prompts / json -> context
│   ├── character_profile_pipeline.py        # character profile 適用
│   ├── context_pipeline.py                  # scene variation / garnish
│   ├── clothing_builder.py                  # clothing 展開本体
│   ├── location_builder.py                  # location 展開本体
│   ├── mood_builder.py                      # mood 展開本体
│   ├── prompt_orchestrator.py               # prompt builder / template orchestration 本体
│   ├── content_pipeline.py                  # extracted modules への互換 facade。内部実装の default import 先ではない
│   └── action_generator.py                  # action 選択ロジック
├── vocab/
│   ├── __init__.py
│   ├── loader.py                            # 語彙データ読込
│   ├── loc_tag_builder.py                   # location alias / tag map 構築
│   ├── policy.py                            # 語彙ルール
│   ├── seed_utils.py                        # seed mixing
│   ├── templates_intro.txt                  # prompt part テンプレ
│   ├── templates_body.txt
│   ├── templates_end.txt
│   ├── background/
│   │   ├── __init__.py
│   │   ├── concept_packs.py                 # 背景 pack 定義
│   │   ├── defaults.py                      # 背景 default 定義
│   │   └── loc_tag_map.py                   # 背景 location map
│   ├── clothing/
│   │   ├── __init__.py
│   │   ├── concept_packs.py                 # 衣装 pack 定義
│   │   ├── constants.py                     # 衣装関連定数
│   │   └── theme_map.py                     # clothing theme map
│   ├── garnish/
│   │   ├── __init__.py
│   │   ├── base_vocab.py                    # garnish 基本語彙
│   │   ├── logic.py                         # garnish 生成ロジック
│   │   ├── micro_actions.py                 # micro action 語彙
│   │   └── utils.py                         # garnish utility
│   └── data/
│       ├── action_pools.json
│       ├── background_alias_overrides.json
│       ├── background_defaults.json
│       ├── background_loc_tag_map.json      # legacy fallback location map
│       ├── background_packs.json
│       ├── character_profiles.json
│       ├── clothing_constants.json
│       ├── clothing_packs.json
│       ├── clothing_theme_map.json
│       ├── garnish_base_vocab.json
│       ├── garnish_exclusive_groups.json
│       ├── garnish_micro_actions.json
│       ├── loc_aliases.json                 # deprecated placeholder。runtime は参照しない
│       ├── loc_aliases_canonical.json       # canonical normalization layer
│       ├── loc_aliases_legacy.json          # legacy workflow compatibility layer
│       ├── loc_aliases_fallback.json        # semantic fallback layer
│       ├── object_concentration_policy.json
│       ├── policy_terms.json                # banned-domain canonical source
│       ├── scene_axis.json
│       ├── scene_compatibility.json
│       └── template_catalog.json
├── background_vocab.py                      # vocab/background の互換 facade
├── clothing_vocab.py                        # vocab/clothing の互換 facade
├── improved_pose_emotion_vocab.py           # vocab/garnish の互換 facade
├── prompts.jsonl                            # ContextSource の入力ソース
├── templates.txt                            # PromptBuilder 系テンプレ資産
├── mood_map.json                            # mood 展開データ
└── ComfyUI-workflow-context.json            # 現行 primary workflow サンプル
```

## 2. スクリプトの検証用の部分

workflow の widget 整合、Python 側のユニットテスト、validator、フロントエンド round-trip、GUI round-trip をここで検証します。  
active / recommended な workflow sample は `ComfyUI-workflow-context.json` だけで、現行の `Context*` node spec に合わせて維持します。

```text
.
├── workflow_widget_validation.py            # workflow widget 値の検証ロジック
├── workflow_class_map.py                    # workflow 内 node type -> class 対応
├── workflow_samples.py                      # workflow sample manifest loader
├── workflow_samples.json                    # active workflow sample manifest
├── assets/
│   ├── ARCHITECTURE.md
│   ├── test_context_state_adapter.py        # internal typed state adapter 回帰
│   ├── test_location_resolution.py          # location resolver 回帰
│   ├── test_character_resolution.py         # character resolver 回帰
│   ├── test_prompt_renderer.py              # prompt renderer 回帰
│   ├── test_deprecated_behavior.py          # legacy surface / no-op 回帰
│   ├── test_asset_validator.py              # asset validator 回帰
│   ├── test_context_content_pipeline.py     # content pipeline 回帰
│   ├── test_context_pipeline.py             # scene / garnish 回帰
│   ├── test_context_nodes.py                # public Context* node 回帰
│   ├── test_character_profile_pipeline.py   # character profile pipeline 回帰
│   ├── test_prompt_snapshots.py             # prompt snapshot / baseline 回帰
│   ├── test_semantic_policy.py              # banned-domain 回帰
│   ├── test_registry.py                     # registry facade 回帰
│   ├── test_data_consistency.py             # vocab/data 整合確認
│   ├── test_workflow_samples.py             # active workflow sample の spec / round-trip 回帰
│   ├── test_personality_garnish.py          # garnish personality 連動回帰
│   ├── test_*.py                            # そのほか Python unittest 群
│   ├── verify_*.py                          # 個別検証スクリプト
│   ├── validate_compatibility.py            # registry 経由のデータ互換性チェック
│   ├── generate_baseline.py                 # baseline 生成
│   ├── generate_baseline_full.py
│   ├── evaluate_kpi.py                      # KPI 評価
│   ├── calc_variations.py                   # バリエーション規模計測
│   ├── fixtures/                            # テスト入力
│   ├── results/                             # 生成結果の置き場
│   └── archive/                             # 過去の検証資産
├── tools/
│   ├── check_widgets_values.py              # sample workflow の widget 検証
│   ├── verify_full_flow.py                  # end-to-end 検証
│   ├── validate_prompt_data.py              # prompt data 整合性チェック
│   ├── audit_action_diversity.py            # action 多様性監査
│   ├── audit_repetition_guard.py            # repetition guard 監査
│   ├── audit_template_diversity.py          # template 多様性監査
│   ├── run_bias_audit.py                    # bias 監査
│   ├── measure_baseline.py                  # baseline 計測
│   ├── analyze_context_workflow_diversity.py
│   ├── run_frontend_workflow_validation.ps1 # frontend Vitest 実行
│   ├── run_custom_workflow_roundtrip.ps1    # browser / GUI roundtrip 実行
│   ├── sync_upstream_verification_assets.ps1
│   └── archive/                             # 退役済み補助ツール
├── verification/
│   ├── frontend/
│   │   ├── customNodeWorkflowCompatibility.test.ts
│   │   ├── customNodeWorkflowRoundtrip.test.ts
│   │   └── vitest.custom-node.config.mts
│   └── browser/
│       ├── customWorkflowRoundtrip.spec.ts
│       └── playwright.custom-node.config.mts
├── ComfyUI/                                 # GUI 側検証用のローカル checkout
└── ComfyUI_frontend/                        # frontend 側検証用のローカル checkout
```

## 3. 補足

今回の分類では、次は主対象から外しています。

- `docs/`: 設計メモ、移行資料
- `agent/`: 作業ログやエージェント補助資料
- `README.md` などの説明文書
- `simple_template_debug.log` などの生成ログ

ランタイムの入口だけを追う場合は、まず `__init__.py` -> `nodes_context.py` / `nodes_prompt_cleaner.py` -> `pipeline/` -> `core/` / service modules / `vocab/` の順で見ると把握しやすいです。

source of truth は次で見るとズレにくいです。

- character: `vocab/data/character_profiles.json` + `vocab/data/scene_compatibility.json` を `character_service.py` で統合
- location: `vocab/data/background_packs.json` の pack key / aliases と `vocab/data/background_alias_overrides.json` が主経路。`loc_aliases_canonical.json` / `loc_aliases_legacy.json` / `loc_aliases_fallback.json` を `location_service.py` が順序付きで重ね、`background_loc_tag_map.json` は legacy fallback。`loc_aliases.json` は inert placeholder で、runtime source ではない
- clothing: `vocab/data/clothing_theme_map.json` と `vocab/data/clothing_packs.json`
- banned terms: `vocab/data/policy_terms.json` を `core/semantic_policy.py` / `nodes_prompt_cleaner.py` / `asset_validator.py` が共有

refactor 完了後も、意図的に残している compatibility surface があります。

- `meta.style`: legacy read-only metadata。prompt 生成では無視し、`ContextInspector` / context payload の `notes` で可視化
- `ContextGarnish.include_camera`: public UI からは削除済み。hidden legacy arg としてのみ残り no-op
- `pipeline.content_pipeline`: 旧 import 先のための facade。実装本体ではない。repo-owned で意図的に残している caller は `assets/test_deprecated_behavior.py` のみ

asset を編集したら、最低限 `asset_validator.py` と該当 `assets/test_*.py` を一緒に見る前提です。
