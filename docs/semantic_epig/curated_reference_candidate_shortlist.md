# Curated Reference Candidate Shortlist

対象リポジトリ: `ComfyUI-Scripted-Context-Generator`  
作成日: 2026-06-17 JST  
関連文書:

- `curated_reference_adoption_spec.md`
- `curated_reference_adoption_progress.md`
- `curated_reference_adoption_tasks.md`

---

## 1. Purpose

`assets/results/subject_centric_descriptor_candidates.json` の `direct` / `needs_phrase`
候補を、runtime 採用前に小さく triage するための repo-tracked メモ。

この文書は reference-derived score overlay ではない。候補の採否理由と、
repo-authored phrase へ書き直す方針だけを記録する。

Rules:

- Reference row / score / raw phrase をそのまま runtime data にしない。
- `assets/results/subject_centric_descriptor_candidates.json` は local/generated のままにする。
- Accepted phrase も、次 wave で validator と passive debug を通すまで runtime には入れない。

---

## 2. Current local report summary

Generated from current `..\参考`:

```text
descriptor_count=809
direct_count=7
needs_phrase_count=80
reject_count=595
unmatched_count=127
warning_count=0
```

Interpretation:

- `direct` は既存 descriptor の reference coverage signal。
- `needs_phrase` はそのまま採用せず、repo-authored phrase へ書き直す候補。
- `reject` は採用しない。
- `unmatched` は reference signal がないだけで、既存 descriptor としては維持する。

---

## 3. Shortlist decisions

### 3.1 Accepted for future passive/debug experiment

| candidate_id | source_classification | source_hint | target_slot | proposed_repo_phrase | rewrite_reason | risk_note | decision |
|---|---|---|---|---|---|---|---|
| sc_gaze_downcast_01 | needs_phrase | `downcast eyes` / subject token `downcast` | gaze | `downcast eyes` | Existing repo-style subject gaze descriptor; useful for shy / sad / subdued states | Avoid treating as image-control wording; keep as eye behavior | active_first |
| sc_gaze_curious_01 | needs_phrase | `curious eyes`, `curious look` | gaze | `curious eyes` | Converts curiosity into subject expression instead of scene mood | Low risk; semantic behavior only | active_wave3 |
| sc_expression_calm_01 | needs_phrase | `calm expression` | expression | `calm expression` | Stable low-arousal expression descriptor | Avoid replacing full emotion model; gated to calm/relieved moods | active_wave5 |
| sc_expression_contented_01 | needs_phrase | `contented mouth` | expression | `contented mouth` | Subject-centric mouth expression, concise and already repo-styled | Low risk; gated to joy/relieved moods and repetition/audit guard | active_wave6 |
| sc_expression_reassuring_01 | needs_phrase | `small reassuring smile` | expression | `small reassuring smile` | Good gentle / faithful personality bridge | Keep as subtle expression, not moral judgment | active_wave2 |
| sc_posture_relaxed_01 | needs_phrase | `relaxed posture`, `posture relaxed` | posture | `relaxed posture` | Good calm / gentle / home-context body expression | Avoid overusing in active / high-pressure action contexts | keep_passive_future_posture_gate |
| sc_hands_touching_lips_01 | needs_phrase | `touching lips`, `fingers pressing lightly to her lips` | hands | `fingers resting near her lips` | Rewrites gesture into safe subject hand descriptor | Avoid sensual/body emphasis; context filter required | active_wave4 |
| sc_expression_wry_01 | needs_phrase | `wry grin`, `soft grin` | expression | `wry grin` | Useful for awkward / amused / restrained affect | Keep as expression; gated to awkward/playful/mysterious moods | active_wave7 |

### 3.2 Keep as validation signal only

| candidate_id | source_classification | source_hint | reason | decision |
|---|---|---|---|---|
| sc_direct_cheerful | direct | `cheerful` | Existing mood term; too broad as new descriptor | validation_only |
| sc_direct_crying | direct | `crying` | Already covered by mood/expression; active adoption could be too strong | validation_only |
| sc_direct_laughing | direct | `laughing` | Existing strong expression; no new phrase needed | validation_only |
| sc_direct_frowning | direct | `frowning` | Existing expression; keep for coverage | validation_only |

### 3.3 Rejected for this wave

| candidate_id | source_classification | source_hint | reason | decision |
|---|---|---|---|---|
| sc_reject_angry_eyes | needs_phrase | `angry eyes` | Too intense for first small adoption; can dominate prompt | reject_now |
| sc_reject_happy_tears | needs_phrase | `happy tears`, `tears of joy` | Strong emotional event; needs separate intensity gate | reject_now |
| sc_reject_shielding_sun | needs_phrase | `shielding eyes from sun` | More location/weather action than personality/garnish descriptor | reject_now |
| sc_reject_stretching_neck | needs_phrase | `stretching neck` | Body-part action risk; not suitable as subject-centric emotion descriptor | reject_now |
| sc_reject_vibrato_motion | needs_phrase | `vibrato finger motion` | Domain-specific performance action; belongs to action pool if used | reject_now |

---

## 4. Proposed first passive data shape

For C6, use a new curated file rather than editing broad personality data directly:

```text
vocab/data/subject_centric_descriptor_overrides.json
```

Initial scope:

- 6〜8 descriptors max
- one narrow active descriptor first; all other descriptors stay `mode=passive`
- personality / mood tags as optional matching hints
- no score fields
- no copied raw reference rows

Required fields:

```text
id
slot
text
source_hint
rewrite_reason
risk_note
mode
```

Optional fields:

```text
personality
mood_keys
reject_context_terms
debug_tags
```

---

## 5. Next gate

Before any active runtime integration:

1. Keep validator coverage for the curated file schema passing.
2. Keep passive loader tests passing.
3. Prove passive mode does not change prompt output.
4. Extend active/passive audit only when active adoption is proposed.

Current active adoption is intentionally narrow:

- `sc_gaze_downcast_01` is active for `shy` / `gloomy`.
- `sc_expression_reassuring_01` is active for `gentle` / `faithful`.
- `sc_gaze_curious_01` is active for `mysterious` / `cheerful`.
- `sc_hands_touching_lips_01` is active for `shy` only when `mood_keys=["moved"]` matches; context rejects are configured.
- `sc_expression_calm_01` is active for `neutral` / `gentle` only when calm/relieved mood keys match; context rejects are configured.
- `sc_expression_contented_01` is active for `gentle` / `cheerful` only when joy/relieved mood keys match; context rejects are configured.
- `sc_expression_wry_01` is active for `mysterious` / `serious` only when awkward/playful/mysterious mood keys match; context rejects are configured.
- Runtime selection now supports optional `mood_keys` and `reject_context_terms` for future descriptors.
- Other curated descriptors remain passive/debug-only.
- Any additional active descriptor requires another audit pass.
