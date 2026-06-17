# EPIG Reference Refresh Tasks

対象リポジトリ: `ComfyUI-Scripted-Context-Generator`
作成日: 2026-06-16
関連仕様: `reference_refresh_spec.md`
関連進捗: `reference_refresh_progress.md`

---

## 0. Common Rules

- Do not change public `Context*` node inputs or outputs.
- Do not add dependencies.
- Do not copy full external reference datasets into the repo without license/redistribution review.
- Do not commit files from `<REFERENCE_ROOT>` (for example `..\参考` from the repo root).
- Generated score-bearing overlays from reference data may be used locally.
- Do not track source-repo data as-is.
- Track only repo-specific curated/derived descriptors, rules, tests, or minimal overlays transformed for this project.
- Prefer repo-native curated descriptors/rules/tests authored for this project when they are sufficient.
- Preserve seed determinism.
- Preserve semantic-only policy.
- Treat `llm_expanded_prompts.csv` as negative/policy corpus, not prompt source.
- Keep reference-derived score overlays generated/local by default.
- Start with audit/debug-only behavior.
- Add or update tests before any runtime behavior change.

Focused verification:

```bash
python -m unittest assets.test_emotion_vad_profiles assets.test_emotion_vad_alignment assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig_audit
python tools/validate_prompt_data.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## Q0. Current Implementation And Reference Inventory

### Q0.1 Review existing docs and runtime

Files:

```text
docs/emotion_epig/spec.md
docs/emotion_epig/progress.md
docs/semantic_epig/refactor_spec.md
docs/semantic_epig/refactor_progress.md
vocab/emotion_vad.py
vocab/data/emotion_vad_profiles.json
vocab/personality_semantics.py
vocab/data/personality_behavior_profiles.json
```

Acceptance:

- [x] Confirm current implementation is EPIG-lite plus Semantic EPIG all-active
- [x] Confirm full NRC import was previously a non-goal
- [x] Confirm current runtime does not read `subject_centric` / NRC v2.1 raw files

### Q0.2 Inventory added references

References:

```text
参考/EPIG
参考/NRC-VAD-Lexicon-v2.1
参考/2503.23547v1.pdf
参考/lexicons.html
参考/EmotionDynamics
```

Acceptance:

- [x] EPIG repository README reviewed
- [x] NRC VAD v2 paper identity and implications recorded
- [x] EPIG subject-centric CSV counted
- [x] NRC v2.1 files counted
- [x] `llm_expanded_prompts.csv` risk noted
- [x] `lexicons.html` lexicon catalog reviewed
- [x] Terms of Use redistribution constraint noted
- [x] `EmotionDynamics` checkout state inspected
- [x] `EmotionDynamics` README/code/uedLib docs reviewed
- [x] `EmotionDynamics` local lexicon CSV formats sampled

---

## Q1. Reference Refresh Docs Setup

Files:

```text
docs/semantic_epig/reference_refresh_spec.md
docs/semantic_epig/reference_refresh_progress.md
docs/semantic_epig/reference_refresh_tasks.md
```

Acceptance:

- [x] Spec records whether more refactor is needed
- [x] Progress records current findings and risks
- [x] Tasks separate audit/data-only work from runtime adoption

---

## Q2. Behavior Lock For Reference Audit

### Q2.1 Run focused baseline

Run:

```bash
python -m unittest assets.test_emotion_vad_profiles assets.test_emotion_vad_alignment assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig_audit
python tools/validate_prompt_data.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Acceptance:

- [x] Results recorded in `reference_refresh_progress.md`
- [x] Existing failures are separated from reference-refresh changes

### Q2.2 Capture active/passive audit baseline

Run:

```bash
python tools/audit_semantic_epig_outputs.py --samples assets/fixtures/semantic_epig_audit_cases.json --seed-start 0 --seed-count 8 --output assets/results/semantic_epig_audit_reference_refresh_baseline.json
```

Acceptance:

- [x] Baseline JSON is generated locally
- [x] Summary metrics are recorded in progress
- [x] No repo config mutation occurs

---

## Q3. Reference Alignment Audit Tool

### Q3.1 Add reference adapter

Candidate file:

```text
vocab/epig_reference.py
```

Functions:

```python
def normalize_nrc_score(value: float) -> float: ...
def read_epig_subject_centric_csv(path: str) -> dict[str, dict]: ...
def read_nrc_vad_tsv(path: str, *, normalize: bool = True) -> dict[str, dict]: ...
def lookup_vad(term: str, *sources) -> dict | None: ...
```

Acceptance:

- [x] Uses stdlib only
- [x] Handles EPIG 0..1 scale and NRC -1..1 scale
- [x] Missing files produce clear audit errors, not runtime crashes
- [x] Unit tests use tiny fixtures, not full external data

### Q3.2 Add audit CLI

Candidate file:

```text
tools/audit_epig_reference_alignment.py
```

CLI:

```bash
python tools/audit_epig_reference_alignment.py --epig-dir "../参考/EPIG" --nrc-dir "../参考/NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1" --output assets/results/epig_reference_alignment.json
```

Acceptance:

- [x] Reports current emotion category / nuance distance to reference terms
- [x] Reports personality descriptor reference coverage
- [x] Reports subject-centric candidate counts
- [x] Reports LLM prompt policy issues
- [x] Reports lexicon catalog availability from `lexicons.html`
- [x] Reports missing optional sources such as WorryWords / Words of Warmth data
- [x] Reports whether `EmotionDynamics` has usable source files and local lexicon CSVs
- [x] Does not alter `semantic_epig_config.json`

### Q3.3 Add tests

Candidate file:

```text
assets/test_epig_reference_alignment.py
```

Acceptance:

- [x] Tiny EPIG CSV fixture parses
- [x] Tiny NRC TSV fixture parses
- [x] -1..1 to 0..1 normalization is tested
- [x] Audit schema is deterministic

---

## Q4. Current-Vocabulary Reference Overlay

### Q4.1 Extract current repo vocabulary

Candidate file:

```text
tools/extract_epig_reference_overlay.py
```

Inputs:

```text
vocab/data/*.json
vocab/garnish/*.py
vocab/source/action_pools/*.json
```

Acceptance:

- [x] Extracts descriptor phrases and normalized term tokens from current repo vocabulary
- [x] Does not scan unrelated generated outputs by default
- [x] Records source file and field path for each extracted term

### Q4.2 Match extracted terms against local reference sources

Reference sources:

```text
参考/EPIG/data/NRC_VAD_with_subject_centric.csv
参考/NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1.txt
参考/NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1/MWE/mwe-NRC-VAD-Lexicon-v2.1.txt
参考/EmotionDynamics/code/uedLib/lexicons/NRC-VAD-Lexicon.csv
参考/EmotionDynamics/lexicons/NRC_VAD_*.csv
参考/EmotionDynamics/lexicons/NRC_EmoLex_*.csv
```

Acceptance:

- [x] EPIG 0..1 scores are read without rescaling
- [x] NRC v2.1 -1..1 scores are normalized to 0..1
- [x] Exact phrase match is preferred before token fallback
- [x] MWE matches are reported separately from unigram matches
- [x] MWE-first behavior is covered by a tiny fixture test
- [x] EmotionDynamics VAD/EmoLex local CSVs are optional lookup sources
- [x] Missing reference files are warnings, not hard failures

### Q4.3 Write local overlay

Output:

```text
assets/results/epig_reference_overlay.local.json
```

Acceptance:

- [x] Overlay contains only current repo vocabulary matches
- [x] Overlay includes source reference metadata and scale normalization metadata
- [x] Overlay is not tracked by default
- [x] Runtime does not read it in active mode yet

---

## Q5. Subject-Centric Descriptor Audit

### Q5.1 Compare current garnish descriptors to EPIG subject-centric terms

Acceptance:

- [x] Existing expression/gaze/behavior/personality descriptors are tokenized conservatively
- [x] Matching reference terms are reported
- [x] Non-matching but useful descriptors are not automatically removed

### Q5.2 Produce candidate report

Output:

```text
assets/results/subject_centric_descriptor_candidates.json
```

Acceptance:

- [x] Candidate list is local/generated, not tracked until license decision
- [x] Candidates are tagged as `direct`, `needs_phrase`, `reject`, or `unmatched`
- [x] No runtime prompt changes

---

## Q6. Dominance / EmotionDynamics / WorryWords / Warmth Pilot

### Q6.1 Add audit-only dominance projection

Candidate mapping:

```text
dominance -> confidence/restraint
valence -> warmth/sociability
arousal -> motion_energy/time_pressure
```

Acceptance:

- [x] Ranking deltas are reported for personality descriptors
- [x] Action/personality runtime output remains unchanged
- [x] High-risk stereotype drift examples are recorded

### Q6.2 Add optional WorryWords and Words of Warmth audit hooks

Acceptance:

- [x] WorryWords missing data is reported as optional missing input
- [x] Words of Warmth missing data is reported as optional missing input
- [ ] If local data is later added, calmness-anxiety maps only to audit metrics first
- [ ] If local data is later added, warmth/sociability/trust/competence maps only to personality audit metrics first

### Q6.3 Add EmotionDynamics-inspired coverage metrics

Use ideas from:

```text
参考/EmotionDynamics/code/avgEmoValues.py
参考/EmotionDynamics/code/uedLib/lib/ued.py
```

Acceptance:

- [x] Compute lexicon token coverage for current repo vocabulary
- [x] Compute average reference VAD for matched descriptor groups
- [x] Do not add pandas/numpy/scipy/nltk/PyYAML/python_box/tqdm dependencies
- [x] Rolling-window UED metrics remain optional research notes, not runtime logic

### Q6.4 Decide whether dominance belongs in runtime axes

Acceptance:

- [x] Decision recorded in progress
- [x] If rejected/deferred, reason is recorded
- [x] If accepted, next task requires tests and active/passive audit

---

## Q7. LLM Expanded Prompt Negative Corpus

### Q7.1 Scan expanded prompts for semantic-only policy violations

Reference:

```text
参考/EPIG/data/llm_expanded_prompts.csv
```

Acceptance:

- [x] camera terms are counted
- [x] quality/style/render terms are counted
- [x] body-type or sensitive terms are counted if present
- [x] report is saved under `assets/results/`

### Q7.2 Add validator fixture only if useful

Acceptance:

- [x] Small hand-curated negative examples are added to tests
- [x] Full CSV is not copied into repo
- [x] Runtime prompt generation does not use expanded prompts

---

## Q8. EmotionDynamics Availability Review

### Q8.1 Verify local checkout usability

Reference:

```text
参考/EmotionDynamics
```

Acceptance:

- [x] Current folder inspected
- [x] Current folder has usable source files
- [x] Available APIs and metrics summarized in `reference_refresh_spec.md`
- [ ] Do not add dependencies from EmotionDynamics without a separate plan

Current state:

```text
Done: local checkout is readable; git commands still hit safe.directory ownership protection.
```

---

## Q9. Adoption Decision

### Q9.1 Review audit outputs

Inputs:

```text
assets/results/epig_reference_alignment.json
assets/results/epig_reference_overlay.local.json
assets/results/semantic_epig_audit_reference_refresh_baseline.json
assets/results/subject_centric_descriptor_candidates.json
```

Acceptance:

- [x] Decide whether current implementation is already sufficient
- [x] Decide whether to add small derived data subsets
- [x] Decide whether dominance remains audit-only

### Q9.2 If adopting derived data, create a new active/passive plan

Acceptance:

- [x] N/A for this wave: no derived runtime data is adopted
- [x] N/A for this wave: no active output changes are made
- [x] N/A for this wave: no prompt snapshot changes are introduced
- [x] `reference_refresh_progress.md` is updated with the no-adoption decision
- [x] No tracked source rows or score-bearing overlays are added
- [x] Source/rationale/transformation requirements are deferred to any future adoption wave
- [x] `参考/` files remain untracked

Current decision:

```text
No derived runtime data is adopted in this wave, so no active/passive runtime plan is opened.
Any future runtime adoption must start a new behavior spec and tests before code changes.
```

---

## Completion Checklist

- [x] Current state analyzed
- [x] Additional reference value assessed
- [x] Spec/progress/tasks docs created
- [x] Behavior baseline rerun after docs
- [x] Reference audit tool implemented
- [x] Current-vocabulary local overlay implemented
- [x] Subject-centric descriptor audit implemented
- [x] Dominance / EmotionDynamics audit-only pilot implemented
- [x] LLM expanded prompt negative corpus audit implemented
- [x] Adoption/rejection decision implemented
- [x] Commit policy resolved: keep `参考/` out of commits; do not track source data as-is
- [x] License/redistribution gate resolved for this wave: no score-bearing data is tracked
- [x] Adoption/rejection decision recorded
