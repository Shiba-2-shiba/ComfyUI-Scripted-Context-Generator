# object concentration 改修仕様書

更新日: 2026-03-06

参照:
- `object_concentration_refactor_evaluation.md`
- `assets/results/audit/object_eval_20260306/`
- `scene_emotion_priority_spec.md`

---

## 1. 目的

- object concentration 改修を `tropical_beach / surfboard` 単独対策ではなく、全体設計として再定義する
- `true_bias_background` / `true_bias_action` / `thematic_anchor` / `audit_artifact` を責務分離したまま改善する
- 日常系比率、感情重視、seed 再現性、ノード互換性、既存ワークフロー互換を維持する

---

## 2. 現状整理

`object_concentration_refactor_evaluation.md` と `assets/results/audit/object_eval_20260306/` の結果を前提に、現状は次の 4 類型に分かれる。

1. `true_bias_background`
   - `karaoke_bar / screen`
   - `street_cafe / coffee`
   - `tropical_beach / surfboard`
   - 背景 pack の `environment / core / props` が object を固定化している
2. `true_bias_action`
   - `commuter_transport / phone`
   - action pool と daily-life scene axis の micro action が phone 系へ寄る
3. `thematic_anchor`
   - `school_library / book`
   - `magic_academy_library / book`
   - `wave_barrel / surfboard`
   - loc の主題物なのでゼロ化対象ではない
4. `audit_artifact`
   - `cozy_bookstore / screen`
   - `fashion_boutique / screen`
   - `shopping_mall_atrium / screen`
   - `cozy_living_room / coffee`
   - 監査正規化の誤検知であり、content 側を改変しない

---

## 3. 設計方針

### 3.1 基本方針

- content 側と audit 側を同一 issue として扱わない
- true bias は prompt 内容の再配分で下げる
- audit artifact は正規化ルールの見直しで下げる
- thematic anchor は別 threshold で監視し、自然さを壊さない

### 3.2 設計単位

改修は以下の 3 層で行う。

1. `policy layer`
   - object concentration 制御ポリシーをデータ化する
   - background/action/audit/anchor の責務を 1 つの policy で管理する
2. `content redistribution layer`
   - `ThemeLocationExpander` で background pack の object-heavy segment を減衰する
   - `SceneVariator` と scene axis data で action 系の object-heavy wording を減衰する
3. `audit normalization layer`
   - object 正規化を phrase-aware にし、`display` や `coffee table` の誤検知を除外する

### 3.3 互換性方針

- ノードの I/O は変更しない
- 乱択は既存の seed 系列上で重みのみ調整し、再現性を保つ
- 既存 workflow JSON が要求する node 名、port 名、返却型は変えない

---

## 4. 改修要件

### 4.1 policy layer

新規 policy ファイルを追加し、最低限以下を持つ。

- `thresholds`
  - default conditional threshold
  - anchor conditional threshold
  - raw final-prompt quality gate
  - true-bias-only quality gate
- `content_redistribution.background`
  - loc ごとの `environment/core/props/fx` 重み調整
- `content_redistribution.action`
  - loc ごとの action wording 重み調整
- `thematic_anchor`
  - loc-object ごとの anchor-aware threshold
- `true_bias_background`
  - loc-object の一次管理表
- `true_bias_action`
  - loc-object の一次管理表
- `audit_artifact`
  - loc-object の artifact 管理表
- `audit_normalization`
  - object ごとの除外 phrase ルール

### 4.2 background redistribution

`ThemeLocationExpander` は `environment / core / props / fx` ごとに policy 重みを読めること。

一次対象:

- `karaoke_bar`
  - `screen` を含む core を低頻度化する
  - karaoke room らしさは lyric control / sofa / room furnishing で維持する
- `street_cafe`
  - `coffee` を含む environment / fx を低頻度化する
  - cafe らしさは terrace / table / menu / pedestrians で維持する
- `tropical_beach`
  - `surfboard` prop を低頻度化する
  - beach らしさは parasol / tote / shells / deck chair で維持する

### 4.3 action redistribution

`SceneVariator` は loc ごとの action weight を読めること。

一次対象:

- `commuter_transport / phone`
  - action pool の phone wording を低頻度化する
  - scene axis の `commute / wait / delay` で phone 依存の micro action を減らす
  - 代替は `strap`, `route strip`, `platform sign`, `clock`, `bag`, `posture` 系で分散する

### 4.4 thematic anchor

anchor loc は raw rate をそのまま true bias と見なさない。

初期対象:

- `school_library / book`
- `magic_academy_library / book`
- `wave_barrel / surfboard`

要件:

- `audit_object_rate_by_location.csv` に classification と effective threshold を出す
- `thematic_anchor` は alert 閾値を一般 loc より高くする
- anchor は content 側でゼロ化しない

### 4.5 audit normalization

`tools/run_bias_audit.py` の object normalization は phrase-aware に変更する。

必須除外:

- `screen`
  - `display cart`
  - `display counter`
  - `display cabinet`
  - `display case`
  - `storefront displays`
- `coffee`
  - `coffee table`

要件:

- phrase 除外後に通常の object include pattern を適用する
- `audit_artifact` は `high_object_bias` ではなく artifact として扱えること

---

## 5. 受け入れ条件

### 5.1 維持条件

- `daily_life_share` は 0.60 から 0.75 を維持する
- `emotion_embodiment_rate` を悪化させない
- `unwanted_noun_rate = 0`
- `disallowed_fx_rate = 0`
- seed 再現性テストを維持する
- compatibility / full-flow を壊さない

### 5.2 object concentration 条件

- 既存の `max_object_concentration_final_prompt` は継続出力する
- 追加で `max_object_concentration_true_bias` を出力する
- `audit_object_rate_by_location.csv` に以下を追加する
  - `classification`
  - `effective_threshold`
  - `policy_source`
- `audit_artifact` は true bias の quality gate から除外する
- `thematic_anchor` は anchor threshold で判定する

---

## 6. 実装順序

1. policy file を追加する
2. `ThemeLocationExpander` に background redistribution を入れる
3. `SceneVariator` と `scene_axis.json` に action redistribution を入れる
4. `run_bias_audit.py` に phrase-aware normalization と policy-aware metric を入れる
5. unit / flow / audit の順で検証する
6. agent log と session notes を更新する

---

## 7. 検証計画

### Stage A: policy / unit

- policy 読み込み
- audit normalization の phrase 除外
- anchor / true bias classification

### Stage B: node / flow

- `ThemeLocationExpander`
- `SceneVariator`
- `verify_full_flow`
- determinism

### Stage C: audit

- bias audit を before/after 比較可能な run_id で実行
- hotspot の conditional rate と quality metrics を確認

---

## 8. 非目標

- 日常系比率を下げること
- anchor 物体を完全に消すこと
- audit artifact 解消のために content 語彙を不必要に削ること
- node interface を変更すること
