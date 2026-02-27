# Request Template (Common)

依頼を構造化することで、Agent が不要な確認なしに動けるようになります。
すべてのフィールドを埋める必要はありませんが、Purpose と Deliverables は必須です。

---

## テンプレート

```
## Purpose（必須）
何を達成したいか？
例: 第1章の書き出しを3パターン作成したい

## Deliverables（必須）
期待する出力の形式・内容
例: Markdown ファイル 3 つ（draft_a.md / draft_b.md / draft_c.md）、各800文字以内

## Constraints（あれば）
ハードな制約（ツール・サイズ・形式・禁止事項）
例: 外部APIは使わない / 英語禁止 / 既存ファイルは上書きしない

## Context（あれば）
関連する背景・参照すべきファイル・前提情報
例: character_sheet.md のキャラ設定に従うこと

## Priority（あれば）
速さ vs 品質のバランス
例: 品質優先でよい（時間制限なし）
```

---

## 記入例

```
## Purpose
第1章の冒頭シーン（主人公が異世界転移する直前）を書いてほしい

## Deliverables
- ファイル: chapter_1_draft.md
- 長さ: 1000〜1500文字
- 視点: 一人称（主人公「ジェイク」）

## Constraints
- novel/SKILL.md の Do Not セクションに従う
- キャラ設定は memory/global_notes.md を参照

## Context
- 概念シート: concept_sheet.md 参照
- 前章なし（第1章が最初）
```
