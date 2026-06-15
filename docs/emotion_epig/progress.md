# EPIG-Informed Emotion Expression Progress

Last updated: 2026-06-15

## Status Summary

Overall status: `EPIG-lite implemented and verified`

Current phase: `P1-P5 complete; P6 deferred`

Primary target:

- EPIG の Valence-Arousal / role-aware / subject-centric descriptor selection を
  既存 garnish pipeline へ軽量に取り込む。
- public node sockets と workflow compatibility を維持する。
- 初期導入では context descriptor を生成せず、subject-centric expression に限定する。
- seed determinism と `max_items=3` の挙動を守る。

## Current Baseline

解析済みの現行実装:

```text
emotion categories: joy, playful, anger, sadness, relax, focus, care, impatience, moved
intensities: mild, medium, strong
default garnish max_items: 3
generation mode: scene_emotion_priority
public garnish node: ContextGarnish
public mood node: ContextMoodExpander
runtime facade: improved_pose_emotion_vocab.py
core implementation: vocab/garnish/logic.py
```

代表サンプル確認:

```text
quiet_focused + reading a book quietly
-> brows knit in concentration, steady gaze, hands kept precise and controlled

creepy_fear + waiting in a rainy bus stop
-> uneasy face, checking the room again, fingers drumming

energetic_joy + running toward the station
-> bright smile, eyes brightening, fingers tapping lightly

intense_anger + arguing in a classroom
-> furrowed brow, glaring straight ahead, knuckles whitening
```

現行挙動の評価:

- subject-centric な身体表出は既に実装済み。
- `k=3` に近い出力制御が既にある。
- VAD 座標と descriptor ranking は未実装。
- role-aware decomposition は明示モデルとしては未実装。

## Source Paper Baseline

対象文献:

```text
2606.13247v1.pdf
EPIG: Emotion-Based Prompting for Personalised Image Generation
```

取り込む設計要素:

- Valence-Arousal prototypes
- Euclidean VAD distance
- subject / stimulus / context role model
- subject-only descriptor insertion as first implementation shape
- deterministic, training-free prompt preprocessing

初期導入から外すもの:

- new parser dependency
- full NRC VAD lexicon ingestion
- context descriptor insertion
- LLM-based expansion
- model-internal attention or fine-tuning

## Phase Progress

| Phase | Scope | Status | Notes |
| --- | --- | --- | --- |
| P0 | Documentation and baseline | Done | spec/progress/tasks created |
| P1 | VAD metadata introduction | Done | `emotion_vad_profiles.json` and loader added |
| P2 | VAD-aware category resolution | Done | target VAD and compatibility-aware fallback added |
| P3 | VAD-aware descriptor ranking | Done | descriptor ranking and debug summaries added |
| P4 | Role-aware debug and guardrails | Done | subject-only role debug added |
| P5 | Evaluation and audit | Done | focused VAD alignment tests and audit artifacts added |
| P6 | Optional context descriptor experiment | Deferred | do not start before P5 |

## Decisions

- Use `EPIG-lite`, not full EPIG, for the first implementation.
- Keep subject-centric descriptor generation as the first target.
- Do not add new dependencies in the initial pass.
- Keep `ContextGarnish` public inputs stable.
- Keep `improved_pose_emotion_vocab.py` as a backward-compatible facade.
- Treat personality as a weak prior, not an override of the VAD target.
- Use `k=3` as the default selection shape because it matches both the paper and current node defaults.
- Introduce VAD metadata before changing selection behavior.

## Proposed VAD Mapping

| Existing category | V | A | Status |
| --- | ---: | ---: | --- |
| joy | 0.85 | 0.75 | proposed |
| playful | 0.80 | 0.70 | proposed |
| relax | 0.70 | 0.20 | proposed |
| care | 0.72 | 0.35 | proposed |
| moved | 0.68 | 0.55 | proposed |
| focus | 0.55 | 0.45 | proposed |
| sadness | 0.20 | 0.30 | proposed |
| anger | 0.25 | 0.85 | proposed |
| impatience | 0.30 | 0.80 | proposed |

## Verification Log

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-06-15 | repository read-only inspection | Pass | no script changes |
| 2026-06-15 | PDF text extraction and method review | Pass | EPIG method and limitations summarized |
| 2026-06-15 | `sample_garnish_fields` representative samples | Pass | deterministic 3-tag subject-centric outputs observed |
| 2026-06-15 | `git status --short` | Pass | clean before docs |
| 2026-06-15 | `python -m unittest assets.test_emotion_vad_profiles assets.test_emotion_vad_alignment` | Pass | 9 tests OK |
| 2026-06-15 | `python -m unittest assets.test_personality_garnish` | Pass | 6 tests OK |
| 2026-06-15 | `python -m unittest assets.test_mood_builder assets.test_mood_map_repetition_controls` | Pass | 9 tests OK |
| 2026-06-15 | `python -m unittest assets.test_prompt_renderer assets.test_prompt_snapshots` | Pass | 7 tests OK; snapshots updated for intentional VAD-ranked garnish changes |
| 2026-06-15 | `python -m unittest assets.test_vocab_lint assets.test_semantic_policy assets.test_policy_alignment` | Pass | 11 tests OK |
| 2026-06-15 | `python tools/validate_prompt_data.py` | Pass | `ERROR: []`, `WARNING: []` |
| 2026-06-15 | `python tools/check_widgets_values.py` | Pass | no widget value issues |
| 2026-06-15 | `python -m unittest assets.test_context_nodes assets.test_node_registry assets.test_determinism` | Pass | 13 tests OK |
| 2026-06-15 | `python tools/verify_full_flow.py` | Pass | OK |
| 2026-06-15 | `python tools/audit_prompt_repetition.py --samples-per-row 8 --output assets/results/prompt_repetition_active_source_8.json --enforce-thresholds` | Pass | threshold evaluation passed |
| 2026-06-15 | `python tools/audit_template_diversity.py --seed-count 32 --output assets/results/template_diversity_32.json --enforce-thresholds` | Pass | threshold evaluation passed |
| 2026-06-15 | `python -m unittest discover -s assets -p "test_*.py"` | Pass | 279 tests OK |

## Next Step

The subject-only EPIG-lite lane is complete. The remaining optional work is P6:
context descriptor experimentation behind a feature flag or data-only experiment,
not as a default behavior change.

## Open Risks

- The paper's NRC VAD lexicon is not currently bundled in the repo.
- Full parser-based role decomposition would add dependency and complexity.
- Existing prompt snapshot tests may drift once descriptor ranking changes.
- Context descriptors are useful in theory but are the highest semantic-drift risk.
- Non-human or object-centered subjects remain a known limitation of prompt-level emotion control.
