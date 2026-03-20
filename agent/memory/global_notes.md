# Global Notes (Project)

このファイルには **プロジェクト全体で変わらない制約・ルール・前提条件** を記録します。
セッションをまたいで有効な情報のみを書いてください。

---

## プロジェクト基本情報

- プロジェクト名: `ComfyUI-Scripted-Context-Generator`
- 種別: ComfyUI カスタムノード集（プロンプト構築支援）
- 主目的: LLM 非依存のルールベース/決定論的ロジックで自然言語プロンプトを構築する
- 主言語: Python（ComfyUI custom nodes）
- ドキュメント言語: 日本語中心（一部英語併記）

## 技術方針（不変に近い前提）

- 外部 LLM に依存しない設計を維持する
- 再現性を重視するため、乱択は seed ベースで制御する
- ファイルベース語彙（`vocab/`、`templates.txt`、`prompts.jsonl`）を差し替え/編集して拡張する前提
- upstream `ComfyUI` / `ComfyUI_frontend` は差し替え前提で扱い、この repo 側で検証資産を保持する
- ComfyUI のカスタムノードとして使うため、保存済み workflow 互換性を壊す変更は慎重に扱う

## 生成フローの基準

- 推奨パイプライン順序:
  `ContextSource` -> `ContextCharacterProfile` -> `ContextSceneVariator`
  -> `ContextClothingExpander` / `ContextLocationExpander` / `ContextMoodExpander`
  -> `ContextGarnish` -> `ContextPromptBuilder` -> `PromptCleaner`
- 現在の公開面は `nodes_context.py` と `nodes_prompt_cleaner.py` のみ
- compat / transition / bridge ノードは退役済みで、archive と historical note にのみ残す
- 「未検証の挙動」を「動作確認済み」と表現しない

## データ/資産編集時の注意

- 主な編集ポイント:
  `templates.txt`, `prompts.jsonl`, `mood_map.json`, `vocab/data/*.json`
- 語彙データ拡張時はキー名や参照関係の互換性を優先する
- 破壊的変更を避けるため、必要に応じて `assets/` / `tools/` / `verification/` の検証を行う
- 既存のワークフロー JSON やユーザー設定を無断で上書きしない
- historical workflow fixture や旧 spec は `assets/archive/` / `tools/archive/`
  / `docs/context_refactor/archive/` に寄せ、live surface に戻さない

## コンテンツ前提

- 同梱語彙は作者用途（女性主人公・SFW 寄り）に寄った初期実装
- 追加語彙/拡張は利用者側で実施可能な設計
- 最終的な生成結果の確認と利用判断は利用者責任

## Agent 運用メモ

- 実装変更時は `code` 観点（回帰防止）と `comfyui` 観点（ワークフロー再現性）を両立して判断する
- 変更提案時は「対象ノード」「入力/出力影響」「seed 再現性への影響」を明記する
- 語彙/テンプレート変更時は、コード変更と同等に影響範囲を説明する
- 現行 baseline は `ComfyUI-workflow-context.json` のみで、workflow sample manifest も context-only 前提
- frontend / GUI 検証は repo-local `verification/` を source-of-truth とし、
  実行前に `tools/sync_upstream_verification_assets.ps1` で upstream frontend に同期する
