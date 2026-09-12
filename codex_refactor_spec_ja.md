# Codex向けリファクタリング仕様書

## 文書名
ComfyUI カスタムノード（自然言語プロンプト生成器）リファクタリング仕様書

## 目的
このカスタムノードは、**イラスト調の女性主人公を中心とした自然言語プロンプト**を生成する。
今回のリファクタリングでは、生成品質を上げつつ、**意味的なバリエーションの拡張**と**データ整合性の改善**を行う。

本リファクタリングの最重要方針は、以下をこのノードの責務から外すこと。

- 画風・style
- 品質語
- カメラ / 構図 / 視点 / レンズ / DoF
- 体型 / 体格 / プロポーション

このノードは今後、
**主語 / 役割 / 衣装テーマ / 場所テーマ / 行動 / 感情ニュアンス / 日常文脈 / 小物 / 状態**
に限定した、**意味生成器**として再設計する。

---

## 現行コードベースの前提
現状の主要ファイルは以下。

- `schema.py`
- `context_codec.py`
- `context_ops.py`
- `source_pipeline.py`
- `context_pipeline.py`
- `content_pipeline.py`
- `logic.py`
- `loc_tag_builder.py`
- `theme_map.py`
- `scene_compatibility.json`
- `background_packs.json`
- `background_loc_tag_map.json`
- `background_alias_overrides.json`
- `action_pools.json`
- `character_profiles.json`
- `clothing_theme_map.json`
- `background_defaults.json`
- `garnish_base_vocab.json`
- `garnish_micro_actions.json`
- `object_concentration_policy.json`

### 現状監査で確認できた課題
1. `MetaInfo.style` が `schema.py` に残っており、`content_pipeline.py` では `meta_style` がテンプレート置換対象になっている。
2. `source_pipeline.py` は `meta.style` をソース選好スコアに使っている。
3. `logic.py` の `sample_garnish()` は `include_camera` を受け取り、`VIEW_FRAMING` / `VIEW_ANGLES` を足せる。
4. `logic.py` の効果タグ選択は `soft lighting`, `natural lighting`, `dim lighting`, `low key lighting`, `detailed texture` などを返しうる。
5. `background_defaults.json` と `garnish_base_vocab.json` に `depth of field`, `cinematic`, `highly detailed`, `front view`, `profile view`, `close-up`, `cowboy shot` など、今回除外すべき語彙が含まれる。
6. `scene_compatibility.json` の `daily_life_locs` は 62 件あるが、そのうち 27 件に `action_pools.json` 側の専用アクションがない。
7. `scene_compatibility.json` の `daily_life_locs` のうち 2 件（`japanese_garden`, `tea_room`）は `background_packs.json` に存在しない。
8. `character_profiles.json` の `default_costume` のうち 6 件（`exotic_dancer`, `idols_stage`, `library_girl`, `sleek_evening_gown`, `steampunk_inventor`, `street_casual`）が `clothing_theme_map.json` に存在しない。
9. `loc_tag_builder.py` は alias 自動生成機能を持つが、`background_loc_tag_map.json` は手動マップが主で、現状の自動生成との差分が大きい（自動生成側に 110 件の追加 alias がある）。
10. `context_pipeline.py` ではシーン変更後、対応アクションプールがない場合 `ctx.action` を温存するため、場所と行動のズレが起こりうる。

---

## リファクタリングの基本方針

### 方針A: このノードは「意味」を生成する
このノードが生成してよい情報は以下のみ。

- 主人公の役割・人物像
- 衣装テーマ・服の意味的ディテール
- 場所テーマ・環境文脈
- 行動
- 感情ニュアンス
- 日常シーンの背景文脈
- 小物
- 状態変化・進行中の出来事

### 方針B: 除外対象はノード全体で一貫して排除する
以下は**入力互換のため一時的に受け取れても、最終生成結果および内部選択ロジックでは使用禁止**。

- 画風語: `anime`, `watercolor`, `painting`, `lineart`, `cel shading`, `sketch`, `illustration style` など
- 品質語: `masterpiece`, `best quality`, `high quality`, `ultra detailed`, `highly detailed`, `detailed texture`, `8k` など
- カメラ語: `front view`, `profile view`, `close-up`, `cowboy shot`, `bird's eye view`, `low angle`, `depth of field`, `cinematic blur`, `bokeh` など
- 体型語: `slim`, `petite`, `curvy`, `voluptuous`, `athletic build`, `long legs` など

### 方針C: データの整合性を先に直す
語彙を増やす前に、以下を常に整合させる。

- `character_profiles` → `clothing_theme_map`
- `scene_compatibility` → `background_packs`
- `scene_compatibility` → `action_pools`
- `background_packs.aliases` → `background_loc_tag_map`

### 方針D: バリエーションは「列挙」ではなく「構文合成」で増やす
アクションは loc ごとの固定文を増やすだけでなく、以下の合成で生成する。

- 姿勢
- 手元動作
- 視線先
- 目的
- 進行状態
- 小さな障害 / きっかけ
- 日常タグに基づく時間・混雑・社会距離

---

## 非目標
今回やらないこと。

1. 画風生成の強化
2. 品質プロンプトの最適化
3. カメラ・構図・視点制御
4. 体型・性的特徴・外見誇張の最適化
5. 画像モデル依存のタグ最適化
6. LoRA / checkpoint ごとの特化チューニング

---

## 目標アーキテクチャ

### 1. Registry 層
**目的:** 文字列のゆらぎと参照不整合をなくす。

追加または整理対象:

- `registry.py` もしくは同等のユーティリティ層を新設
- canonical key を一元管理
- alias 正規化を共通化
- 以下の解決器を用意
  - `resolve_location_key(raw)`
  - `resolve_clothing_theme(raw)`
  - `resolve_character_key(raw)`
  - `resolve_location_alias_map()`

要件:

- `background_packs.json` の `aliases` を第一級の真実源にする
- `background_alias_overrides.json` は override のみ担当
- `background_loc_tag_map.json` は最終的に自動生成ベースへ移行
- ただし移行期間中は既存ファイル読込互換を維持

### 2. Validator 層
**目的:** データ追加時に破綻を防ぐ。

追加ファイル候補:

- `tools/validate_prompt_data.py`
- `tests/test_data_consistency.py`

検査要件:

- 全 `character_profiles.default_costume` が有効 theme に解決できること
- 全 `scene_compatibility.daily_life_locs` が `background_packs.json` に存在すること
- 全使用対象 loc が `action_pools` で直接対応、または compositional action generator の fallback 対象であること
- alias 衝突が検出されること
- banned domain 語彙が user-facing prompt 経路に流れ込まないこと

出力要件:

- ERROR / WARNING / INFO を持つレポート JSON を出力
- CI/ローカル両方で実行可能

### 3. Semantic Generation 層
**目的:** 主体・衣装・場所・行動・感情を意味的に構成する。

#### 3-1. Subject/Character
現状の `character_profile_pipeline.py` は維持しつつ、人物描写は以下までに制限する。

- 名前
- 役割
- 髪色
- 髪型
- 瞳色
- 性格
- パレット

**禁止:** 体型、胸囲、脚長、露骨な肉体特徴。

#### 3-2. Clothing
`content_pipeline.py` の衣装生成は継続利用可。
ただし以下を明確化する。

- 衣装の `styles` は**画風ではなく服飾スタイル**として扱うため許可
- 服の色・素材・柄・装飾・状態は保持可
- 体型を想起しやすい語は別途ポリシーで抑制対象にできるようにする

#### 3-3. Scene
`background_packs.json` と `scene_compatibility.json` を基礎に、場所は次の情報で構成する。

- 場所ラベル
- 環境属性
- 時間帯
- 天気
- 混雑度
- 日常タグに基づく生活文脈

**許可:** `rainy afternoon`, `after school`, `during a lunch break` のような世界状態。
**禁止:** `cinematic blur`, `depth of field`, `highly detailed textures` のようなレンダリング語。

#### 3-4. Action
`action_pools.json` のみ依存をやめ、**compositional action generator** を導入する。

生成単位:

- posture
- hand_action
- gaze_target
- purpose
- progress_state
- obstacle_or_trigger
- optional_micro_action

優先順位:

1. loc 専用 action pool があれば優先
2. なければ loc の daily-life tag / scene axis / object policy から構文合成
3. それも無理なら generic fallback だが loc と矛盾しないこと

要件:

- シーン変更後に action pool がない場合、旧 `ctx.action` を温存してそのまま使うのは禁止
- 最低でも loc 適合 fallback action を再生成すること

#### 3-5. Garnish
`logic.py` の `sample_garnish()` を semantic-only 化する。

残してよいもの:

- 表情
- 視線
- 手の動き
- 姿勢
- 微動作
- 行動に付随する小さな状態

削除対象:

- camera 系分岐 (`include_camera` による `VIEW_FRAMING`, `VIEW_ANGLES`)
- lighting/effect 系の user-facing 出力
- `detailed texture` など品質語

互換方針:

- 引数 `include_camera` は当面残してよい
- ただしこのノード内では no-op にし、debug/warning を残すのみ

### 4. Prompt Assembly 層
`content_pipeline.py` を prompt assembly 専任に近づける。

要件:

- `meta_style` を prompt 生成経路から除去
- `{meta_style}` プレースホルダを廃止
- テンプレートは意味情報のみを受け取る
- prompt 正規化で banned domain 語彙が残っていれば削除または失敗扱いにする

### 5. Repetition Guard 層
`PromptContext.history` を活用し、近傍反復を抑制する。

最低限抑制対象:

- 同一 loc の連発
- 同一 action 冒頭動詞の連発
- 同一 costume theme の連発
- 同一小物（phone/book/coffee など）の連発
- 同一テンプレート骨格の連発

---

## データ / スキーマ要件

### `schema.py`
方針:

- `PromptContext` は維持
- `MetaInfo.style` は**後方互換のため当面残すが deprecated**
- 新規コードでは `meta.style` を参照しない
- 必要なら warning を付与できるようにする

要件:

- `MetaInfo` の docstring を「style and mood」から見直す
- `style` は “legacy compatibility only” と明記
- `default_extras()` に banned-domain 関連の出力を追加しない

### `context_codec.py` / `context_ops.py`
要件:

- 旧 context を読めること
- `style` が入っていても prompt 生成に影響させないこと
- merge 時も style を優先キーにしないこと
- 旧 payload を normalize した場合、必要なら warning を積むこと

---

## ファイル別の具体的リファクタリング要求

### `source_pipeline.py`
対応内容:

- style による source score 補正を削除
- source の選好は daily-life / mood / purpose / rare-loc 補正に限定
- style positive/negative hints は削除または deprecated 化

### `logic.py`
対応内容:

- `sample_garnish()` を semantic-only に変更
- `include_camera=True` でも camera 系タグを出さない
- `_choose_effect_tag()` は lighting / quality 系を返さない設計へ変更
- 必要なら `_choose_effect_tag()` 自体を廃止し、semantic state tag 選択へ差し替え
- banned domain フィルタを通す

### `content_pipeline.py`
対応内容:

- `build_prompt_text()` から `meta_style` を外す
- `build_prompt_from_context()` で `ctx.meta.style` を渡さない
- `{meta_style}` 置換を削除
- 場所展開で `background_defaults.json` の render/camera/quality 語が混入しないようにする
- 衣装生成部分は服飾スタイルのみ維持

### `context_pipeline.py`
対応内容:

- scene variation 後に loc に対応した action を必ず再評価
- action pool 不在時は compositional generator へフォールバック
- `history` を使った反復抑制を導入
- `sample_garnish_fields()` 内の `include_camera` は no-op 扱いへ移行

### `loc_tag_builder.py`
対応内容:

- 正式な location alias 生成経路として採用
- `background_loc_tag_map.json` は自動生成結果のキャッシュ/生成物扱いに寄せる
- override は `background_alias_overrides.json` のみを特例として使用

### `theme_map.py` / `clothing_theme_map.json`
対応内容:

- `character_profiles.default_costume` の未解決テーマを解消
- canonical clothing theme registry を整備
- alias が必要なら clothing 側にも resolver を追加

### `scene_compatibility.json` / `action_pools.json` / `background_packs.json`
対応内容:

- 欠落 loc の補完または fallback 指定
- 少なくとも現行 `daily_life_locs` 全件が「背景あり」「行動生成可能」状態になること

---

## 実装順序

### Phase 1: 禁止ドメインの隔離
1. style / camera / quality / body-type 禁止ポリシーを追加
2. `source_pipeline.py` の style scoring を撤去
3. `content_pipeline.py` の `meta_style` 経路を撤去
4. `logic.py` から camera / effect / quality 出力を撤去

### Phase 2: 正規化と整合性の回復
1. canonical resolver 導入
2. clothing theme 不整合を解消
3. background / action / compatibility の不整合を validator で可視化
4. alias 自動生成を正規経路へ

### Phase 3: action generator 再設計
1. compositional action generator 追加
2. loc 専用 pool と fallback を統合
3. daily-life tag / scene axis / object policy を action 合成へ接続

### Phase 4: 反復抑制
1. `history` を利用した repetition guard 実装
2. loc / action / costume / object / template の近傍重複抑制

### Phase 5: テンプレート再整理
1. intro/body/end の役割を明確化
2. 構文骨格の反復を減らす
3. 意味語彙中心の表現差分を増やす

---

## 受け入れ条件

### 機能面
1. 生成 prompt に style / camera / quality / body-type 語が含まれないこと
2. 同一 seed・同一入力で決定的な出力になること
3. scene を変更したとき、action が loc と矛盾しないこと
4. character profile の `default_costume` が必ず有効 theme に解決されること
5. daily-life loc が「背景解決可能」かつ「行動生成可能」であること
6. alias 解決が deterministic であること

### データ面
1. validator の ERROR が 0 件になること
2. validator の WARNING は理由付きで許容可能であること
3. 自動生成 alias と手動 override の責務が分離されていること

### 品質面
1. 32 seed 連続生成で loc / action / costume の重複率が現状より明確に改善すること
2. 少なくとも daily-life 系では、同一 loc でも文脈差分が出ること
3. カメラ・品質語に頼らずに prompt が成立すること

### 互換面
1. 既存 context JSON を読み込めること
2. `style` や `include_camera` が渡されても処理が壊れないこと
3. 既存ノードの public I/O は極力維持すること

---

## テスト要件

### Unit Test
- theme 解決テスト
- location alias 解決テスト
- banned domain filter テスト
- action fallback 生成テスト
- history repetition guard テスト

### Data Consistency Test
- `character_profiles.json` → `clothing_theme_map.json`
- `scene_compatibility.json` → `background_packs.json`
- `scene_compatibility.json` → `action_pools.json`
- alias collision report

### Snapshot Test
- seed 固定の prompt snapshot
- banned 語彙 0 件確認

### Regression Test
- 既存 context 読み込み
- old node path からの prompt build
- composition mode / legacy mode 両方

---

## Codexへの実装指示
以下のルールで実装させること。

1. **最初に validator と banned-domain policy を実装すること**
2. その後に registry / resolver を入れること
3. それから action generator を compositional 化すること
4. 最後にテンプレートと反復抑制を触ること
5. 変更は小さな単位で分け、各段階でテストを追加すること
6. public API を無闇に壊さないこと
7. 互換維持のため deprecated フィールドは即削除せず、まず無効化すること
8. コメントと docstring を日本語または明瞭な英語で補うこと
9. 実装後に「何を残し、何を無効化したか」を `readme.md` に追記すること

---

## Codexへそのまま渡せるプロンプト
```text
あなたは、この ComfyUI カスタムノードの Python/JSON コードベースをリファクタリングする担当です。
目的は、自然言語プロンプト生成器を「意味生成器」として再設計することです。

厳守条件:
- このノードでは画風(style)を扱わない
- このノードでは品質語を扱わない
- このノードではカメラ/構図/視点/DoF/レンズを扱わない
- このノードでは体型/体格/プロポーションを扱わない
- public API は極力維持する
- 既存 context JSON は読めるようにする
- deprecated フィールドは即削除せず、まず無効化する

必須対応:
1. validator と banned-domain policy を最初に実装
2. source_pipeline.py から style scoring を撤去
3. content_pipeline.py から meta_style 経路と {meta_style} 置換を撤去
4. logic.py の sample_garnish を semantic-only 化し、include_camera を no-op にする
5. background_defaults.json / garnish_base_vocab.json 由来の camera/quality/render 語が prompt に出ないようにする
6. location / clothing / character の canonical resolver を実装
7. background_packs の aliases を中心に loc alias 自動生成を正式採用
8. character_profiles.default_costume が必ず clothing_theme_map に解決されるようにする
9. daily_life_locs が必ず背景解決可能かつ行動生成可能になるようにする
10. action_pools にない loc でも compositional action generator により loc 適合 action を生成する
11. PromptContext.history を利用した repetition guard を追加する
12. テストを追加する

現状の不整合:
- daily_life_locs 62件中、27件は action_pools 未対応
- daily_life_locs のうち japanese_garden, tea_room は background_packs 未対応
- character_profiles.default_costume のうち exotic_dancer, idols_stage, library_girl, sleek_evening_gown, steampunk_inventor, street_casual が clothing_theme_map 未対応
- loc_tag_builder の自動生成 alias は hand-maintained map より 110 件多い

実装順:
Phase 1: 禁止ドメイン隔離
Phase 2: 正規化と整合性回復
Phase 3: action generator 再設計
Phase 4: repetition guard
Phase 5: テンプレート整理

期待成果物:
- リファクタ済みコード
- validator スクリプト
- pytest テスト
- README 更新
- 変更点サマリ
```

---

## 補足判断基準
- 「world state」として自然な情報は許可する
  - 例: 雨、夕方、放課後、昼休み、混雑、待ち合わせ前
- 「render / camera / art style」は禁止する
  - 例: cinematic, front view, close-up, depth of field, masterpiece, watercolor style
- 「衣装スタイル」は許可する
  - 例: vintage cardigan, tailored jacket, lace-trimmed blouse
- 「人物の身体属性」は禁止する
  - 例: slim body, curvy figure, long legs

---

## 最終ゴール
このノードを、
**「画風やカメラではなく、生活感・状況・行動・感情の組み合わせで差が出るプロンプト生成器」**
として完成させること。
