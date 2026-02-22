# widgets_valuesズレ問題のまとめ（中学生向け）

この文章は、今回の「ワークフロー読み込み時に数値がずれる問題」について、
**どこで起きて、なぜ起きて、どう直したか**を
**フロントエンド / ワークフロー / スクリプト**の3つに分けて、
やさしく説明したものです。

---

## 1. 何が起きていたの？

ComfyUIでワークフローを読み込むと、次のような変な表示が出ました。

- **seed が NaN になる**
- **control（生成後の制御）の値が別の値にすり替わる**
- **Prompt Cleaner の mode が true になる**

これは、**保存されている値の並びがずれてしまった**ためです。

---

## 2. 原因（フロントエンド側）

フロントエンドには、古いワークフローを読みやすくするための
「補正処理（migrate）」があります。

### 2-1. `forceInput` って何？
`forceInput` は「**入力ソケットとして必ず外部からつなぐ前提**」の入力です。  
つまり **UIの入力欄（widget）としては作られない**タイプです。

昔のワークフローでは、  
この `forceInput` でも **ダミー値（使われない値）が
`widgets_values` に入っている**ことがありました。

そのため migrate は、
「**`forceInput` の分は古いダミー値**」と判断して削除します。

### 2-2. seed の control widget は何？
`seed` の近くに出る
**「生成後の制御（randomize / fixed / increment など）」のリスト**
のことです。

これは **フロント側が自動で追加する追加 widget** です。
（ノード定義の中に明示されていなくても作られる）

つまり **「暗黙で追加される」** とは、
**randomize などのリストが自動で増える**という意味です。

### 2-3. なぜズレるのか（簡単な例）

例: `DictionaryExpand` の入力（概念）
- `key`（forceInput）
- `json_path`（widget）
- `default_value`（widget）
- `seed`（widget）
- `control_after_generate`（seed の自動追加 widget）

保存された `widgets_values` がこうだとします：
```
["mood_map.json", "", 0, "randomize"]
```

フロントは
「forceInput があるから、先頭はダミーだ」と判断して
**先頭を削除**します。

その結果は：
```
["", 0, "randomize"]
```

こうなると、
- `json_path` には `""`  
- `default_value` には `0`  
- `seed` には `"randomize"`  
が入ってしまいます。

これが **seed が NaN になったり、control 欄がズレる**原因です。

---

### 2-4. 「一致してしまう長さ」を数字で説明

フロントの migrate は、次のように数えます。

1. **forceInput も含めた“入力の数”**を数える  
2. `seed` がある場合は **control widget も 1 つある**とみなす  
3. その数と `widgets_values` の長さが **ピッタリ一致**したら  
   「古いダミー値が入っている」と判断して **先頭を削除**します

#### 具体例 1: Theme Location Expander

入力定義（概念）:
- `loc_tag` → forceInput
- `seed` → widget
- `control_after_generate` → seed の自動追加 widget
- `mode` → widget

**フロントが数える想定数**
- forceInput も含めた入力数: 3（loc_tag, seed, mode）
- seed の control widget: +1  
**合計 = 4**

**`widgets_values` の長さによる結果**

| `widgets_values` の長さ | migrate 判定 | 結果 |
|---|---|---|
| 4 | 一致 → 先頭削除 | 値がズレる |
| 3 | 不一致 → 削除なし | ズレない |
| 2 | 不一致 → 削除なし | ズレない |

#### 具体例 2: DictionaryExpand

入力定義（概念）:
- `key` → forceInput
- `json_path` → widget
- `default_value` → widget
- `seed` → widget
- `control_after_generate` → seed の自動追加 widget

**フロントが数える想定数**
- forceInput も含めた入力数: 4（key, json_path, default_value, seed）
- seed の control widget: +1  
**合計 = 5**

**`widgets_values` の長さによる結果**

| `widgets_values` の長さ | migrate 判定 | 結果 |
|---|---|---|
| 5 | 一致 → 先頭削除 | 値がズレる |
| 4 | 不一致 → 削除なし | ズレない |
| 3 | 不一致 → 削除なし | ズレない |

---

### 2-5. どうして「短い配列」で回避できるの？

判定は「**長さがピッタリ一致**した時だけ」起きます。  
だから **わざと短くしておけば一致しない → 削除されない**。

これが **回避の理屈**です。

---

## 3. 解決策（ワークフロー側）

フロントが修正できないため、
**ワークフローの `widgets_values` を「短い配列」にする**ことで
「先頭を消される判定」を回避しました。

### 3-1. どうして短くすると回避できるの？

migrate は **「入力数と widgets_values の長さがピッタリ一致する時だけ」**
「先頭（forceInput分）を削除」します。

逆に言うと：

- **長さが一致しない場合は削除しない**

だから **わざと短くしておくと、削除が起きなくなる**のです。

### 3-2. 具体的な動きの例

`DictionaryExpand` の場合：

- 想定数は **5**
- もし `widgets_values` の長さが **5** なら削除が起きる  
- だから **長さを 3 にすると削除されない**  

削除が起きないので、値の並びがズレません。

具体的には、次のようにしました。

- DictionaryExpand  
  変更前: `["mood_map.json", "", 0, "randomize"]`  
  変更後: `["mood_map.json", "", 0]`

- ThemeLocationExpander  
  変更前: `[0, "randomize", "detailed"]`  
  変更後: `[0, "randomize"]`

- PromptCleaner  
  変更前: `["nl", true]`  
  変更後: `["", "nl", true]`

**ポイント**
- 「余計な値を消して短くする」ことで、
  フロントの「先頭削除」が起きない状態にする。
- 値の並びがずれないので、UI表示が正しくなる。

---

## 4. 解決策（スクリプト側）

もしワークフローが壊れていても **ノードが落ちない**ように、
ノードのスクリプト側で「変な値を受けても安全にする」対処を入れました。

やったこと：

- `seed` は **数値に変換できなければ 0 にする**
- `mode` などは **想定外の値なら既定値に戻す**

これで、たとえ `seed="randomize"` のような値が来ても、
**エラーにならず安全に動く**ようになりました。

---

## 5. どんな検証をしたの？

フロントが使えない環境でも検証できるように、
**移行処理のシミュレーションスクリプト**を作成しました。

使ったツール：
- `tools/simulate_widgets_values_migration.py`
- 出力: `tools/widgets_values_simulation_report.json`

このスクリプトで、
「読み込み時にどの値がどうずれるか」を再現しました。

---

## 6. まとめ（中学生向けの一言）

**問題**  
「フロントが勝手に値を消してしまうので、値の順番がずれていた」

**解決**  
「ワークフローの値を短くして、消されない形にした」  
「もし変な値が来ても、スクリプトで安全に直すようにした」

---

## 7. 次の確認ポイント

1. ComfyUIで `ComfyUI-workflow-exmaple.json` を読み込む  
2. 3ノードの表示が正しくなっているか確認する  

もしズレが残る場合は、スクショとノード名を共有すれば
追加の対策が可能です。
