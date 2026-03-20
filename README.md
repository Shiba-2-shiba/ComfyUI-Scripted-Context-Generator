# ComfyUI-Scripted-Context-Generator

LLM に依存せず、**ルールベース + シード再現**で自然言語的プロンプトを構築する ComfyUI カスタムノード集です。  
This custom-node pack generates natural-language prompts via deterministic/rule-based logic (no LLM required).

---

## 重要な前提 / Important Notice

- 本リポジトリは、作者の用途（女性主人公・SFW寄り）向けに設計された語彙セットを同梱しています。
- 収録語彙はあくまで初期実装です。運用用途に合わせて `vocab/data/*.json` や `templates.txt` を編集してください。
- プロンプトの追加依頼については対応は原則行いません。
- プロンプトの追加・拡張は個人で行うことが可能です。このカスタムノードは、Google antigravityをメインに使用して作成をしているため、調整したい場合はGoogle antigravityを使うと楽だと思われます。
- 生成結果の最終確認・利用判断は利用者自身の責任で行ってください。

---

## このリポジトリの現在地

従来の「テンプレート置換」中心から、以下のように強化されています。

- **context-first を主系として確立**: `context_json` を中心に受け渡す新ノード群を正式系として扱い、今後の機能追加先もここに集約します。
- **legacy/bridge は退役済み**: 旧来の compat ノードと bridge ノードは active surface から外れ、現在の公開面は context-first のみです。
- **検証 baseline も context-only**: active workflow sample と frontend / GUI round-trip の検証対象は `ComfyUI-workflow-context.json` のみです。
- **語彙モジュール分離**: `vocab/` 配下に衣装・背景・ガーニッシュ語彙を分割し、データ差し替えで拡張しやすい構成。
- **検証資産の整備**: `assets/` にユニットテスト、整合性検証、分布検証、ベースライン生成を集約。
- **全面移行の準備完了**: schema, workflow asset, frontend save/reload, GUI round-trip まで検証済みで、以後は新規系に寄せて改修を進める段階です。

---

## バリエーション規模（最新計測値）

このノードで作れるプロンプトの幅を、**画像生成でイメージしやすい形**でまとめると次のようになります。

### キャラクターの幅

- **58人分**のキャラクター候補を収録。
- 各キャラクターは、単なる名前だけでなく、**外見・性格・カラーパレット**の情報を持たせており、同じ場所でも雰囲気を変えやすい構成です。

### 場所（ロケーション）の幅

- 場所テーマとしては **58種類** を用意。
- そのうち、現在の整合チェック済みデータとして実際に組み合わせ計算へ使われている場所は **45種類** です。

### アクションの幅

- ロケーションごとに用意される行動候補は **4〜12件（中央値6、平均7.07）**。
- キャラクター × 場所 × 行動の組み合わせで、**6,208パターン**のベースシーンを生成できます。

### 構図・演出の幅

- カメラ構図（アングル × フレーミング）は **120パターン**。
- したがって、ベースシーン 6,208 に構図だけを掛けても、**744,960通り**の見え方が期待できます。
- さらに演出語彙として、ムード **13種**・マイクロアクション **280種**・エフェクト **22種**・背景ディテール **680種** を持つため、最終的な表現幅はより大きくなります。

> 要するに、
> **「キャラ差」×「場所差」×「行動差」×「構図差」** を土台に、
> さらにムードや細かな仕草を重ねてバリエーションを増やせる設計です。

---

## 主なノード

### Primary Nodes

- `ContextSource`  
  `prompts.jsonl` または JSON 文字列から `context_json` を生成する、context-first 系の起点ノードです。

- `ContextCharacterProfile`  
  キャラ外見・性格・パレットを `context_json` に反映します。

- `ContextSceneVariator` / `ContextClothingExpander` / `ContextLocationExpander` / `ContextMoodExpander` / `ContextGarnish`  
  シーン変化、衣装展開、場所展開、ムード展開、補助描写追加をすべて `context_json` 上で行います。

- `ContextPromptBuilder` / `ContextInspector`  
  `context_json` から最終プロンプトを組み立てるノードと、中身を確認するデバッグノードです。

- `PromptCleaner`  
  句読点、空白、不要区切りなどをルールベースで整形。

---

## 基本フロー

### 新規開発フロー

新規 workflow は `Context*` 系のみを使う前提で構成してください。

1. `ContextSource` で `context_json` を生成
2. `ContextCharacterProfile` でキャラクター情報を追加
3. `ContextSceneVariator` でシーン整合性を調整
4. `ContextClothingExpander` / `ContextLocationExpander` / `ContextMoodExpander` / `ContextGarnish` で描写を拡張
5. `ContextPromptBuilder` で自然言語文に組み立て
6. `PromptCleaner` で最終整形

推奨サンプル:
- `ComfyUI-workflow-context.json`

### 最終方針

このリポジトリは、最終的に旧来の field-by-field 系から `context_json` 中心の新規設計へ全面移行する想定です。

1. 新機能は `Context*` 系と shared `pipeline/` にのみ追加します。
2. compat ノードは退役済みで、以後は再導入しません。
3. bridge ノードも退役済みで、今後の移行導線は historical note としてのみ保持します。
4. workflow baseline と round-trip 検証は `ComfyUI-workflow-context.json` のみです。

---

## 移行ロードマップ

1. `Context*` 系をこのリポジトリの正式 API として固定する
2. 既存 workflow は historical reference とし、新規運用は `context_json` ベースへ統一する
3. README・sample workflow・検証導線を新規系中心に保つ
4. transition/compat の historical note は archive と docs に限定する
5. その後の機能追加は新規設計版の上で継続する

---

## 検証スクリプト（抜粋）

`assets/` には以下の検証系スクリプトがあります。

- 単体テスト: `test_schema.py`, `test_composition.py`, `test_prompt_cleaner.py` など
- 整合性検証: `verify_integrated_flow.py`, `verify_consistency.py`, `verify_location_quality.py`
- 分布確認: `test_roulette_distribution.py`, `verify_color_distribution.py`
- KPI/規模評価: `evaluate_kpi.py`, `calc_variations.py`

必要に応じて CI に組み込むことで、語彙拡張時の破壊的変更を早期検出できます。

---

## インストール

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/<your-account>/ComfyUI-Scripted-Context-Generator.git
```

1. `ComfyUI/custom_nodes/` に配置
2. ComfyUI を再起動
3. ノード一覧で `prompt_builder` 系カテゴリを確認

---

## データ編集ポイント

- `templates.txt`: 文テンプレート
- `prompts.jsonl`: ベースシーン候補
- `mood_map.json`: ムード辞書
- `vocab/data/character_profiles.json`: キャラ設定
- `vocab/data/scene_compatibility.json`: シーン互換ルール
- `vocab/data/action_pools.json`: ロケーション別アクション
- `vocab/data/garnish_*.json`: ガーニッシュ語彙

---

## ライセンス

このプロジェクトは **Apache License 2.0** の下で公開されています。詳細は `LICENSE` を参照してください。
