# widgets_values 不整合の原因と対処

## 何が起きているか
ComfyUI_frontend では、ワークフロー読み込み時に `widgets_values` を補正します。  
この補正は **`forceInput` がある入力を「古いワークフローのダミー値」とみなして削除**する仕組みです。

そのため、**`widgets_values` の長さが「forceInput を含む入力数」と一致すると、先頭側の値が削除されます。**  
結果として、値の位置がズレて `seed` が `"randomize"` になったり、`mode` が不正値扱いになったりします。

## 関連コード（ComfyUI_frontend）
- `src/utils/litegraphUtil.ts`
  - `migrateWidgetsValues()` が `forceInput` を基準に値を削除する
- `src/lib/litegraph/src/LGraphNode.ts`
  - `configure()` が `widgets_values` を順に widget へ適用する

## なぜ ThemeLocationExpander / DictionaryExpand で壊れるか
これらのノードは `forceInput` を含みます。

- **ThemeLocationExpander**
  - 入力: `loc_tag (forceInput)`, `seed`, `mode`
  - `widgets_values` が 3 つあると `loc_tag` 分が削除される
  - その結果 `seed` に `"randomize"` が入り **NaN** になる

- **DictionaryExpand**
  - 入力: `key (forceInput)`, `json_path`, `default_value`, `seed`
  - `widgets_values` が 4 つあると `key` 分が削除される
  - `json_path` が空扱いになる、`default_value` が数値になる

## 対処方針
**`widgets_values` を forceInput を含まない長さにする**  
（= 先頭のダミー値を入れない）

例:
- ThemeLocationExpander: `[0, "detailed"]`
- DictionaryExpand: `["mood_map.json", "", 0]`

## 回避策（フロント修正が不可の場合）
フロントで `seed` の暗黙 control widget が考慮されないため、
`widgets_values` の長さが一致すると先頭が削除されることがある。
以下の「短い配列」にすることで削除判定を回避できる。

推奨 widgets_values:
- DictionaryExpand: `["mood_map.json", "", 0]`
- ThemeLocationExpander: `[0, "randomize"]`
- PromptCleaner: `["", "nl", true]`

検証:
- `python tools/simulate_widgets_values_migration.py`
- レポート: `tools/widgets_values_simulation_report.json`

## control_after_generate / seed の補足
フロントエンド側では `seed` / `noise_seed` に **自動で control widget** が追加されます。  
この値は通常シリアライズされませんが、古いワークフローでは
`widgets_values` に混入している場合があります。

その場合、値の並びは以下の順序になります。
- `seed`, `seed__control`, その後に他の widget

## 自動チェック
`tools/check_widgets_values.py` を追加しました。

このスクリプトは、カスタムノードの `INPUT_TYPES()` を参照し、
`widgets_values` の長さや型のズレを検出します。

実行:
```bash
python tools/check_widgets_values.py
```

## 現状の未解決事項（要再調査）
- UI上で **control-after-generate** の値がずれる現象が残っています。
  - 例: `GarnishSampler` で control欄に `max_items` が入る
  - 例: `ThemeClothingExpander` で control欄に `outfit_mode` が入る
- JSON上は `seed` の直後に `"randomize"` を挿入しているが、UI反映で改善されない。
- 次回は **ComfyUI_frontend の widget生成・保存の流れ**（migrate/serialize/validate）を
  UI表示と突き合わせて、実際の適用順を確認する必要がある。
