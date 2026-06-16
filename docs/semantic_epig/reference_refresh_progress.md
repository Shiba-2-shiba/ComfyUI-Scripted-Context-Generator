# EPIG Reference Refresh Progress

対象リポジトリ: `ComfyUI-Scripted-Context-Generator`
作成日: 2026-06-16
関連仕様: `reference_refresh_spec.md`
関連タスク: `reference_refresh_tasks.md`

---

## 1. Current State

現行実装は Semantic EPIG の all-active rollout と、その後の refactor wave を完了している。

Current active domains:

```text
action: active
object_relation: active
location_scene: active
clothing_tpo: active
personality_behavior: active
```

追加資料を見た結論:

- 実装方針は十分反映済み
- 実データの runtime 取り込みは未実施
- reference alignment / data-only audit の初期実装は開始済み
- 既存 runtime を作り直す必要はない

---

## 2. Local Reference Inventory

| Reference | Status | Notes |
|---|---|---|
| `参考/2606.13247v1.pdf` | Already used indirectly | Existing `docs/emotion_epig` says EPIG-lite was extracted from this paper |
| `参考/2503.23547v1.pdf` | Reviewed via arXiv metadata and local reference context | NRC VAD Lexicon v2 paper; >55k English terms, ~25k added words, ~10k MWE, V/A/D dimensions |
| `参考/EPIG/README.md` | Reviewed | Confirms training-free V/A and role-aware decomposition |
| `参考/EPIG/data/NRC_VAD_with_subject_centric.csv` | Reviewed | 19,970 rows; 965 subject-centric rows |
| `参考/EPIG/data/llm_expanded_prompts.csv` | Reviewed | Contains many style/camera/quality terms; not suitable as direct prompt source |
| `参考/NRC-VAD-Lexicon-v2.1/.../README.txt` | Reviewed | Version 2.1, March 2025, -1..1 score range |
| `NRC-VAD-Lexicon-v2.1.txt` | Counted | 54,802 lines including header |
| `Unigrams/unigrams-NRC-VAD-Lexicon-v2.1.txt` | Counted | 44,729 lines including header |
| `MWE/mwe-NRC-VAD-Lexicon-v2.1.txt` | Counted | 10,074 lines including header |
| `OneFilePerDimension/PolarSubset/valence-polar...txt` | Counted | 29,042 lines including header |
| `参考/lexicons.html` | Reviewed | Catalog lists EmoLex, Affect Intensity, VAD, WorryWords, Words of Warmth, composition lexicons, colour lexicon, and Terms of Use |
| `参考/EmotionDynamics` | Reviewed | Completed local clone is readable; contains UED code, VAD/EmoLex lexicons, sample data, and MIT-licensed code |

---

## 3. Existing Implementation Findings

### 3.1 Confirmed strengths

- `vocab/emotion_vad.py` implements deterministic V/A distance, relevance, closest category, and descriptor ranking.
- `vocab/data/emotion_vad_profiles.json` defines category and nuance V/A values.
- `vocab/garnish/logic.py` records `target_vad`, category distances, descriptor rankings, subject/stimulus/context role debug.
- `vocab/personality_semantics.py` and `personality_behavior_profiles.json` implement data-driven personality behavior ranking.
- `tools/audit_semantic_epig_outputs.py` can compare active/passive prompt changes.
- Existing docs explicitly scoped the first emotion pass as EPIG-lite and excluded full NRC import.

### 3.2 Gaps

| Gap | Evidence | Severity |
|---|---|---:|
| Full NRC/EPIG reference data not loaded | Search found no `subject_centric`, `llm_expanded`, or NRC lexicon loader in runtime | Medium |
| Dominance dimension unused | `emotion_vad.py` uses only `(valence, arousal)` | Low/Medium |
| Subject-centric CSV not used for descriptor validation | Current subject-centric behavior is hand-authored | Medium |
| LLM expanded prompts not used as negative corpus | Current validator does not reference this CSV | Low |
| License gate not documented for derived data | Current docs mention NRC not bundled, but not a gate for next work | Medium |
| WorryWords / Words of Warmth not represented | `lexicons.html` lists them but local data files are not present | Low/Medium |
| EmotionDynamics dependency stack unsuitable for direct import | Requirements include pandas/numpy/scipy/nltk/PyYAML/python_box/tqdm | Low |

---

## 4. Decision Log

| Date | Decision | Reason | Impact |
|---|---|---|---|
| 2026-06-16 | Do not rewrite current Semantic EPIG | all-active implementation and refactor are already complete and verified in docs | Keep next wave bounded |
| 2026-06-16 | Treat new references as audit/calibration inputs first | Reference data may improve ranking, but direct adoption risks output drift | Start passive/debug-only |
| 2026-06-16 | Do not directly use `llm_expanded_prompts.csv` for output | It contains style/camera/quality/render terms that violate semantic-only policy | Use as negative corpus only |
| 2026-06-16 | Gate raw/derived NRC data on redistribution review | External lexicon has Terms of Use | Avoid committing questionable data |
| 2026-06-16 | Keep no-new-dependency policy | Existing custom node should stay lightweight | Use stdlib CSV/TSV parsing |
| 2026-06-16 | Prefer a local current-vocabulary overlay over full lexicon import | It uses only terms already present in this repo and avoids bundling full external data | Generate under `assets/results/` by default |
| 2026-06-16 | Make MWE-first lookup a reference-refresh requirement | `2503.23547v1` specifically adds common multi-word phrases to NRC VAD v2 | Exact phrase matches should beat token fallback |
| 2026-06-16 | Treat WorryWords and Words of Warmth as optional audit lanes | They map well to anxiety/warmth/sociability axes, but the actual data is not currently local | Do not block VAD overlay work |
| 2026-06-16 | Use EmotionDynamics as a reference, not a dependency | Completed clone is available, but its dependency stack is too heavy for this custom node | Reuse ideas and local CSV formats only |
| 2026-06-16 | Do not reuse source data as-is; adopt repo-specific transformed data | Reference data is useful for calibration, but tracked data must fit this repo's schema and policy | Use raw data locally; commit only curated/derived project data |

---

## 5. Cleanup Plan

Scope:

- Documentation for reference-driven next wave
- Reference inventory and gap analysis
- Future audit/tool tasks only

Out of scope for this planning pass:

- Runtime behavior changes
- New vocab data files
- Copying reference datasets into repo
- Public node I/O changes
- New dependencies

Order:

1. Document current-state analysis
2. Specify safe reference refresh plan
3. Create task board
4. Defer implementation until behavior lock and license gate are complete

---

## 6. Milestone Status

| Milestone | Title | Status | Notes |
|---|---|---|---|
| Q0 | Current implementation and reference inventory | Done | Existing docs/code and local reference files reviewed |
| Q1 | Reference refresh docs setup | Done | `reference_refresh_spec.md`, `reference_refresh_progress.md`, `reference_refresh_tasks.md` added |
| Q2 | Behavior lock for reference audit | Done | Focused baseline and active/passive audit baseline generated |
| Q3 | Reference alignment audit tool | Done | `tools/audit_epig_reference_alignment.py` now reports emotion/personality coverage, subject-centric counts, LLM policy scan, and source availability |
| Q4 | Current-vocabulary reference overlay | Done | `tools/extract_epig_reference_overlay.py` added; generated local overlay JSON |
| Q5 | Subject-centric descriptor audit | Done | `tools/audit_subject_centric_descriptors.py` added; generated local candidate report with no runtime changes |
| Q6 | Dominance / EmotionDynamics / WorryWords / Warmth pilot | Done | Audit-only projection and coverage report generated; runtime axis adoption deferred |
| Q7 | Negative corpus extraction from LLM prompts | Done | Dedicated policy audit added; small repo-authored negative fixture added |
| Q8 | EmotionDynamics availability review | Done | Completed clone inspected; use as reference-only source |
| Q9 | Adoption decision | Done | No runtime adoption now; generated overlays stay local; repo-authored negative fixture is accepted |

---

## 7. Implementation Log

### 7.1 Q2 behavior lock

Baseline verification before code edits:

| Command | Result |
|---|---|
| `python -m unittest assets.test_emotion_vad_profiles assets.test_emotion_vad_alignment assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig_audit` | Pass: 27 tests OK |
| `python tools\validate_prompt_data.py` | Pass: `ERROR: []`, `WARNING: []` |
| `asset_validator.validate_assets()` | Pass: `0` issues |

Active/passive audit baseline:

```text
python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-start 0 --seed-count 8 --output assets\results\semantic_epig_audit_reference_refresh_baseline.json
```

Result:

```text
record_count=40
changed_count=40
policy_issue_count=0
```

### 7.2 Q3 reference alignment audit

Added:

```text
vocab/epig_reference.py
tools/audit_epig_reference_alignment.py
assets/test_epig_reference_alignment.py
```

Implemented:

- EPIG subject-centric CSV reader
- NRC VAD TSV reader with `-1..1` to `0..1` normalization
- EmotionDynamics VAD / EmoLex CSV readers
- normalized exact lookup
- current `emotion_vad_profiles.json` alignment report
- personality descriptor coverage report
- EPIG subject-centric current-vocabulary exact match counts
- LLM expanded prompt policy scan
- optional WorryWords / Words of Warmth availability flags
- reference availability report

Local reference run:

```text
python tools\audit_epig_reference_alignment.py --reference-root "C:\Users\inott\Downloads\新しいフォルダー (3)\参考" --output assets\results\epig_reference_alignment.json
```

Result:

```text
source_count=26
emotion_profile_matched_count=15
exact_reference_match_count=3003
warning_count=0
```

Additional audit details:

```text
personality_descriptor_count=9
personality_exact_match_count=0
personality_token_fallback_count=9
subject_centric_record_count=965
current_vocab_exact_subject_match_count=201
llm_expanded_prompt_row_count=44
llm_expanded_prompt_policy_issue_count=83
llm_policy_domain_counts={camera: 7, quality: 58, render: 7, style: 11}
worrywords_available=False
words_of_warmth_available=False
```

### 7.3 Q4 current-vocabulary reference overlay

Added:

```text
tools/extract_epig_reference_overlay.py
assets/test_epig_reference_overlay.py
```

Implemented:

- current repo vocabulary extraction from `vocab/data/*.json`, `vocab/source/action_pools/*.json`, and `vocab/garnish/*.py`
- exact phrase lookup before token fallback
- MWE-first reference behavior through source ordering and tests
- optional EmotionDynamics VAD/EmoLex lookup sources
- local JSON overlay writing under ignored `assets/results/`

Local reference run:

```text
python tools\extract_epig_reference_overlay.py --reference-root "C:\Users\inott\Downloads\新しいフォルダー (3)\参考" --output assets\results\epig_reference_overlay.local.json
```

Result:

```text
extracted_term_count=8728
matched_term_count=7700
unmatched_term_count=1028
warning_count=0
```

### 7.4 Q5 subject-centric descriptor audit

Added:

```text
tools/audit_subject_centric_descriptors.py
assets/test_subject_centric_descriptor_audit.py
```

Implemented:

- descriptor collection from subject-facing garnish/personality/micro-action sources
- exclusion of camera/view/framing categories from adoption candidates
- `PERSONALITY_GARNISH_BIAS` extraction limited to `prefer` descriptors, not category labels
- conservative token fallback requiring subject descriptor context such as gaze, face, mouth, posture, hands, or expression
- classification into `direct`, `needs_phrase`, `reject`, and `unmatched`
- local report writing under ignored `assets/results/`

Local reference run:

```text
python tools\audit_subject_centric_descriptors.py --reference-root "C:\Users\inott\Downloads\新しいフォルダー (3)\参考" --output assets\results\subject_centric_descriptor_candidates.json
```

Result:

```text
descriptor_count=809
direct_count=7
needs_phrase_count=80
reject_count=595
unmatched_count=127
warning_count=0
```

Interpretation:

- `direct` is exact current repo descriptor match to an EPIG subject-centric term.
- `needs_phrase` is not direct adoption; it is a signal for repo-specific phrase authoring.
- `reject` includes non-subject categories, exact non-subject-centric matches, and policy-banned terms.
- `unmatched` descriptors remain repo-authored descriptors and are not removed automatically.

### 7.5 Q6 dominance / EmotionDynamics coverage pilot

Added:

```text
tools/audit_reference_dimension_projection.py
assets/test_reference_dimension_projection.py
```

Implemented:

- audit-only dominance projection from reference VAD into existing personality-adjacent axes
- current vocabulary coverage and average reference VAD summary
- personality descriptor group average VAD summary
- ranking delta report comparing current personality descriptor ranking to dominance-projected ranking
- optional WorryWords / Words of Warmth availability hooks
- explicit runtime adoption decision field set to `deferred`

Local reference run:

```text
python tools\audit_reference_dimension_projection.py --reference-root "C:\Users\inott\Downloads\新しいフォルダー (3)\参考" --output assets\results\reference_dimension_projection.json
```

Result:

```text
extracted_term_count=8728
exact_match_count=3003
token_fallback_match_count=4697
matched_term_count=7700
average_vad={valence: 0.6042, arousal: 0.3762, dominance: 0.4732}
projection_comparison_count=99
high_risk_count=15
warning_count=0
worrywords_available=False
words_of_warmth_available=False
```

Descriptor group averages:

```text
personality.gaze: matched=3/3, average_vad={valence: 0.6381, arousal: 0.4228, dominance: 0.5424}
personality.hands: matched=3/3, average_vad={valence: 0.5795, arousal: 0.3809, dominance: 0.4570}
personality.posture: matched=3/3, average_vad={valence: 0.6095, arousal: 0.3548, dominance: 0.5945}
```

Decision:

- Dominance is useful as an audit lens.
- Runtime adoption is deferred because all 99 personality projection comparisons are token-fallback matches, not exact descriptor matches.
- The 15 high-risk rank shifts are useful for review, but too weak for automatic personality-axis changes.
- EmotionDynamics-style coverage metrics are useful for report generation without importing its dependency stack.

### 7.6 Q7 LLM expanded prompt negative corpus

Added:

```text
tools/audit_llm_expanded_prompt_policy.py
assets/test_llm_expanded_prompt_policy.py
assets/fixtures/semantic_policy_negative_examples.json
```

Implemented:

- dedicated scan of `EPIG/data/llm_expanded_prompts.csv` as a negative/policy corpus
- explicit counts for all semantic policy domains, including `body_type=0`
- term-level counts for banned prompt style/camera/quality/render/body-type terms
- small hand-authored negative fixture for validator/policy regression tests
- local report writing under ignored `assets/results/`

Local reference run:

```text
python tools\audit_llm_expanded_prompt_policy.py --reference-root "C:\Users\inott\Downloads\新しいフォルダー (3)\参考" --output assets\results\llm_expanded_prompt_policy_audit.json
```

Result:

```text
row_count=44
rows_with_policy_issues=34
policy_issue_count=83
domain_counts={body_type: 0, camera: 7, quality: 58, render: 7, style: 11}
```

Top term counts:

```text
quality: best quality=17, masterpiece=16, 8k=15, ultra detailed=4, high quality=3, highly detailed=3
camera: depth of field=6, bokeh=1
style: illustration=7, painting=3, digital art=1
render: soft lighting=6, cinematic lighting=1
body_type: none found
```

Decision:

- `llm_expanded_prompts.csv` remains a negative corpus only.
- The full CSV is not copied into the repo.
- The tracked negative fixture is repo-authored and intentionally small.
- Runtime prompt generation must not use LLM expanded prompts as source data.

### 7.7 Q9 adoption decision

Added:

```text
tools/review_reference_refresh_adoption.py
assets/test_reference_refresh_adoption.py
```

Implemented:

- aggregation of Q3-Q7 generated audit outputs
- explicit adoption decisions for runtime prompt changes, score-bearing overlay, subject descriptor subset, dominance runtime axis, and LLM expanded prompts
- local decision JSON under ignored `assets/results/`
- acceptance flags for Q9 task closure

Local decision run:

```text
python tools\review_reference_refresh_adoption.py --results-dir assets\results --output assets\results\reference_refresh_adoption_decision.json
```

Result:

```text
overall_decision=no_runtime_adoption_now
missing_count=0
runtime_prompt_changes=deferred
dominance_runtime_axis=audit_only
small_derived_data_subsets_should_be_added_now=False
```

Decision details:

- Current implementation is sufficient for now.
- Do not add runtime prompt changes from reference data in this wave.
- Do not track the score-bearing overlay; keep it generated/local.
- Do not add subject descriptor subsets yet; `needs_phrase=80` requires repo-specific rewriting before tracked adoption.
- Keep dominance audit-only; current evidence is token-fallback based.
- Keep LLM expanded prompts as negative corpus only.
- The small repo-authored negative fixture is acceptable and tracked.

---

## 8. Verification Notes

Runtime prompt generation was not changed. Reference-derived score files remain generated local artifacts under `assets/results/`.

Reference material policy:

- `参考/` is not part of the commit scope.
- Generated overlays under `assets/results/` stay local/ignored by default.
- Raw data / score-bearing overlays may be used for development and audit.
- Source repo data is not tracked as-is.
- Future tracked changes should be repo-specific curated/derived data.
- If a score-bearing overlay is adopted, it must be transformed, scoped, documented, and not a raw source dump.

Commands used for analysis:

```bash
rg --files
rg -n "subject_centric|NRC|lexicon|vad|Valence|Arousal|Dominance|llm_expanded|expanded_prompts|2606|EPIG" .
Get-Content reference README / CSV / TSV samples
Import-Csv reference EPIG subject-centric CSV and count rows
Measure-Object -Line for NRC v2.1 files
Select-String over lexicons.html for lexicon sections and Terms of Use
Get-ChildItem -Force over EmotionDynamics to verify checkout state
Read EmotionDynamics README/code README/uedLib README and key lexicon headers
```

Known environment note:

- `git status` is currently blocked by Git safe.directory dubious ownership protection for this checkout. Use `git config --global --add safe.directory ...` only if repository status commands are required.

---

## 9. Verification Snapshot

| Command | Result |
|---|---|
| `python -m unittest assets.test_reference_refresh_adoption assets.test_llm_expanded_prompt_policy assets.test_reference_dimension_projection assets.test_subject_centric_descriptor_audit assets.test_epig_reference_alignment assets.test_epig_reference_overlay assets.test_emotion_vad_profiles assets.test_emotion_vad_alignment assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig_audit assets.test_semantic_policy` | Pass: 50 tests OK |
| `python -m py_compile vocab\epig_reference.py tools\extract_epig_reference_overlay.py tools\audit_epig_reference_alignment.py tools\audit_subject_centric_descriptors.py tools\audit_reference_dimension_projection.py tools\audit_llm_expanded_prompt_policy.py tools\review_reference_refresh_adoption.py assets\test_epig_reference_alignment.py assets\test_epig_reference_overlay.py assets\test_subject_centric_descriptor_audit.py assets\test_reference_dimension_projection.py assets\test_llm_expanded_prompt_policy.py assets\test_reference_refresh_adoption.py` | Pass |
| `python tools\validate_prompt_data.py` | Pass: `ERROR: []`, `WARNING: []` |
| `asset_validator.validate_assets()` | Pass: `0` issues |

---

## 10. Remaining Risks

| Risk | Level | Mitigation |
|---|---:|---|
| Reference-derived VAD changes could drift prompt snapshots | Medium | Audit-only first; active/passive diff before adoption |
| NRC redistribution terms may block committing derived data | Medium | License gate before adding data |
| Local overlay may still contain derived scores | Medium | Keep it generated/ignored by default; adopt only transformed repo-specific subsets |
| Accidental commit of local reference material | Medium | Keep `参考/` outside repo scope and do not track generated overlays |
| Subject-centric term list includes words that are not usable prompt descriptors | Medium | Use as coverage/weight signal, not direct insertion |
| Dominance mapping may overfit personality stereotypes | Medium | Keep pilot audit-only and inspect samples |
| Optional WorryWords/WoW data may not be available | Low | Treat as optional missing input |
| EmotionDynamics dependencies may tempt broad import | Medium | Reference algorithms only; no new dependency |
| LLM expanded prompts contain banned prompt style terms | High | Negative corpus only; never runtime source |
