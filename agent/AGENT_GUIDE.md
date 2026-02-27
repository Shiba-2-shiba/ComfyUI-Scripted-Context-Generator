# Agent Guide (Common)

このフォルダは全プロジェクト共通のベースです。
`compose_agent_package.py` によって `<project>/agent/` としてセットアップされます。

---

## Agent が最初に読む順番

1. **このファイル（AGENT_GUIDE.md）** — 全体像を把握する
2. **personality.md** — アクティブなパーソナリティを確認する
3. **decision_rules.md** — 行動制約と安全ルールを確認する
4. **state_schema_*.yaml** — プロジェクト固有の状態・制約・進捗を確認する
5. **skills/SKILL_*.md** — 今のタスクに対応するスキル手順を確認する
6. **memory/global_notes.md** — このプロジェクト固有の不変情報を確認する
7. **memory/session_notes.md** — 前セッションの引き継ぎ事項を確認する

---

## 各ファイルの役割

| ファイル | 役割 | 更新タイミング |
|----------|------|----------------|
| `personality.md` | Agentの応答スタイル定義 | プロジェクト開始時に1回 |
| `decision_rules.md` | 行動の判断基準・安全ルール | 変更時のみ |
| `state_schema_*.yaml` | プロジェクト固有の状態スキーマ（制約・進捗・設定） | 状態変化時に更新 |
| `compaction_policy.md` | セッション記憶の圧縮ルール | 変更時のみ |
| `naming_conventions.md` | ファイル・フォルダ名のルール | 変更時のみ |
| `request_template.md` | 依頼を構造化するテンプレート | 依頼のたびに参照 |
| `memory/global_notes.md` | プロジェクト全体の不変情報 | 重要決定時に更新 |
| `memory/session_notes.md` | セッション中の作業メモ | セッションごとに更新・圧縮 |
| `decisions_log.md` | 重要な判断の履歴 | 重要決定のたびに追記 |
| `change_log.md` | ファイル変更の履歴 | 変更のたびに追記 |
| `evals/` | スキル出力品質の検証プロンプト | evalを実行するとき参照 |
| `skills/SKILL_*.md` | カタログ固有のスキル手順 | タスク開始時に参照 |

---

## セッション開始・終了のチェックリスト

### セッション開始時
- [ ] `session_notes.md` の未解決事項を確認
- [ ] `global_notes.md` のプロジェクト制約を確認
- [ ] 今のタスクに対応する `skills/SKILL_*.md` を確認

### セッション終了時
- [ ] `session_notes.md` を `compaction_policy.md` のルールに従って更新
- [ ] 重要な決定があれば `decisions_log.md` に追記
- [ ] ファイルを変更した場合は `change_log.md` に追記

---

## Selected Catalogs
- code, comfyui

