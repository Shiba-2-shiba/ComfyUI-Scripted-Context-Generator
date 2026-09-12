# Clothing State Location Gate Refactor Plan

Last updated: 2026-05-09

## Goal

衣装 pack の `states` が Location と衝突する問題を、雪だけの個別対応ではなく
共通の location gate として整理する。

現在確認できている問題は、`states` の語が服や人物の物理状態として prompt に
入るため、屋内 Location でも人物・床・机などが天候や環境状態に引っ張られる
ことです。

## Current Finding

`vocab/data/clothing_packs.json` の dresses / separates には、Location と
衝突しやすい state が複数あります。

| State family | Current terms | Risk |
| --- | --- | --- |
| snow | `covered in snow` | 屋内でも人物や家具に雪が積もる |
| rain / wet | `rain-soaked`, `wet` | 屋内店舗・部屋・机周りまで濡れる |
| sun / beach | `sun-kissed glow` | 屋内や夜/地下系でも海辺・日焼け感が出る |
| exertion | `sweaty` | 通常の店内・オフィス・キッチンで運動後の状態になる |
| battle damage | `battle-worn`, `blood-stained` | 日常 Location で戦闘後の状態になる |
| workshop dirt | `grease stained` | 清潔な部屋や店舗で機械油汚れになる |

Outerwear 側にも同種の state はありますが、現行 renderer は outerwear の
`states` を出力していません。今回の主対象は dresses / separates の state
selection です。

## Implementation Status

Status: `verified`

Implemented in:

- `pipeline/clothing_builder.py`
- `assets/test_context_content_pipeline.py`
- `assets/fixtures/prompt_snapshot_cases.json`

The implementation uses one shared `STATE_DETAIL_RULES` table and a common
state-detail gate. It preserves RNG choice order by drawing the state detail
first, then dropping only the selected detail when the current Location is not
allowed for that state family.

## Non-Goals

- public node surface や `PromptContext` schema は変更しない
- `clothing_packs.json` の data schema は変更しない
- `scene_compatibility.json` や `variation_scope.json` の compatibility row は変更しない
- `assets/compatibility_review.csv` は変更しない
- 新規 dependency は追加しない
- state 語を削除して variation を減らすのではなく、Location に合う場合だけ出す

## Behavior Lock

実装前後で、次を regression として固定します。

1. 屋内 Location では環境依存 state が出ない。
   - `modern_office`, `food_court`, `tea_room`, `messy_kitchen`
   - `antique_shop`, `art_gallery`, `bedroom_boudoir`, `cinema_lobby`
2. 自然な Location では該当 state がまだ出る。
   - snow: `winter_street`
   - wet/rain: `rainy_alley`, `rainy_bus_stop`, `japanese_bath`
   - sun/beach: `tropical_beach`, `poolside_resort`
   - exertion: `fitness_gym`, `yoga_studio`, `stadium_court`
   - battle damage: `burning_battlefield`, `dragon_lair`, `dungeon_crypt`
   - workshop dirt: `clockwork_workshop`
3. RNG 消費順を極力維持し、state が不許可の場合はその state だけを落とす。
   既存 snapshot の広範囲な揺れを避ける。

## Implementation Plan

### P14-1: State Family Inventory

Status: `done`

`clothing_packs.json` から `states` を抽出し、location gate が必要な state
family を固定する。

Initial families:

- `snow`
- `wet`
- `sun_beach`
- `exertion`
- `battle_damage`
- `workshop_dirt`

### P14-2: Shared Gate Helper

Status: `done`

`pipeline/clothing_builder.py` に、雪専用 helper ではなく共通 helper を置く。

Suggested shape:

```text
STATE_DETAIL_RULES = [
  {
    family,
    terms,
    allowed_location_keys,
    allowed_location_terms,
  }
]
```

判定順:

1. state text がどの family に属するか判定する。
2. family に属さない state は従来どおり許可する。
3. family に属する state は、resolved location key または raw loc text が
   allowed set / terms に合う場合だけ許可する。
4. 不許可の場合は RNG の選択結果を再抽選せず、その detail だけ追加しない。

### P14-3: Regression Tests

Status: `done`

`assets/test_context_content_pipeline.py` に state family ごとの positive /
negative test を追加する。

Minimum cases:

- indoor negative:
  - snow, wet, sun-beach, sweaty, battle damage, grease
- location-positive:
  - `winter_street`, `rainy_bus_stop`, `tropical_beach`, `fitness_gym`,
    `burning_battlefield`, `clockwork_workshop`

### P14-4: Snapshot Update

Status: `done`

既存 snapshot が不自然な state を含む場合だけ更新する。

Current changes:

- `suburban_daily_life` snapshot から `covered in snow` を除去
- `fantasy_scene` snapshot から `battle-worn` を除去

### P14-5: Verification

Status: `done`

Targeted checks:

```bash
python -m unittest assets.test_context_content_pipeline
python -m unittest assets.test_prompt_snapshots
python -m unittest assets.test_determinism assets.test_registry
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
```

Broader checks:

```bash
python -m unittest discover -s assets -p "test_*.py"
```

Known environment caveat:

- Full discovery currently requires
  `assets/results/prompt_repetition_active_source_8.json`
  and `assets/results/template_diversity_32.json`.
  If those artifacts are absent, run targeted checks and report the artifact
  gap separately.

## Acceptance Criteria

- All state family gates are implemented through one shared helper.
- No snow/wet/sun/sweaty/battle/grease state appears in incompatible indoor
  prompt samples.
- Each gated state family still appears in at least one compatible Location.
- Existing deterministic behavior stays stable except where an incompatible
  state is intentionally removed.
- Prompt data validation and variation scope checks remain clean.

## Remaining Risks

- Some conflicts come from broad costume-to-location compatibility, not only
  `states`. For example `fantasy_battle` can still appear in some daily-public
  locations even if `battle-worn` is suppressed.
- A term like `wet` may be valid in baths, rain, poolside, and beach contexts,
  so over-restricting it would reduce useful variation.
- `sun-kissed glow` is less physically destructive than snow/wet, but it still
  carries strong beach/daylight semantics and should be gated conservatively.
