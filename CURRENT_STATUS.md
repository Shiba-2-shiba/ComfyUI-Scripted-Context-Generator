# Current Status

Last verified: 2026-06-19

このファイルは、毎回全スクリプトを読み直さずに現在地を把握するための短い入口です。
詳細な構造は `REPO_STRUCTURE.md`、設計背景は `assets/ARCHITECTURE.md` と
`docs/context_refactor/README.md` を参照してください。
subject / location / base variations を増やす作業は `EXPANSION_GUIDE.md` を先に参照してください。
日常系 location / action pool の拡張作業は `docs/variation_expansion/README.md` に計画と進捗があります。
100k base variations gate は通過済みです。次の拡張計画対象は 500k に向けた subject / location / action-depth の再設計です。
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

- rollout docs: `docs/semantic_epig/progress.md`
- refactor docs: `docs/semantic_epig/refactor_spec.md`, `docs/semantic_epig/refactor_progress.md`, `docs/semantic_epig/refactor_tasks.md`

Current refactor state:

- R1-R7 are complete.
- Builders were split into action parser / relation binder / renderer, location policy / selector, and clothing candidate renderer / selector.
- Remaining follow-up: add a relation-key-specific action descriptor fixture/test.

## Current Metrics

Command:

```bash
python assets/calc_variations.py --json
```

Current semantic-only summary:

- unique subjects: `120`
- unique locations: `90`
- compatibility review rows: `5,806`
- base variations: `103,212`
- actions per location: `min 12 / median 16 / mean 15.6 / max 20`
- missing action pools: `0`
- runtime action pools: `96`
- split action pool source files: `96` location files + `_manifest.json` + `_shared_families.json`
- mood keys: `9`
- unique mood tags: `172`
- unique micro actions: `280`
- unique background context tags: `835`
- semantic units: `1,287`
- semantic garnish universe: `11,583`
- theoretical max: `1,223,303,796`

Legacy-disabled vocabulary still present for audit visibility:

- camera configs: `120`
- effect tags: `22`

These legacy-disabled counts are not part of active output-space sizing.

Interpretation:

- `base variations` is calculated from `assets/compatibility_review.csv`
  rows and dedicated action counts in `vocab/data/action_pools.json`.
- Current base sizing is stable at `120 subjects × 90 locations` within
  `vocab/data/variation_scope.json`, producing `103,212` counted base
  variations.
- The split files in `vocab/source/action_pools/` are for editing/review only;
  runtime still reads the generated flat `vocab/data/action_pools.json`.
- `vocab/source/action_pools/_shared_families.json` is the shared authoring
  layer for repeated semantic action patterns. Do not hand-edit the runtime
  action pool for normal authoring.

## Verification Snapshot

Last verified commands:

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
python tools/plan_variation_target.py --target 100000
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Results:

- variation regression tests: `15 tests OK`
- context/workflow/prompt tests: `28 tests OK`
- full flow: `OK`
- prompt data validator: `ERROR: []`, `WARNING: []`
- variation metrics: base variations `103,212`, missing action pools `0`
- variation scope / compatibility generation / action pool checks: `ERROR: []`, `WARNING: []`
- target planner: target `100000` still met at `103,212`
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

Recent expansion:

- 10 daily-life locations were promoted into base variation sizing
- 8 remaining daily-life locations were promoted in P8
- P9 added read-only 100k target planning
- P10 added mid-level compatibility tags, promoted 120 subjects / 91 locations,
  and added missing daily-life action pools
- P11 added shared action families and raised action depth to the 12/16/20 tier
- base variations increased from `11,916` to `105,612`
- Later variation restrictions reduced the active counted boundary to 120 subjects / 90 locations.
- `vocab/data/variation_scope.json` now records the active 120 subjects / 90 locations boundary
- `tools/build_compatibility_review.py --check` now verifies scoped CSV regeneration with `ERROR: []`
- `tools/build_action_pools.py --check` now verifies split action-pool source
  rebuilds the runtime JSON exactly

Current expansion state:

- P10 result: `unique subjects 58 -> 120`, `unique locations 76 -> 91`,
  rows `1,637 -> 5,926`, base variations `15,610 -> 52,121`.
- P11 result: action depth `min 12 / median 16 / mean 15.6 / max 20`,
  base variations `52,121 -> 105,612`.
- P12 stabilization gate commands have passed at the 100k scale.
- Current restricted sizing remains above the 100k target at `103,212`.
- Next planning target: `500,000` base variations without making the 100k
  implementation noisy or repetitive.
- Detailed current plan: `docs/variation_expansion/base_variations_100k_plan.md`.

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

Before expanding subjects / locations / actions:

```bash
python -m unittest assets.test_data_consistency assets.test_character_resolution assets.test_location_resolution assets.test_action_generator assets.test_calc_variations
python tools/validate_prompt_data.py
python tools/plan_variation_target.py --target 100000
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python assets/calc_variations.py --json
```

Scoped CSV regeneration check:

```bash
python tools/build_compatibility_review.py --check
```

Current expected result is `ERROR: []` and `WARNING: []`.
