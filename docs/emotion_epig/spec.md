# EPIG-Informed Emotion Expression Specification

Last updated: 2026-06-15

## 1. Purpose

この仕様書は、`ComfyUI-Scripted-Context-Generator` の感情表現部分に
`2606.13247v1.pdf` の EPIG (Emotion-Based Prompting for Personalised
Image Generation) の考え方を適用するための実装方針を定義する。

今回の目的は、既存の `scene_emotion_priority` 方針を壊さず、感情を
より明示的に Valence-Arousal 空間で扱い、subject-centric な身体表出へ
安定して落とすことである。

## 2. Source Paper Summary

対象文献:

- `../2606.13247v1.pdf`
- Title: `EPIG: Emotion-Based Prompting for Personalised Image Generation`
- arXiv: `2606.13247v1`

EPIG の主要要素:

1. 感情を Valence-Arousal 空間で表す。
2. prompt を `subject`, `stimulus`, `context` に分解する。
3. NRC VAD lexicon から目標 Valence-Arousal 座標に近い descriptor を選ぶ。
4. descriptor はグローバルに挿入せず、役割に応じて subject や stimulus に束縛する。
5. main experiment では `k=3`、かつ subject-centric descriptor のみを使用する。
6. training-free / deterministic / black-box compatible を維持する。

論文が示す実用上の注意:

- 効果は arousal control に強く出る。
- 明確な subject がある prompt で最も効く。
- 風景・物体中心・非人間主体では感情表現が弱くなる。
- context descriptor は semantic drift を起こしやすいため、初期導入では慎重に扱う。

## 3. Current Implementation Baseline

既存実装の主要箇所:

- `vocab/garnish/logic.py`
  - `EMOTION_CATEGORIES`
  - `LEGACY_MAP`
  - `EMOTION_NUANCE_MAP`
  - `PERSONALITY_GARNISH_BIAS`
  - `EMOTION_MODEL`
  - `sample_garnish()`
- `mood_map.json`
  - mood key から scene description と staging tags を展開する。
- `pipeline/mood_builder.py`
  - `ContextMoodExpander` の実体。mood key を seed 決定的に文章化する。
- `pipeline/context_pipeline.py`
  - `apply_garnish()` で garnish 語彙を呼び出す。
- `nodes_context.py`
  - `ContextMoodExpander`
  - `ContextGarnish`
- `prompt_renderer.py`
  - garnish / mood / staging tags の意味ファミリ重複を抑え、最終プロンプトへ合成する。

既存の良い性質:

- 既に training-free である。
- seed 決定性がある。
- 既定 `max_items=3` が論文の `k=3` と合う。
- subject-centric な表情・視線・姿勢・手元・行動タグを生成している。
- `scene_emotion_priority` 方針が既に導入されている。
- semantic family budget によって過剰な顔・視線・姿勢重複を抑えている。

既存の不足:

- 感情カテゴリは離散ラベル中心で、Valence-Arousal 座標を持たない。
- category 選択は VAD 距離ではなく、legacy mapping / weighted random / context load で決まる。
- `stimulus` と `context` の役割が明示的に記録されていない。
- descriptor ごとの `subject-centric` / `context-centric` 注釈がない。
- arousal control の評価指標がない。

## 4. Design Direction

### 4.1 EPIG-Lite First

初期実装は、論文の full EPIG ではなく `EPIG-lite` とする。

採用するもの:

- Valence-Arousal 座標
- deterministic descriptor selection
- `k=3` の subject-centric garnish
- role annotation
- debug log への target emotion / VAD / selected descriptor 記録

初期実装で採用しないもの:

- spaCy などの新規 parser 依存
- NRC VAD lexicon の全量導入
- context descriptor の常時挿入
- LLM による prompt expansion
- diffusion model 内部への介入

理由:

- このリポジトリは ComfyUI custom node として軽量・ローカル・依存少なめであることが重要。
- 既存 `sample_garnish()` が subject-centric な身体表出 generator として機能している。
- 論文の main experiment も subject-only descriptor insertion を使っている。

### 4.2 Core Emotion Prototypes

EPIG 論文の4象限を基準にする。

| Prototype | Valence | Arousal | Meaning |
| --- | ---: | ---: | --- |
| joy | 0.85 | 0.75 | 高快・高覚醒 |
| calm | 0.70 | 0.20 | 高快・低覚醒 |
| sadness | 0.20 | 0.30 | 低快・低覚醒 |
| anxiety | 0.30 | 0.80 | 低快・高覚醒 |

既存カテゴリはこの4象限へ直接置き換えず、VAD 座標を持つ拡張カテゴリとして扱う。

初期案:

| Existing category | Proposed V | Proposed A | Notes |
| --- | ---: | ---: | --- |
| joy | 0.85 | 0.75 | EPIG joy prototype |
| playful | 0.80 | 0.70 | joy 寄り、やや軽い |
| relax | 0.70 | 0.20 | EPIG calm prototype |
| care | 0.72 | 0.35 | calm と joy の中間 |
| moved | 0.68 | 0.55 | positive but emotionally charged |
| focus | 0.55 | 0.45 | neutral-positive, moderate arousal |
| sadness | 0.20 | 0.30 | EPIG sadness prototype |
| anger | 0.25 | 0.85 | low valence, high arousal |
| impatience | 0.30 | 0.80 | EPIG anxiety proxy |

`creepy_fear` は legacy mood としては `impatience/anxiety` へ寄せる。

### 4.3 Role Model

full parser は導入せず、既存 context fields を role として利用する。

| EPIG role | Existing field | Initial handling |
| --- | --- | --- |
| subject | `ctx.subj`, character profile | expression の担い手 |
| stimulus | `ctx.action` | 感情の直接トリガー候補 |
| context | `ctx.loc`, `meta.mood`, `extras.staging_tags` | 背景・状況・空気感 |

初期実装では `subject-centric` を最優先し、context descriptor は生成しない。
context は compatibility / out-of-context filtering / semantic budget の材料として使う。

### 4.4 Descriptor Data Shape

新規データは小さく始める。

候補ファイル:

- `vocab/data/emotion_vad_profiles.json`
- `vocab/emotion_vad.py`

想定 JSON 形状:

```json
{
  "categories": {
    "joy": {
      "vad": [0.85, 0.75],
      "aliases": ["energetic_joy", "energetic"],
      "subject_descriptors": {
        "expression": ["bright smile", "eyes crinkling softly"],
        "gaze": ["warm gaze", "eyes brightening"],
        "posture": ["shoulders opening up"],
        "hands": ["hands moving with excitement"],
        "behavior": ["leaning into the moment"]
      }
    }
  }
}
```

既存 `EMOTION_MODEL` をすぐ全移行しない。最初は VAD metadata を加えた補助テーブルとして
使い、既存 selection の動作を保ったまま VAD selection を導入する。

### 4.5 Target Emotion Resolution

`_resolve_target_emotion()` は段階的に置き換える。

初期 resolver の入力:

- `meta_mood`
- `emotion_nuance`
- `personality`
- `action_load`
- optional `scene_tags`

初期 resolver の出力:

- `category`
- `intensity`
- `target_vad`
- `target_source`
- `vad_distance_debug`

選択順:

1. `meta_mood` が legacy key なら、対応カテゴリと既定 VAD を使う。
2. `emotion_nuance` が明示されていれば、VAD を補正する。
3. `personality` は VAD ではなく category prior として弱く効かせる。
4. `action_load` が `tense` の場合は arousal を上げる。
5. category 未決定時は、allowed category の中から target VAD に最も近い category を選ぶ。
6. 完全未指定時は既存 weighted random を fallback として使う。

### 4.6 Descriptor Selection

論文の距離式を採用する。

```text
delta(w, t) = sqrt((v_w - v_t)^2 + (a_w - a_t)^2)
alpha(w, t) = exp(-gamma * delta(w, t))
```

初期実装では `alpha` は ranking 用 debug として記録し、random choice を完全には消さない。
理由は、このリポジトリは seed variation を重視しているためである。

推奨:

- `gamma = 2.0`
- `k = max_items`, default `3`
- top candidate pool を VAD distance で絞り、その中から seed 決定的に選ぶ。
- selected tags は既存 `_is_out_of_context()` と `sanitize_sequence()` を通す。

### 4.7 Public Compatibility

守るもの:

- public node socket は原則変更しない。
- `ContextGarnish` の `emotion_nuance` choices は初期実装で増やさない。
- `include_camera` legacy handling は維持する。
- `improved_pose_emotion_vocab.py` facade は維持する。
- `sample_garnish()` の戻り値は `List[str]` のまま。
- `sample_garnish_fields()` の戻り値は `(garnish_text, debug_info)` のまま。

追加してよいもの:

- debug log keys
- data file
- internal helper functions
- tests
- docs

## 5. Implementation Phases

## P0. Documentation and Baseline

目的:

- EPIG 適用範囲を固定する。
- 現行の生成挙動を記録する。
- 実装前に regression target を決める。

成果物:

- `docs/emotion_epig/spec.md`
- `docs/emotion_epig/progress.md`
- `docs/emotion_epig/tasks.md`
- baseline samples for representative moods

## P1. VAD Metadata Introduction

目的:

- 既存カテゴリを VAD 空間に写像する。
- runtime behavior をほぼ変えずに debug 可能にする。

変更候補:

- `vocab/data/emotion_vad_profiles.json`
- `vocab/emotion_vad.py`
- `assets/test_emotion_vad_profiles.py`

受け入れ基準:

- 全 `EMOTION_CATEGORIES` に VAD 座標がある。
- VAD 座標は `[0, 1]` 範囲。
- legacy mood key がカテゴリへ解決できる。
- 既存 garnish tests が通る。

## P2. VAD-Aware Category Resolution

目的:

- `meta_mood` / `emotion_nuance` / `action_load` を VAD target として扱う。
- category 未指定時に VAD 距離で候補を選べるようにする。

変更候補:

- `vocab/garnish/logic.py`
- `assets/test_personality_garnish.py`
- new focused tests

受け入れ基準:

- 同じ seed / input は同じ category / tags になる。
- `quiet_focused` は低-中 arousal の focus に寄る。
- `creepy_fear` は low valence / high arousal に寄る。
- tense action は arousal が上がる。
- calm action では過剰な face-forward tags が抑制される。

## P3. VAD-Aware Descriptor Ranking

目的:

- descriptor 選択に VAD 距離を導入する。
- `k=3` の subject-centric selection を安定させる。

変更候補:

- `vocab/garnish/logic.py`
- possible split data under `vocab/data/emotion_vad_profiles.json`

受け入れ基準:

- selected descriptors が `max_items` を超えない。
- selected descriptors は `_is_out_of_context()` を通る。
- debug log に target VAD と descriptor ranking summary が入る。
- 既存 prompt snapshots の drift は意図したものだけに限定される。

## P4. Role-Aware Debug and Guardrails

目的:

- EPIG の `subject/stimulus/context` 概念を runtime debug に反映する。
- context descriptor を生成しない理由と fallback を明示する。

変更候補:

- `pipeline/context_pipeline.py`
- `vocab/garnish/logic.py`

受け入れ基準:

- debug log に `emotion_role_mode: subject_only` が入る。
- `subject_role`, `stimulus_role`, `context_role` が確認できる。
- context は descriptor source ではなく filter/context として使われる。

## P5. Evaluation and Audit

目的:

- 好みではなく観測可能な改善として確認する。

追加候補:

- `tools/audit_emotion_vad_alignment.py`
- `assets/test_emotion_vad_alignment.py`

初期指標:

- emotion embodiment rate
- high / low arousal bucket consistency
- semantic drift proxy
- max tag count compliance
- deterministic output rate

受け入れ基準:

- representative sample で 85% 以上に身体的表出がある。
- high arousal moods は low arousal moods より high-arousal tag family が多い。
- low arousal calm / focus で過剰な顔タグが増えない。
- full asset tests が通る。

## P6. Optional Context Descriptor Experiment

目的:

- subject-only の安定後に、context descriptor を限定的に試す。

初期では実装しない。導入する場合も feature flag / hidden option / data-only experiment に留める。

## 6. Non-Goals

- 新規 LLM 依存を入れない。
- spaCy など parser 依存を初期実装で入れない。
- ComfyUI public node UI を広げない。
- フォトリアル向け style / camera prompt を増やさない。
- mood_map を NRC VAD 全量で置き換えない。
- diffusion model の重み、LoRA、attention を変更しない。

## 7. Verification Plan

Focused checks:

```bash
python -m unittest assets.test_personality_garnish
python -m unittest assets.test_mood_builder assets.test_mood_map_repetition_controls
python -m unittest assets.test_prompt_renderer assets.test_prompt_snapshots
```

Data and policy checks:

```bash
python tools/validate_prompt_data.py
python -m unittest assets.test_vocab_lint assets.test_semantic_policy assets.test_policy_alignment
```

Full checks:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/verify_full_flow.py
```

Optional workflow checks if node surface or workflow compatibility changes:

```bash
python tools/check_widgets_values.py
pwsh -File tools/run_custom_workflow_roundtrip.ps1
```

## 8. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| VAD metadata changes output distribution too much | prompt snapshots drift | introduce metadata first, then selection changes |
| high arousal tags become too aggressive | unnatural daily-life prompts | keep `_is_out_of_context()` and semantic family budget |
| context descriptors cause background drift | paper-known failure mode | subject-only first |
| personality bias overwhelms VAD target | inconsistent emotion control | personality is category prior, not hard override |
| tests become too brittle against seed variation | slow iteration | assert buckets and invariants, not exact tag everywhere |

## 9. Completion Definition

EPIG-lite implementation is complete when:

- all existing emotion categories have VAD metadata;
- `sample_garnish()` resolves target emotion with VAD-aware debug;
- subject-centric descriptor selection remains deterministic and respects `max_items`;
- public node sockets and workflow compatibility remain stable;
- focused and full verification pass;
- progress and task docs record completed phases and remaining risks.
