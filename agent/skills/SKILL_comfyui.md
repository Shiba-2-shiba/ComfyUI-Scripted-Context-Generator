---
name: comfyui-workflow
description: ComfyUI workflow design, node organization, and reproducibility improvement.
version: 0.2
---

# When To Use

- ComfyUI ワークフローの新規設計・既存整理・再現性向上
- ノード接続のレビューや依存関係の可視化が必要なとき

# Inputs

- `goal`: 達成したい出力（例: "LoRA適用済みのキャラクター画像生成"）
- `constraints`: 制約（例: "VRAM 8GB 以内 / SDXL ベース"）

# Procedure

1. `goal` と `constraints` を確認する。不明点があればユーザーに確認する
2. 既存ワークフロー（JSON）がある場合は読み込んで現状を把握する
3. ノードを論理ブロック（入力 / 処理 / 出力）に分類する
4. 再利用可能な構成として整理する
5. `agent/evals/prompts/p1_structure.txt` の基準でセルフチェックする
6. 依存関係と手順をドキュメント化する

# Outputs

- 整理済みワークフロー（JSON または設計メモ）
- ノード依存関係の説明（ブロック図または箇条書き）
- 再現手順（使用モデル・設定値込み）

# Do Not

- ユーザーの既存ワークフロー JSON を無断で書き換えない
- 制約（VRAM 等）を無視したノード構成を提案しない
- 未検証のモデル・ノードを「動作確認済み」として提示しない
