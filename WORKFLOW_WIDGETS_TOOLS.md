# widgets_values 自動チェック/修正ツール

このドキュメントは、作成した自動チェック/修正スクリプトの **機能と使い方** をまとめたものです。

## 対象スクリプト
- `tools/check_widgets_values.py`
- `tools/scan_workflows_widgets.py`
- `tools/fix_workflows_widgets.py`

## 1. `tools/check_widgets_values.py`
**目的:**  
単一ワークフロー（`ComfyUI-workflow-exmaple.json`）内のカスタムノードに対して、`widgets_values` の整合性を検証します。

**チェック内容**
- `INPUT_TYPES()` に基づく期待ウィジェット数との一致
- `forceInput` による旧形式ダミー値混入の検出
- `seed` などの **control widget** 混入の検出
- INT/FLOAT への `"randomize"` 文字列や NaN 混入

**実行方法**
```bash
python tools/check_widgets_values.py
```

**出力**
- 問題がなければ `OK` を表示
- 問題があればノードID・型・原因を表示

---

## 2. `tools/scan_workflows_widgets.py`
**目的:**  
指定フォルダ以下の **全ワークフロー JSON** をスキャンし、`widgets_values` の不整合を検出します。

**特徴**
- 既定ではリポジトリ配下の `.json` を走査
- 除外ディレクトリ: `.git`, `node_modules`, `dist`, `build`, `.venv`, `__pycache__`
- 結果を `tools/widgets_values_report.json` に保存

**実行方法**
```bash
python tools/scan_workflows_widgets.py
```

**任意のパス指定**
```bash
python tools/scan_workflows_widgets.py C:\path\to\workflows
```

**出力**
- 問題がなければ `OK` と件数
- 問題があれば検出数とレポートパス

---

## 3. `tools/fix_workflows_widgets.py`
**目的:**  
`widgets_values` の典型的なズレを **自動修正** します。

**自動修正の対象**
- `forceInput` に由来するダミー値が含まれているケース
- `seed` の control widget が含まれているケース
- 末尾に `true/false` が混入しているケース（旧形式）

**実行方法**
```bash
python tools/fix_workflows_widgets.py
```

**任意のパス指定**
```bash
python tools/fix_workflows_widgets.py C:\path\to\workflows
```

**出力**
- 修正したノード数とファイル数を表示

---

## 推奨ワークフロー
1. `python tools/scan_workflows_widgets.py` で全体スキャン
2. 問題があれば `python tools/fix_workflows_widgets.py` で修正
3. 再度 `scan` を実行して問題が解消したか確認

---

## 注意点
- これらのツールは **カスタムノード定義に基づいて検証**します。
- ComfyUI 本体のノードや外部ノードは対象外です。
- `widgets_values` の並びが特殊なケースは、手動確認が必要です。

## 現状の未解決事項
- UI上で **control-after-generate** の値がずれる現象が残っています。
  - 例: `GarnishSampler` の control欄に `max_items` が入る
  - 例: `ThemeClothingExpander` の control欄に `outfit_mode` が入る
- JSON上は `seed` の直後に `"randomize"` を挿入しているが、UI反映で改善されない。
- 次回は **ComfyUI_frontend の widget生成・保存の流れ**を UI表示と突き合わせて確認する必要があります。

## フロント修正ができない場合の回避策
以下の短い `widgets_values` を使い、migrate の削除判定を回避する。

- DictionaryExpand: `["mood_map.json", "", 0]`
- ThemeLocationExpander: `[0, "randomize"]`
- PromptCleaner: `["", "nl", true]`

検証:
```bash
python tools/simulate_widgets_values_migration.py
```
レポート: `tools/widgets_values_simulation_report.json`

## 運用ルール（再発防止）
forceInput と seed/noise_seed を持つノードは、
`widgets_values` を「想定長さにピッタリ一致させない」こと。

理由:
- migrate が長さ一致時に「先頭はダミー」と判断して削除するため

手順:
- `tools/simulate_widgets_values_migration.py` で事前チェック
- もし一致していれば `widgets_values` を短く調整する
