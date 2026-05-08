# Current Status

Last verified: 2026-05-08

このファイルは、毎回全スクリプトを読み直さずに現在地を把握するための短い入口です。
詳細な構造は `REPO_STRUCTURE.md`、設計背景は `assets/ARCHITECTURE.md` と
`docs/context_refactor/README.md` を参照してください。
subject / location / base variations を増やす作業は `EXPANSION_GUIDE.md` を先に参照してください。

## Runtime Surface

現行の ComfyUI 公開面は context-first 構成です。

- Active node families: `Context*` nodes and `PromptCleaner`
- Entry points: `__init__.py`, `nodes_context.py`, `nodes_prompt_cleaner.py`
- Transport: `context_json: STRING`
- Main runtime logic: `pipeline/`
- Schema / context operations / policy: `core/`
- Data source of truth: `vocab/data/`

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

## Current Metrics

Command:

```bash
python assets/calc_variations.py --json
```

Current semantic-only summary:

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

Legacy-disabled vocabulary still present for audit visibility:

- camera configs: `120`
- effect tags: `22`

These legacy-disabled counts are not part of active output-space sizing.

## Verification Snapshot

Last verified commands:

```bash
python -m unittest assets.test_scene_variator assets.test_vocab_lint assets.test_char_profile_nl assets.test_calc_variations
python -m unittest discover -s assets -p "test_*.py"
python -m unittest assets.test_context_nodes assets.test_workflow_samples
python tools/verify_full_flow.py
python tools/validate_prompt_data.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print('issues', len(issues))"
python tools/check_widgets_values.py
python -m py_compile assets/calc_variations.py assets/test_calc_variations.py assets/test_char_profile_nl.py assets/test_scene_variator.py assets/test_vocab_lint.py
```

Results:

- targeted unittest group: `14 tests OK`
- assets unittest discovery: `250 tests OK`
- context/workflow smoke tests: `12 tests OK`
- full flow: `OK`
- prompt data validator: `ERROR: []`, `WARNING: []`
- asset validator: `issues 0`
- workflow widget validation: `OK`
- compile check: `OK`

Notes:

- `assets/results/` is ignored by git. Some audit tests compare against generated baseline JSON files there.
- If those files are missing, regenerate them with:

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
- `pipeline/action_profiles.py` holds expansion-oriented daily-life/location action profile tables

## Refactor Risk Map

Lower-risk cleanup candidates:

- documentation/path cleanup
- verification command consolidation
- small test readability improvements
- reducing print noise in isolated smoke tests

Medium-risk cleanup candidates:

- splitting `pipeline/action_generator.py`
- splitting `prompt_renderer.py`
- tightening compatibility facade boundaries
- making generated audit baseline handling explicit in tests

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
```

Optional before/after expansion comparison:

```bash
python tools/report_expansion_delta.py assets/results/variation_before.json assets/results/variation_after.json --enforce
```

Before expanding subjects / locations / actions:

```bash
python -m unittest assets.test_data_consistency assets.test_character_resolution assets.test_location_resolution assets.test_action_generator assets.test_calc_variations
python tools/validate_prompt_data.py
python assets/calc_variations.py --json
```
