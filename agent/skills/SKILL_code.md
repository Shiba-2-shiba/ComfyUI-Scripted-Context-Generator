---
name: code-maintainer
description: Codebase refactor, bugfix, and feature addition workflow.
version: 0.2
---

# When To Use

- バグ修正・リファクタリング・機能追加・テスト追加
- コードレビューや影響調査が必要なとき

# Inputs

- `repo_path`: 対象リポジトリのルートパス
- `task`: 変更内容の要約（例: "ログイン処理のバグ修正"）

# Procedure

1. `repo_path` が存在するか確認する
2. 変更対象のファイルを特定する（grep・find を活用）
3. 影響範囲を洗い出す（依存ファイル・呼び出し元を確認）
4. テスト方針を整理する（既存テストで十分か、新規テストが必要か）
5. 変更を実装する
6. テストを実行して結果を確認する

   ```
   # Python の場合
   python -m pytest tests/ -v

   # Node.js の場合
   npm test

   # 個別ファイルの場合
   python -m pytest tests/test_target.py -v
   ```

7. 変更点の要約を作成する

# Outputs

- 変更ファイルの一覧と各変更点の要約
- テスト実行結果（Pass/Fail・エラーメッセージ）
- 残存リスク・未対応事項のリスト

# Do Not

- テストが失敗したまま変更を完了としない
- スコープ外のファイルをリファクタリングしない
- 既存の公開インターフェース（関数シグネチャ等）を無断で変更しない
- バックアップなしに元ファイルを削除しない
