# Session Notes

このファイルには **このセッションでの作業メモ** を記録します。
セッション終了時に `compaction_policy.md` のルールに従って圧縮し、
必要なら `global_notes.md` に昇格させてください。

---

## [2026-02-26] Agenthelper 初期導入

### 新事実

- `Agenthelper` により `agent/` テンプレートを導入済み
- 適用カタログ: `code`, `comfyui`
- `AGENT_GUIDE.md` の `Selected Catalogs` は `code, comfyui` に更新済み
- `global_notes.md` を本プロジェクト向け前提（LLM 非依存、seed 再現性重視、語彙データ編集前提）で初期化
- ローカルシェルの Python バージョンは `3.12.10`
- 標準テスト実行コマンド候補として `python assets/runner.py all` を state schema に記録

### 決定事項

- このリポジトリでは Agent は `code` と `comfyui` の両方の観点で作業判断する
- ComfyUI ワークフロー/ノード提案時は再現性（seed/設定値）を必ず意識する

### 未解決

- 対象 ComfyUI バージョン/検証環境（OS, ComfyUI 本体）の明文化
- 推奨テスト実行コマンド（`assets/` のどこまでを標準チェックにするか）
- このプロジェクトで維持すべき後方互換性の範囲（ノード名/ポート名/JSON 互換）

### 次アクション

- `state_schema_code.yaml` / `state_schema_comfyui.yaml` に実運用の値を入力（環境・制約・現タスク）
- `memory/global_notes.md` にローカル運用ルール（命名、レビュー基準、対応優先度）を追加
- 初回変更タスク着手時に `change_log.md` / `decisions_log.md` の運用を開始

## [2026-02-27] 偏り監査と抑制実装

### 新事実

- `assets/eval_promptbuilder_v5.py` は `sys` 未importと現行ノードI/F不一致があり、修正して実行可能化
- `tools/run_bias_audit.py` を追加し、8種CSV監査を1コマンドで出力可能にした
- `run_id=20260227_bias_a01` で N=1000 の監査を実行し、`assets/results/audit/20260227_bias_a01/` に出力

### 決定事項

- SceneVariator のタグ候補は重複排除して重み増しを防ぐ
- action_pool は同一小物が過半を占める場合に抽選ペナルティをかける
- ThemeLocationExpander は small props pool / symbolic prop に対して props採用率を抑制する

### 未解決

- `wave_barrel` 条件付きの surfboard 率は依然高め（監査で 0.411765）
- `screen` 系語句の全体率が他語より高め（監査で 0.091）

### 次アクション

- 監査CSVを使って location別の object集中上位を順次再配分
- しきい値（alert閾値）の最終運用値を決定して固定
- 必要なら `tools/run_bias_audit.py` に before/after 比較モードを追加

## [2026-03-06] シーン描写・感情重視 改善計画の作成

### 新事実

- 現行評価として、`assets/results/audit/review_20260306/` に N=800 の bias audit を出力
- `python -m unittest assets.test_fx_cleanup` は通過
- `python -X utf8 assets/validate_compatibility.py` は warnings 付きで通過
- 改善方針ドキュメントとして `assets/scene_emotion_priority_spec.md` を追加
- 次チャットでの実装着手用に `assets/実装チェックリスト版.md` と `assets/進捗.md` を追加

### 決定事項

- 日常系の比率が高いことは仕様上の意図として維持する
- ただし「同じ日常に見える」問題は、broad scene の削減ではなく scene axis と感情軸の強化で対処する
- 感情は garnish 的な添え物ではなく、行動・姿勢・視線・テンプレート構造に影響する重要要素として扱う
- 次チャットでの実装は `P0 -> P1 -> P4 -> P3 -> P2 -> P5 -> P6` を推奨順とする

### 未解決

- `emotion embodiment rate` の具体算出方法
- broad scene の定義方法と daily-life share の算出ルール
- gritty 系 pack の例外許可基準
- `meta_style` をどこまで既定出力から下げるか

### 次アクション

- 次チャット開始時に `assets/進捗.md` の対象フェーズを `in_progress` に更新
- `P0` の既定挙動整理から着手
- フェーズごとに検証ログを `assets/進捗.md` に残す

## [2026-03-06] シーン描写・感情重視 実装 P0-P4 完了

### 新事実

- `P0` を完了し、`SimpleTemplateBuilder` の既定モードを `scene_emotion_priority` として style 非依存に固定
- `P1` を完了し、`vocab/garnish/logic.py` に emotion core / intensity / expression / behavior モデルと `_is_out_of_context` を実装
- `P2` を完了し、daily-life scene axis を `SceneVariator` / `ThemeLocationExpander` に反映、`scene_compatibility.json` の universal daily-life loc も再編
- `P3` を完了し、`mood_map.json` と template 群を scene/person 記述へ差し替え、render 語中心の mood 展開を除去
- `P4` を完了し、`imaginary`・daily-life の `trash / debris`・画面加工系 FX 語を data / cleaner / lint の三層で抑制
- `background_loc_tag_map.json` と `background_alias_overrides.json` に `neon_city_street -> cyberpunk_street` を追加し、lint の参照不整合を解消

### 決定事項

- フェーズ進行は今回ここで停止し、次チャットは `P5` から再開する
- daily-life 比率は維持しつつ、状況差は location の置換よりも action/location の axis 追加で出す方針を採用
- unwanted noun / FX 抑制は runtime cleaner だけでなく、語彙 data と lint でも防ぐ

### 未解決

- `P5` の template 自然文再設計は未着手
- `P6` の daily-life share / broad scene entropy / object concentration / emotion embodiment の定量指標統合は未着手
- `assets/test_vocab_lint.py` には mood suffix coverage と anchor 例外の WARN が残る

### 次アクション

- 次チャット開始時に `assets/進捗.md` で `P5` を `in_progress` に更新
- `nodes_simple_template.py` と `templates*.txt` を 1 本の visual sentence 寄りに再設計
- `P5` 完了後に `P6` で監査指標を追加し、最終の bias audit / compatibility / cleanup を再実行

## [2026-03-06] シーン描写・感情重視 実装 P5 完了

### 新事実

- `SimpleTemplateBuilder` に `subject_clause` / `action_clause` / `scene_clause` を追加し、既定テンプレートを 1 本の visual sentence 構造へ変更
- composition mode は intro/body/end の clause をカンマ結合し、`In/At {loc}, {meta_mood}` 依存の説明調を削減
- `templates.txt` と `vocab/templates_*.txt` を scene visualization 寄りの文型へ差し替え
- `python -m unittest assets.test_composition`、`python -m unittest assets.test_consistency`、`python assets/test_determinism.py`、`python tools/verify_full_flow.py` が通過
- fixed input 20 sample の手動監査で `unique_openers = 6`、mood key 生出力 0 を確認

### 決定事項

- P5 では I/O を変えず、複合プレースホルダーの追加だけで visual sentence 化する
- clause 結合はランダム性を増やすのではなく、既存 seed に従う選択結果の見え方を改善する用途に限定する
- location 展開文と相性の悪い `with {loc} stretching behind her` 系の終端は採用しない

### 未解決

- `P6` の daily-life share / broad scene entropy / emotion embodiment / unwanted noun rate の統合実装は未着手
- template opener の分散は改善したが、P6 で数値監査へ組み込むかは未決定

### 次アクション

- `assets/進捗.md` で `P6` を `in_progress` に更新
- 追加監査指標を `tools/run_bias_audit.py` などへ統合する
- 最終フェーズで bias audit / compatibility / cleanup / determinism を再実行する

## [2026-03-06] シーン描写・感情重視 実装 P6 完了

### 新事実

- `tools/run_bias_audit.py` を final prompt ベースの監査へ拡張し、`audit_prompt_quality.csv` と `audit_quality_metrics.csv` を追加
- quality metrics として `daily_life_share`, `broad_scene_entropy`, `broad_scene_top1_share`, `emotion_embodiment_rate`, `abstract_style_term_rate`, `unwanted_noun_rate`, `disallowed_fx_rate`, `max_object_concentration_final_prompt` を出力
- `assets/results/audit/p6_20260306/` を生成し、`daily_life_share=0.7175`, `emotion_embodiment_rate=0.995`, `abstract_style_term_rate=0`, `unwanted_noun_rate=0`, `disallowed_fx_rate=0` を確認
- `assets/test_bias_audit_metrics.py` を追加し、broad scene 判定・quality hit 検知・gate 行生成を単体テスト化
- `background_packs.json` の `glass of sparkling water` を `glass of chilled water` に置換し、FX 誤検知を解消

### 決定事項

- P6 の品質ゲートは location/action 部分文字列ではなく、garnish/template/cleaner 後の final prompt を基準に評価する
- `trash/debris` は daily-life では failure とするが、backstreet/battlefield/alien crash などの gritty 例外文脈では unwanted noun failure に数えない
- `taking a photo` のような動作は style term に含めず、abstract style は `anime style`, `illustration`, `photorealistic`, `cinematic`, `masterpiece`, `high quality` 系に限定する

### 未解決

- `tropical_beach` の surfboard conditional rate が 0.60 で、`max_object_concentration_final_prompt <= 0.55` の gate は WARN のまま
- `assets/validate_compatibility.py` の unused loc / universal loc coverage 警告は継続

### 次アクション

- 必要なら次タスクで `tropical_beach` の surfboard 偏りを action/background 側で再配分する
- compatibility 側の unused loc と universal coverage を別タスクで整理する
- 以後の変更では `assets/results/audit/p6_20260306/` を比較基準として使う

## [2026-03-06] object concentration 再リファクタリング 事前評価

### 新事実

- 仕様書作成前の評価として `python tools/run_bias_audit.py --sample-count 1000 --seed-start 0 --variation-mode full --location-mode detailed --lighting-mode auto --input-mode canonical --run-id object_eval_20260306` を実行し、`assets/results/audit/object_eval_20260306/` を生成
- `audit_quality_metrics.csv` では `daily_life_share=0.73`, `emotion_embodiment_rate=0.987`, `max_object_concentration_final_prompt=0.764706` を確認
- 主要 hotspot は `karaoke_bar / screen`, `street_cafe / coffee`, `tropical_beach / surfboard`, `commuter_transport / phone` で、background pack 起因が優勢
- `cozy_bookstore / screen`, `fashion_boutique / screen`, `shopping_mall_atrium / screen`, `cozy_living_room / coffee` は監査正規化 artifact と判定
- `school_library / book`, `magic_academy_library / book`, `wave_barrel / surfboard` は loc の主題物として `thematic anchor` 扱いが妥当
- 評価メモとして `assets/object_concentration_refactor_evaluation.md` を追加

### 決定事項

- 次の object concentration 仕様書は、`content redistribution` と `audit normalization redesign` を分離して設計する
- `high_location_bias` alert は loc 選択の偏りを示すため、object concentration 専用仕様の一次対象には含めない
- `display -> screen`、`coffee table -> coffee` のような誤検知は content 側ではなく audit 側で解消する

### 未解決

- anchor-aware threshold を具体的にどこへ置くかは未決定
- background pack と action pool の object 寄与を継続監査用にどう定量化するかは未決定
- `abstract_style_term_rate=0.001` の発生箇所は object concentration 仕様とは別論点だが、次の仕様書で扱うかは未決定

### 次アクション

- 次チャットで `assets/object_concentration_refactor_evaluation.md` を元に専用仕様書を作成
- 一次対象を `karaoke_bar`, `street_cafe`, `tropical_beach`, `commuter_transport` に絞って改修計画を立てる
- 監査側は `screen` / `coffee` 正規化ルールの見直し案を先に定義する

## [2026-03-06] object concentration 再リファクタリング 実装完了

### 新事実

- 新規仕様書として `assets/object_concentration_refactor_spec.md` を追加し、`true_bias_background` / `true_bias_action` / `thematic_anchor` / `audit_artifact` の責務分離を固定
- 検証記録として `assets/object_concentration_refactor_verification.md` を追加し、Stage A-D の検証結果と before/after を記録
- `vocab/data/object_concentration_policy.json` を追加し、background/action redistribution、anchor threshold、audit artifact、phrase-aware normalization の共通 policy layer を導入
- `ThemeLocationExpander` は section-aware weighted selection を読むようになり、`karaoke_bar / screen`, `street_cafe / coffee`, `tropical_beach / surfboard`, `boardroom / coffee`, `concert_stage / microphone` を policy ベースで再配分
- `SceneVariator` は loc-aware action weight を読むようになり、dominant object がない場合も policy penalty が効くよう修正
- `scene_axis.json` の `commute / wait / delay / wrapping_up` から phone / coffee 依存の micro action を外し、`commuter_transport / phone` の真の action bias を低減
- `tools/run_bias_audit.py` は phrase-aware normalization、policy-aware classification/effective threshold、`max_object_concentration_true_bias` を出力するよう拡張
- `python tools/run_bias_audit.py --sample-count 1000 --seed-start 0 --variation-mode full --location-mode detailed --lighting-mode auto --input-mode canonical --run-id object_refactor_20260306_r2` を実行し、`assets/results/audit/object_refactor_20260306_r2/` を生成
- 最終監査で `daily_life_share=0.73`, `emotion_embodiment_rate=0.985`, `max_object_concentration_final_prompt=0.5`, `max_object_concentration_true_bias=0.304348` を確認
- before/after では `karaoke_bar / screen: 0.764706 -> 0.176471`, `street_cafe / coffee: 0.521739 -> 0.304348`, `tropical_beach / surfboard: 0.36 -> 0.08`, `commuter_transport / phone: 0.333333 -> 0.0` を確認

### 決定事項

- object concentration 改修は今後も policy file を基点にし、content 側の redistribution と audit 側の normalization を別レイヤで管理する
- `audit_artifact` は true-bias gate から除外し、`max_object_concentration_true_bias` を主受け入れ指標として併記する
- `thematic_anchor` は raw observability には残しつつ、anchor-aware threshold で判定する
- prompt 内容を壊さずに bias を下げるため、background/action の語彙削除より weighted sampling を優先する

### 未解決

- `abstract_style_term_rate=0.003` は warn のまま残る
- `validate_compatibility.py` の unused loc / universal coverage 警告は継続
- `concert_stage / microphone`、`office_elevator / phone` などは watchlist として継続監視したい

### 次アクション

- 必要なら `abstract_style_term_rate` の発生 source を別タスクで追跡する
- object concentration の継続監視では `assets/results/audit/object_refactor_20260306_r2/` を新しい比較基準に使う
- watchlist loc/object を増やす場合は `vocab/data/object_concentration_policy.json` に寄せて管理する
