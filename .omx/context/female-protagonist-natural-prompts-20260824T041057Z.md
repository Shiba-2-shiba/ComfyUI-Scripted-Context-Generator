# Context Snapshot: Female Protagonist Natural Prompts

## Task statement

女性を主役とし、内容に一貫性があり、かつバリエーションに富んだ自然言語プロンプトを生成するための、今後の修正対象と段階的リファクタリング計画を提案する。

## Desired outcome

- 単一の女性主人公が各生成段階を通して保持される。
- character / clothing / location / action / mood / garnish が互いに矛盾しない。
- 最終出力がタグ列ではなく、冗長性の少ない自然な英語文になる。
- seed 再現性を維持したまま、語彙・構文・シーンの多様性を測定できる。
- ComfyUI の公開 node I/O、workflow round-trip、既存 context JSON を壊さない。

## Known facts and evidence

- 公開面は `Context*` nodes と `PromptCleaner`。transport は `context_json: STRING`。
- `PromptContext` は top-level fields、`meta`、自由形式 `extras`、無制限の `history` を持つ。
- `GenerationState` は `extras` を型付きの character / clothing / location / fragments に投影し、再び `extras` patch に戻す。
- scene、action、clothing、location、mood、garnish は seed 派生乱数と履歴ベース反復抑制を使う。
- Semantic EPIG は action、object relation、location、clothing、personality の各 domain で active。
- subject-centric emotion/garnish と solo-safety の既存設計・テストがある。
- runtime action pool は authoring source から生成され、variation sizing は別の scope / CSV 契約を持つ。
- 2026-08-24 の読み取り専用検証で Python unittest 394件、prompt data、full flow、widget validation、compatibility CSV check、action pool sync がすべて成功。
- JavaScript UI実装はなく、frontend互換性は workflow fixture と外部 ComfyUI frontend / browser test で確認する構成。

## Constraints

- behavior lock first。
- 公開 `Context*` input/output、widget順序、hidden legacy argsを初期フェーズでは変更しない。
- `context_version` と旧payloadの読み込み互換を維持する。
- seed determinism と履歴ベース反復抑制を維持する。
- semantic-only policyを維持し、camera / quality / art-styleを再導入しない。
- source JSONと生成runtime JSONの二重管理契約を破らない。
- 新規依存は導入しない。

## Unknowns

- 外部利用者が互換facadeや未文書化extras keyを直接利用している範囲。
- 「女性」の年齢帯、人数、語調を将来UI設定として公開する必要があるか。
- 人手評価で許容される文体、文長、叙述密度の具体的基準。
- 大規模sampleでの現行 contradiction / repetition / naturalness baseline。

## Likely touchpoints

- `core/schema.py`
- `core/context_state.py`
- `core/context_ops.py`
- `core/solo_safety.py`
- `pipeline/context_pipeline.py`
- `pipeline/action_generator.py`
- `pipeline/action_parser.py`
- `pipeline/action_renderer.py`
- `pipeline/prompt_orchestrator.py`
- `prompt_renderer.py`
- `vocab/garnish/logic.py`
- `character_service.py`
- `location_service.py`
- `vocab/data/character_profiles.json`
- `vocab/data/scene_compatibility.json`
- `vocab/data/*semantic*.json`
- `vocab/source/action_pools/*.json`
- `tools/audit_*.py`
- `assets/test_*.py`
- `verification/frontend/*`
- `verification/browser/*`
