# EPIG Reference Refresh Handoff

作成日: 2026-06-16
対象ブランチ: `dev2`
直近実装コミット: `acfa45c Constrain reference refresh to auditable local adoption decisions`

---

## 1. 現在の結論

今回の reference refresh wave では、EPIG / NRC VAD / EmotionDynamics / LLM expanded prompts を runtime prompt 生成へ直接接続していない。

最終判断:

```text
overall_decision=no_runtime_adoption_now
```

理由:

- 既存 Semantic EPIG runtime は現時点で十分に機能している。
- 参照資料は監査・校正には有用だが、raw data / score-bearing overlay を追跡・runtime化するにはライセンスと出力 drift のリスクがある。
- `subject_centric_descriptor_candidates.json` の `needs_phrase=80` は、そのまま採用する語彙ではなく、リポ用に書き直す候補。
- dominance projection は有用な監査軸だが、現状の personality 比較 99件はすべて token fallback 由来で、runtime axis 採用には弱い。
- `llm_expanded_prompts.csv` は style / quality / camera / render terms を多く含むため、prompt source ではなく negative corpus 扱い。

---

## 2. 今回追加した tracked files

Reference readers:

```text
vocab/epig_reference.py
```

Audit / decision tools:

```text
tools/audit_epig_reference_alignment.py
tools/extract_epig_reference_overlay.py
tools/audit_subject_centric_descriptors.py
tools/audit_reference_dimension_projection.py
tools/audit_llm_expanded_prompt_policy.py
tools/review_reference_refresh_adoption.py
```

Tests / fixtures:

```text
assets/test_epig_reference_alignment.py
assets/test_epig_reference_overlay.py
assets/test_subject_centric_descriptor_audit.py
assets/test_reference_dimension_projection.py
assets/test_llm_expanded_prompt_policy.py
assets/test_reference_refresh_adoption.py
assets/fixtures/semantic_policy_negative_examples.json
```

Docs:

```text
docs/semantic_epig/reference_refresh_spec.md
docs/semantic_epig/reference_refresh_progress.md
docs/semantic_epig/reference_refresh_tasks.md
docs/semantic_epig/reference_refresh_handoff.md
```

---

## 3. Local generated files

以下は `assets/results/` 配下の生成物で、`.gitignore` 対象。コミットしない。

```text
assets/results/epig_reference_alignment.json
assets/results/epig_reference_overlay.local.json
assets/results/subject_centric_descriptor_candidates.json
assets/results/reference_dimension_projection.json
assets/results/llm_expanded_prompt_policy_audit.json
assets/results/reference_refresh_adoption_decision.json
assets/results/semantic_epig_audit_reference_refresh_baseline.json
```

`参考/` 配下の資料もコミット対象外。

---

## 4. Key metrics from the latest local run

Current vocabulary overlay:

```text
extracted_term_count=8728
matched_term_count=7700
unmatched_term_count=1028
warning_count=0
```

Subject-centric descriptor audit:

```text
descriptor_count=809
direct_count=7
needs_phrase_count=80
reject_count=595
unmatched_count=127
warning_count=0
```

Dominance / EmotionDynamics-style projection:

```text
matched_term_count=7700
projection_comparison_count=99
high_risk_count=15
runtime_axis_adoption=deferred
```

LLM expanded prompt policy audit:

```text
row_count=44
rows_with_policy_issues=34
policy_issue_count=83
domain_counts={body_type: 0, camera: 7, quality: 58, render: 7, style: 11}
```

Adoption decision:

```text
overall_decision=no_runtime_adoption_now
runtime_prompt_changes=deferred
dominance_runtime_axis=audit_only
small_derived_data_subsets_should_be_added_now=False
```

---

## 5. How to regenerate local reports

Run from repo root:

```bash
python tools\audit_epig_reference_alignment.py --reference-root "..\参考" --output assets\results\epig_reference_alignment.json
python tools\extract_epig_reference_overlay.py --reference-root "..\参考" --output assets\results\epig_reference_overlay.local.json
python tools\audit_subject_centric_descriptors.py --reference-root "..\参考" --output assets\results\subject_centric_descriptor_candidates.json
python tools\audit_reference_dimension_projection.py --reference-root "..\参考" --output assets\results\reference_dimension_projection.json
python tools\audit_llm_expanded_prompt_policy.py --reference-root "..\参考" --output assets\results\llm_expanded_prompt_policy_audit.json
python tools\review_reference_refresh_adoption.py --results-dir assets\results --output assets\results\reference_refresh_adoption_decision.json
```

---

## 6. Verification commands

Latest verification:

```bash
python -m unittest assets.test_reference_refresh_adoption assets.test_llm_expanded_prompt_policy assets.test_reference_dimension_projection assets.test_subject_centric_descriptor_audit assets.test_epig_reference_alignment assets.test_epig_reference_overlay assets.test_emotion_vad_profiles assets.test_emotion_vad_alignment assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig_audit assets.test_semantic_policy
python -m py_compile vocab\epig_reference.py tools\extract_epig_reference_overlay.py tools\audit_epig_reference_alignment.py tools\audit_subject_centric_descriptors.py tools\audit_reference_dimension_projection.py tools\audit_llm_expanded_prompt_policy.py tools\review_reference_refresh_adoption.py assets\test_epig_reference_alignment.py assets\test_epig_reference_overlay.py assets\test_subject_centric_descriptor_audit.py assets\test_reference_dimension_projection.py assets\test_llm_expanded_prompt_policy.py assets\test_reference_refresh_adoption.py
python tools\validate_prompt_data.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Expected result:

```text
50 tests OK
py_compile OK
validate_prompt_data.py -> ERROR: [], WARNING: []
asset_validator.validate_assets() -> 0 issues
```

---

## 7. Important constraints for the next session

- Do not commit `参考/`.
- Do not commit `assets/results/`.
- Do not runtime-load raw EPIG / NRC / EmotionDynamics data.
- Do not use `llm_expanded_prompts.csv` as prompt source.
- Do not adopt score-bearing overlays without a new active/passive behavior spec.
- Do not add dependencies for EmotionDynamics.
- Keep public ComfyUI node I/O unchanged unless a separate migration plan is approved.

---

## 8. If runtime improvement is requested next

Recommended path:

1. Pick a narrow target, probably subject-centric descriptor refinement.
2. Review `assets/results/subject_centric_descriptor_candidates.json`.
3. Treat `needs_phrase` as hints only.
4. Write a small repo-authored descriptor list or modify existing descriptors by hand.
5. Add tests before runtime changes.
6. Run active/passive prompt audit and snapshot checks.
7. Only then connect the curated data to runtime ranking.

Do not start by loading the generated overlay at runtime.

