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

## リファクタ後の保守ルール

Phase 1〜6 の整理により、内部責務と source of truth は次で固定しています。

- `core/context_state.py`: `PromptContext.extras` を internal typed state に寄せる adapter
- `location_service.py`: location alias 解決の主経路
- `character_service.py`: named profile と scene compatibility archetype の橋渡し
- `history_service.py`: history 利用 helper
- `prompt_renderer.py`: 最終 prompt clause の組み立て
- `pipeline/content_pipeline.py`: extracted modules への互換 facade。内部実装の default import 先ではなく、compatibility surface としてのみ維持
- `asset_validator.py`: policy と asset のズレ検出

### Source Of Truth

- character:
  `vocab/data/character_profiles.json` を named profile の正、`vocab/data/scene_compatibility.json` を compatibility の正とし、`character_service.py` で統合します。
- location:
  `vocab/data/background_packs.json` の pack key / aliases と `vocab/data/background_alias_overrides.json` を主経路とし、`loc_aliases_canonical.json` / `loc_aliases_legacy.json` / `loc_aliases_fallback.json` の 3 層を `location_service.py` が順序付きで解決します。`background_loc_tag_map.json` は legacy fallback です。
- clothing:
  `vocab/data/clothing_theme_map.json` を theme 解決の正、`vocab/data/clothing_packs.json` を pack 定義の正とします。
- banned terms:
  `vocab/data/policy_terms.json` を canonical source とし、`core/semantic_policy.py` / `nodes_prompt_cleaner.py` / `asset_validator.py` がそこを共有します。

### Deprecated Compatibility

- `meta.style` は legacy read-only metadata です。保持はしますが、prompt 生成では使いません。ingest 時は `warnings` ではなく `notes` に記録します。
- `ContextGarnish.include_camera` は public UI からは削除済みです。旧 workflow 互換のため hidden runtime arg としてのみ残り、実行時は no-op です。
- `ContextInspector` は上記 2 点を deprecated/legacy と明示して表示します。特に `meta.style` は `style(legacy-read-only)=...` と `notes=` で見え、通常の runtime warning には混ぜません。
- `pipeline/content_pipeline.py` は旧 import 先のための facade としてのみ残しています。実装本体は builder / orchestrator 側で、repo-owned caller は原則そちらを直接 import します。
- repo-owned で意図的に facade を残しているのは `assets/test_deprecated_behavior.py` の互換ガードだけです。外部互換を確認するための明示的な例外であり、新しい内部 caller をここへ増やさないでください。

### Asset Editing Rule

- `background_defaults.json`、`background_packs.json`、`clothing_packs.json`、`garnish_base_vocab.json`、`garnish_exclusive_groups.json`、`garnish_micro_actions.json` など banned-domain と衝突しやすい asset は、編集後に `asset_validator.py` を必ず確認します。
- camera / style / render / body-type 語は asset に戻さない前提です。
- false positive 回避は既存 policy に合わせます。たとえば `slim-fit` のような衣装語は body-type ban として潰さないでください。

最小確認コマンド:

```bash
python -c "from asset_validator import validate_assets; print(validate_assets())"
python -m unittest assets.test_asset_validator assets.test_semantic_policy assets.test_prompt_renderer
```

---

## セマンティック生成への移行メモ

このノードは現在、**style / quality / camera / body-type を生成責務から外す**方向で整理しています。

- `meta.style` は **後方互換のため保持**していますが、prompt 生成では使用しません。legacy metadata として `notes` に残し、warning ノイズは増やさない方針です。
- `include_camera` は **public UI から外し、hidden legacy arg としてのみ保持**しています。semantic-only な garnish を返します。
- location alias は `location_service.py` が canonical / legacy / fallback の 3 層で解決します。`background_packs.json` の pack key / `aliases` と `background_alias_overrides.json` が主経路、`background_loc_tag_map.json` は legacy fallback です。
- `tools/validate_prompt_data.py` で clothing / location / action 生成可否と banned-domain 混入を検証できます。
- `asset_validator.py` で policy と JSON asset のズレを静的検出できます。
- `tools/audit_action_diversity.py --scope daily_life --seed-count 32 --enforce-thresholds` で、Phase 3 の 32-seed action 多様性監査をしきい値付きで実行できます。
- `tools/audit_repetition_guard.py --step-count 32 --scenario-count 8 --enforce-thresholds` で、Phase 4 の history-based repetition guard を `loc / action verb / costume signature / template key / object overlap` 単位で監査できます。
- `tools/audit_template_diversity.py --seed-count 32 --enforce-thresholds` で、Phase 5 の `intro / body / end / template_key` 多様性と part 偏りを監査できます。
- `vocab/data/template_catalog.json` により、Phase 5 の prompt builder は `intro / body / end` を意味役割つきで選び、`PromptContext.history` の recent part key を見て骨格反復を下げます。
- `train_station_platform` など action pool 未定義の loc でも、compositional fallback action で loc 適合 action を再生成します。
- `PromptContext.history` には scene / clothing / location / garnish / prompt builder の decision を積み、近傍の loc / action verb / object / template 骨格の重複を抑えます。

今回の refactor で**残したもの**:
- `meta.style` フィールド
- hidden legacy `include_camera` 引数
- `background_loc_tag_map.json` の legacy 読み込み互換
- `pipeline/content_pipeline.py` の import facade

今回の refactor で**無効化したもの**:
- source 選好における style scoring
- prompt assembly における `{meta_style}` 経路
- garnish の camera / lighting / quality 出力
- location expansion における lighting フィールドの user-facing 出力

---

## バリエーション規模（最新計測値）

このノードで作れるプロンプトの幅を、**画像生成でイメージしやすい形**でまとめると次のようになります。

### キャラクターの幅

- **58人分**のキャラクター候補を収録。
- 各キャラクターは、単なる名前だけでなく、**外見・性格・カラーパレット**の情報を持たせており、同じ場所でも雰囲気を変えやすい構成です。

### 場所（ロケーション）の幅

- 場所テーマとしては **58種類** を用意。
- 現行の整合チェック済みデータでも、計測上は **58種類** が有効です。

### アクションの幅

- ロケーションごとに用意される行動候補は **4〜12件（中央値 8、平均 7.6）**。
- キャラクター × 場所 × 行動の組み合わせで、**11,916パターン**のベースシーンを生成できます。

### ガーニッシュと背景の幅

- garnish 系の内部語彙として、mood key **9種**・ユニーク mood tag **172種**・micro action **280種**・effect **22種**・背景ディテール **982種** を持ちます。
- `assets/calc_variations.py --json` の現行出力では、ベースシーンは **11,916 パターン**、アクション候補は **4〜12件（中央値 8、平均 7.6）** です。
- 同じ計測では camera vocabulary universe も **120** と出ますが、これは内部語彙資産の規模です。現行の public prompt surface と `ContextGarnish` UI は camera/framing を前提にしていません。

> 要するに、
> **「キャラ差」×「場所差」×「行動差」** を土台に、
> さらにムードや細かな仕草、背景ディテールを重ねてバリエーションを増やせる設計です。

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
- `vocab/data/background_packs.json`: location pack / aliases の主 source
- `vocab/data/background_alias_overrides.json`: location alias override
- `vocab/data/action_pools.json`: ロケーション別アクション
- `vocab/data/garnish_*.json`: ガーニッシュ語彙

編集前後の判断に迷ったら、`REPO_STRUCTURE.md` と `REFACTOR_SPEC.md` を先に確認してください。

---

## ライセンス

このプロジェクトは **Apache License 2.0** の下で公開されています。詳細は `LICENSE` を参照してください。
