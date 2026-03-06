# object concentration 改修 検証記録

更新日: 2026-03-06

参照:
- `assets/object_concentration_refactor_spec.md`
- `assets/object_concentration_refactor_evaluation.md`
- `assets/results/audit/object_eval_20260306/`
- `assets/results/audit/object_refactor_20260306_r2/`

---

## 1. 変更理由の要約

- object concentration は content 側の偏りと audit 側の誤検知が混在していたため、責務分離を先に仕様化した
- background/action の偏りは data を全面削除せず、policy ベースの重み調整で分散させた
- thematic anchor はゼロ化せず threshold 分離で扱い、loc の自然さを維持した
- audit artifact は phrase-aware normalization に寄せ、`display` と `coffee table` の誤検知を content 側改変なしで除外した

---

## 2. ファイル単位サマリ

- `assets/object_concentration_refactor_spec.md`
  - object concentration 専用の新規仕様書を追加
- `assets/object_concentration_refactor_verification.md`
  - 段階検証と before/after を記録
- `vocab/data/object_concentration_policy.json`
  - background/action/audit/anchor を分離した policy layer を追加
- `nodes_dictionary_expand.py`
  - `ThemeLocationExpander` に section-aware の weighted selection を追加
- `nodes_scene_variator.py`
  - loc-aware action weight を追加し、dominant object がない場合も policy weight が効くよう修正
- `tools/run_bias_audit.py`
  - phrase-aware object normalization、classification、effective threshold、`max_object_concentration_true_bias` を追加
- `vocab/data/background_packs.json`
  - `karaoke_bar` の core variation を増やし、screen 固定化を緩和
- `vocab/data/action_pools.json`
  - `commuter_transport` の explicit phone action を non-phone wording に置換
- `vocab/data/scene_axis.json`
  - `commute / wait / delay / wrapping_up` の phone/coffee 依存 micro action を一般表現へ置換
- `assets/test_bias_audit_metrics.py`
  - phrase-aware normalization と policy classification の単体検証を追加
- `assets/test_bias_controls.py`
  - karaoke/street_cafe/tropical_beach/background bias と commuter action bias の回帰テストを追加

---

## 3. 段階検証

### Stage A: policy / unit

| Command | Result | Notes |
|------|------|------|
| `python -m unittest assets.test_bias_audit_metrics` | pass | normalization 除外、classification、quality metric を確認 |
| `python -m unittest assets.test_bias_controls` | pass | background/action bias control の回帰を確認 |

### Stage B: flow / compatibility

| Command | Result | Notes |
|------|------|------|
| `python assets/test_determinism.py` | pass | seed 再現性維持 |
| `python tools/verify_full_flow.py` | pass | 既存 pipeline の smoke test 通過 |
| `python assets/test_scene_variator.py` | pass | loc/action variation の回帰なし |
| `python -X utf8 assets/validate_compatibility.py` | pass_with_warnings | unused loc と universal coverage 警告は継続、互換性エラーなし |

### Stage C: audit smoke

| Command | Result | Notes |
|------|------|------|
| `python tools/run_bias_audit.py --sample-count 400 --seed-start 0 --variation-mode full --location-mode detailed --lighting-mode auto --input-mode canonical --run-id object_refactor_smoke_20260306` | pass | `max_object_concentration_final_prompt=0.5`, `max_object_concentration_true_bias=0.1` を確認 |

Stage C で `blackboard -> board -> surfboard` の artifact を発見したため、`tools/run_bias_audit.py` の surfboard normalization を `surfboard` 明示語のみに修正した。

### Stage D: final audit

| Command | Result | Notes |
|------|------|------|
| `python tools/run_bias_audit.py --sample-count 1000 --seed-start 0 --variation-mode full --location-mode detailed --lighting-mode auto --input-mode canonical --run-id object_refactor_20260306_r2` | pass_with_warnings | object gate は pass、`abstract_style_term_rate=0.003` は warn |

---

## 4. before / after

`assets/results/audit/object_eval_20260306/` と `assets/results/audit/object_refactor_20260306_r2/` の比較。

| Loc | Object | Before | After | 差分 | 判定 |
|------|------|------:|------:|------:|------|
| `karaoke_bar` | `screen` | 0.764706 | 0.176471 | -0.588235 | 改善 |
| `street_cafe` | `coffee` | 0.521739 | 0.304348 | -0.217391 | 改善 |
| `tropical_beach` | `surfboard` | 0.36 | 0.08 | -0.28 | 改善 |
| `commuter_transport` | `phone` | 0.333333 | 0.0 | -0.333333 | 改善 |
| `boardroom` | `coffee` | 0.5 | 0.125 | -0.375 | 改善 |
| `cozy_bookstore` | `screen` | 0.521739 | 0.086957 | -0.434782 | artifact 解消方向 |
| `fashion_boutique` | `screen` | 0.473684 | 0.157895 | -0.315789 | artifact 解消方向 |
| `shopping_mall_atrium` | `screen` | 0.294118 | 0.147059 | -0.147059 | artifact 解消方向 |
| `cozy_living_room` | `coffee` | 0.25 | 0.0 | -0.25 | artifact 解消方向 |
| `school_library` | `book` | 0.461538 | 0.5 | +0.038462 | anchor 許容範囲内 |
| `magic_academy_library` | `book` | 0.5 | 0.2 | -0.3 | anchor 許容範囲内 |
| `wave_barrel` | `surfboard` | 0.333333 | 0.333333 | 0.0 | anchor 許容範囲内 |

---

## 5. 最終 quality metrics

`assets/results/audit/object_refactor_20260306_r2/audit_quality_metrics.csv`

| Metric | Value | Status |
|------|------:|------|
| `daily_life_share` | 0.73 | pass |
| `emotion_embodiment_rate` | 0.985 | pass |
| `unwanted_noun_rate` | 0.0 | pass |
| `disallowed_fx_rate` | 0.0 | pass |
| `max_object_concentration_final_prompt` | 0.5 | pass |
| `max_object_concentration_true_bias` | 0.304348 | pass |
| `abstract_style_term_rate` | 0.003 | warn |

---

## 6. 残課題

- `abstract_style_term_rate` は 0.003 で warn のまま
- `validate_compatibility.py` の unused loc / universal coverage 警告は今回も継続
- `concert_stage / microphone` や `office_elevator / phone` など、仕様上は許容範囲だが watchlist として継続監視したい対象が残る
