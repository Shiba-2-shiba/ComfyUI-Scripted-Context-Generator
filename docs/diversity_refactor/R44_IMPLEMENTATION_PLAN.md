# R44 Realizer v2 Coverage Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase ordinary Realizer v2 reachability from the verified 11/512, 3-family checkpoint toward and, within at most three bounded coverage packets, to **>=64/512 ordinary v2 applications and >=5 ordinarily executed required syntax families**, while preserving V150 semantics, exact fallback compatibility, source-bound proof, and determinism.

**Architecture:** Reuse the existing R43 reachability audit and `RealizationEvidence`/`FamilyProof` authority. Add a diagnostic-only `CoverageSignature` and deterministic packet selector to cluster recurring blocker structures without using whole prompt text or seeds as permission. Implement at most three TDD-driven producer-bound coverage packets selected from those clusters; each packet is independently measured against the preceding preserved checkpoint.

**Tech Stack:** Python 3.10-compatible standard library, existing `unittest` test style, existing ComfyUI repository modules, existing canonical JSON/hash helpers, Git/GitHub source snapshots. No new runtime dependency.

**Spec:** `docs/diversity_refactor/R44_DESIGN.md` (use the supplied `R44_DESIGN.md` as the source text)

## Global Constraints

- Work from `refactor/realizer-v2`; authoring HEAD is `b16a4dbca7d91d6d1cdefbfd521fd6a44787765a`.
- Preserve the latest verified 11/512 development behavior before the first R44 runtime change.
- Do not change public `Context*` inputs/outputs, `PromptCleaner` public behavior, or `context_json` version/schema.
- Do not change V150 protected variation data to increase coverage.
- Do not add LLM, embedding, parser, POS-tagger, dependency-parser, or other NLP dependencies.
- Do not add camera/style/quality/artist/render language.
- Do not add seed allowlists, fixture-ID runtime branches, complete prompt allowlists, or complete action/scene-string permission tables.
- Exact text equality may validate replay/binding; it may not be the sole authorization for a new grammar capability.
- Preserve `Truth.TRUE/FALSE/UNKNOWN`; UNKNOWN never becomes safe by default.
- Do not relax A1.6 thresholds, family requirements, source-binding checks, or policy/solo-safety checks.
- Do not count forced family execution as ordinary family observation.
- Do not activate N2.8, D3, or promote to `main` in R44.
- Heavy formal reference8192/gate2048/fixed80/blind-review/confirmation/release work remains NOT_RUN in R44.
- Implement no more than three accepted runtime coverage packets. If the 64/5 guide is still unmet, finish R44 as BLOCKED with a measured handoff.
- Every accepted runtime packet gets its own source-bound checkpoint and commit.
- Existing published comparison tags must never be force-moved or deleted.
- Use Python 3.10-compatible syntax.

---

## File Structure Map

### New files

- `docs/diversity_refactor/R44_DESIGN.md` — approved R44 architecture/specification.
- `docs/diversity_refactor/R44_IMPLEMENTATION_PLAN.md` — this execution plan.
- `docs/diversity_refactor/r44_progress.md` — R44-only task ledger, commands, hashes, verdicts.
- `tools/realizer_coverage_signatures.py` — pure/read-only coarse structural signature builder; never runtime authorization.
- `tools/select_r44_coverage_packets.py` — deterministic cluster ranking and packet manifest generator.
- `assets/test_r44_coverage_signatures.py` — signature contract tests.
- `assets/test_r44_packet_selection.py` — deterministic packet ranking tests.
- `assets/test_r44_packet_a.py` — packet A real/recombination/adversarial tests.
- `assets/test_r44_packet_b.py` — packet B tests.
- `assets/test_r44_packet_c.py` — packet C tests when packet C is needed; create only when selected.
- `docs/diversity_refactor/r44_packet_a.json` — frozen packet A diagnostic selection.
- `docs/diversity_refactor/r44_packet_b.json` — frozen packet B selection.
- `docs/diversity_refactor/r44_packet_c.json` — frozen packet C selection when needed.
- `docs/diversity_refactor/r44_handoff.md` — final development handoff.
- `docs/diversity_refactor/r44_handoff_summary.json` — compact source-bound R44 verdict.

### Existing files that may change

- `tools/realizer_reachability_diagnostics.py` — attach diagnostic coverage signature to each row; no permission change.
- `tools/audit_realizer_reachability.py` — aggregate signature counts and emit a stable development report.
- `pipeline/v2_common_action_grammar.py` — only for selected producer-bound Action capabilities.
- `pipeline/v2_leaf_grammar.py` — only for reusable bounded leaf grammar required by selected packets.
- `pipeline/v2_structural_evidence.py` — only if new Action atoms/facts need exact source-bound projection.
- `pipeline/v2_scene_provenance.py` — only for selected Scene source/ownership/nominal capabilities.
- `pipeline/v2_clothing_provenance.py` — only if a selected packet proves Clothing is an unavoidable blocker.
- `pipeline/v2_support_provenance.py` — only if Subject/Garnish/Mood support is an unavoidable selected blocker.
- `pipeline/v2_template_provenance.py` — only if selected packet requires a new bounded template topology proof.
- `pipeline/family_capabilities.py` — only when an already-proved atom/placement cannot currently be represented by the existing family constructor/proof; no new semantic inference here.
- `pipeline/v2_candidate_bridge.py` — diagnostics only unless a zero-behavior-change common-proof shadow check is added; no scheduler and no direct-route retirement requirement.
- `CURRENT_STATUS.md`, `docs/diversity_refactor/tasks.md`, `docs/diversity_refactor/progress.md` — measured status only.

### Files that R44 should normally not touch

- `vocab/data/variation_scope.json`
- `assets/compatibility_review.csv`
- `vocab/source/action_pools/*.json`
- `vocab/source/action_pools/_shared_families.json`
- `vocab/data/action_pools.json`
- `vocab/data/natural_language_realizer_v2.json` unless a catalog bug is independently demonstrated; R44 does not add syntax families.
- public node signatures in `nodes_context.py`

---

## Task 0: Create an isolated R44 execution workspace and lock the pre-R44 baseline

**Files:**
- Create: `docs/diversity_refactor/R44_DESIGN.md`
- Create: `docs/diversity_refactor/R44_IMPLEMENTATION_PLAN.md`
- Create: `docs/diversity_refactor/r44_progress.md`
- Create: `docs/diversity_refactor/r44_baseline.json`
- Modify: `docs/diversity_refactor/tasks.md`
- Modify: `CURRENT_STATUS.md`
- Evidence output: `assets/results/diversity_refactor/r44/baseline-01/`

**Interfaces:**
- Consumes: current `refactor/realizer-v2` source and existing R43/AS01 verifier/audit tools.
- Produces: a source-bound, replayable 11/512 R44 baseline that every later packet compares against, plus immutable tag `realizer-v2-r44-baseline-11`.

- [ ] **Step 1: Create an isolated worktree/branch using Superpowers**

Use `superpowers:using-git-worktrees` before modifying source. Create a branch named `refactor/realizer-v2-r44` from the current `refactor/realizer-v2` HEAD unless the repository already has a dedicated user-approved R44 branch.

Run:

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse refactor/realizer-v2
```

Expected at plan authoring time:

```text
b16a4dbca7d91d6d1cdefbfd521fd6a44787765a
```

If the current branch HEAD differs, do **not** silently reset it. Compare runtime-relevant changes:

```bash
git diff --stat b16a4dbca7d91d6d1cdefbfd521fd6a44787765a..HEAD -- \
  pipeline prompt_renderer.py tools vocab/data/natural_language_realizer_v2.json \
  core nodes_context.py nodes_prompt_cleaner.py
```

If this shows runtime changes not already incorporated into a new verified 512 checkpoint, record `R44-00 = BLOCKED` and stop. Documentation-only or comparison-source-preservation changes may proceed after their hashes are recorded.

- [ ] **Step 2: Install the supplied design and plan text into the repository**

Copy the supplied artifacts verbatim to:

```text
docs/diversity_refactor/R44_DESIGN.md
docs/diversity_refactor/R44_IMPLEMENTATION_PLAN.md
```

Do not rewrite the design to make current failures disappear.

- [ ] **Step 3: Add the R44 progress ledger before runtime edits**

Create `docs/diversity_refactor/r44_progress.md` with this exact initial structure:

```markdown
# R44 Progress

## Baseline
- branch:
- head:
- source_tree_hash:
- baseline_reachability_sha256:
- ordinary_v2: pending
- ordinary_families: pending
- forced_families: pending

## Task ledger
| Task | State | Commit | Evidence | Notes |
|---|---|---|---|---|
| R44-00 | IN_PROGRESS | | | baseline lock |
| R44-01 | NOT_STARTED | | | coverage signatures |
| R44-02 | NOT_STARTED | | | packet selection |
| R44-03 | NOT_STARTED | | | packet A |
| R44-04 | NOT_STARTED | | | packet B |
| R44-05 | NOT_STARTED | | | packet C / conditional |
| R44-06 | NOT_STARTED | | | development gate |
| R44-07 | NOT_STARTED | | | handoff |
```

- [ ] **Step 4: Run the pre-edit focused and regression verifier**

Use new output directories:

```bash
python tools/verify_realizer_v2_candidate.py \
  --stage focused \
  --output-dir assets/results/diversity_refactor/r44/baseline-01/focused

python tools/verify_realizer_v2_candidate.py \
  --stage regression \
  --output-dir assets/results/diversity_refactor/r44/baseline-01/regression
```

Expected: both development stages pass with no unexplained skip/xfail/collection/setup/teardown failure.

- [ ] **Step 5: Run and preserve the ordinary 512 reachability baseline**

```bash
python tools/audit_realizer_reachability.py \
  --profile intake \
  --force-families all \
  --output-dir assets/results/diversity_refactor/r44/baseline-01/reachability
```

Assert from `reachability.json`:

```python
assert report["status"] == "ok"
assert report["actual"]["v2_applied_count"] == 11
assert report["actual"]["executed_v2_family_count"] == 3
assert not report["actual"]["errors"]
```

Also verify all six family keys have real forced proof according to the current R43/AS01 contract.

- [ ] **Step 6: Record a machine-readable baseline identity and mark R44-00 PASS**

Create `docs/diversity_refactor/r44_baseline.json` programmatically from the just-completed audit. The committed object must contain exactly these keys: `schema_version`, `git_commit`, `source_tree_hash`, `reachability_sha256`, `rows_sha256`, `ordinary_v2_count`, and `ordinary_family_count`. Generate it with the following command:

```bash
python - <<'PY'
import hashlib, json, pathlib, subprocess
root = pathlib.Path('.')
rdir = root / 'assets/results/diversity_refactor/r44/baseline-01/reachability'
report = json.loads((rdir / 'reachability.json').read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
payload = {
    'schema_version': 'r44-baseline/v1',
    'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'source_tree_hash': report['identity']['source_tree_hash'],
    'reachability_sha256': sha(rdir / 'reachability.json'),
    'rows_sha256': sha(rdir / 'rows.jsonl'),
    'ordinary_v2_count': report['actual']['v2_applied_count'],
    'ordinary_family_count': report['actual']['executed_v2_family_count'],
}
assert payload['ordinary_v2_count'] == 11
assert payload['ordinary_family_count'] == 3
(root / 'docs/diversity_refactor/r44_baseline.json').write_text(
    json.dumps(payload, sort_keys=True, indent=2) + '\n', encoding='utf-8')
PY
```

Create immutable baseline tag. If it already exists, it must point to the same commit; otherwise stop rather than move it:

```bash
BASELINE_COMMIT=$(python -c "import json; print(json.load(open('docs/diversity_refactor/r44_baseline.json'))['git_commit'])")
if git rev-parse -q --verify refs/tags/realizer-v2-r44-baseline-11 >/dev/null; then
  test "$(git rev-list -n1 realizer-v2-r44-baseline-11)" = "$BASELINE_COMMIT"
else
  git tag -a realizer-v2-r44-baseline-11 "$BASELINE_COMMIT" -m "R44 pre-change 11/512 development baseline"
fi
```

Update `r44_progress.md`, `tasks.md`, and `CURRENT_STATUS.md` with measured values only.

- [ ] **Step 7: Verify documentation-only diff and commit**

```bash
git diff --check
git status --short
```

Commit:

```bash
git add docs/diversity_refactor/R44_DESIGN.md \
        docs/diversity_refactor/R44_IMPLEMENTATION_PLAN.md \
        docs/diversity_refactor/r44_progress.md \
        docs/diversity_refactor/r44_baseline.json \
        docs/diversity_refactor/tasks.md CURRENT_STATUS.md
git commit -m "docs: start R44 coverage engineering wave"
```

---

## Task 1: Add diagnostic-only structural coverage signatures

**Files:**
- Create: `tools/realizer_coverage_signatures.py`
- Modify: `tools/realizer_reachability_diagnostics.py` (`diagnose_snapshot` return payload only)
- Modify: `tools/audit_realizer_reachability.py` (`summarize` and report identity)
- Create: `assets/test_r44_coverage_signatures.py`
- Create: `assets/test_r44_reachability_accounting.py`
- Modify: `docs/diversity_refactor/r44_progress.md`

**Interfaces:**
- Consumes: detached audit-sink snapshot plus the already-computed reachability diagnosis.
- Produces:

```python
build_coverage_signature(snapshot: Mapping[str, Any], diagnosis: Mapping[str, Any]) -> dict[str, Any]
coverage_signature_hash(signature: Mapping[str, Any]) -> str
```

The returned schema is `realizer-coverage-signature/v1`. It is diagnostic only and must never be imported by runtime authorization code.

- [ ] **Step 1: Write contract tests before implementation**

Create tests covering:

```python
class TestCoverageSignature(unittest.TestCase):
    def test_same_structure_different_text_has_same_signature(self): ...
    def test_different_action_slot_sequence_changes_signature(self): ...
    def test_different_scene_source_fields_changes_signature(self): ...
    def test_signature_contains_no_full_prompt_or_seed(self): ...
    def test_family_blockers_are_sorted_and_canonical(self): ...
    def test_signature_is_identical_across_dict_insertion_order(self): ...
    def test_unknown_owner_stays_unknown(self): ...
    def test_fallback_with_common_inputs_rebuilds_common_family_blockers(self): ...
    def test_stale_common_inputs_do_not_grant_diagnostic_eligibility(self): ...
```

The no-text test must recursively reject keys named `raw_prompt`, `cleaned_prompt`, `legacy_text`, `source_text`, and `run_seed`, and reject values equal to the supplied complete Action/Scene test strings.

- [ ] **Step 2: Run the new tests and verify failure**

```bash
python -m unittest assets.test_r44_coverage_signatures -v
```

Expected: import or missing-function failure because `tools/realizer_coverage_signatures.py` does not exist yet.

- [ ] **Step 3: Implement the pure signature builder**

Create `tools/realizer_coverage_signatures.py` with these constants and public functions:

```python
SCHEMA_VERSION = "realizer-coverage-signature/v1"

REPAIRABLE_OWNER_CLASSES = (
    "protagonist",
    "protagonist_body_part",
    "primary_object_part",
    "scene_event",
    "unknown",
)


def build_coverage_signature(snapshot, diagnosis):
    ...


def coverage_signature_hash(signature):
    ...
```

Implementation rules:

1. Canonicalize using the repository's existing canonical JSON helper rather than `repr`.
2. Whenever valid `bridge["common_inputs"]` exist, rebuild `RealizationEvidence` from those inputs and call existing `prove_all_families(...)` in read-only mode, even if ordinary dispatch fell back. Do not trust serialized proof bytes and do not alter selection.
3. Represent Action shape using constructor ID, ordered source fields, atom `form`, `attachment`, coarse owner class, and `grammar_known` truth value.
4. Represent Scene/Clothing/Template/support shape using constructor ID, source field sequence, catalog-source category, atom attachment/form/owner class, and runtime-availability state.
5. Represent family state with sorted eligible family keys and sorted blocker IDs from the freshly reconstructed common `FamilyProof` objects when available; otherwise retain the legacy diagnostic family state and mark its proof basis explicitly.
6. Include `blocked_domains` as sorted domain names.
7. Never include complete surface text, run seed, prompt text, or caller paths.

A valid shape resembles:

```python
{
    "schema_version": "realizer-coverage-signature/v1",
    "route": "common_evidence",
    "blocked_domains": ["action", "scene"],
    "domains": {
        "action": {
            "constructor_id": "action_slots:activity_first:false",
            "source_fields": ["primary_action", "posture", "time_or_weather"],
            "forms": ["gerund", "", "finite"],
            "attachments": ["main_predicate", "", "dependent_temporal_event"],
            "owners": ["protagonist", "unknown", "scene_event"],
            "grammar": ["true", "unknown", "true"],
        },
        "scene": {...},
    },
    "eligible_families": [],
    "family_blockers": {
        "scene_lead_subject_action": ["action.leaf_grammar_unknown"],
    },
}
```

Do not hardcode actual prompt phrases into the implementation.

- [ ] **Step 4: Re-run signature tests**

```bash
python -m unittest assets.test_r44_coverage_signatures -v
```

Expected: PASS.

- [ ] **Step 5: Attach the signature to `diagnose_snapshot` without changing permission**

In `tools/realizer_reachability_diagnostics.py`, after `domains`, `families`, `route`, and blockers are computed, build the signature and add:

```python
"coverage_signature": signature,
"coverage_signature_sha256": coverage_signature_hash(signature),
```

The return value of any runtime function in `pipeline/` must not depend on either field.

- [ ] **Step 6: Add accounting tests proving behavior is diagnostic-only**

`assets/test_r44_reachability_accounting.py` must verify on a fixed small cohort:

```python
before_prompt == after_prompt
before_context == after_context
before_selected_family == after_selected_family
before_rng_state == after_rng_state
```

It must also verify signature counts are independent of row order.

- [ ] **Step 7: Extend audit summary with signature counts**

In `tools/audit_realizer_reachability.py:summarize`, add:

```python
"coverage_signatures": [
    {
        "sha256": ...,
        "count": ...,
        "blocked_domains": ...,
        "example_seed_family_rows": ...,
    }
]
```

Requirements:

- sorted by descending count then SHA-256,
- no more than 8 examples per signature,
- counts are ordinary seed-family diagnostic rows, not promised rescue counts,
- update `audit_implementation_hash` to include `realizer_coverage_signatures.py`.

- [ ] **Step 8: Run focused tests and a 16-seed smoke audit twice**

```bash
python -m unittest \
  assets.test_r44_coverage_signatures \
  assets.test_r44_reachability_accounting -v

python tools/audit_realizer_reachability.py \
  --profile smoke --force-families all \
  --output-dir assets/results/diversity_refactor/r44/signature-smoke-a

python tools/audit_realizer_reachability.py \
  --profile smoke --force-families all \
  --output-dir assets/results/diversity_refactor/r44/signature-smoke-b
```

Compare canonical signature sections, ignoring output-directory/environment elapsed-time fields. They must be identical.

- [ ] **Step 9: Verify full 512 behavior remains 11/512 and 3 families**

```bash
python tools/audit_realizer_reachability.py \
  --profile intake --force-families all \
  --output-dir assets/results/diversity_refactor/r44/signature-intake
```

Assert ordinary output behavior did not change:

```python
assert report["actual"]["v2_applied_count"] == 11
assert report["actual"]["executed_v2_family_count"] == 3
```

- [ ] **Step 10: Commit Task 1**

```bash
git diff --check
git add tools/realizer_coverage_signatures.py \
        tools/realizer_reachability_diagnostics.py \
        tools/audit_realizer_reachability.py \
        assets/test_r44_coverage_signatures.py \
        assets/test_r44_reachability_accounting.py \
        docs/diversity_refactor/r44_progress.md
git commit -m "test: add R44 structural coverage signatures"
```

---

## Task 2: Add deterministic coverage-packet selection

**Files:**
- Create: `tools/select_r44_coverage_packets.py`
- Create: `assets/test_r44_packet_selection.py`
- Create: `docs/diversity_refactor/r44_packet_a.json`
- Create: `docs/diversity_refactor/r44_packet_b.json`
- Conditionally create: `docs/diversity_refactor/r44_packet_c.json`
- Modify: `docs/diversity_refactor/r44_progress.md`

**Interfaces:**
- Consumes: `rows.jsonl` from a current 512 R44 reachability audit with coverage signatures.
- Produces:

```python
select_packets(rows: Sequence[Mapping[str, Any]], *, max_packets: int = 3) -> list[dict[str, Any]]
```

CLI:

```bash
python tools/select_r44_coverage_packets.py \
  --rows assets/results/diversity_refactor/r44/packet-selection-intake/rows.jsonl \
  --output assets/results/diversity_refactor/r44/packet-selection.json \
  --max-packets 3
```

- [ ] **Step 1: Write packet-selection tests first**

Tests must cover:

```python
def test_excludes_existing_v2_successes(): ...
def test_excludes_policy_conflict(): ...
def test_excludes_binding_replay_mismatch(): ...
def test_excludes_family_role_mismatch_as_a_coverage_target(): ...
def test_requires_at_least_four_distinct_seeds(): ...
def test_prefers_more_distinct_seeds(): ...
def test_prefers_unobserved_family_potential_on_tie(): ...
def test_prefers_fewer_blocked_domains_on_tie(): ...
def test_tie_breaks_by_signature_hash(): ...
def test_input_row_order_does_not_change_packets(): ...
def test_packets_do_not_share_the_same_seed_signature_group(): ...
```

- [ ] **Step 2: Run tests and confirm failure**

```bash
python -m unittest assets.test_r44_packet_selection -v
```

Expected: missing module/function failure.

- [ ] **Step 3: Implement explicit blocker classification**

In `tools/select_r44_coverage_packets.py`, define immutable sets/prefix checks:

```python
HARD_EXCLUDE_IDS = {
    "policy.conflict",
    "binding.frame_current_text_mismatch",
    "binding.replay_mismatch",
    "render.proof_constructor_mismatch",
    "transport.runtime_inputs_missing",
}

ROUTE_ONLY_EXCLUDE_IDS = {
    "family.role_mismatch",
    "family.composition_mode_disabled",
}

REPAIRABLE_PREFIXES = (
    "action.",
    "scene.",
    "clothing.",
    "subject.",
    "template.",
    "garnish.",
    "mood.",
    "family.required_fact_not_true.",
    "family.forbidden_fact_not_false.",
    "family.missing_slot.",
)
```

`family.legacy_route_ceiling` is not enough by itself to select a packet; it may accompany a packet whose actual missing producer evidence is repairable.

- [ ] **Step 4: Implement deterministic packet scoring**

Each packet groups the same `coverage_signature_sha256` across ordinary fallback seeds. Calculate:

```python
score = (
    distinct_seed_count,
    unobserved_family_potential_count,
    -blocked_domain_count,
    -repairable_blocker_count,
)
```

Sort descending by this tuple, then ascending by SHA-256.

A packet manifest must contain:

```python
{
  "schema_version": "r44-coverage-packet/v1",
  "packet_id": "R44-A",
  "coverage_signature_sha256": "...",
  "distinct_seed_count": 0,
  "blocked_domains": [],
  "repairable_blocker_ids": [],
  "target_family_keys": [],
  "example_seeds": [],
  "projected_upper_bound": 0,
  "acceptance_min_new_ordinary": 0,
}
```

Define:

```python
acceptance_min_new_ordinary = max(4, min(16, projected_upper_bound // 2))
```

This is a development ROI floor, not an adoption threshold.

- [ ] **Step 5: Run packet-selection tests**

```bash
python -m unittest assets.test_r44_packet_selection -v
```

Expected: PASS.

- [ ] **Step 6: Generate the current 512 audit and packet selection**

```bash
python tools/audit_realizer_reachability.py \
  --profile intake --force-families all \
  --output-dir assets/results/diversity_refactor/r44/packet-selection-intake

python tools/select_r44_coverage_packets.py \
  --rows assets/results/diversity_refactor/r44/packet-selection-intake/rows.jsonl \
  --output assets/results/diversity_refactor/r44/packet-selection.json \
  --max-packets 3
```

- [ ] **Step 7: Apply the R44 bounded-scope viability gate**

Before runtime edits, assert:

1. packet A exists,
2. packet A has at least 4 seeds,
3. none of A/B/C has a hard-excluded blocker,
4. union of projected upper-bound seed sets across selected packets is large enough that `11 + union_count >= 64`.

If condition 4 fails, do not widen packet count or relax selection. Mark R44 `BLOCKED: bounded selected clusters cannot reach 64/512` and proceed directly to Task 7 handoff.

- [ ] **Step 8: Freeze packet manifests before implementation**

Copy selected packet entries into tracked files `r44_packet_a.json`, `r44_packet_b.json`, and, if selected, `r44_packet_c.json`. Add source-tree hash, reachability rows hash, selector implementation hash, and selection JSON hash.

Do not put complete prompt/action/scene text in these manifests.

- [ ] **Step 9: Commit Task 2**

```bash
git diff --check
git add tools/select_r44_coverage_packets.py \
        assets/test_r44_packet_selection.py \
        docs/diversity_refactor/r44_packet_*.json \
        docs/diversity_refactor/r44_progress.md
git commit -m "feat: rank R44 coverage packets deterministically"
```

---

## Task 3: Implement Coverage Packet A with TDD

**Files:**
- Test: `assets/test_r44_packet_a.py`
- Fixture/projection if needed: `assets/fixtures/r44_packet_a_cases.json`
- Modify only the runtime files required by the frozen `r44_packet_a.json`, chosen from:
  - `pipeline/v2_common_action_grammar.py`
  - `pipeline/v2_leaf_grammar.py`
  - `pipeline/v2_structural_evidence.py`
  - `pipeline/v2_scene_provenance.py`
  - `pipeline/v2_clothing_provenance.py`
  - `pipeline/v2_support_provenance.py`
  - `pipeline/v2_template_provenance.py`
  - `pipeline/family_capabilities.py`
- Modify: `docs/diversity_refactor/r44_progress.md`
- Evidence: `assets/results/diversity_refactor/r44/packet-a/`

**Interfaces:**
- Consumes: exactly the structural capability described by `docs/diversity_refactor/r44_packet_a.json`.
- Produces: reusable producer-bound grammar/evidence facts; no packet-specific runtime permission API.

- [ ] **Step 1: Mark R44-03 IN_PROGRESS and verify the packet manifest is still source-bound**

Recompute current source tree and input rows hash. If the source changed since Task 2 outside committed R44 work, regenerate packet selection before continuing.

- [ ] **Step 2: Export only minimal reproducible case projections**

For packet A example seeds, create `assets/fixtures/r44_packet_a_cases.json` containing only data necessary to reproduce the producer structure and expected blocker IDs. Do not use the fixture file as a runtime lookup.

Each fixture row must include:

```json
{
  "seed": 0,
  "coverage_signature_sha256": "...",
  "expected_blocked_domains": ["action", "scene"],
  "expected_target_families": ["..."],
  "expected_source_fields": {
    "action": ["..."],
    "scene": ["..."]
  }
}
```

- [ ] **Step 3: Write real-workflow failing tests**

For every distinct producer structure represented by the packet examples, add a test that currently reproduces the expected blocker and is expected to become proved after implementation.

Required shape:

```python
def test_packet_a_real_case_becomes_source_bound_and_eligible(self):
    snapshot = build_snapshot_for_seed(SEED)
    before = diagnose_snapshot(snapshot, force_families=True)
    self.assertIn(EXPECTED_BLOCKER, collect_blockers(before))

    # After implementation this assertion is the intended target:
    self.assertTrue(
        any(before["families"][family]["runtime_eligible"]
            for family in TARGET_FAMILIES)
    )
```

Initially separate the "current blocker reproduced" assertion from the future eligibility assertion so the first red test clearly identifies the missing capability rather than a fixture error.

- [ ] **Step 4: Add productive recombination tests before code**

Create at least two recombination tests that reuse source-bound parts from different positive examples or part-level fixtures without reusing complete original clauses.

For Action, vary at least one of:

- allowed source slot,
- allowed bounded nominal/object,
- modifier order already supported by the producer,
- supported manner/temporal leaf.

For Scene, vary at least one of:

- source field within the same grammatical category,
- modifier/head combination already present in source catalogs,
- producer-owned attachment with the same ownership topology.

The recombination must be accepted after implementation even though its complete string did not appear in the real seed examples.

- [ ] **Step 5: Add adversarial near-miss tests before code**

At minimum cover:

```text
wrong owner
wrong grammatical subject
wrong source field
stale history/source binding
unsupported extra tail words
place reference introduced into an action rule that claims no place reference
duplicate/ambiguous scene source origin
changed attachment target
changed template topology when topology is part of proof
```

All must remain blocked/fallback.

- [ ] **Step 6: Run Packet A tests and verify they fail for the intended missing capability**

```bash
python -m unittest assets.test_r44_packet_a -v
```

Expected: positive/productive tests FAIL; adversarial tests either already PASS or fail only because the new test helper is incomplete. Fix helpers before runtime code.

- [ ] **Step 7: Implement the smallest reusable capability**

Implementation rules:

- use producer slot/field/constructor identity plus bounded grammar,
- keep exact source binding,
- preserve atom owner and grammatical subject separately,
- preserve place-reference unknowns unless proven absent,
- insert articles/connectors only through explicit tested transform rules,
- do not add branches on seed, fixture ID, or full clause,
- do not change existing accepted rule behavior.

If the packet cannot be implemented without a new producer trace, first add a failing test showing the required source/ownership fact cannot be reconstructed from existing history/context. Then add the smallest **internal-only** trace carrying source structure, not permission booleans.

- [ ] **Step 8: Run Packet A focused tests**

```bash
python -m unittest assets.test_r44_packet_a -v
```

Expected: all positive, productive, and adversarial tests PASS.

- [ ] **Step 9: Run touched-domain regression tests**

At minimum include the existing R43 tests for every changed module. For Action/Scene changes:

```bash
python -m unittest \
  assets.test_r43_common_action_grammar \
  assets.test_r43_action_evidence \
  assets.test_r43_scene_binding \
  assets.test_r43_scene_trace \
  assets.test_r43_family_capabilities \
  assets.test_r43_runtime_integration -v
```

Add Clothing/Template/Support R43 modules when those files are touched.

- [ ] **Step 10: Measure Packet A against the preserved pre-packet baseline**

Create a recoverable source copy/tag of the previous accepted checkpoint using the existing comparison-source policy, then run:

```bash
BASELINE_ROOT=../scg-r44-baseline-11
git worktree remove --force "$BASELINE_ROOT" 2>/dev/null || true
git worktree add --detach "$BASELINE_ROOT" realizer-v2-r44-baseline-11
python tools/audit_realizer_reachability.py \
  --profile intake --force-families all \
  --baseline-root "$BASELINE_ROOT" \
  --output-dir assets/results/diversity_refactor/r44/packet-a/reachability
```

Validate the report with an executable check. Intentional newly-proved v2 prose changes make the audit's whole comparison status `FAIL`, so do not require whole-record equality for new successes:

```bash
python - <<'PY'
import json
from pathlib import Path
root = Path('assets/results/diversity_refactor/r44/packet-a/reachability')
report = json.loads((root / 'reachability.json').read_text(encoding='utf-8'))
packet = json.loads(Path('docs/diversity_refactor/r44_packet_a.json').read_text(encoding='utf-8'))
cmp = report['comparison']
assert cmp['status'] != 'NOT_COMPARABLE'
assert not cmp['regressed_success_seeds']
new = set(cmp['new_success_seeds'])
assert len(new) >= packet['acceptance_min_new_ordinary']
assert not report['actual']['errors']
for row in cmp['rows']:
    seed = row['run_seed']
    mismatches = set(row['mismatches'])
    if seed not in new:
        assert not mismatches, (seed, mismatches)
    else:
        assert 'final_context' not in mismatches, (seed, mismatches)
PY
```

Then compare `packet-selection-intake/rows.jsonl` to Packet A `rows.jsonl` by seed and require `normal.core`, `normal.frame`, and `normal.upstream_context_sha256` to be identical for **all 512 seeds**, including new v2 successes.

- [ ] **Step 11: Reject rather than rationalize a low-yield packet**

If new ordinary successes are below `acceptance_min_new_ordinary`, revert only Packet A runtime/test changes that depended on the rejected capability, retain the diagnostic selection record, mark `R44-03 = REJECTED`, regenerate packet selection excluding the rejected signature, and use the next eligible packet as A. Do not lower the ROI floor.

- [ ] **Step 12: Commit accepted Packet A**

```bash
git diff --check
git add assets/test_r44_packet_a.py assets/fixtures/r44_packet_a_cases.json \
        pipeline docs/diversity_refactor/r44_progress.md
git commit -m "feat: expand Realizer v2 coverage packet A"
PACKET_A_COMMIT=$(git rev-parse HEAD)
if git rev-parse -q --verify refs/tags/realizer-v2-r44-packet-a >/dev/null; then
  test "$(git rev-list -n1 realizer-v2-r44-packet-a)" = "$PACKET_A_COMMIT"
else
  git tag -a realizer-v2-r44-packet-a "$PACKET_A_COMMIT" -m "R44 accepted coverage packet A"
fi
```

Because execution occurs in an isolated R44 worktree, stage the exact packet files and do not carry unrelated user edits into the packet commit.

---

## Task 4: Re-profile and implement Coverage Packet B

**Files:**
- Test: `assets/test_r44_packet_b.py`
- Fixture/projection: `assets/fixtures/r44_packet_b_cases.json`
- Modify: only selected domain files from the allowed runtime list in Task 3
- Modify: `docs/diversity_refactor/r44_packet_b.json`
- Modify: `docs/diversity_refactor/r44_progress.md`
- Evidence: `assets/results/diversity_refactor/r44/packet-b/`

**Interfaces:**
- Consumes: the post-A source and a **freshly regenerated** packet selection. The old B ranking may be stale because A changes blocker intersections.
- Produces: a second independently reviewable reusable capability.

- [ ] **Step 1: Run fresh post-A 512 reachability and regenerate packet ranking**

```bash
python tools/audit_realizer_reachability.py \
  --profile intake --force-families all \
  --output-dir assets/results/diversity_refactor/r44/post-a-selection

python tools/select_r44_coverage_packets.py \
  --rows assets/results/diversity_refactor/r44/post-a-selection/rows.jsonl \
  --output assets/results/diversity_refactor/r44/post-a-packets.json \
  --max-packets 2
```

Replace `r44_packet_b.json` with the newly source-bound first eligible packet. Preserve the original Task-2 B proposal in evidence, not as runtime authority.

- [ ] **Step 2: Stop early if the R44 development target is already met**

If post-A ordinary v2 is `>=64/512` and ordinary family count is `>=5`, do not create unnecessary runtime changes. Mark Packet B `SKIPPED_TARGET_ALREADY_MET` and continue to Task 6.

- [ ] **Step 3: Apply the same hard-exclusion and viability checks to B**

B must have at least 4 distinct seeds and no hard-excluded blocker. If no B exists, mark R44 bounded coverage `BLOCKED` and continue to Task 6/7 without inventing a new packet class.

- [ ] **Step 4: Write B real-workflow failing tests**

Reproduce each distinct B producer structure and assert the pre-implementation blocker.

- [ ] **Step 5: Write at least two productive recombination tests**

The new rule must accept novel combinations of already source-bound structural parts; complete B example strings must not be the only positives.

- [ ] **Step 6: Write adversarial near-miss tests**

Repeat all relevant owner/source/attachment/stale/place/topology attacks for B, even if A tested similar concepts. B may touch different adapters.

- [ ] **Step 7: Run tests to confirm the intended failures**

```bash
python -m unittest assets.test_r44_packet_b -v
```

- [ ] **Step 8: Implement only B's selected reusable capability**

Do not opportunistically fix C or unrelated blocker families in the same commit.

- [ ] **Step 9: Run B tests and all R43/R44 tests for touched modules**

```bash
python -m unittest assets.test_r44_packet_b -v
```

Then run the relevant R43 suites plus `assets.test_r44_packet_a` to ensure A remains preserved.

- [ ] **Step 10: Measure B against the accepted Packet-A source**

```bash
PACKET_A_ROOT=../scg-r44-packet-a
git worktree remove --force "$PACKET_A_ROOT" 2>/dev/null || true
git worktree add --detach "$PACKET_A_ROOT" realizer-v2-r44-packet-a
python tools/audit_realizer_reachability.py \
  --profile intake --force-families all \
  --baseline-root "$PACKET_A_ROOT" \
  --output-dir assets/results/diversity_refactor/r44/packet-b/reachability
```

Validate `packet-b/reachability/reachability.json` exactly as for Packet A:

```python
packet_b = json.load(open("docs/diversity_refactor/r44_packet_b.json", encoding="utf-8"))
cmp = report["comparison"]
assert cmp["status"] != "NOT_COMPARABLE"
assert not cmp["regressed_success_seeds"]
new = set(cmp["new_success_seeds"])
assert len(new) >= packet_b["acceptance_min_new_ordinary"]
assert not report["actual"]["errors"]
for row in cmp["rows"]:
    if row["run_seed"] not in new:
        assert row["mismatches"] == []
    else:
        assert "final_context" not in row["mismatches"]
```

Compare post-A selection rows to Packet B rows and require `normal.core`, `normal.frame`, and `normal.upstream_context_sha256` equality for all 512 seeds.

- [ ] **Step 11: Commit accepted Packet B**

```bash
git diff --check
git add pipeline/v2_common_action_grammar.py pipeline/v2_leaf_grammar.py \
        pipeline/v2_structural_evidence.py pipeline/v2_scene_provenance.py \
        pipeline/v2_clothing_provenance.py pipeline/v2_support_provenance.py \
        pipeline/v2_template_provenance.py pipeline/family_capabilities.py \
        docs/diversity_refactor/r44_progress.md docs/diversity_refactor/r44_packet_b.json \
        assets/test_r44_packet_b.py assets/fixtures/r44_packet_b_cases.json
git commit -m "feat: expand Realizer v2 coverage packet B"
PACKET_B_COMMIT=$(git rev-parse HEAD)
if git rev-parse -q --verify refs/tags/realizer-v2-r44-packet-b >/dev/null; then
  test "$(git rev-list -n1 realizer-v2-r44-packet-b)" = "$PACKET_B_COMMIT"
else
  git tag -a realizer-v2-r44-packet-b "$PACKET_B_COMMIT" -m "R44 accepted coverage packet B"
fi
```

---

## Task 5: Conditionally implement the final bounded Coverage Packet C

**Files:**
- Conditionally create: `assets/test_r44_packet_c.py`
- Conditionally create: `assets/fixtures/r44_packet_c_cases.json`
- Conditionally create/modify: `docs/diversity_refactor/r44_packet_c.json`
- Modify only selected runtime domain files
- Modify: `docs/diversity_refactor/r44_progress.md`
- Evidence: `assets/results/diversity_refactor/r44/packet-c/`

**Interfaces:**
- Consumes: fresh post-B reachability.
- Produces: the third and final allowed R44 runtime coverage packet.

- [ ] **Step 1: Re-run 512 reachability after B**

```bash
python tools/audit_realizer_reachability.py \
  --profile intake --force-families all \
  --output-dir assets/results/diversity_refactor/r44/post-b-selection
```

- [ ] **Step 2: If 64/5 is already met, do not implement C**

Record `R44-05 = SKIPPED_TARGET_ALREADY_MET` and continue to Task 6.

- [ ] **Step 3: Generate exactly one final packet candidate**

```bash
python tools/select_r44_coverage_packets.py \
  --rows assets/results/diversity_refactor/r44/post-b-selection/rows.jsonl \
  --output assets/results/diversity_refactor/r44/post-b-packet-c.json \
  --max-packets 1
```

Freeze it as `r44_packet_c.json` with source and rows hashes.

- [ ] **Step 4: Apply bounded viability checks**

If no packet with at least 4 seeds and no hard blocker exists, do not expand scope. Mark `R44-05 = BLOCKED_NO_BOUNDED_PACKET` and continue to Task 6/7.

- [ ] **Step 5: Write C real-workflow failing tests**

Cover every distinct producer structure in the C examples.

- [ ] **Step 6: Write at least two productive recombination tests**

The accepted capability must generalize beyond the complete real clauses in C.

- [ ] **Step 7: Write C adversarial tests**

Include all applicable owner/source/attachment/place/stale/topology near misses.

- [ ] **Step 8: Run the C tests red**

```bash
python -m unittest assets.test_r44_packet_c -v
```

- [ ] **Step 9: Implement only the selected C capability**

No fourth packet is permitted in R44.

- [ ] **Step 10: Run C + A + B focused tests and relevant R43 suites**

```bash
python -m unittest \
  assets.test_r44_packet_a \
  assets.test_r44_packet_b \
  assets.test_r44_packet_c -v
```

- [ ] **Step 11: Measure C against the accepted Packet-B source**

```bash
PACKET_B_ROOT=../scg-r44-packet-b
git worktree remove --force "$PACKET_B_ROOT" 2>/dev/null || true
git worktree add --detach "$PACKET_B_ROOT" realizer-v2-r44-packet-b
python tools/audit_realizer_reachability.py \
  --profile intake --force-families all \
  --baseline-root "$PACKET_B_ROOT" \
  --output-dir assets/results/diversity_refactor/r44/packet-c/reachability
```

Require `comparison.status != NOT_COMPARABLE`, no regressed successes, no audit errors, and at least C's `acceptance_min_new_ordinary` new ordinary cases. For every seed not newly promoted to v2, require an empty comparison mismatch list; for newly promoted seeds, `final_context` must still match. Compare post-B and post-C rows and require `normal.core`, `normal.frame`, and `normal.upstream_context_sha256` equality for all 512 seeds.

- [ ] **Step 12: Commit accepted C**

```bash
git diff --check
git add pipeline/v2_common_action_grammar.py pipeline/v2_leaf_grammar.py \
        pipeline/v2_structural_evidence.py pipeline/v2_scene_provenance.py \
        pipeline/v2_clothing_provenance.py pipeline/v2_support_provenance.py \
        pipeline/v2_template_provenance.py pipeline/family_capabilities.py \
        docs/diversity_refactor/r44_progress.md docs/diversity_refactor/r44_packet_c.json \
        assets/test_r44_packet_c.py assets/fixtures/r44_packet_c_cases.json
git commit -m "feat: expand Realizer v2 coverage packet C"
```

---

## Task 6: Run the R44 development gate and classify the result

**Files:**
- Create: `assets/test_r44_final_preservation.py`
- Modify: `docs/diversity_refactor/r44_progress.md`
- Modify: `docs/diversity_refactor/tasks.md`
- Modify: `CURRENT_STATUS.md`
- Evidence: `assets/results/diversity_refactor/r44/final-development/`

**Interfaces:**
- Consumes: the final accepted R44 source after zero to three runtime packets.
- Produces: an explicit `PASS_DEVELOPMENT_GUIDE` or `BLOCKED_DEVELOPMENT_GUIDE` result. It does not produce formal adoption.

- [ ] **Step 1: Run the portable focused verifier**

```bash
python tools/verify_realizer_v2_candidate.py \
  --stage focused \
  --output-dir assets/results/diversity_refactor/r44/final-development/focused
```

Require zero failed tests/subtests and zero unexplained skip/xfail/collection/setup/teardown errors.

- [ ] **Step 2: Run the regression verifier**

```bash
python tools/verify_realizer_v2_candidate.py \
  --stage regression \
  --output-dir assets/results/diversity_refactor/r44/final-development/regression
```

Require PASS.

- [ ] **Step 3: Run validators and full flow**

```bash
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python tools/verify_full_flow.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20]); raise SystemExit(1 if issues else 0)"
python assets/calc_variations.py --json
```

Verify V150 counts/protected scope remain unchanged from the locked baseline.

- [ ] **Step 4: Run final ordinary/forced 512 reachability against the pre-R44 source**

Use a restored/pinned pre-R44 11-case source as baseline:

```bash
BASELINE_ROOT=../scg-r44-baseline-11
git worktree remove --force "$BASELINE_ROOT" 2>/dev/null || true
git worktree add --detach "$BASELINE_ROOT" realizer-v2-r44-baseline-11
python tools/audit_realizer_reachability.py \
  --profile intake --force-families all \
  --baseline-root "$BASELINE_ROOT" \
  --output-dir assets/results/diversity_refactor/r44/final-development/reachability
```

- [ ] **Step 5: Create and run the final preservation test**

Create `assets/test_r44_final_preservation.py`. It loads:

```text
assets/results/diversity_refactor/r44/baseline-01/reachability/rows.jsonl
assets/results/diversity_refactor/r44/final-development/reachability/rows.jsonl
assets/results/diversity_refactor/r44/final-development/reachability/reachability.json
```

The test must calculate seed-indexed baseline/final maps and assert:

```python
self.assertEqual(report["status"], "ok")
self.assertFalse(report["actual"]["errors"])
self.assertNotEqual(report["comparison"]["status"], "NOT_COMPARABLE")
self.assertEqual(report["comparison"]["regressed_success_seeds"], [])

baseline_v2 = {s for s, r in baseline.items() if r["normal"]["realizer_version"] == "v2"}
final_v2 = {s for s, r in final.items() if r["normal"]["realizer_version"] == "v2"}
self.assertTrue(baseline_v2 <= final_v2)

for seed in sorted(final):
    self.assertEqual(final[seed]["normal"]["core"], baseline[seed]["normal"]["core"])
    self.assertEqual(final[seed]["normal"]["frame"], baseline[seed]["normal"]["frame"])
    self.assertEqual(final[seed]["normal"]["upstream_context_sha256"], baseline[seed]["normal"]["upstream_context_sha256"])

for seed in sorted(set(final) - final_v2):
    self.assertEqual(final[seed]["normal"]["raw_prompt"], baseline[seed]["normal"]["raw_prompt"])
    self.assertEqual(final[seed]["normal"]["cleaned_prompt"], baseline[seed]["normal"]["cleaned_prompt"])

forced = report["families"]
self.assertEqual(6, sum(v["forced_render_v2"]["true"] > 0 for v in forced.values()))
```

If the existing audit representation uses a different exact forced-proof field, use that existing field and add a regression assertion documenting the mapping; do not infer proof from constructor count alone.

Run:

```bash
python -m unittest assets.test_r44_final_preservation -v
```

Do not treat changed syntax-family labels on a v1 fallback as v2 success.

- [ ] **Step 6: Verify the development guide**

Classify with exact integer counts:

```python
meets_coverage = report["actual"]["v2_applied_count"] >= 64
meets_families = report["actual"]["executed_v2_family_count"] >= 5
```

If both are true:

```text
R44 development verdict = PASS_DEVELOPMENT_GUIDE
formal adoption = BLOCKED / NOT_RUN
```

Otherwise:

```text
R44 development verdict = BLOCKED_DEVELOPMENT_GUIDE
formal adoption = BLOCKED / NOT_RUN
```

Do not label an unmet development guide `REJECTED` unless an actual locked formal threshold was run and failed.

- [ ] **Step 7: Check Python 3.10 syntax for changed Python files**

Use the repository's existing Python 3.10 AST/static-check method. At minimum:

```bash
python - <<'PY'
import ast, pathlib
for p in pathlib.Path('.').rglob('*.py'):
    if any(part in {'.git', 'assets/results'} for part in p.parts):
        continue
    ast.parse(p.read_text(encoding='utf-8'), filename=str(p), feature_version=(3, 10))
print('python310 AST PASS')
PY
```

- [ ] **Step 8: Run diff hygiene and status review**

```bash
git diff --check
git status --short
git diff --stat realizer-v2-r44-baseline-11..HEAD
```

Confirm no protected variation files changed unexpectedly.

- [ ] **Step 9: Update status docs with measured facts only**

Record:

- final ordinary v2 count,
- final ordinary family count,
- forced family count,
- new-success seed count,
- preserved pre-R44 success count,
- remaining fallback count,
- focused/regression counts,
- validators/full-flow status,
- source tree hash,
- formal gates explicitly NOT_RUN.

- [ ] **Step 10: Commit the development gate receipts/docs**

```bash
git add docs/diversity_refactor/r44_progress.md \
        docs/diversity_refactor/tasks.md CURRENT_STATUS.md
git commit -m "test: record R44 development coverage gate"
```

---

## Task 7: Freeze a recoverable R44 checkpoint and write the handoff

**Files:**
- Create: `docs/diversity_refactor/r44_handoff.md`
- Create: `docs/diversity_refactor/r44_handoff_summary.json`
- Modify: `docs/diversity_refactor/r44_progress.md`
- Modify: comparison-source registry/docs using the repository's existing recoverable-tag policy

**Interfaces:**
- Consumes: final R44 development verdict from Task 6.
- Produces: a recoverable checkpoint and unambiguous next-step boundary for a future formal-evaluation task or R45 coverage wave.

- [ ] **Step 1: Capture final source identity**

Record:

```bash
git rev-parse HEAD
git rev-parse HEAD^{tree}
```

Capture the repository's source-tree hash using the same manifest tool as the R43/R44 audits.

- [ ] **Step 2: Create a new immutable comparison tag/checkpoint**

Use a new annotated tag name; never move an existing tag. Suggested names:

```text
realizer-v2-r44-dev-64x5-20260913
```

when the development guide passes, or:

```text
realizer-v2-r44-blocked-20260913
```

when it does not.

If execution occurs on another date, use that execution date rather than pretending the plan date is current.

- [ ] **Step 3: Verify restored checkpoint reproducibility**

Restore/archive the tagged source according to `docs/diversity_refactor/comparison_sources/README.md`, then rerun the lightweight source guard and a development replay sufficient to prove the stored source reproduces the final 512 verdict bytes.

- [ ] **Step 4: Write `r44_handoff.md`**

It must contain:

```text
R44 source identity
pre-R44 baseline identity
accepted/rejected/skipped packet list
ordinary v2 count / 512
ordinary family count
all-six forced proof status
preservation status
focused/regression/validator/full-flow status
V150 protected-file status
formal evaluation status = NOT_RUN
N2.8 status = BLOCKED
D3 status = DEFERRED
```

If 64/5 passed, the next task is **formal source/config freeze and formal N2.7 evaluation**.

If 64/5 did not pass after three accepted bounded packets, the next task is **R45 profiler-driven coverage using the new R44 signatures**, not a fourth hidden R44 packet.

- [ ] **Step 5: Write machine-readable `r44_handoff_summary.json`**

Required top-level keys:

```json
{
  "schema_version": "r44-handoff/v1",
  "development_verdict": "PASS_DEVELOPMENT_GUIDE",
  "adoption_status": "BLOCKED",
  "formal_status": "NOT_RUN",
  "source": {},
  "baseline": {},
  "coverage": {},
  "packets": [],
  "tests": {},
  "preservation": {},
  "next_task": ""
}
```

Use `BLOCKED_DEVELOPMENT_GUIDE` when appropriate.

- [ ] **Step 6: Self-review the handoff for overclaiming**

Search for these forbidden claims unless supported by formal evidence:

```text
adopted
production ready
formal pass
N2.8 active
scheduler active
main merged
```

The handoff may say architecture/development PASS only when Task 6 actually passed its relevant checks.

- [ ] **Step 7: Final verification before claiming completion**

Invoke `superpowers:verification-before-completion` and rerun the required verification commands it calls for. Do not rely on earlier console output alone.

- [ ] **Step 8: Commit the handoff**

```bash
git diff --check
git add docs/diversity_refactor/r44_handoff.md \
        docs/diversity_refactor/r44_handoff_summary.json \
        docs/diversity_refactor/r44_progress.md \
        docs/diversity_refactor/comparison_sources
git commit -m "docs: hand off R44 coverage engineering checkpoint"
```

Do not include generated heavy result directories in Git unless the existing repository policy explicitly tracks those exact receipt types.

---

# Cross-Task Review Rules

## Reviewer gate after every runtime packet

A reviewer must reject the packet if any of these are true:

1. a new runtime condition names a seed or fixture ID,
2. a new permission rule is keyed only by a complete phrase,
3. catalog membership is treated as grammar proof,
4. `Truth.UNKNOWN` is coerced to safe false/true,
5. owner and grammatical subject are conflated,
6. a location/place reference is assumed absent without evidence,
7. source/history mismatch is ignored,
8. an existing success changes unexpectedly,
9. a remaining fallback changes text without becoming a proved v2 case,
10. the packet modifies protected variation data to improve coverage,
11. the packet changes family-selection randomness/scheduling as a way to hit the 5-family target,
12. tests demonstrate only the exact real string and no productive recombination.

## Required evidence for every accepted packet

- pre-edit source identity,
- post-edit source identity,
- packet manifest hash,
- focused test result,
- touched-domain regression result,
- 512 reachability report,
- comparison against immediate previous accepted checkpoint,
- new-success seeds,
- preserved-success seeds,
- regressed-success seeds = empty,
- remaining-fallback exact-preservation result,
- independent source restore/replay before final R44 handoff.

---

# R44 Stop Conditions

Stop implementation immediately and record `BLOCKED` when:

- current runtime source is not the verified starting source and the divergence is not independently baselined,
- packet selector finds insufficient bounded clusters to make 64/512 reachable within three packets,
- a selected packet requires a general NLP dependency,
- a selected packet requires seed/full-clause allowlisting,
- a required source/owner fact cannot be reconstructed or transported without changing public schema,
- preservation comparison regresses an existing v2 success,
- remaining fallback output changes without a new valid proof,
- V150 protected counts/scope change unexpectedly,
- determinism/replay fails,
- a packet would require relaxing locked thresholds or policy.

Do not continue to “make the numbers work.”

---

# What R44 Completion Means

## If `PASS_DEVELOPMENT_GUIDE`

R44 has established that the source-bound Realizer architecture is broad enough to justify a **separate formal N2.7 evaluation task**. It does **not** mean Realizer v2 is adopted or active-default.

Next task should perform an explicit formal candidate freeze and then the unchanged source-bound 8192/2048/fixed80/review/confirmation/frontend/release obligations already locked in the repository.

## If `BLOCKED_DEVELOPMENT_GUIDE`

R44 has still produced value: a reusable structural coverage profiler, deterministic packet ranking, measured accepted/rejected packets, and a new checkpoint. The next coverage wave should start from the profiler output rather than return to seed-by-seed manual diagnosis.

---

# Plan Self-Review Checklist

Before execution begins, verify:

- [ ] every new runtime capability is selected from measured ordinary blockers,
- [ ] diagnostic signatures are not imported by runtime authorization,
- [ ] packet manifests contain structure, not whole prompt permission,
- [ ] no new syntax family or scheduler is needed to claim R44 success,
- [ ] no task requires changing public node I/O,
- [ ] formal evaluation remains a separate explicit task,
- [ ] at most three runtime packets are allowed,
- [ ] each packet has red/green TDD, productive recombination, adversarial tests, and immediate 512 comparison,
- [ ] final verdict distinguishes development PASS/BLOCKED from formal adoption.

