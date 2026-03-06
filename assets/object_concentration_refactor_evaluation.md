# object concentration 再リファクタリング 評価メモ

更新日: 2026-03-06

---

## 目的

- `tropical_beach / surfboard` だけでなく、全 loc / pack を対象に object concentration の再評価を行う
- 次の仕様書では、`true bias` と `thematic anchor` と `audit artifact` を分離して扱えるようにする
- 既存方針である `daily_life_share` 維持、感情重視、seed 再現性維持、ノード互換性維持は前提として保つ

---

## 実行条件

- 監査コマンド:
  - `python tools/run_bias_audit.py --sample-count 1000 --seed-start 0 --variation-mode full --location-mode detailed --lighting-mode auto --input-mode canonical --run-id object_eval_20260306`
- 出力先:
  - `assets/results/audit/object_eval_20260306/`
- 主に参照したファイル:
  - `audit_object_rate_by_location.csv`
  - `audit_stage_sampling.csv`
  - `audit_quality_metrics.csv`
  - `audit_alerts.csv`

---

## 全体所見

- object concentration の主要 hotspot は、`action pool` より `background pack` 起因が多い
- `screen` 系の高率は、その一部が実際の monitor ではなく `display cart` / `display counter` / `storefront displays` を `screen` と正規化している監査側 artifact である
- `book` や `surfboard` の一部は、偏りというより loc の主題物として期待される `thematic anchor` に当たる
- よって次の仕様書では、内容側の再配分と監査側の正規化見直しを分離しないと、不要なデータ改変が混ざる

---

## ベースライン品質

`audit_quality_metrics.csv` の主要値:

| Metric | Value | Status |
|------|------:|------|
| `daily_life_share` | 0.73 | pass |
| `emotion_embodiment_rate` | 0.987 | pass |
| `abstract_style_term_rate` | 0.001 | warn |
| `unwanted_noun_rate` | 0.0 | pass |
| `disallowed_fx_rate` | 0.0 | pass |
| `max_object_concentration_final_prompt` | 0.764706 | warn |

備考:

- 今回の object concentration 評価でも、日常系比率と感情表出の基準は維持できている
- 次の改修は object concentration の改善を主目標にしつつ、上記品質値を悪化させないことを前提にする

---

## 評価ルール

- 主判定は `final_prompt` を基準に行う
- ただし原因切り分けには `background` / `action` の rate も併用する
- `count_location_samples >= 8` の loc を主評価対象にする
- `audit_alerts.csv` の `high_location_bias` は loc 選択そのものを報告しており、今回の object concentration 仕様では直接の改善対象にしない

分類ラベル:

- `true_bias_background`: background pack の環境 / core / props 語彙が偏りを作っている
- `true_bias_action`: action pool の動作語彙が偏りを作っている
- `thematic_anchor`: loc の主題物としてある程度は自然で、別 threshold で管理すべき
- `audit_artifact`: 監査の object 正規化が広すぎて、実際の偏り以上に検出されている
- `watchlist`: 小標本または二次的偏りで、次 phase では観察対象に留める

---

## 主要 hotspot の分類

| Loc | Object | Final rate | Samples | 主因 | 分類 | 評価 |
|------|------|------:|------:|------|------|------|
| `karaoke_bar` | `screen` | 0.764706 | 17 | background core の `large monitor screen displaying lyrics` | `true_bias_background` | 最優先 |
| `street_cafe` | `coffee` | 0.521739 | 23 | background environment の `cozy coffee shop terrace` | `true_bias_background` | 最優先 |
| `tropical_beach` | `surfboard` | 0.36 | 25 | background props の `leaning surfboard` | `true_bias_background` | 高 |
| `commuter_transport` | `phone` | 0.333333 | 27 | action pool の `standing and checking phone` 系 | `true_bias_action` | 高 |
| `karaoke_bar` | `drink` | 0.411765 | 17 | background props の `pitchers of drinks and glass cups` | `watchlist` | 中 |
| `boardroom` | `coffee` | 0.5 | 8 | background core の `credenza with coffee service` | `watchlist` | 中 |
| `school_library` | `book` | 0.461538 | 26 | background と action の双方 | `thematic_anchor` | threshold 分離候補 |
| `magic_academy_library` | `book` | 0.5 | 10 | action pool の `floating book` / `grimoire` 系 | `thematic_anchor` | threshold 分離候補 |
| `wave_barrel` | `surfboard` | 0.333333 | 9 | action pool の `standing on a surfboard` | `thematic_anchor` | threshold 分離候補 |
| `cozy_bookstore` | `screen` | 0.521739 | 23 | `display cart` を `screen` に正規化 | `audit_artifact` | 監査修正対象 |
| `fashion_boutique` | `screen` | 0.473684 | 19 | `glass display counter` を `screen` に正規化 | `audit_artifact` | 監査修正対象 |
| `shopping_mall_atrium` | `screen` | 0.294118 | 34 | `storefront displays` を `screen` に正規化 | `audit_artifact` | 監査修正対象 |
| `cozy_living_room` | `coffee` | 0.25 | 28 | `coffee table` を `coffee` に正規化 | `audit_artifact` | 監査修正対象 |

---

## root cause の詳細

### 1. background pack 主導の true bias

- `karaoke_bar / screen`
  - background rate は 0.705882
  - `core` に `large monitor screen displaying lyrics` が固定で入っている
- `street_cafe / coffee`
  - background rate は 0.478261
  - `environment` の `cozy coffee shop terrace` が高頻度で final prompt に残る
- `tropical_beach / surfboard`
  - background rate は 0.36
  - `props` の `leaning surfboard` が主要因

結論:

- object concentration の主要課題は、まず background pack の environment / core / props の再配分で解くべき

### 2. action pool 主導の true bias

- `commuter_transport / phone`
  - action rate は 0.333333
  - `standing and checking phone`、`checking route on phone` が繰り返し効いている

結論:

- action pool 側は loc ごとの phone / drink / book の頻出動作を分散し、同機能の非 object 動作へ置き換える余地がある

### 3. thematic anchor

- `school_library / book`
  - 図書室で book がある程度出るのは自然
- `magic_academy_library / book`
  - `floating book` や `grimoire` は loc の主題物
- `wave_barrel / surfboard`
  - surf scene では surfboard が自然

結論:

- 次の仕様書では、`all locations 共通 threshold` ではなく `anchor-aware threshold` を導入する必要がある
- anchor をゼロに寄せるのではなく、過剰集中だけを抑える設計にすべき

### 4. audit artifact

- `cozy_bookstore / screen`
  - 実態は `wooden display cart of staff picks`
- `fashion_boutique / screen`
  - 実態は `glass display counter`
- `shopping_mall_atrium / screen`
  - 実態は `bright storefront displays`
- `cozy_living_room / coffee`
  - 実態は `coffee table`

結論:

- これらは prompt 内容の改修より、object detector / normalization ルールの改善が先
- `display` を一律 `screen` 扱いしない、`coffee table` を beverage `coffee` に数えない、といった監査側の定義調整が必要

---

## 次の仕様書に入れるべき論点

1. object concentration 改善を `content redistribution` と `audit normalization redesign` の 2 本立てで管理する
2. `general location` と `thematic anchor location` で threshold を分ける
3. background pack は `environment/core/props` ごとに object 寄与を観測し、固定 anchor になっている語を分散する
4. action pool は `phone / drink / book` 系の便利動作に代替動作を増やす
5. `screen` と `coffee` の検出語彙は監査側で精密化し、`display` や `coffee table` の誤検知を除外する
6. 受け入れ条件は `max_object_concentration_final_prompt` だけでなく、`true bias only` の再集計値でも判定する

---

## 仕様書作成に向けた暫定スコープ

次 phase の一次対象:

- background pack 再配分
  - `karaoke_bar`
  - `street_cafe`
  - `tropical_beach`
- action pool 再配分
  - `commuter_transport`
- audit normalization 見直し
  - `screen <- display`
  - `coffee <- coffee table`

次 phase の二次対象:

- anchor policy 設計
  - `school_library`
  - `magic_academy_library`
  - `wave_barrel`
- watchlist
  - `boardroom / coffee`
  - `karaoke_bar / drink`

---

## 結論

- 現在の object concentration 問題は、`tropical_beach / surfboard` 単独ではなく、background pack 主導の複数 hotspot と監査正規化 artifact が混在している
- 次の仕様書は、`どの loc を減らすか` ではなく、`何を content 側で直し、何を audit 側で直すか` を先に分ける必要がある
- この評価を前提に、次チャットでは object concentration 専用の仕様書と段階的改修プランを作成する
