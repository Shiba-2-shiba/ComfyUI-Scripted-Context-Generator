# Prompt IR Refactor Specification

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-19

関連文書:

- `CURRENT_STATUS.md`
- `REPO_STRUCTURE.md`
- `docs/prompt_ir_refactor/progress.md`
- `docs/prompt_ir_refactor/tasks.md`
- `docs/semantic_epig/refactor_spec.md`
- `docs/repository_cleanup/spec.md`

参照したローカル論文 PDF:

- `Autonomous Exploration and Reasoning for ComfyUI Workflows.pdf`
- `Long-Text-to-Image Generation via Compositional Prompt Decomposition.pdf`
- `Text-to-Image Diffusion Model against NSFW Generation.pdf`
- `Training-Free Object-Background Compositional T2I via Dynamic Spatial Guidance and Multi-Path Pruning.pdf`
- `Training-Free Text-to-Image Compositional Food Generation via Prompt Grafting.pdf`

---

## 1. 目的

このリファクタの目的は、LLM を使わず、既存のスクリプト生成方針を維持したまま、
自然言語 prompt の構成品質を上げることである。

中核方針:

```text
Prompt IR を構造化する
  -> 複数候補を deterministic に生成する
  -> script validator で採点する
  -> 最良候補を選ぶ
  -> DebugInfo / audit に理由を残す
```

この波は、論文のモデル内部技術を移植するものではない。
論文から取り込むのは、次の設計思想に限定する。

- PRISM: long prompt を constituent components に分解する
- ComfySearch: validation-guided construction と state-aware repair
- Object-Background compositional T2I: foreground / background entity split と multi-path pruning
- Prompt Grafting: layout-first / detail-later の二段構成
- DDiffusion: keyword block ではなく risk family / concept distribution で見る

---

## 2. Non-Goals

このリファクタでは次を行わない。

- LLM decomposition の導入
- CLIP / MLP / embedding model の導入
- diffusion sampling 内部の attention / guidance 操作
- model fine-tuning
- ComfyUI workflow 自動生成 agent
- public `Context*` node input/output spec の変更
- `PromptContext` JSON schema の破壊的変更
- camera / quality / render effect / body-type prompt の復活
- base variation sizing の意図的変更

---

## 3. Current Code Anchors

現状の主な接続点:

- `core/schema.py`: `PromptContext`, `DebugInfo`
- `pipeline/prompt_orchestrator.py`: `build_prompt_from_context()`
- `prompt_renderer.py`: `build_prompt_text()`, semantic family budget, solo support filtering
- `core/solo_safety.py`: solo duplicate / other-person risk detection
- `core/semantic_families.py`: semantic family detection and budget
- `pipeline/context_pipeline.py`: scene / garnish / history decisions
- `pipeline/action_generator.py`: action slot generation and solo-safe filtering
- `pipeline/location_builder.py`: location segment selection and background fragments

既存の良い土台:

- `PromptContext.history` に `DebugInfo` を積める
- semantic family budget が既にある
- solo safety の risk flags が既にある
- action / location / clothing / personality に semantic EPIG debug がある
- audit / validation tool を `tools/` と `assets/test_*.py` で維持する文化がある

既存の制約:

- `prompt_renderer.py` は最終文字列化と安全化が混ざりやすい
- foreground / background / props / garnish が最終 prompt では混ざる
- solo safety は regex と phrase-level 判定に寄っている
- 複数候補を作って評価する標準構造がない

---

## 4. Literature-To-Design Mapping

### 4.1 PRISM -> Prompt IR component decomposition

取り込む思想:

- long prompt は monolithic に扱わない
- subject, scene, background, spatial relation などを component として扱う
- component ごとに budget と responsibility を持たせる

このリポでの形:

```text
PromptIR
  subject
  character_profile
  clothing
  foreground_action
  object_relation
  location_core
  background_context
  props
  mood
  garnish
```

### 4.2 ComfySearch -> validation-guided prompt construction

取り込む思想:

- one-shot construction ではなく、段階ごとに検証する
- state-aware validator を通してから次へ進む
- diagnostic feedback を debug に残す
- branching は不確実性が高い箇所に限定する

このリポでの形:

```text
build PromptIR
  -> validate components
  -> repair/drop only failed components
  -> render candidates
  -> score
  -> select
```

### 4.3 Object-Background compositionality -> entity split and pruning

取り込む思想:

- foreground と background を独立した意味単位として扱う
- foreground entity set と background entity set を分ける
- 複数 path を評価し、object-background alignment が悪いものを prune する

このリポでの形:

```text
N_obj:
  subject entity
  action object
  held/used object
  clothing object-like terms

N_bg:
  location objects
  props
  crowd/social/background entities
  environmental context
```

### 4.4 Prompt Grafting -> layout-first rendering

取り込む思想:

- early layout と later detail を分ける
- spatial cue だけに頼らず、layout skeleton を先に作る
- detail は skeleton を壊さない範囲で追加する

このリポでの形:

```text
layout clause:
  subject placement
  location core
  foreground/background relationship

detail clauses:
  clothing
  action object
  props
  mood
  garnish
```

### 4.5 DDiffusion -> risk family and local sanitization

取り込む思想:

- keyword block だけに頼らない
- binary reject ではなく、問題 component だけを sanitize する
- benign detail は残す
- concept family 単位で risk を見る

このリポでの形:

```text
risk_family:
  other_person
  crowd
  social_interaction
  family_artifact
  mirror_clone
  ineffective_motion
  plural_prop_overload
  foreground_background_conflict
```

---

## 5. Target Design

### 5.1 Prompt IR

初期実装では dataclass か dict-based payload のどちらかを選ぶ。
public `PromptContext` JSON compatibility を守るため、最初は `extras` / debug payload に閉じる。

Candidate shape:

```python
PromptComponent = {
    "name": "background_context",
    "text": "quiet cafe tables near the window",
    "source": "location_builder",
    "entities": ["cafe tables", "window"],
    "families": ["background_context"],
    "risk_families": [],
    "budget_cost": 1,
}

PromptIR = {
    "subject": [PromptComponent],
    "clothing": [PromptComponent],
    "foreground_action": [PromptComponent],
    "object_relation": [PromptComponent],
    "location_core": [PromptComponent],
    "background_context": [PromptComponent],
    "props": [PromptComponent],
    "mood": [PromptComponent],
    "garnish": [PromptComponent],
}
```

### 5.2 Prompt Candidate

```python
PromptCandidate = {
    "candidate_id": "seed:42:branch:1",
    "ir": PromptIR,
    "rendered_text": "...",
    "scores": {
        "solo_conflict": 0,
        "plural_artifact": 1,
        "foreground_background_alignment": 8,
        "semantic_family_budget": 9,
        "layout_order": 8,
        "location_object_consistency": 8,
        "prompt_length_budget": 7,
    },
    "total_score": 41,
    "dropped_components": [],
    "warnings": [],
}
```

### 5.3 Validators

初期 validator は read-only audit として作る。

Validator families:

- `solo_conflict_score`
- `plural_artifact_score`
- `foreground_background_alignment_score`
- `semantic_family_overload_score`
- `layout_order_score`
- `location_object_consistency_score`
- `prompt_length_budget_score`

重要:

- validator は最初から prompt を変更しない
- report だけを出す
- report が安定してから candidate selection に使う

### 5.4 Candidate Branching

branch は固定 seed から deterministic に作る。
random call order の変化で既存挙動が壊れないよう、branch 専用 seed label を使う。

```text
branch_seed = mix_seed(seed, "prompt_candidate:{branch_index}:{component_name}")
```

初期 branching 対象:

- background_context
- props
- garnish
- action surface

branch しない対象:

- subject identity
- public node I/O
- variation scope

### 5.5 Layout-First Renderer

renderer は次の順序を目標にする。

```text
layout skeleton:
  subject + location_core + foreground_action

detail pass:
  clothing + object_relation + props

atmosphere pass:
  mood + garnish + background_context
```

ただし既存 prompt snapshots を壊しやすいため、最初は passive mode の audit で比較する。

### 5.6 Risk Family Policy

`core/solo_safety.py` を肥大化させず、risk family を data/policy 化する。

Candidate file:

```text
vocab/data/prompt_risk_families.json
```

最初の目的:

- `family photos`
- `people`
- `friends`
- `staff`
- `customers`
- plural props like `decorative pillows`
- ineffective motion like `quick step`

を個別 regex ではなく family policy として扱う。

---

## 6. Implementation Phases

### P0. Documentation and behavior lock

この文書セットを作成し、現状の verification command を記録する。

### P1. Prompt IR specification

コード変更前に、IR の component names, fields, budget semantics, debug contract を固める。

### P2. Read-only prompt validator audit

既存 prompt 文字列を入力し、validator report を出す。
この段階では output prompt を変更しない。

### P3. Candidate-and-rerank

同じ context から複数候補を作り、validator score で選ぶ。
最初は feature flag / passive debug で導入し、既存 output と比較する。

### P4. Layout-first renderer

Prompt Grafting の思想を文字列構成順に落とす。
sampling 中の prompt switching はしない。

### P5. Risk family policy

solo safety / plural artifact / social background を risk family として data-driven にする。

---

## 7. Verification Gates

### 7.1 Baseline

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python assets/calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

### 7.2 After Prompt IR

```bash
python -m unittest assets.test_context_state_adapter assets.test_context_pipeline assets.test_prompt_renderer
python tools/validate_prompt_data.py
```

### 7.3 After read-only validator

```bash
python -m unittest assets.test_prompt_ir_validator
python tools/audit_prompt_ir_candidates.py --seed-count 8 --output assets/results/prompt_ir_validator_smoke.json
```

### 7.4 After candidate-and-rerank

```bash
python -m unittest assets.test_prompt_candidate_rerank assets.test_prompt_snapshots assets.test_determinism
python tools/audit_prompt_ir_candidates.py --seed-count 32 --output assets/results/prompt_ir_rerank_audit.json
```

### 7.5 After layout-first renderer

```bash
python -m unittest assets.test_prompt_renderer assets.test_prompt_snapshots assets.test_solo_duplicate_suppression
python tools/verify_full_flow.py
```

### 7.6 After risk family policy

```bash
python -m unittest assets.test_solo_duplicate_suppression assets.test_semantic_policy assets.test_asset_validator
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## 8. Definition of Done

- Prompt IR component contract is documented and tested
- read-only validator reports solo, plural, object/background, family budget, and length issues
- candidate generation is deterministic for a fixed seed
- rerank reasons are visible in `DebugInfo.decision`
- layout-first renderer improves or preserves prompt snapshots under documented expectations
- risk family policy is data-driven and validated
- public `Context*` node I/O remains unchanged
- base variations remain `103,212` unless intentionally changed by a separate variation task
- final verification gate passes

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Prompt output changes too early | Start with read-only audit and passive debug |
| `PromptContext` compatibility breaks | Keep IR in `extras` / debug first; no schema-breaking fields |
| Candidate branching changes seed determinism | Use labeled `mix_seed()` per branch |
| Validator becomes regex sprawl | Move risk families into data policy |
| Renderer refactor grows too broad | Do layout-first only after validator and rerank are stable |
| Tests become slow again | Keep long audits under `tools/`, not normal unittest prerequisites |
