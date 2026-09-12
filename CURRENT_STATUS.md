# Current Status

Last verified: 2026-09-06 (F0 baseline: counts, validators, full flow, 40 focused tests)
Candidate development verified: 2026-09-09 (N2.7-R4.2 candidate07)
Source storage verified: 2026-09-10 (candidate04-07 committed as ordinary source; main runtime unchanged)

このブランチ `refactor/realizer-v2` はR43-00〜10の開発・条件付き引き継ぎを完了しました。architecture／developmentは **PASS**、正式評価への実行引き継ぎ・採用は **BLOCKED** です。
V150 stable は `main` に保持し、正式採用は **BLOCKED** のままです。
以下の「現行生成」「未反映」は stable `main` に対する過去の検証記録です。
開発と検証の入口は [development_branch.md](docs/diversity_refactor/development_branch.md) を参照してください。

2026-09-12: [R4.3実装計画](docs/diversity_refactor/r43_implementation_plan.md) の
R43-08で共通Action文法と所有関係の証明を追加し、通常v2適用が9→10/512件へ増えました。
既存9成功例と残る502 fallbackは本文・context・debugを保持し、上流入力とcore/frameも一致しています。
新規1件はbook/pagesとeyesの所有関係、原文要素、Scene文に付く時刻を検証しています。
全6構文の実入力proof／強制描画は維持しています（計15 seed-family行）。
R43-09のportableなintake CLIで、重点492件・1,990 subtests、回帰87件・33 subtests、
validator/full-flow・paired512・root/package再現性をまとめて検証しました。
独立したクリーンなsourceコピーでも全intakeが通り、判定JSONは同一bytesです。
skip・除外・xfail・collection／setup／teardownエラーは別集計し、すべて0件です。
通常選択での実行構文は3種類のため、適用範囲には改善余地があります。
64/512・通常5構文という開発上の目安は未達で、正式評価は自動実行していません。
R43-10でoriginal V150の封印済み1120ファイルと過去のgate/reference/paired2048/fixed80証拠を照合し、
完全なA1.6条件とsource/configの比較可能性を整理しました。stable mainとは別の正式baselineです。
candidateの正式評価・品質比較はNOT_RUN、正式評価用freezeも未作成です。N2.8/D3は未着手。
次は残るfallbackのAction+Scene交差に基づく適用範囲改善です。[引き継ぎ](docs/diversity_refactor/r43_handoff.md)を参照してください。

このファイルは、毎回全スクリプトを読み直さずに現在地を把握するための短い入口です。
詳細な構造は `REPO_STRUCTURE.md`、設計背景は `assets/ARCHITECTURE.md` と
`docs/context_refactor/README.md` を参照してください。
現在の方針は [`docs/diversity_refactor/spec.md`](./docs/diversity_refactor/spec.md)、
作業と証拠は [`tasks.md`](./docs/diversity_refactor/tasks.md) / [`progress.md`](./docs/diversity_refactor/progress.md) を正本とします。
V150 の semantic-base を固定し、Effective Diversity Audit → Natural Language Realizer v2 → Deterministic Diversity Scheduler の順に進めます。
V150 固定と Audit CLI（A1.4）を完了しました。128 seed smoke の通常実行・再実行・参照集合再利用は同一bytesで、関連134テストも成功しています。
正式なgate基準計測（A1.5）を完了しました。固定8,192件の参照集合に対する2,048件測定と再実行が同一bytesです。
core署名1,963種類、frame署名2,042種類。詳細・欠損・hashは [`基準計測`](./docs/diversity_refactor/progress.md#6-effective-diversity-baseline) に記録しています。
目標／非回帰閾値（A1.6）を固定し、Phase A の監査・基準値・受入条件を整えました。
Realizer v2契約テスト（N2.1）を追加し、比較用sourceを保存しました。
6種類の候補構文メタデータと厳格な検証（N2.2）を追加しました。128 seedの出力・指標は従来と同一です。
安全な対応構文だけを残すeligibility engine（N2.3）を実装しました。現行生成には未接続で、128 seedの出力・指標は従来と同一です。
必要な6構文とBuilder decision/debug（N2.6）が実装済みです。関連188件はすべて成功し、期待される失敗は0件です。
監査は128件すべての構文をBuilder metadataから読み、現行workflow本文・指標は不変です。
初回Realizer v2候補（N2.7）は **REJECTED** です。実workflowの2,048件すべてがv1へfallbackし、v2適用0件・構文改善なしでした。
意味・本文と品質の自動保護条件は維持しましたが、6構文の観測・entropy目標が未達です。N2.8の採用は保留します。
R1〜R3を経て、N2.7-R4（candidate05）でproducerのslot追跡・runtime-only構造証拠・限定的な従属句文法を実装しました。
採用判定は **BLOCKED**。512件のaction replayは完全一致し、主action文法の認識は旧8件に対し新28件ですが、
実v2適用は5/512・観測4構文のままです。scene・衣装等との交差と修飾先の証明が不足しています。
120テスト・1,807 subtestsとvalidator/full-flowが成功し、既存5例・fallback・意味・上流contextを維持しました。
正式8192参照/2048 gate/fixed80品質比較は未実施です。現行生成へは反映していません。
続くN2.7-R4.1（candidate06）では衣装・sceneの生成元と修飾先を検証し、実v2適用を**5→7/512**へ増やしました。
新しい実例190/482はaction原文を維持して別文構文へ変換されます。場所の重複が不明な判定はNoneのままです。
139重点テスト・1,862 subtests、29関連回帰が成功し、既存5例・505 fallback・意味・上流contextは一致しました。
観測構文は4種類のため正式評価・main反映は未実施で、採用は引き続き**BLOCKED**です。
N2.7-R4.2（candidate07）では身体部位の付帯句と、テンプレート由来のroomを保持する独立文を実装し、
実v2適用を**7→9/512**へ増やしました。新規88/234が動作し、既存7例・503 fallbackと意味・上流contextは一致しています。
複合動詞のsemantic main verbと文頭動詞を別々に検証し、galleryの修飾先も明示しました。
160重点テスト・1,890 subtestsと29関連回帰が成功しています。観測4構文のため採用は引き続き**BLOCKED**です。
次は残る句全体・構文配置の証拠を拡大します。正式評価・main反映・N2.8は保留です。
閾値・適用段階・品質条件は [`受入条件`](./docs/diversity_refactor/progress.md#7-locked-target--guard-metrics) を参照してください。
監査コマンド: `python tools/audit_effective_diversity.py --profile smoke --output assets/results/effective_diversity/smoke.json`。
V250/V350/V500 は **DEFERRED while effective-diversity refactor is active**。
数量拡張の履歴は `docs/variation_expansion/README.md`、延期した将来計画は
`docs/variation_expansion/500k_loop_plan.md`、再開時の手順は `EXPANSION_GUIDE.md` に保持します。
現在の variation sizing 境界は `vocab/data/variation_scope.json` に固定されています。
書類整理方針は `docs/documentation_cleanup_plan.md` を参照してください。
repository cleanup の直近リファクタは `docs/repository_cleanup/` に仕様・進捗・タスクがあります。

## Runtime Surface

現行の ComfyUI 公開面は context-first 構成です。

- Active node families: `Context*` nodes and `PromptCleaner`
- Entry points: `__init__.py`, `nodes_context.py`, `nodes_prompt_cleaner.py`
- Transport: `context_json: STRING`
- Main runtime logic: `pipeline/`
- Schema / context operations / policy: `core/`
- Data source of truth: `vocab/data/`
- Action authoring source: `vocab/source/action_pools/` with shared families in `_shared_families.json`
- Semantic EPIG config: `vocab/data/semantic_epig_config.json`

Retired / compatibility state:

- bridge / legacy node families are retired
- `pipeline/content_pipeline.py` is a compatibility facade only
- `meta.style` is legacy read-only metadata and is ignored by prompt generation
- `ContextGarnish.include_camera` is hidden legacy input and no-op at runtime

## Semantic-Only Policy

Prompt output is intended to describe semantic content only:

- subject / role / character profile
- clothing theme and clothing details
- location / environment context
- action / state / small event
- mood nuance / staging / garnish

Prompt output should not depend on these domains:

- art style
- quality terms
- camera / framing / lens / DoF
- body type / body-shape emphasis
- render effects

Shared policy source:

- `vocab/data/policy_terms.json`
- `core/semantic_policy.py`
- `nodes_prompt_cleaner.py`
- `asset_validator.py`

## Semantic EPIG State

All semantic EPIG domains are active through `vocab/data/semantic_epig_config.json`.
The rollout keeps the public `Context*` node I/O unchanged and records rankings
under `DebugInfo.decision.semantic_epig`.

Active domains:

- `action`: semantic score adjusts action slot weights
- `object_relation`: object-use relation slots are added without overwriting existing slots
- `location_scene`: scene-axis score adjusts location segment weights
- `clothing_tpo`: final candidate penalty combines repeat and semantic penalties
- `personality_behavior`: semantic descriptor ranking selects personality garnish with inline fallback

Implementation/audit docs:

- canonical index and change gate: `docs/semantic_epig/README.md`
- rollout docs: `docs/semantic_epig/progress.md`（完了履歴）
- R0-R7 refactor docs: `docs/semantic_epig/refactor_spec.md`,
  `docs/semantic_epig/refactor_progress.md`,
  `docs/semantic_epig/refactor_tasks.md`（完了履歴）

Current refactor state:

- R1-R7 are complete.
- Builders were split into action parser / relation binder / renderer, location policy / selector, and clothing candidate renderer / selector.
- Relation-key-specific action descriptor matching has dedicated regression coverage.
- Future changes start a new loop-engineering experiment; completed task boards are not reopened.

## Current Metrics

Command:

```bash
python assets/calc_variations.py --json
```

Current semantic-only summary:

- unique subjects: `135`
- unique locations: `109`
- compatibility review rows: `8,227`
- base variations: `150,184`
- actions per location: `min 12 / median 16 / mean 16.33 / max 20`
- missing action pools: `0`
- runtime action pools: `115`
- split action pool source files: `115` location files + `_manifest.json` + `_shared_families.json`
- mood keys: `9`
- unique mood tags: `172`
- unique micro actions: `280`
- unique background context tags: `1,028`
- semantic units: `1,480`
- semantic garnish universe: `13,320`
- theoretical max: `2,000,450,880` (not measured effective diversity)

Legacy-disabled vocabulary still present for audit visibility:

- camera configs: `120`
- effect tags: `22`

These legacy-disabled counts are not part of active output-space sizing.

Interpretation:

- `base variations` is calculated from `assets/compatibility_review.csv`
  rows and dedicated action counts in `vocab/data/action_pools.json`.
- Current base sizing is frozen at `135 subjects × 109 locations` within
  `vocab/data/variation_scope.json`, producing `150,184` counted base
  variations.
- The split files in `vocab/source/action_pools/` are for editing/review only;
  runtime still reads the generated flat `vocab/data/action_pools.json`.
- `vocab/source/action_pools/_shared_families.json` is the shared authoring
  layer for repeated semantic action patterns. Do not hand-edit the runtime
  action pool for normal authoring.

## Verification Snapshot

Current F0 baseline (2026-09-06):

- main HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`.
- Exact sizing above; missing action pools: `0`.
- `validate_prompt_data`, `check_variation_scope`, `build_action_pools --check`,
  `build_compatibility_review --check`: `ERROR: []`, `WARNING: []`.
- `verify_full_flow`: `OK`; focused variation/context/workflow/snapshot/determinism tests: `40 OK`.
- Commands, receipt SHA256 and protected-file manifest: [`F0.2 receipt`](./docs/diversity_refactor/progress.md#5-baseline-command-receipt).
- Previous release frontend/browser/blind-review evidence remains historical; F0 changes no runtime prompt surface.

### Historical verification snapshot (2026-08-31, pre-V150)

The following commands/results describe the earlier 100k baseline, not the current wave:

```bash
python -m unittest assets.test_calc_variations assets.test_variation_target_planner assets.test_variation_scope assets.test_build_compatibility_review assets.test_build_action_pools
python -m unittest assets.test_context_nodes assets.test_workflow_samples assets.test_prompt_snapshots assets.test_context_pipeline assets.test_context_state_adapter assets.test_determinism
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python assets/calc_variations.py --json
python tools/check_variation_scope.py
python tools/build_compatibility_review.py --check
python tools/build_action_pools.py --check
python tools/plan_variation_target.py --target 500000
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Results:

- variation regression tests: `15 tests OK`
- context/workflow/prompt tests: `28 tests OK`
- full flow: `OK`
- prompt data validator: `ERROR: []`, `WARNING: []`
- variation metrics: base variations `103,212`, missing action pools `0`
- variation scope / compatibility generation / action pool checks: `ERROR: []`, `WARNING: []`
- target planner: the `500000` baseline probe records the current `103,212`
  surface and shows that new mixed-scenario modeling is required
- asset validator: `0` issues
- workflow widget validation: `OK`

Notes:

- `assets/results/` is ignored by git and is reserved for generated audit outputs.
- Normal unittest no longer depends on ignored `assets/results/` JSON artifacts.
- Long audit artifacts can be regenerated explicitly with:

```bash
python tools/audit_prompt_repetition.py --samples-per-row 8 --output assets/results/prompt_repetition_active_source_8.json --enforce-thresholds
python tools/audit_template_diversity.py --seed-count 32 --seed-start 0 --output assets/results/template_diversity_32.json --enforce-thresholds
```

## Test Script State

Standalone `test_*.py` scripts have been normalized into `unittest` tests except:

- `assets/test_bootstrap.py`: helper module, not a test case

Recent cleanup:

- `assets/test_scene_variator.py` now validates current scene/action behavior through assertions
- `assets/test_vocab_lint.py` now uses unittest assertions instead of print-only checks
- `assets/test_char_profile_nl.py` now checks expected profile text programmatically
- `assets/test_calc_variations.py` locks semantic-only metric shape
- audit-style unittest coverage now uses unit-sized inputs; long prompt/template/repetition audits remain explicit `tools/audit_*.py` commands
- compatibility facades are guarded by `assets/test_compatibility_boundaries.py`
- empty `vocab/*/test.md` placeholders and the tracked generated `assets/results` baseline were removed
- `pipeline/action_profiles.py` holds expansion-oriented daily-life/location action profile tables

Historical expansion (pre-V150):

- 10 daily-life locations were promoted into base variation sizing
- 8 remaining daily-life locations were promoted in P8
- P9 added read-only 100k target planning
- P10 added mid-level compatibility tags, promoted 120 subjects / 91 locations,
  and added missing daily-life action pools
- P11 added shared action families and raised action depth to the 12/16/20 tier
- base variations increased from `11,916` to `105,612`
- Later variation restrictions reduced the active counted boundary to 120 subjects / 90 locations.
- At that stage, `vocab/data/variation_scope.json` recorded the 120 subjects / 90 locations boundary
- `tools/build_compatibility_review.py --check` now verifies scoped CSV regeneration with `ERROR: []`
- `tools/build_action_pools.py --check` now verifies split action-pool source
  rebuilds the runtime JSON exactly

Historical P10–P12 results:

- P10 result: `unique subjects 58 -> 120`, `unique locations 76 -> 91`,
  rows `1,637 -> 5,926`, base variations `15,610 -> 52,121`.
- P11 result: action depth `min 12 / median 16 / mean 15.6 / max 20`,
  base variations `52,121 -> 105,612`.
- P12 stabilization gate commands have passed at the 100k scale.
- P12 restricted sizing was `103,212`; V150 subsequently reached `150,184`.
- The historical `500,000` roadmap remains in `docs/variation_expansion/500k_loop_plan.md` as deferred work.
- Current work follows `docs/diversity_refactor/` and preserves the accepted
  prompt-quality target/guard baseline from `docs/prompt_quality/`.

## Refactor Risk Map

Lower-risk cleanup candidates:

- documentation/path cleanup
- verification command consolidation
- small test readability improvements
- reducing print noise in isolated smoke tests

Medium-risk cleanup candidates:

- splitting `pipeline/action_generator.py`
- splitting `prompt_renderer.py`
- further relocation of Python tests out of `assets/` if the import churn is justified

Higher-risk areas:

- `Context*` public input/output specs
- `PromptContext` JSON compatibility
- location / clothing / character resolver semantics
- seed determinism and history-based repetition control
- ComfyUI workflow widget round-trip behavior

## Recommended Next Checks

Before changing runtime generation logic:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
```

Before changing workflow node specs:

```bash
python -m unittest assets.test_context_nodes assets.test_workflow_samples
python tools/check_widgets_values.py
```

Before changing vocabulary assets:

```bash
python -c "from asset_validator import validate_assets; print(validate_assets())"
python tools/validate_prompt_data.py
python assets/calc_variations.py --json
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
```

Optional before/after expansion comparison:

```bash
python tools/report_expansion_delta.py assets/results/variation_before.json assets/results/variation_after.json --enforce
```

For a future quantity-expansion wave only (currently deferred):

```bash
python -m unittest assets.test_data_consistency assets.test_character_resolution assets.test_location_resolution assets.test_action_generator assets.test_calc_variations
python tools/validate_prompt_data.py
python tools/plan_variation_target.py --target 500000
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python assets/calc_variations.py --json
```

Scoped CSV regeneration check:

```bash
python tools/build_compatibility_review.py --check
```

Current expected result is `ERROR: []` and `WARNING: []`.
