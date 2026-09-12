# Semantic Diversity / Natural Language Refactor Progress

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`  
仕様: `docs/diversity_refactor/spec.md`  
タスク: `docs/diversity_refactor/tasks.md`  
作成日: 2026-09-06

---

## 1. Wave Status

```text
Wave: Semantic Diversity / Natural Language Refactor
State: PLANNED
Current task: F0.1
Baseline: V150
Active quantity target: NONE
V250/V350/V500: DEFERRED
```

### Decision

V150 を semantic-base の一旦の完成版として扱う。

この wave では:
- base variation 数を success metric としない
- effective diversity を測る
- Natural Language Realizer v2 を作る
- Deterministic Diversity Scheduler を作る

---

## 2. Current Known V150 Reference

2026-09-06 repository documentation reference:

```text
unique subjects: 135
unique locations: 109
base variations: 150,184
compatibility rows: 8,227
actions/location: min 12 / median 16 / mean ~16.33 / max 20
mood tags: 172
micro actions: 280
background context tags: 1,028
semantic units: 1,480
```

**F0.2 で実 repository HEAD から再計測して上書き/確認する。**

Baseline HEAD:

```text
PENDING
```

Baseline date:

```text
PENDING
```

---

## 3. Protected V150 Surfaces

Feature expansion 目的の変更禁止:

```text
vocab/data/variation_scope.json
assets/compatibility_review.csv
vocab/source/action_pools/*.json
vocab/source/action_pools/_shared_families.json
vocab/data/action_pools.json
```

Approved exception tasks:

```text
none
```

---

## 4. Task Board

Status values:

```text
TODO
IN_PROGRESS
BLOCKED
ELIGIBLE
PROMOTED
REJECTED
SKIPPED
```

| ID | Task | Status | Owner files / note |
|---|---|---|---|
| F0.1 | Add canonical wave docs | TODO | `docs/diversity_refactor/*` |
| F0.2 | Capture exact V150 baseline | TODO | read-only + progress |
| F0.3 | Mark V250/V350/V500 deferred | TODO | docs only |
| F0.4 | Add V150 freeze regression guard | TODO | test |
| A1.1 | Lock metric schema | TODO | docs |
| A1.2 | Implement pure diversity metrics | TODO | tools + tests |
| A1.3 | Implement semantic signature builder | TODO | tools + tests |
| A1.4 | Implement Effective Diversity Audit CLI | TODO | tools + tests |
| A1.5 | Capture V150 diversity baseline | TODO | generated report + progress |
| A1.6 | Lock target/guard thresholds | TODO | progress |
| N2.1 | Add Realizer v2 contract tests | TODO | tests |
| N2.2 | Extend syntax-family metadata | TODO | vocab/config |
| N2.3 | Implement eligibility engine | TODO | realizer |
| N2.4 | Implement first 3 syntax families | TODO | realizer |
| N2.5 | Implement remaining required families | TODO | realizer |
| N2.6 | Add v2 debug payload | TODO | builder/debug |
| N2.7 | Run Realizer v2 candidate gate | TODO | read-only evaluation |
| N2.8 | Activate v2 for composition mode | TODO | runtime |
| D3.1 | Implement scheduler primitive | TODO | new module + tests |
| D3.2 | Add generic spread-group selector | TODO | scheduler |
| D3.3 | Integrate syntax scheduler | TODO | realizer/scheduler |
| D3.4 | Audit action-family bias | TODO | read-only evaluation |
| D3.5 | Integrate action scheduler | TODO | action generator |
| D3.6 | Optional extra scheduler axes | TODO | only with evidence |
| R4.1 | Combined final gate | TODO | verification |
| R4.2 | Final before/after table | TODO | progress |
| R4.3 | Update canonical docs | TODO | docs |
| R4.4 | Close wave | TODO | progress |

---

## 5. Baseline Command Receipt

### F0.2

Status:

```text
NOT RUN
```

Commands:

```bash
git status --short --branch
git rev-parse HEAD
python assets/calc_variations.py --json
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python tools/verify_full_flow.py
```

Results:

```text
PENDING
```

---

## 6. Effective Diversity Baseline

### Metric schema

```text
schema_version: effective-diversity-audit/v1
semantic signature:
  - semantic_signature_v1/core
  - semantic_signature_v1/frame
```

Status:

```text
NOT IMPLEMENTED
```

### Baseline metrics

| Metric | @128 | @512 | @2048 | @8192 |
|---|---:|---:|---:|---:|
| semantic_core_unique | pending | pending | pending | pending |
| semantic_frame_unique | pending | pending | pending | pending |
| subject_coverage | pending | pending | pending | pending |
| location_coverage | pending | pending | pending | pending |
| action_family_coverage | pending | pending | pending | pending |
| object_family_coverage | pending | pending | pending | pending |
| syntax_family_coverage | pending | pending | pending | pending |

Other:

```text
exact_prompt_duplicate_rate: pending
normalized_prompt_duplicate_rate: pending
semantic_core_duplicate_rate: pending
semantic_frame_duplicate_rate: pending
syntax_entropy_raw: pending
syntax_entropy_normalized: pending
dominant_syntax_share: pending
max_consecutive_same_syntax_family: pending
max_consecutive_same_action_family: pending
```

Baseline artifact:

```text
path: pending
sha256: pending
source_hash: pending
workflow_hash: pending
config_hash: pending
```

---

## 7. Locked Target / Guard Metrics

**A1.6 まで数値を lock しない。**

### Targets

```text
syntax diversity target: PENDING BASELINE
targeted coverage target: PENDING BASELINE
consecutive repetition target: PENDING BASELINE
```

### Guards

```text
semantic core uniqueness: NON-REGRESSION
semantic frame uniqueness: NON-REGRESSION
semantic consistency: NON-REGRESSION
naturalness: NON-REGRESSION
image-prompt suitability: NON-REGRESSION
protagonist clarity: NON-REGRESSION
banned-domain leakage: ZERO
determinism: EXACT
V150 count: FROZEN
public node I/O: UNCHANGED
```

---

## 8. Natural Language Realizer v2 State

```text
State: NOT STARTED
Required active families: 6
Optional families: up to 2
Active default: no
Legacy rollback: composition_mode=false
```

Family status:

| Family | Implemented | Eligible tests | Active |
|---|---|---|---|
| subject_action_scene | existing baseline | pending v2 | no |
| subject_action__scene_tail | partial existing behavior | pending | no |
| scene_lead_subject_action | no | pending | no |
| action_lead_subject_scene | no | pending | no |
| subject_scene_action | no | pending | no |
| subject_action_scene_insert | no | pending | no |
| scene_sentence__subject_action | optional | pending | no |
| subject_action_progress__scene | optional | pending | no |

Candidate receipt:

```text
candidate HEAD: pending
effective-diversity report: pending
prompt-quality comparison: pending
verdict: pending
```

---

## 9. Deterministic Diversity Scheduler State

```text
State: NOT STARTED
Core primitive: pending
Syntax integration: pending
Action integration: pending
Optional axes: none approved
```

Targeted axes:

| Axis | Baseline bias measured | Scheduler integrated | Verdict |
|---|---|---|---|
| syntax_family | no | no | pending |
| action_family | no | no | pending |
| garnish_family | no | no | not authorized |
| clothing_family | no | no | not authorized |

---

## 10. Before / After Comparison

Fill only with hash-bound reports.

| Metric | V150 baseline | Realizer v2 | Realizer v2 + Scheduler |
|---|---:|---:|---:|
| semantic_core_unique@2048 | pending | pending | pending |
| semantic_frame_unique@2048 | pending | pending | pending |
| action_family_coverage@2048 | pending | pending | pending |
| syntax_family_coverage@2048 | pending | pending | pending |
| normalized_prompt_duplicate_rate | pending | pending | pending |
| syntax_entropy_normalized | pending | pending | pending |
| max_same_syntax_run | pending | pending | pending |
| max_same_action_run | pending | pending | pending |
| semantic consistency | pending | pending | pending |
| naturalness | pending | pending | pending |

---

## 11. Work Log

Codex は各 task 後に追記する。

Template:

```text
### YYYY-MM-DD — TASK-ID — TITLE

State: PROMOTED | ELIGIBLE | REJECTED | BLOCKED

Baseline HEAD:
Candidate HEAD:

Owned files:
- ...

Changes:
- ...

Commands:
- `...`

Results:
- ...

Metrics:
- target:
- guards:

Decision:
- ...

Follow-up:
- ...

Evidence:
- artifact path:
- sha256:
```

---

## 12. Decision Log

### D-001 — Freeze V150

Date: 2026-09-06  
Status: ACCEPTED

Decision:

```text
V150 is the semantic-base reference for this wave.
V250/V350/V500 are deferred.
Base variation count is not the optimization target.
```

Reason:

```text
Further quantity expansion has high authoring/review/Codex cost.
The repository already has a substantial semantic-only base and existing
ActionFrame/ContentPlan structures that can create more effective diversity
through better realization and deterministic selection.
```

### D-002 — No LLM in runtime

Date: 2026-09-06  
Status: ACCEPTED

```text
Effective diversity, realization, and scheduling remain pure rule-based.
LLM comparison may be external research only, not runtime dependency.
```

### D-003 — Measure before tuning

Date: 2026-09-06  
Status: ACCEPTED

```text
Do not lock numeric Realizer/Scheduler improvement thresholds until
A1 Effective Diversity baseline has been measured.
```

---

## 13. Blockers

Current:

```text
none
```

Add blockers without deleting previous entries.

---

## 14. Final Receipt

State:

```text
NOT READY
```

Final HEAD:

```text
pending
```

Final verification:

```text
pending
```

Final wave verdict:

```text
pending
```

Promoted features:

```text
pending
```

Rejected/deferred features:

```text
V250/V350/V500: deferred before wave start
others: pending
```
