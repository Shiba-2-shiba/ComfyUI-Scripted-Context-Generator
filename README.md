# ComfyUI-Scripted-Context-Generator

LLMに依存せず、ルールベースで自然言語プロンプトを構築する ComfyUI カスタムノード群です。  
This is a ComfyUI custom-node pack that generates natural-language prompts via deterministic/rule-based logic (no LLM required).

## 重要な前提 / Important Notice

- このカスタムノードは**女性を主人公としたシーン向けの SFW 自然言語プロンプト生成**を目的に、作者が**個人的に作成**したものです。
- 収録語彙やシーン内容は最小限に留めており、**内容の追加・調整は各自で実施してください**（`vocab/data/*.json` や `templates.txt` などを編集）。
- 生成結果の最終確認・利用判断は利用者自身の責任で行ってください。

## 概要

タグ列（例: `1girl, solo, red hair`）をそのまま使うのではなく、以下のような文章化を想定しています。

- 例: `A solo girl with long straight hair and green eyes. She is reading a book by the window...`

主な構成は次の3点です。

1. `prompts.jsonl` などのデータをシード付きで抽選
2. 各種 Expander で衣装・背景・ムードを展開
3. テンプレートへ埋め込み、Cleaner で文面を整形

## 主な機能

- **LLM不要の軽量動作**: Pythonロジックのみで生成。APIキー不要。
- **シード再現性**: 多くのノードが `seed` 入力を持ち、再現可能な抽選を実施。
- **自然言語テンプレート構築**: `SimpleTemplateBuilder` で文テンプレート組み立て。
- **シーン整合性の補助**: `SceneVariator` が `scene_compatibility.json` と `action_pools.json` を使ってロケーション・行動を調整。
- **衣装/背景展開**: `ThemeClothingExpander` / `ThemeLocationExpander` が `vocab/data` から語彙を展開。
- **追加描写（Garnish）**: アクション・ムードに応じてポーズ/微表情語彙を追加。

## 同梱ノード（概要）

- `PackParser`  
  `prompts.jsonl`（または入力JSON）から `subj / costume / loc / action / meta_*` を分解。

- `SimpleTemplateBuilder`  
  プレースホルダ（`{subj}` など）で自然文を構築。未指定時は `templates.txt` からランダム読込。

- `DictionaryExpand`  
  `mood_map.json` などの辞書JSONをキー展開。値が配列ならシード抽選。

- `ThemeClothingExpander` / `ThemeLocationExpander`  
  テーマやロケーションタグから詳細文を生成（`vocab/` 配下を使用）。

- `SceneVariator`  
  互換テーブルを使ってロケーション候補を変更し、必要に応じて行動文も差し替え。

- `GarnishSampler` / `ActionMerge`  
  補助描写の生成と既存 Action への連結。

- `PromptCleaner`  
  句読点・空白・空括弧などを整理して最終文を安定化。

- `CharacterProfileNode`  
  キャラクタープロファイルから外見・性格・カラーパレットを抽出。

## インストール

1. `ComfyUI/custom_nodes/` にこのリポジトリを配置
2. ComfyUIを再起動
3. ノード一覧で `prompt_builder` 系カテゴリを確認

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/<your-account>/ComfyUI-Scripted-Context-Generator.git
```

## 基本的な使い方（推奨フロー）

1. `PackParser` でベース要素を取得（空入力なら `prompts.jsonl` を使用）
2. `ThemeClothingExpander` / `ThemeLocationExpander` でディテール強化
3. `GarnishSampler` で動作ニュアンスを追加
4. `SimpleTemplateBuilder` で文を組み立て
5. `PromptCleaner` で最終整形

## データファイルと編集ポイント

### ルート直下

- `templates.txt` : 文テンプレート集
- `prompts.jsonl` : ベースシーン候補
- `mood_map.json` : ムードキー辞書

### `vocab/data/`

- `character_profiles.json` : キャラ外見・性格・色
- `scene_compatibility.json` : シーン互換/除外ルール
- `action_pools.json` : ロケーション別アクション
- `clothing_*.json`, `background_*.json` : 衣装・背景語彙
- `garnish_*.json` : 補助描写語彙

> 補足: 多くのノードは相対パス入力時、ノードファイル基準で解決します。通常はファイル名のみ（例: `mood_map.json`）で利用可能です。

## 既知の注意点

- 以前の説明で `templete.txt` / `prompt.jsonl` と書かれているケースがありますが、現行ファイル名は **`templates.txt` / `prompts.jsonl`** です。
- 本ノードは女性主人公・SFW寄りの設計思想です。用途に応じた語彙拡張は各自で実施してください。

## ライセンス

このプロジェクトは **Apache License 2.0** の下で公開されています。詳細は `LICENSE` を参照してください。
