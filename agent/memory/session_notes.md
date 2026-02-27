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
