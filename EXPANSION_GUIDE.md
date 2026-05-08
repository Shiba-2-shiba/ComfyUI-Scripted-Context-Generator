# Expansion Guide

このガイドは、subject / location / base variations を増やす前に見る作業入口です。
目的は、語彙を増やしても resolver、validator、workflow 互換を崩さないことです。

## Expansion Goal

現在の主な拡張指標は次です。

- unique subjects
- unique locations
- base variations
- action coverage
- semantic-only prompt cleanliness

現在値は `CURRENT_STATUS.md` と次のコマンドで確認します。
日常系 location / action pool の具体的な拡張計画は `docs/variation_expansion/README.md` を参照します。

```bash
python assets/calc_variations.py --json
```

## Source Files

### Subject

Primary files:

- `vocab/data/character_profiles.json`
- `vocab/data/scene_compatibility.json`

Required connections:

- profile key / display name
- `default_costume` resolves through `vocab/data/clothing_theme_map.json`
- compatibility key exists in `scene_compatibility.characters`
- compatibility tags map to usable locations

Validation:

```bash
python -m unittest assets.test_character_resolution assets.test_data_consistency
python tools/validate_prompt_data.py
```

### Location

Primary files:

- `vocab/data/background_packs.json`
- `vocab/data/background_alias_overrides.json`
- `vocab/data/loc_aliases_canonical.json`
- `vocab/data/loc_aliases_legacy.json`
- `vocab/data/loc_aliases_fallback.json`
- `vocab/data/scene_compatibility.json`

Required connections:

- background pack key is canonical
- aliases resolve deterministically
- scene compatibility tag includes the location when it should be selectable
- location can generate an action through either a dedicated pool or compositional fallback

Validation:

```bash
python -m unittest assets.test_location_resolution assets.test_scene_variator assets.test_data_consistency
python tools/validate_prompt_data.py
```

### Action

Primary files:

- `vocab/data/action_pools.json`
- `vocab/data/scene_axis.json`
- `pipeline/action_profiles.py`
- `pipeline/action_generator.py`

Required connections:

- dedicated pool entries should parse into semantic slots
- locations without dedicated pools must still pass compositional fallback
- generated actions must stay semantic-only and avoid object overconcentration
- reusable daily-life and location-specific profile defaults should live in `pipeline/action_profiles.py`

Validation:

```bash
python -m unittest assets.test_action_generator assets.test_action_diversity_audit assets.test_repetition_guard_audit
python tools/validate_prompt_data.py
```

### Clothing

Primary files:

- `vocab/data/clothing_theme_map.json`
- `vocab/data/clothing_packs.json`

Required connections:

- theme aliases resolve through `resolve_clothing_theme`
- packs avoid body-shape and render-quality phrasing
- character `default_costume` values resolve

Validation:

```bash
python -m unittest assets.test_registry assets.test_asset_validator assets.test_vocab_lint
python -c "from asset_validator import validate_assets; print(validate_assets())"
```

## Expansion Workflow

1. Record current metrics:

```bash
python assets/calc_variations.py --json > assets/results/variation_before.json
```

2. Edit the smallest data surface that expresses the new variation.

3. Run the matching focused checks from the sections above.

4. Run the expansion validator:

```bash
python tools/validate_prompt_data.py
```

5. Compare variation metrics:

```bash
python assets/calc_variations.py --json > assets/results/variation_after.json
python tools/report_expansion_delta.py assets/results/variation_before.json assets/results/variation_after.json
```

6. Run the broader safety checks before committing:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/verify_full_flow.py
python tools/check_widgets_values.py
```

## Safety Rules

- Do not add style, quality, camera, render-effect, or body-type terms to active prompt output.
- Prefer data additions over runtime logic changes when the desired variation is declarative.
- Add aliases only when they help real user/workflow input resolve to canonical keys.
- Do not rely on `background_loc_tag_map.json` as the new source of truth.
- Keep public `Context*` node inputs stable unless workflow round-trip tests are updated together.

## Reading The Validator Summary

`tools/validate_prompt_data.py` includes an `expansion_summary` info block.

Key fields:

- `subject_count`: number of character profiles
- `variation_subject_count`: unique subjects currently counted by `calc_variations.py`
- `variation_location_count`: unique locations currently counted by `calc_variations.py`
- `variation_row_count`: compatibility-review rows used by base variation sizing
- `compat_character_count`: number of scene compatibility character entries
- `background_pack_count`: number of canonical location packs
- `location_candidate_count`: selectable location candidates
- `action_pool_count`: dedicated action pools
- `action_generatable_count`: locations covered by dedicated pools or compositional fallback
- `dedicated_action_pool_missing_count`: locations relying on fallback
- `alias_entry_count`: resolver alias surface size

For expansion work, `ERROR` must stay empty. `dedicated_action_pool_missing_count` can be nonzero if fallback is intentional.
