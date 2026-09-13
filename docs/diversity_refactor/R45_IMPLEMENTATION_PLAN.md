# R45 Capability Projection and Provenance Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the verified R44 11/512 runtime behavior while replacing full-state packet grouping with domain-local capability measurement, separating Scene source provenance from grammar proof, and producing a reproducible R46 candidate ranking.

**Architecture:** Keep `realizer-coverage-signature/v1` unchanged as the forensic fingerprint. Add diagnostic-only blocker normalization, atomic capability projection, and a flat capability/blocker/family measurement graph. Refactor Scene evidence so exact producer provenance can survive unsupported grammar as `Truth.UNKNOWN`; existing `FamilyProof` remains the sole runtime authorization authority and must not gain eligibility from R45 alone.

**Tech Stack:** Python 3.10-compatible stdlib only, existing repository dataclasses/helpers, `unittest`/`pytest`, canonical JSON/SHA-256, current workflow/replay/verifier tooling. No new dependency.

**Spec:** `docs/diversity_refactor/R45_DESIGN.md`

## Global Constraints

- Implementation starts from `refactor/realizer-v2-r44` HEAD `8c0dce2a6a2f485d683c306736b76a114bae3165` unless a newer commit contains documentation-only changes that are explicitly reconciled before R45-00.
- Preserve immutable R44 runtime/diagnostic source checkpoint `98a8ef33ab9a851240cf678864b0ed65879228e4` and tag `realizer-v2-r44-blocked-20260913`; never force-update/delete published comparison tags.
- Create implementation branch `refactor/realizer-v2-r45` in an isolated worktree at execution time.
- Work on exactly one R45 task ID at a time. Mark `docs/diversity_refactor/r45_progress.md` `IN_PROGRESS` before source edits and record commands/results/commit before advancing.
- Public `Context*` node I/O and `context_json` contract/version must not change.
- V150 protected variation files must not change for feature expansion: `vocab/data/variation_scope.json`, `assets/compatibility_review.csv`, `vocab/source/action_pools/*.json`, `vocab/source/action_pools/_shared_families.json`, `vocab/data/action_pools.json`.
- No LLM, embedding, parser/NLP package, or other new runtime/audit dependency.
- No camera/quality/style/artist output domain.
- No new syntax family, Scheduler activation, N2.8 activation, or threshold relaxation.
- R45 must not deliberately increase ordinary v2 coverage; ordinary output must remain byte-compatible with R44 unless a pre-existing source bug is separately rejected and escalated.
- Diagnostic capability modules under `tools/` must never be imported by runtime authorization modules under `pipeline/`.
- Full prompt/action/scene text, exact seed, exact selected catalog key, and selected vocabulary text hashes must not be part of a capability identity hash.
- Diagnostic data never grants runtime permission. `FamilyProof` reconstructed from current inputs remains the authority.
- `UNKNOWN` must never be promoted to `TRUE` to improve reachability.
- Do not add seed allowlists, full-clause allowlists, exact phrase allowlists, or hand-selected rescue lists.
- Formal candidate `reference8192`, `gate2048`, paired formal comparison, `fixed80`, blind review, fresh confirmations, frontend/browser, and `release8192` remain `NOT_RUN` throughout R45.
- If a task fails its acceptance criteria, stop. Record `BLOCKED` or `REJECTED`; do not compensate by weakening gates.

---

## File Map and Ownership

### New files

- `docs/diversity_refactor/R45_DESIGN.md` — governing R45 design copied from the approved plan input.
- `docs/diversity_refactor/R45_IMPLEMENTATION_PLAN.md` — this implementation contract copied verbatim.
- `docs/diversity_refactor/r45_progress.md` — detailed one-task-at-a-time execution ledger.
- `docs/diversity_refactor/r45_handoff.md` — final measured verdict and R46 boundary.
- `tools/realizer_blocker_taxonomy.py` — diagnostic-only canonical blocker IDs and blocker classification.
- `tools/realizer_capability_projection.py` — pure, text-free typed capability identities plus snapshot projection.
- `tools/audit_realizer_capabilities.py` — canonical CLI that consumes reachability rows and produces graph/summary/R46 candidates.
- `assets/test_r45_blocker_taxonomy.py` — delimiter/hard-exclusion/selector contract tests.
- `assets/test_r45_capability_projection.py` — capability identity and privacy/determinism tests.
- `assets/test_r45_scene_provenance_separation.py` — Scene source-vs-grammar separation tests.
- `assets/test_r45_capability_audit.py` — graph accounting/ranking/CLI tests.

### Existing files expected to change

- `tools/select_r44_coverage_packets.py` — consume canonical blocker taxonomy without changing R44 receipt files.
- `tools/realizer_reachability_diagnostics.py` — attach additive typed capability projection after R44 binding validation.
- `assets/test_r43_common_diagnostics.py` — preserve all pre-R45 diagnostic fields while testing the additive projection.
- `pipeline/v2_scene_provenance.py` — split exact source binding from grammar classification.
- `docs/diversity_refactor/tasks.md` — append R45 task ledger/link.
- `docs/diversity_refactor/progress.md` — concise R45 milestone status.
- `CURRENT_STATUS.md` — final status only after R45 verdict.

### Files that must not change in R45 runtime logic

- `pipeline/family_capabilities.py`
- `pipeline/prompt_realizer.py`
- `pipeline/v2_candidate_bridge.py`
- `vocab/data/natural_language_realizer_v2.json`

If implementation appears to require changing one of these, stop and record why. That is R46/runtime scope, not R45 measurement scope.

---

# Task R45-00: Isolate R45 and Freeze the R44 Checkpoint

**Purpose:** Establish a recoverable R45 baseline before any diagnostic or provenance change.

**Files:**
- Create: `docs/diversity_refactor/R45_DESIGN.md`
- Create: `docs/diversity_refactor/R45_IMPLEMENTATION_PLAN.md`
- Create: `docs/diversity_refactor/r45_progress.md`
- Modify: `docs/diversity_refactor/tasks.md`
- Modify: `docs/diversity_refactor/progress.md`
- Read/verify: `docs/diversity_refactor/r44_handoff.md`
- Read/verify: `docs/diversity_refactor/comparison_sources/r44/registry.json`

**Interfaces:**
- Consumes: R44 ordinary baseline `11/512`, 3 ordinary families, 6 real-input forced families, 501 exact fallbacks.
- Produces: pinned R45 starting commit/source hashes and pre-edit verification receipts used by every later task.

- [ ] **Step 1: Create an isolated worktree/branch from the R44 handoff HEAD**

Run:

```bash
git fetch origin --tags
git rev-parse origin/refactor/realizer-v2-r44
git worktree add ../ComfyUI-Scripted-Context-Generator-r45 -b refactor/realizer-v2-r45 origin/refactor/realizer-v2-r44
cd ../ComfyUI-Scripted-Context-Generator-r45
git status --short --branch
git rev-parse HEAD
```

Expected starting commit:

```text
8c0dce2a6a2f485d683c306736b76a114bae3165
```

If the remote branch has advanced, inspect the intervening commits. Proceed only if they are documentation/evidence-only or explicitly reconcile the source delta in `r45_progress.md` before any edit.

- [ ] **Step 2: Verify the R44 immutable source tags and registry**

Run:

```bash
git rev-parse realizer-v2-r44-baseline-11^{}
git rev-parse realizer-v2-r44-blocked-20260913^{}
python - <<'PY'
import json
from pathlib import Path
p = Path('docs/diversity_refactor/comparison_sources/r44/registry.json')
data = json.loads(p.read_text(encoding='utf-8'))
assert data['publication_status'] == 'SOURCE_TAGS_VERIFIED'
roles = {row['role']: row for row in data['sources']}
assert roles['pre_r44_baseline']['ordinary_v2_count'] == 11
assert roles['pre_r44_baseline']['ordinary_family_count'] == 3
assert roles['r44_diagnostics']['ordinary_v2_count'] == 11
assert roles['r44_diagnostics']['ordinary_family_count'] == 3
print('R44 registry PASS')
PY
```

Expected: both peeled tag commits match the registry and Python prints `R44 registry PASS`.

- [ ] **Step 3: Copy the approved R45 design and plan verbatim into the repository**

Place the supplied files at:

```text
docs/diversity_refactor/R45_DESIGN.md
docs/diversity_refactor/R45_IMPLEMENTATION_PLAN.md
```

Record their SHA-256 values:

```bash
python - <<'PY'
from hashlib import sha256
from pathlib import Path
for name in ('R45_DESIGN.md', 'R45_IMPLEMENTATION_PLAN.md'):
    p = Path('docs/diversity_refactor') / name
    print(name, sha256(p.read_bytes()).hexdigest())
PY
```

- [ ] **Step 4: Create the R45 progress ledger before source work**

Create `docs/diversity_refactor/r45_progress.md` with this exact initial structure:

```markdown
# R45 Progress

## Baseline
- branch: refactor/realizer-v2-r45
- parent_branch: refactor/realizer-v2-r44
- start_head: 8c0dce2a6a2f485d683c306736b76a114bae3165
- ordinary_v2: pending preflight
- ordinary_families: pending preflight
- forced_families: pending preflight

## Task ledger
| Task | State | Commit | Evidence | Notes |
|---|---|---|---|---|
| R45-00 | IN_PROGRESS | | | baseline lock |
| R45-01 | PENDING | | | blocker taxonomy |
| R45-02 | PENDING | | | capability projection |
| R45-03 | PENDING | | | Scene provenance separation |
| R45-04 | PENDING | | | capability audit graph |
| R45-05 | PENDING | | | R46 readiness verdict |
| R45-06 | PENDING | | | handoff/checkpoint |

## Formal scope
Formal N2.7/N2.8/D3 evaluation: NOT_RUN / BLOCKED / DEFERRED.
```

If R45-00 reconciles a newer documentation-only parent, replace this recorded start SHA with that exact reconciled SHA before the first commit and explain the difference in the Baseline section.

- [ ] **Step 5: Run the existing R44 development baseline verification**

Use new output directories:

```bash
python tools/verify_realizer_v2_candidate.py --stage focused --output-dir assets/results/diversity_refactor/r45/baseline/focused
python tools/verify_realizer_v2_candidate.py --stage regression --output-dir assets/results/diversity_refactor/r45/baseline/regression
python tools/audit_realizer_reachability.py --profile intake --force-families all --output-dir assets/results/diversity_refactor/r45/baseline/reachability
python tools/realizer_candidate_replay.py --source-root . --pairs assets/results/diversity_refactor/r45/baseline/reachability/normal-pairs.jsonl --output-dir assets/results/diversity_refactor/r45/baseline/replay-root --import-mode root
```

Expected baseline facts:

```text
ordinary v2 = 11 / 512
ordinary executed families = 3
fallback = 501
real-input common forced families = 6
focused = PASS
regression = PASS
replay = PASS
```

Do not continue if ordinary counts differ without a documented source reconciliation.

- [ ] **Step 6: Record protected-input hashes before R45 changes**

Run:

```bash
python - <<'PY'
from hashlib import sha256
from pathlib import Path
paths = [Path('vocab/data/variation_scope.json'), Path('assets/compatibility_review.csv'),
         Path('vocab/data/action_pools.json'), Path('vocab/source/action_pools/_shared_families.json')]
paths.extend(sorted(Path('vocab/source/action_pools').glob('*.json')))
rows = []
for p in sorted(set(paths)):
    rows.append((p.as_posix(), sha256(p.read_bytes()).hexdigest()))
for name, digest in rows:
    print(digest, name)
print('protected_count', len(rows))
PY
```

Save the output hash/list under the R45 results directory and record the compact SHA-256 in `r45_progress.md`.

- [ ] **Step 7: Update task documents to point to R45 without changing active runtime claims**

Add an R45 section at the top of `docs/diversity_refactor/tasks.md` linking the design/plan/progress and stating:

```text
R45 is diagnostic/provenance work. Ordinary Realizer v2 remains 11/512 until a later R46 runtime capability task is explicitly approved.
```

Append a concise R45 start entry to `docs/diversity_refactor/progress.md`.

- [ ] **Step 8: Mark R45-00 PASS and commit**

Before commit, run:

```bash
git diff --check
git status --short
```

Update `r45_progress.md` with the exact verification commands and results, then:

```bash
git add docs/diversity_refactor/R45_DESIGN.md \
        docs/diversity_refactor/R45_IMPLEMENTATION_PLAN.md \
        docs/diversity_refactor/r45_progress.md \
        docs/diversity_refactor/tasks.md \
        docs/diversity_refactor/progress.md
git commit -m "docs: lock R45 capability baseline"
```

**Acceptance R45-00:**

- Baseline is exactly 11/512, 3 ordinary families, 501 fallbacks, 6 real-input forced families.
- Focused/regression/replay pass.
- Protected input hashes are recorded.
- No runtime/data source changed.
- Published R44 tags remain untouched.

---

# Task R45-01: Canonicalize Diagnostic Blocker Taxonomy

**Purpose:** Fix the dot/colon diagnostic contract mismatch without changing `FamilyProof` production or runtime authorization.

**Files:**
- Create: `tools/realizer_blocker_taxonomy.py`
- Create: `assets/test_r45_blocker_taxonomy.py`
- Modify: `tools/select_r44_coverage_packets.py`
- Modify: `docs/diversity_refactor/r45_progress.md`

**Interfaces:**
- Produces: `canonical_blocker_id(identifier: str) -> str`, `is_hard_excluded(identifier: str) -> bool`, `is_repairable_blocker(identifier: str) -> bool`, `blocker_domain(identifier: str) -> str | None`.
- Consumers: R44 packet selector for compatibility; R45 capability audit for canonical blocker graph.

- [ ] **Step 1: Mark R45-01 IN_PROGRESS**

Update only the R45-01 task row in `r45_progress.md` before code edits.

- [ ] **Step 2: Write failing taxonomy tests for colon and legacy dot forms**

Create `assets/test_r45_blocker_taxonomy.py` containing at minimum:

```python
import unittest

from tools.realizer_blocker_taxonomy import (
    blocker_domain, canonical_blocker_id, is_hard_excluded, is_repairable_blocker,
)


class TestBlockerTaxonomy(unittest.TestCase):
    def test_canonicalizes_legacy_family_delimiters(self):
        pairs = {
            'family.required_fact_not_true.scene_lead_safe':
                'family.required_fact_not_true:scene_lead_safe',
            'family.forbidden_fact_not_false.scene_action_overlap':
                'family.forbidden_fact_not_false:scene_action_overlap',
            'family.missing_slot.scene': 'family.missing_slot:scene',
        }
        for source, expected in pairs.items():
            with self.subTest(source=source):
                self.assertEqual(canonical_blocker_id(source), expected)

    def test_native_colon_family_ids_are_repairable(self):
        ids = (
            'family.required_fact_not_true:scene_lead_safe',
            'family.forbidden_fact_not_false:scene_action_overlap',
            'family.missing_slot:scene',
        )
        self.assertTrue(all(is_repairable_blocker(value) for value in ids))

    def test_hard_binding_and_policy_failures_remain_excluded(self):
        ids = (
            'policy.conflict', 'binding.current_input_mismatch',
            'binding.replay_mismatch', 'binding.history_stale',
            'transport.runtime_inputs_missing', 'render.proof_constructor_mismatch',
        )
        self.assertTrue(all(is_hard_excluded(value) for value in ids))

    def test_domain_mapping_is_explicit(self):
        self.assertEqual(blocker_domain('action.leaf_grammar_unknown'), 'action')
        self.assertEqual(blocker_domain('scene.source_or_grammar_unknown'), 'scene')
        self.assertEqual(blocker_domain('family.required_fact_not_true:same_subject_attachment_safe'), 'action')
        self.assertEqual(blocker_domain('family.required_fact_not_true:scene_lead_safe'), 'scene')
        self.assertEqual(blocker_domain('family.forbidden_fact_not_false:scene_action_overlap'), 'action')
        self.assertEqual(blocker_domain('family.required_fact_not_true:scene_action_nonduplicative'), 'action')
        self.assertEqual(blocker_domain('family.scene_overlap_unknown'), 'action')
        self.assertEqual(blocker_domain('family.action_lead_subject_unknown'), 'action')
        self.assertEqual(blocker_domain('family.frame_unproved'), 'action')
        self.assertEqual(blocker_domain('family.independent_subject'), 'action')
        self.assertEqual(blocker_domain('policy.conflict'), None)
```

- [ ] **Step 3: Add a selector regression showing colon-form family blockers are not silently discarded**

Append to `assets/test_r45_blocker_taxonomy.py`:

```python
from assets.test_r44_packet_selection import rows_for
from tools.select_r44_coverage_packets import select_packets


class TestR44SelectorCanonicalTaxonomy(unittest.TestCase):
    def test_colon_family_blocker_can_participate_in_repairable_packet(self):
        rows = rows_for(
            range(4),
            blockers=(
                'scene.placement_constructor_unknown',
                'family.required_fact_not_true:scene_lead_safe',
            ),
            domains=('scene',),
        )
        packets = select_packets(rows)
        self.assertEqual(len(packets), 1)
        self.assertIn('family.required_fact_not_true:scene_lead_safe',
                      packets[0]['repairable_blocker_ids'])
```

- [ ] **Step 4: Run the new tests and verify red state**

Run:

```bash
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_blocker_taxonomy.py
```

Expected: import/function failures because `tools/realizer_blocker_taxonomy.py` does not exist yet, or selector colon handling fails.

- [ ] **Step 5: Implement `tools/realizer_blocker_taxonomy.py` minimally**

Implement this public diagnostic contract:

```python
from __future__ import annotations

FAMILY_PREFIX_ALIASES = {
    'family.required_fact_not_true.': 'family.required_fact_not_true:',
    'family.forbidden_fact_not_false.': 'family.forbidden_fact_not_false:',
    'family.missing_slot.': 'family.missing_slot:',
}

HARD_EXACT = frozenset({
    'policy.conflict', 'binding.frame_current_text_mismatch',
    'binding.replay_mismatch', 'binding.current_input_mismatch',
    'render.proof_constructor_mismatch', 'transport.runtime_inputs_missing',
})

FACT_DOMAIN = {
    'frame_predicate_safe': 'action',
    'independent_action_subject': 'action',
    'same_subject_attachment_safe': 'action',
    # These facts are currently derived from ActionGrammarFacts.no_place_reference
    # in family_capabilities._prepare(), so the repair responsibility is Action.
    'scene_action_overlap': 'action',
    'scene_action_nonduplicative': 'action',
    'scene_lead_safe': 'scene',
    'scene_adjunct_safe': 'scene',
    'standalone_scene_safe': 'scene',
}

SLOT_DOMAIN = {'subject': 'subject', 'adjunct': 'action', 'predicate': 'action', 'scene': 'scene'}

FAMILY_EXACT_DOMAIN = {
    # All four are emitted from Action-derived facts in family_capabilities._proof().
    'family.scene_overlap_unknown': 'action',
    'family.action_lead_subject_unknown': 'action',
    'family.frame_unproved': 'action',
    'family.independent_subject': 'action',
}


def canonical_blocker_id(identifier: str) -> str:
    if not isinstance(identifier, str) or not identifier:
        raise ValueError('blocker identifier must be a non-empty string')
    for old, new in FAMILY_PREFIX_ALIASES.items():
        if identifier.startswith(old):
            return new + identifier[len(old):]
    return identifier


def is_hard_excluded(identifier: str) -> bool:
    identifier = canonical_blocker_id(identifier)
    return (
        identifier in HARD_EXACT
        or identifier.startswith(('policy.', 'binding.', 'transport.'))
        or 'stale' in identifier
        or ('mismatch' in identifier and any(part in identifier for part in
                                             ('binding', 'replay', 'current_input', 'constructor')))
    )


def blocker_domain(identifier: str) -> str | None:
    identifier = canonical_blocker_id(identifier)
    if identifier in FAMILY_EXACT_DOMAIN:
        return FAMILY_EXACT_DOMAIN[identifier]
    for domain in ('action', 'scene', 'clothing', 'subject', 'template', 'garnish', 'mood'):
        if identifier.startswith(domain + '.'):
            return domain
    prefix = 'family.required_fact_not_true:'
    if identifier.startswith(prefix):
        return FACT_DOMAIN.get(identifier[len(prefix):])
    prefix = 'family.forbidden_fact_not_false:'
    if identifier.startswith(prefix):
        return FACT_DOMAIN.get(identifier[len(prefix):])
    prefix = 'family.missing_slot:'
    if identifier.startswith(prefix):
        return SLOT_DOMAIN.get(identifier[len(prefix):])
    return None


def is_repairable_blocker(identifier: str) -> bool:
    identifier = canonical_blocker_id(identifier)
    return not is_hard_excluded(identifier) and blocker_domain(identifier) is not None
```

Do not import runtime modules from this helper.

- [ ] **Step 6: Refactor `tools/select_r44_coverage_packets.py` to use the helper**

Replace local hard-exclusion/prefix logic with a dual import that works both when the file is imported as `tools.select_r44_coverage_packets` and when executed as `python tools/select_r44_coverage_packets.py`:

```python
try:
    from .realizer_blocker_taxonomy import (
        canonical_blocker_id, is_hard_excluded, is_repairable_blocker,
    )
except ImportError:
    from realizer_blocker_taxonomy import (
        canonical_blocker_id, is_hard_excluded, is_repairable_blocker,
    )
```

Canonicalize every blocker before set operations. Preserve `ROUTE_ONLY_EXCLUDE_IDS` and `REQUIRED_FAMILIES` locally because they are selector policy, not taxonomy.

In `_blocker_ids`, return canonical IDs. In `_candidate`, compute:

```python
ids = [canonical_blocker_id(identifier) for identifier in ids]
family_repairable = {identifier for identifier in ids if is_repairable_blocker(identifier)}
```

Do not change the four-distinct-seed R44 floor.

- [ ] **Step 7: Run R45 taxonomy and existing R44 selector tests**

Run:

```bash
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q \
  assets/test_r45_blocker_taxonomy.py assets/test_r44_packet_selection.py
```

Expected: PASS.

- [ ] **Step 8: Re-run the preserved R44 selector input and record whether the result changes**

Using the original R44 diagnostic rows, run:

```bash
python tools/select_r44_coverage_packets.py \
  --rows assets/results/diversity_refactor/r45/baseline/reachability/rows.jsonl \
  --output assets/results/diversity_refactor/r45/r45-01-r44-selector.json \
  --max-packets 3
```

Expected based on R44 grouping: still no >=4-seed full-signature group. If output becomes non-empty, do **not** treat it as authorization; document exactly why before continuing.

- [ ] **Step 9: Verify no runtime output changed**

Run a fresh 512 audit to a new directory and compare `normal-pairs.jsonl` byte-for-byte with Task R45-00 baseline:

```bash
python tools/audit_realizer_reachability.py --profile intake --force-families all \
  --output-dir assets/results/diversity_refactor/r45/r45-01-reachability
python - <<'PY'
from pathlib import Path
left = Path('assets/results/diversity_refactor/r45/baseline/reachability/normal-pairs.jsonl').read_bytes()
right = Path('assets/results/diversity_refactor/r45/r45-01-reachability/normal-pairs.jsonl').read_bytes()
assert left == right
print('ordinary pairs unchanged')
PY
```

- [ ] **Step 10: Commit R45-01**

Update `r45_progress.md` to PASS with the selector result and parity hash, then:

```bash
git add tools/realizer_blocker_taxonomy.py tools/select_r44_coverage_packets.py \
        assets/test_r45_blocker_taxonomy.py docs/diversity_refactor/r45_progress.md
git commit -m "refactor: canonicalize realizer blocker taxonomy"
```

**Acceptance R45-01:**

- Colon-form family blockers are recognized correctly.
- Legacy dot forms normalize to the same canonical IDs.
- Hard exclusions remain hard.
- R44 four-seed viability floor is unchanged.
- Ordinary 512 pairs remain byte-identical.

---

# Task R45-02: Add Typed Atomic Capability Projection

**Purpose:** Project reusable capabilities from the typed `RealizationEvidence` graph without assuming one `ProducerPart` equals one `ClauseEvidence`.

**Files:**
- Create: `tools/realizer_capability_projection.py`
- Create: `assets/test_r45_capability_projection.py`
- Modify: `tools/realizer_reachability_diagnostics.py`
- Modify: `assets/test_r43_common_diagnostics.py`
- Modify: `docs/diversity_refactor/r45_progress.md`

**Interfaces:**
- Consumes: current `RealizationEvidence`, `EvidenceComponent.trace.parts`, `ClauseEvidence.source_part_ids`, and the already validated R44 `coverage_signature.proof_basis`.
- Produces:
  - `capability_sha256(identity: Mapping) -> str`
  - `project_evidence_capabilities(evidence) -> list[dict]`
  - `build_capability_projection(snapshot: Mapping, coverage_signature: Mapping) -> dict`
- `diagnose_snapshot()` appends `capability_projection` and `capability_projection_sha256` after it builds the R44 coverage signature.
- R45-04 consumes the attached projection from canonical reachability rows.

- [ ] **Step 1: Mark R45-02 IN_PROGRESS**

Update the task row in `r45_progress.md` before code edits.

- [ ] **Step 2: Write failing typed-projection tests using existing evidence fixtures**

Create `assets/test_r45_capability_projection.py` with these imports and helper:

```python
import copy
from dataclasses import replace
import unittest

from assets.test_r43_family_capabilities import fixture_case
from tools.realizer_capability_projection import (
    build_capability_projection, capability_sha256, project_evidence_capabilities,
)


def by_domain(items, domain):
    return [item for item in items if item['capability']['domain'] == domain]
```

Add a test proving Action capability identity ignores text/hash payload while preserving structural identity:

```python
class TestTypedCapabilityProjection(unittest.TestCase):
    def test_action_identity_ignores_source_text_and_selected_text_hash(self):
        _, _, evidence = fixture_case()
        before = by_domain(project_evidence_capabilities(evidence), 'action')
        components = list(evidence.components)
        index = next(i for i, component in enumerate(components) if component.domain == 'action')
        component = components[index]
        parts = tuple(
            replace(part, text='different diagnostic text',
                    source=replace(part.source, selected_text_sha256='different-hash'))
            for part in component.trace.parts
        )
        atoms = tuple(replace(atom, source_text='different diagnostic text') for atom in component.atoms)
        components[index] = replace(component, trace=replace(component.trace, parts=parts), atoms=atoms)
        mutated = replace(evidence, components=tuple(components))
        after = by_domain(project_evidence_capabilities(mutated), 'action')
        self.assertEqual(before, after)
```

The projection deliberately ignores text and selected-text hashes; this pure helper does not perform runtime binding validation.

- [ ] **Step 3: Add a source-role-change test**

Mutate only one Action `SourceRef.field` and assert the corresponding capability hash changes:

```python
    def test_action_source_field_change_changes_identity(self):
        _, _, evidence = fixture_case()
        before = by_domain(project_evidence_capabilities(evidence), 'action')
        components = list(evidence.components)
        index = next(i for i, component in enumerate(components) if component.domain == 'action')
        component = components[index]
        parts = list(component.trace.parts)
        parts[0] = replace(parts[0], source=replace(parts[0].source, field='posture'))
        components[index] = replace(component, trace=replace(component.trace, parts=tuple(parts)))
        after = by_domain(project_evidence_capabilities(replace(evidence, components=tuple(components))), 'action')
        self.assertNotEqual(before[0]['capability_sha256'], after[0]['capability_sha256'])
```

- [ ] **Step 4: Add a Clothing multi-part/one-atom contract test**

The test must prove projection follows `ClauseEvidence.source_part_ids`, not parallel list positions:

```python
    def test_clothing_atom_uses_all_referenced_source_parts(self):
        _, _, evidence = fixture_case()
        items = by_domain(project_evidence_capabilities(evidence), 'clothing')
        self.assertEqual(len(items), 1)
        capability = items[0]['capability']
        self.assertEqual(capability['capability_kind'], 'clause_atom')
        self.assertEqual(capability['source_field_classes'], ['palette.colors', 'choices.dresses'])
        self.assertEqual(capability['form_class'], 'noun_phrase')
        self.assertEqual(capability['owner_class'], 'protagonist')
```

If the fixture's current selected source is `character_palette.colors` rather than `palette.colors`, update the expected first field to that exact current structural field after inspecting the fixture once; do not weaken the assertion to unordered membership.

- [ ] **Step 5: Add unrelated-domain isolation and invalid-part-reference tests**

For domain isolation, mutate only the Scene component's trace constructor/source fields and assert every Action capability is byte-for-byte unchanged.

For invalid source reference, replace one atom's `source_part_ids` with `('missing:part',)` and assert `project_evidence_capabilities` raises `ValueError('capability atom references an unknown producer part')`. Do not silently drop the atom.

- [ ] **Step 6: Add wrapper tests for current diagnostic availability**

Use a real R43/R44 snapshot fixture such as `real_snapshot()` from `assets.test_r43_real_graph_placement`.

Required behavior:

```python
projection = build_capability_projection(snapshot, {'proof_basis': 'common_reconstructed'})
self.assertEqual(projection['schema_version'], 'realizer-capability-projection/v1')
self.assertEqual(projection['status'], 'AVAILABLE')
self.assertTrue(projection['capabilities'])

unavailable = build_capability_projection(snapshot, {'proof_basis': 'invalid_common_inputs'})
self.assertEqual(unavailable, {
    'schema_version': 'realizer-capability-projection/v1',
    'status': 'NOT_AVAILABLE',
    'capabilities': [],
})
```

The wrapper must not try to salvage invalid/stale common inputs.

- [ ] **Step 7: Run tests and verify red state**

Run:

```bash
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_capability_projection.py
```

Expected: missing module/functions.

- [ ] **Step 8: Implement typed capability identities**

Create `tools/realizer_capability_projection.py` with this structural skeleton:

```python
from __future__ import annotations

from collections.abc import Mapping
import hashlib

from pipeline.realization_evidence import Truth, build_realization_evidence
from tools.workflow_prompt_runner import canonical_json_bytes

SCHEMA_VERSION = 'realizer-capability-projection/v1'


def capability_sha256(identity: Mapping) -> str:
    return hashlib.sha256(canonical_json_bytes(identity)).hexdigest()


def _owner_class(atom) -> str:
    subject, owner = atom.grammatical_subject_id, atom.owner_id
    if isinstance(subject, str) and subject.startswith('body:') and owner == 'protagonist':
        return 'protagonist_body_part'
    if any(isinstance(value, str) and value.startswith('object:') for value in (subject, owner)):
        return 'primary_object_part'
    if any(isinstance(value, str) and value.startswith('event:') for value in (subject, owner)):
        return 'scene_event'
    if subject == 'protagonist' or owner == 'protagonist':
        return 'protagonist'
    return 'unknown'


def _catalog_source_class(domain: str, source) -> str:
    if domain == 'clothing' and source.field.startswith('character_palette.'):
        return 'character_palette'
    if source.catalog_key is None:
        return 'producer'
    if domain == 'scene':
        return 'background_defaults' if source.catalog_key == 'background_defaults' else 'location_pack'
    return {
        'clothing': 'selected_clothing_pack',
        'subject': 'character_profile',
        'template': 'template_catalog',
        'mood': 'mood_catalog',
    }.get(domain, 'catalog')


def _constructor_class(value: str) -> str:
    if not isinstance(value, str) or not value:
        return 'unknown'
    if value.startswith('action_slots:'):
        return 'action_slots'
    return value.removesuffix('/v1')
```

Implement `project_evidence_capabilities(evidence)` by iterating components and atoms. For each component with `trace is not None`:

```python
parts = {part.part_id: part for part in component.trace.parts}
for atom in component.atoms:
    try:
        sources = [parts[part_id].source for part_id in atom.source_part_ids]
    except KeyError as exc:
        raise ValueError('capability atom references an unknown producer part') from exc
    identity = {
        'schema_version': SCHEMA_VERSION,
        'domain': component.domain,
        'capability_kind': 'clause_atom',
        'producer_class': component.trace.producer,
        'constructor_class': _constructor_class(component.trace.constructor_id),
        'source_field_classes': [source.field for source in sources],
        'catalog_source_classes': [_catalog_source_class(component.domain, source) for source in sources],
        'form_class': atom.form if isinstance(atom.form, str) and atom.form else 'unknown',
        'attachment_class': atom.attachment if isinstance(atom.attachment, str) and atom.attachment else 'unknown',
        'owner_class': _owner_class(atom),
        'grammar_state': atom.grammar_known.value if isinstance(atom.grammar_known, Truth) else 'unknown',
        'source_bound': True,
    }
```

Append:

```python
{'capability': identity, 'capability_sha256': capability_sha256(identity)}
```

Sort final items deterministically by `(domain, capability_sha256)`. Components with no trace or no atoms produce no identity.

- [ ] **Step 9: Implement the snapshot wrapper**

`build_capability_projection(snapshot, coverage_signature)` must:

1. return `NOT_AVAILABLE` unless `coverage_signature['proof_basis'] == 'common_reconstructed'`;
2. if `snapshot['bridge']` or `bridge['common_inputs']` is absent despite that proof basis, raise `ValueError('common reconstructed projection is missing current inputs')` because the diagnostic state is internally inconsistent;
3. rebuild current evidence using `build_realization_evidence(common_inputs)` rather than accepting serialized/frozen evidence;
4. project that typed evidence;
5. return:

```python
{
    'schema_version': SCHEMA_VERSION,
    'status': 'AVAILABLE',
    'capabilities': projected_items,
}
```

Do not accept a caller-supplied frozen evidence object or capability list as authority.

- [ ] **Step 10: Attach projection additively inside `diagnose_snapshot()`**

In `tools/realizer_reachability_diagnostics.py`, after `build_coverage_signature(snapshot, result)` succeeds, call:

```python
projection = build_capability_projection(snapshot, signature)
```

and return additive keys:

```python
'capability_projection': projection,
'capability_projection_sha256': hashlib.sha256(canonical_json_bytes(projection)).hexdigest(),
```

Use existing canonical helper imports rather than `str(dict)` hashing. If `canonical_json_bytes` is not already imported in this file, import it from `tools.workflow_prompt_runner` using the same repository import style as neighboring tools.

Do this in both `bridge is None` and normal diagnostic return paths. `bridge is None` must produce `NOT_AVAILABLE`, never an error.

- [ ] **Step 11: Update the existing diagnostics regression to protect old fields separately**

`assets/test_r43_common_diagnostics.py` already learned to tolerate additive R44 signature fields. Extend the same pattern so the test compares every pre-R45 field exactly, then separately asserts `capability_projection`/hash shape. Do not delete old equality coverage.

- [ ] **Step 12: Run projection and diagnostic tests**

Run:

```bash
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q \
  assets/test_r45_capability_projection.py \
  assets/test_r43_common_diagnostics.py \
  assets/test_r44_coverage_signatures.py \
  assets/test_r44_reachability_accounting.py
```

Expected: PASS.

- [ ] **Step 13: Run a fresh 16-seed diagnostic repeat and verify deterministic additive output**

Run the reachability audit twice with `--sample-count 16` into different directories. Compare `capability_projection` and `capability_projection_sha256` for every seed. Original R44 diagnostic fields must remain equal.

- [ ] **Step 14: Run the projection against the fixed512 baseline before Scene refactor**

Run:

```bash
python tools/audit_realizer_reachability.py --profile intake --force-families all \
  --output-dir assets/results/diversity_refactor/r45/r45-02-reachability
```

Record only measurement facts in `r45_progress.md`: number of AVAILABLE projections, total capability identities, unique capability hashes, and largest repeated capability count. Do not interpret these counts as runtime rescue.

- [ ] **Step 15: Prove ordinary runtime remains unchanged and commit**

Compare `normal-pairs.jsonl` byte-for-byte with R45-00 baseline. Then:

```bash
git add tools/realizer_capability_projection.py \
        tools/realizer_reachability_diagnostics.py \
        assets/test_r45_capability_projection.py \
        assets/test_r43_common_diagnostics.py \
        docs/diversity_refactor/r45_progress.md
git commit -m "feat: project typed realizer capabilities"
```

**Acceptance R45-02:**

- Capability identity follows typed `ClauseEvidence.source_part_ids`, not index-zipped diagnostic arrays.
- Clothing multi-part/one-atom projection is correct.
- Text, selected-text hashes and seed do not affect capability identity.
- Structural source roles/form/owner do affect capability identity.
- Invalid source-part references fail closed.
- Projection is additive diagnostic data only.
- Original R44 diagnostic fields and ordinary fixed512 pairs remain unchanged.

---

# Task R45-03: Separate Scene Source Binding from Scene Grammar Proof

**Purpose:** Preserve exact Scene producer provenance even when the closed Scene grammar cannot prove the selected text.

**Files:**
- Modify: `pipeline/v2_scene_provenance.py`
- Create: `assets/test_r45_scene_provenance_separation.py`
- Modify: `docs/diversity_refactor/r45_progress.md`

**Interfaces:**
- Consumes: current `adapt_scene_component(context, current_scene=None, frame_value=None, *, input_binding_sha256, source_identity_sha256) -> EvidenceComponent` signature unchanged.
- Produces: same `EvidenceComponent` type. Scenes already accepted by the R44 combined parser retain existing behavior. Scenes recovered only by the new source-only binder have `trace is not None`, `runtime_available is True`, diagnostic grammar facts when available, and mandatory blocker `scene.r45_source_only_permission_deferred`.
- Must not change `FamilyProof` API or eligibility rules; the deferred blocker guarantees no new R45 authorization even if every recovered atom happens to be grammatically known.

- [ ] **Step 1: Mark R45-03 IN_PROGRESS**

Record target file ownership before edits.

- [ ] **Step 2: Write failing unit tests that distinguish source binding from grammar proof**

Create `assets/test_r45_scene_provenance_separation.py`. Reuse `unittest.mock.patch` so the fixture is independent of future vocabulary wording.

Use a controlled source pack:

```python
PACKS = {
    'test_room': {
        'environment': ['radiant observatory'],
        'core': ['telescopes beneath the dome'],
        'props': [], 'time': [], 'texture': [], 'fx': [], 'weather': [], 'crowd': [],
    }
}
DEFAULTS = {'details': [], 'texture': [], 'fx': []}
```

Build the fixture with this exact structural shape, patching `pipeline.v2_scene_provenance.load_background_packs` to return `PACKS` and `pipeline.v2_scene_provenance.load_json` to return `DEFAULTS` for `background_defaults.json`:

```python
def unknown_grammar_scene_context():
    scene = 'radiant observatory, featuring telescopes beneath the dome'
    return {
        'loc': 'test_room',
        'extras': {
            'raw_loc_tag': 'test_room',
            'location_prompt': scene,
        },
        'history': [{
            'node': 'ContextLocationExpander',
            'seed': 7,
            'decision': {
                'pack_key': 'test_room',
                'template_key': 'detailed',
                'selected_props': [],
                'semantic_epig': {
                    'location_scene': {
                        'section_changes': {
                            'core': {'semantic': ['telescopes beneath the dome']},
                        }
                    }
                },
            },
        }],
    }, scene
```

Use `frame_value=None`; the existing adapter permits frame-location knowledge to remain `UNKNOWN` when no current frame is supplied. Both source phrases are intentionally outside the existing closed Scene noun grammar, while their source origin and producer assembly are exact.

Required assertions:

```python
from pipeline.realization_evidence import Truth
from pipeline.v2_scene_provenance import adapt_scene_component

self.assertIsNotNone(component.trace)
self.assertTrue(component.runtime_available)
self.assertTrue(component.atoms)
self.assertTrue(all(atom.grammar_known is Truth.UNKNOWN for atom in component.atoms))
self.assertIn('scene.grammar_unknown', component.blockers)
self.assertIn('scene.r45_source_only_permission_deferred', component.blockers)
self.assertNotIn('scene.source_unavailable', component.blockers)
```

The exact blocker name created by R45 must be `scene.grammar_unknown`; do not retain ambiguous `scene.source_or_grammar_unknown` for this state.

- [ ] **Step 3: Add a source-failure control test**

Change current scene text to a phrase not present in the patched source pack and assert:

```python
self.assertIsNone(component.trace)
self.assertFalse(component.runtime_available)
self.assertIn('scene.source_unavailable', component.blockers)
```

This proves source mismatch and grammar unknown are not conflated.

- [ ] **Step 4: Add a family-proof fail-closed integration test**

Build `RealizationEvidence` using the existing real fixture path, substitute the source-bound/grammar-unknown Scene component using `dataclasses.replace`, and call existing family proof logic. Assert all six families remain ineligible and include a Scene grammar blocker.

The test must **not** mock `FamilyProof.eligible` or bypass `_prepare()`.

Also add a control proving the deferred blocker is unconditional for the source-only route. Use `unittest.mock.patch` to force the R44 compatibility oracle `_producer_scene_components(..., bind_sources=True)` to return `None` while allowing `_bind_scene_source_parts` to use the controlled pack, and patch `_classify_bound_scene_part` to return a valid structured tuple for every recovered part. Assert every atom is `grammar_known=TRUE`, the component still contains `scene.r45_source_only_permission_deferred`, and all family proofs remain ineligible. Do **not** mock `FamilyProof.eligible` or `_prepare()`. This protects ordinary behavior from accidental diagnostic-to-runtime promotion.

- [ ] **Step 5: Add a known-grammar preservation test**

Use an existing known Scene fixture from `assets/test_r43_real_graph_placement.py` or `assets/test_r43_scene_binding.py`. Capture the pre-refactor `ProducerTrace`, atom forms/attachments/owners, and component facts. Assert the refactor returns equivalent values for that known case.

- [ ] **Step 6: Run the new tests and verify red state**

Run:

```bash
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q \
  assets/test_r45_scene_provenance_separation.py
```

Expected: source-bound unknown grammar currently collapses to no trace / `scene.source_or_grammar_unknown`.

- [ ] **Step 7: Refactor Scene parsing into two private stages**

Inside `pipeline/v2_scene_provenance.py`, add a frozen private source-part type:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class _BoundScenePart:
    field: str
    raw: str
    source_key: str
```

Add a source-only helper:

```python
def _bind_scene_source_parts(location, location_key, *, bind_sources=True):
    """Return exact ordered producer source parts without requiring grammar proof."""
```

This helper must perform only producer/source topology work already present in `_producer_scene_components`:

- sanitize-and-match the environment against the selected pack exactly;
- preserve the existing guard that rejects an environment-with-commas being reinterpreted as a shorter environment plus segments;
- split only the existing producer prefixes `featuring `, `adorned with `, `with `, and `during `;
- map those prefixes to the existing producer fields `core`, `props`, `props`, and `time`;
- for bare segments, require exactly one origin among pack/default `texture`, `details`, `fx`, plus current pack `weather`/`crowd` when those fields are source-bound;
- require unique raw source membership and reject source ambiguity;
- preserve source field uniqueness, selected order, and duplicate rejection;
- preserve `background_defaults` vs location-pack source key;
- call `_assemble_location_prompt(anchor, segments)` and require the emitted text to equal the current `location` exactly before returning bound parts.

It must not call `_scene_nominal`, `_common_scene_nominal`, `_nominal`, `_scene_modifier`, or `_article` to decide whether source binding succeeded.

Return:

```python
(tuple[_BoundScenePart, ...], anchor, tuple(segments))
```

or `None` for ambiguous/unbound source.

- [ ] **Step 8: Add a grammar-only classifier over bound parts**

Add:

```python
def _classify_bound_scene_part(part: _BoundScenePart, *, reviewed=False):
    """Return existing structured grammar tuple or None; never changes source binding."""
```

Reuse existing `_common_scene_nominal`, `_scene_nominal`, `_nominal`, and reviewed grammar paths. This helper must not search alternate source catalogs.

- [ ] **Step 9: Rebuild `adapt_scene_component` around the two-stage model**

Preserve all current history/current-text/frame checks. Keep the existing combined source+grammar parse as a compatibility oracle and do not broaden it. After the binding/history checks pass:

1. run the existing R44 combined parse (`bind_sources=True`, then reviewed fallback) exactly as before;
2. if that combined parse succeeds, build the component through the existing known-authorized path with no R45 deferred blocker;
3. only when the combined parse fails, call `_bind_scene_source_parts`;
4. if source-only binding also returns `None`, return an unavailable component with `scene.source_unavailable`;
5. if source-only binding succeeds, construct `ProducerPart`/`ProducerTrace` immediately from the bound source parts and set `recovered_source_only = True`; use trace `constructor_id='scene.r45_source_bound_unproved/v1'`, preserve exact `source_identity_sha256`/`input_binding_sha256`, and hash the current raw/emitted output exactly as existing traces do;
6. classify each recovered part grammatically for diagnostics;
7. build one `ClauseEvidence` per part;
8. known parts may retain proved form/attachment/owner values for measurement, but this does not grant authorization;
9. unknown parts use:

```python
grammar_known=Truth.UNKNOWN
grammatical_subject_id=None
owner_id=None
form='unknown'
attachment='unknown'
same_subject=Truth.UNKNOWN
place_refs=None
antecedent_ids=None
rule_ids=()
grammatical_head=None
```

10. every `recovered_source_only` component includes `scene.r45_source_only_permission_deferred`; additionally include `scene.grammar_unknown` if any atom is unknown; the source-bound component remains `runtime_available=True`;
11. source-only component facts must set `source_order_known=TRUE`; set `ownership_known=TRUE` only when every recovered atom has proved ownership, otherwise `UNKNOWN`; keep `frame_location_matches` at the exact value established by the unchanged frame checks.

Do not alter `family_capabilities.py`; `_prepare()` already treats component blockers as authorization failures, so the deferred blocker prevents any R45-only Scene recovery from becoming eligible.

- [ ] **Step 10: Keep rendering constructors fail-closed**

`common_scene_parts`, `producer_owned_scene`, and `common_standalone_scene_parts` still require known grammar before materializing alternate syntax. They must **not** consume unknown atoms just because source binding now succeeds.

Add an explicit test that `producer_owned_scene` returns `None` for the patched `radiant observatory` case.

- [ ] **Step 11: Run focused Scene/evidence/family tests**

Run:

```bash
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -p tools.verify_realizer_v2_candidate -q \
  assets/test_r45_scene_provenance_separation.py \
  assets/test_r43_scene_binding.py \
  assets/test_r43_scene_trace.py \
  assets/test_r43_reviewed_scene_binding.py \
  assets/test_r43_family_capabilities.py \
  assets/test_r43_evidence_contract.py \
  assets/test_r43_real_graph_placement.py
```

Expected: PASS.

- [ ] **Step 12: Run a fresh 512 reachability audit and measure provenance separation**

Run:

```bash
python tools/audit_realizer_reachability.py --profile intake --force-families all \
  --output-dir assets/results/diversity_refactor/r45/r45-03-reachability
```

Extract these metrics to `r45_progress.md`:

```text
scene source_trace count
scene runtime_bound count
scene grammar_known count
scene grammar_unknown count
ordinary v2 count
ordinary family count
fallback count
```

Acceptance requires Scene source-bound count to be **strictly greater than the R44 value 16**. Do not require an arbitrary large number; report the measured result.

- [ ] **Step 13: Prove ordinary output/context parity**

Compare `normal-pairs.jsonl` against R45-00 baseline byte-for-byte:

```bash
python - <<'PY'
from pathlib import Path
left = Path('assets/results/diversity_refactor/r45/baseline/reachability/normal-pairs.jsonl').read_bytes()
right = Path('assets/results/diversity_refactor/r45/r45-03-reachability/normal-pairs.jsonl').read_bytes()
assert left == right
print('ordinary pairs unchanged')
PY
```

Also assert ordinary v2 remains `11/512`, ordinary families remain `3`, and fallback remains `501`.

- [ ] **Step 14: Run package/root replay determinism on the new source**

Run root and package modes with different order/hashseed in fresh output directories and compare summary/evidence/family-row bytes exactly, following the R44 handoff command pattern.

- [ ] **Step 15: Commit R45-03**

Update progress with measured source-bound count and parity hashes. Then:

```bash
git add pipeline/v2_scene_provenance.py \
        assets/test_r45_scene_provenance_separation.py docs/diversity_refactor/r45_progress.md
git commit -m "refactor: separate scene provenance from grammar proof"
```

**Acceptance R45-03:**

- Source-only recovered Scene yields a trace and mandatory `scene.r45_source_only_permission_deferred`; unknown grammar remains `Truth.UNKNOWN`.
- Source-unbound remains unavailable.
- Known Scene proof behavior is preserved.
- Scene source-bound count is >16 on fixed512.
- Ordinary output/context remains byte-identical 11/512, 3 families, 501 fallbacks.
- No FamilyProof gains eligibility solely because source provenance was separated, including recovered scenes whose individual grammar facts are all known.

---

# Task R45-04: Build the Capability/Blocker Audit Graph

**Purpose:** Aggregate atomic capabilities, blockers and syntax families using distinct-seed accounting rather than a full-state composite signature.

**Files:**
- Create: `tools/audit_realizer_capabilities.py`
- Create: `assets/test_r45_capability_audit.py`
- Modify: `docs/diversity_refactor/r45_progress.md`

**Interfaces:**
- Consumes: canonical `rows.jsonl` from `audit_realizer_reachability.py` after R45-03, including additive `capability_projection` records attached by R45-02.
- Produces output directory containing:
  - `capability-occurrences.jsonl`
  - `capability-summary.json`
  - `capability-blocker-intersections.json`
  - `r46-candidates.json`
  - `environment.json`
  - `source-input.json`

- [ ] **Step 1: Mark R45-04 IN_PROGRESS**

- [ ] **Step 2: Write pure accounting tests before CLI implementation**

Create `assets/test_r45_capability_audit.py` and import planned helpers:

```python
from tools.audit_realizer_capabilities import (
    occurrences_from_rows, rank_r46_candidates, summarize_occurrences,
)
```

Use synthetic occurrences where one capability appears for the same seed in multiple families. Assert:

```python
self.assertEqual(summary['capabilities'][cap]['distinct_seed_count'], 2)
self.assertEqual(summary['capabilities'][cap]['seed_family_row_count'], 3)
```

The test must catch accidental family-row counting as distinct seeds.

Also add `test_occurrences_preserve_typed_identity_and_add_context_only`: construct one synthetic reachability row with `capability_projection.status='AVAILABLE'`, a Clothing identity whose `source_field_classes` has two entries, and a `coverage_signature.family_blockers` map. Assert `occurrences_from_rows([row])[0]['capability']` equals the original capability object exactly while `run_seed`, `target_families`, canonical `blocker_ids`, and `family_blockers` are attached outside it.

- [ ] **Step 3: Add blocker/capability intersection tests**

Use two capabilities `A` and `B` with canonical blockers and assert the summary contains:

```text
A x action.leaf_grammar_unknown -> exact distinct seed count
A x subject_action_scene -> exact distinct seed count
blocker pair -> exact distinct seed count
```

Example seeds must be sorted and capped at 8 while `distinct_seed_count` uses the full set.

- [ ] **Step 4: Add ranking tests**

Construct synthetic candidates:

- capability A: 12 distinct seeds, 2 target families, 1 common co-blocker;
- capability B: 12 distinct seeds, 1 target family, 0 co-blockers;
- capability C: 8 distinct seeds.

Assert A ranks before B because family breadth is the second criterion. Add hash tie-break test.

Add a hard-exclusion integration test: pass a synthetic reachability row with `binding.current_input_mismatch` through `occurrences_from_rows`, then through `summarize_occurrences`/`rank_r46_candidates`. Its occurrence may remain in descriptive counts, but it must have `hard_excluded=True` and must not contribute to an R46 candidate.

- [ ] **Step 5: Run tests and verify red state**

Run:

```bash
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q assets/test_r45_capability_audit.py
```

Expected: missing module/functions.

- [ ] **Step 6: Implement canonical occurrence summarization**

Create `tools/audit_realizer_capabilities.py` with:

```python
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.realizer_blocker_taxonomy import (
    blocker_domain, canonical_blocker_id, is_hard_excluded, is_repairable_blocker,
)
from tools.realizer_capability_projection import SCHEMA_VERSION as CAPABILITY_SCHEMA
from tools.workflow_prompt_runner import canonical_json_bytes

SCHEMA = 'realizer-capability-audit/v1'
```

First implement row-to-occurrence conversion. Capability identity comes only from the typed projection already attached to the row; the audit adds seed/family/blocker measurement context without modifying that identity:

```python
def occurrences_from_rows(rows: list[dict]) -> list[dict]:
    occurrences = []
    for row in rows:
        projection = row.get('capability_projection', {})
        if projection.get('status') != 'AVAILABLE':
            continue
        if projection.get('schema_version') != CAPABILITY_SCHEMA:
            raise ValueError('unsupported capability projection schema')
        signature = row.get('coverage_signature', {})
        family_blockers = signature.get('family_blockers')
        if not isinstance(family_blockers, dict):
            raise ValueError('coverage signature family_blockers missing')
        row_ids = set()
        for item in row.get('blockers', ()):
            if isinstance(item, dict) and isinstance(item.get('id'), str):
                row_ids.add(canonical_blocker_id(item['id']))
        for item in row.get('errors', ()):
            if isinstance(item, dict) and isinstance(item.get('id'), str):
                row_ids.add(canonical_blocker_id(item['id']))
        hard_excluded = any(is_hard_excluded(value) for value in row_ids)
        for projected in projection.get('capabilities', ()):
            capability = projected['capability']
            sha = projected['capability_sha256']
            domain = capability['domain']
            relevant = {}
            domain_ids = set()
            for family, raw_ids in sorted(family_blockers.items()):
                ids = [canonical_blocker_id(value) for value in raw_ids]
                matching = [value for value in ids if blocker_domain(value) == domain]
                if matching:
                    relevant[family] = sorted(set(ids))
                    domain_ids.update(matching)
            occurrences.append({
                'schema_version': 'realizer-capability-occurrence/v1',
                'run_seed': row['run_seed'],
                'domain': domain,
                'capability': capability,
                'capability_sha256': sha,
                'ordinary_realizer_version': row.get('normal', {}).get('realizer_version'),
                'ordinary_syntax_family': row.get('normal', {}).get('syntax_family'),
                'target_families': sorted(relevant),
                'blocker_ids': sorted(domain_ids),
                'family_blockers': relevant,
                'hard_excluded': hard_excluded,
            })
    return occurrences
```

Add a test where a Clothing capability has multiple `source_field_classes`; `occurrences_from_rows` must preserve the identity object unchanged and only attach context around it.

Then implement the pure accounting core using set-based distinct-seed accounting. The following code is the required behavioral shape; variable names may be factored into small private helpers but the serialized fields and counting semantics must remain identical:

```python
ROUTE_ONLY = frozenset({'family.legacy_route_ceiling'})


def summarize_occurrences(occurrences: list[dict], observed_ordinary_families=()) -> dict:
    capabilities = {}
    blocker_seeds = defaultdict(set)
    cap_blocker_seeds = defaultdict(set)
    cap_family_seeds = defaultdict(set)
    row_family_blockers = defaultdict(set)
    ordinary_families = set(observed_ordinary_families)

    for item in occurrences:
        seed = item['run_seed']
        sha = item['capability_sha256']
        family_keys = tuple(item.get('target_families', ()))
        record = capabilities.setdefault(sha, {
            'capability': item['capability'],
            'domain': item['domain'],
            'seed_set': set(),
            'seed_family_set': set(),
            'blocker_ids': set(),
            'family_keys': set(),
        })
        record['seed_set'].add(seed)
        record['blocker_ids'].update(item.get('blocker_ids', ()))
        record['family_keys'].update(family_keys)
        for family in family_keys:
            record['seed_family_set'].add((seed, family))
            cap_family_seeds[(sha, family)].add(seed)
        for blocker in item.get('blocker_ids', ()):
            blocker = canonical_blocker_id(blocker)
            blocker_seeds[blocker].add(seed)
            cap_blocker_seeds[(sha, blocker)].add(seed)
        for family, blockers in item.get('family_blockers', {}).items():
            canonical = {canonical_blocker_id(value) for value in blockers}
            row_family_blockers[(seed, family)].update(canonical)
            for blocker in canonical:
                blocker_seeds[blocker].add(seed)
                cap_blocker_seeds[(sha, blocker)].add(seed)
        if item.get('ordinary_realizer_version') == 'v2' and item.get('ordinary_syntax_family'):
            ordinary_families.add(item['ordinary_syntax_family'])

    blocker_pair_seeds = defaultdict(set)
    for (seed, _family), blockers in row_family_blockers.items():
        ordered = sorted(blockers)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                blocker_pair_seeds[(left, right)].add(seed)

    serialized_caps = {}
    for sha, value in sorted(capabilities.items()):
        serialized_caps[sha] = {
            'capability': value['capability'],
            'domain': value['domain'],
            'distinct_seed_count': len(value['seed_set']),
            'seed_family_row_count': len(value['seed_family_set']),
            'family_keys': sorted(value['family_keys']),
            'blocker_ids': sorted(value['blocker_ids']),
            'example_seeds': sorted(value['seed_set'])[:8],
        }

    return {
        'schema_version': SCHEMA,
        'ordinary_families': sorted(ordinary_families),
        'capabilities': serialized_caps,
        'blockers': {
            blocker: {'distinct_seed_count': len(seeds), 'example_seeds': sorted(seeds)[:8]}
            for blocker, seeds in sorted(blocker_seeds.items())
        },
        'capability_blocker_intersections': [
            {'capability_sha256': sha, 'blocker_id': blocker,
             'distinct_seed_count': len(seeds), 'example_seeds': sorted(seeds)[:8]}
            for (sha, blocker), seeds in sorted(cap_blocker_seeds.items())
        ],
        'capability_family_intersections': [
            {'capability_sha256': sha, 'family': family,
             'distinct_seed_count': len(seeds), 'example_seeds': sorted(seeds)[:8]}
            for (sha, family), seeds in sorted(cap_family_seeds.items())
        ],
        'blocker_pairs': [
            {'blocker_ids': [left, right], 'distinct_seed_count': len(seeds),
             'example_seeds': sorted(seeds)[:8]}
            for (left, right), seeds in sorted(blocker_pair_seeds.items())
        ],
    }


def rank_r46_candidates(occurrences: list[dict], summary: dict, *, limit: int = 12) -> list[dict]:
    if type(limit) is not int or limit < 1:
        raise ValueError('limit must be a positive integer')
    by_capability = defaultdict(list)
    for item in occurrences:
        if (item.get('ordinary_realizer_version') == 'v1'
                and item['capability'].get('source_bound') is True
                and item.get('hard_excluded') is not True):
            by_capability[item['capability_sha256']].append(item)

    ranked = []
    for sha, items in by_capability.items():
        meta = summary['capabilities'][sha]
        if meta['distinct_seed_count'] < 4:
            continue
        domain = meta['domain']
        rescue_seeds = set()
        affected_families = set()
        blocker_ids = set()
        for item in items:
            seed = item['run_seed']
            for family, raw_blockers in item.get('family_blockers', {}).items():
                blockers = {canonical_blocker_id(value) for value in raw_blockers}
                if any(is_hard_excluded(value) for value in blockers):
                    continue
                domain_blockers = {
                    value for value in blockers
                    if blocker_domain(value) == domain and is_repairable_blocker(value)
                }
                if not domain_blockers:
                    continue
                affected_families.add(family)
                blocker_ids.update(domain_blockers)
                remaining = {
                    value for value in blockers
                    if value not in ROUTE_ONLY and value not in domain_blockers
                }
                if not remaining:
                    rescue_seeds.add(seed)
        if not affected_families:
            continue
        co = [row for row in summary['capability_blocker_intersections']
              if row['capability_sha256'] == sha and row['blocker_id'] not in blocker_ids]
        co.sort(key=lambda row: (-row['distinct_seed_count'], row['blocker_id']))
        ranked.append({
            'capability_sha256': sha,
            'domain': domain,
            'capability': meta['capability'],
            'distinct_seed_count': meta['distinct_seed_count'],
            'affected_family_keys': sorted(affected_families),
            'blocker_ids': sorted(blocker_ids),
            'top_co_blockers': co[:8],
            'single_capability_rescue_upper_bound': len(rescue_seeds),
            'example_seeds': meta['example_seeds'],
        })

    observed = set(summary.get('ordinary_families', ()))
    ranked.sort(key=lambda row: (
        -row['distinct_seed_count'],
        -len(set(row['affected_family_keys']) - observed),
        len(row['top_co_blockers']),
        row['capability_sha256'],
    ))
    return [dict(row, rank=index + 1) for index, row in enumerate(ranked[:limit])]
```


For every counter, maintain both:

```text
seed_set
seed_family_set
```

Serialize only counts and capped examples, never Python sets.

- [ ] **Step 7: Define `single_capability_rescue_upper_bound` exactly**

For each fallback `(seed, family)` occurrence group:

1. canonicalize all blockers for that family;
2. exclude the row entirely if any hard blocker exists;
3. identify blockers whose `blocker_domain` equals the candidate capability domain;
4. the row contributes to `single_capability_rescue_upper_bound` only when:
   - at least one domain-matching repairable blocker exists; and
   - after removing repairable blockers in that candidate domain, no other non-route blocker remains.

`family.legacy_route_ceiling` may be ignored as route-only for this upper-bound calculation. `family.role_mismatch` and `family.composition_mode_disabled` do not count as repairable runtime capability work.

This is intentionally conservative and remains an upper bound.

- [ ] **Step 8: Implement candidate ranking output**

Each `r46-candidates.json` entry must contain:

```json
{
  "rank": 1,
  "capability_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "domain": "scene",
  "capability": {
    "schema_version": "realizer-capability-projection/v1",
    "domain": "scene",
    "capability_kind": "clause_atom",
    "producer_class": "pipeline.location_builder",
    "constructor_class": "scene.r45_source_bound_unproved",
    "source_field_classes": ["core"],
    "catalog_source_classes": ["location_pack"],
    "form_class": "unknown",
    "attachment_class": "unknown",
    "owner_class": "unknown",
    "grammar_state": "unknown",
    "source_bound": true
  },
  "distinct_seed_count": 24,
  "affected_family_keys": ["scene_lead_subject_action", "subject_action_scene"],
  "blocker_ids": ["scene.grammar_unknown", "scene.r45_source_only_permission_deferred"],
  "top_co_blockers": [],
  "single_capability_rescue_upper_bound": 8,
  "example_seeds": []
}
```

Do not include a complete seed allowlist in the ranked manifest. Full seed membership exists only in the diagnostic occurrence file and is not an implementation input contract.

- [ ] **Step 9: Implement CLI input validation and canonical output**

In `main`, read all reachability rows, derive:

```python
occurrences = occurrences_from_rows(rows)
observed_ordinary_families = sorted({
    row.get('normal', {}).get('syntax_family')
    for row in rows
    if row.get('normal', {}).get('realizer_version') == 'v2'
       and row.get('normal', {}).get('syntax_family')
})
summary = summarize_occurrences(occurrences, observed_ordinary_families)
candidates = rank_r46_candidates(occurrences, summary)
```

CLI:

```bash
python tools/audit_realizer_capabilities.py \
  --rows assets/results/diversity_refactor/r45/r45-03-reachability/rows.jsonl \
  --output-dir assets/results/diversity_refactor/r45/r45-04-capabilities
```

Requirements:

- reject missing/malformed rows with exit code 2;
- reject unsupported coverage signature schema;
- output directory must not already contain conflicting result files;
- write canonical JSON via existing helper;
- record input rows SHA-256 and current git commit when available;
- never mutate source rows or RNG.

- [ ] **Step 10: Run unit tests green**

Run:

```bash
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -q \
  assets/test_r45_capability_projection.py assets/test_r45_capability_audit.py
```

Expected: PASS.

- [ ] **Step 11: Run the capability audit on the post-Scene fixed512 rows**

Run:

```bash
python tools/audit_realizer_capabilities.py \
  --rows assets/results/diversity_refactor/r45/r45-03-reachability/rows.jsonl \
  --output-dir assets/results/diversity_refactor/r45/r45-04-capabilities
```

Record at minimum:

```text
unique capability count
largest capability distinct_seed_count
action unknown-grammar capability groups >=4 seeds
scene unknown-grammar capability groups >=4 seeds
candidate count
largest single_capability_rescue_upper_bound
top 12 candidate domains/families/blockers
```

- [ ] **Step 12: Repeat the audit and verify canonical byte reproducibility**

Run to a second directory and compare all canonical result files except environment elapsed/path fields. At minimum, `capability-occurrences.jsonl`, `capability-summary.json`, `capability-blocker-intersections.json`, and `r46-candidates.json` must match byte-for-byte.

- [ ] **Step 13: Commit R45-04**

Update progress with hashes and top measured results, then:

```bash
git add tools/audit_realizer_capabilities.py \
        assets/test_r45_capability_audit.py docs/diversity_refactor/r45_progress.md
git commit -m "feat: audit realizer capability intersections"
```

**Acceptance R45-04:**

- Distinct seed count is not family-row count.
- Capability identity remains text/seed-free.
- Intersections and ranking are deterministic.
- Hard failures cannot become candidates.
- At least one >=4-seed capability group exists for a PASS result. If none exists, record the condition and proceed to R45-05 only to assign/document `BLOCKED_CAPABILITY_MODEL`; do not start any runtime work.

---

# Task R45-05: Decide R46 Readiness Without Runtime Expansion

**Purpose:** Convert measured capability data into an explicit development verdict; do not implement grammar coverage here.

**Files:**
- Modify: `docs/diversity_refactor/r45_progress.md`
- Create/update compact receipts under: `docs/diversity_refactor/comparison_sources/r45/`
- Modify: `docs/diversity_refactor/tasks.md`
- Modify: `docs/diversity_refactor/progress.md`

**Interfaces:**
- Consumes: R45-03 reachability and R45-04 capability audit.
- Produces: one of `READY_FOR_R46`, `BLOCKED_CAPABILITY_MODEL`, or `REJECTED_REGRESSION` plus recoverable source identities.

- [ ] **Step 1: Mark R45-05 IN_PROGRESS**

- [ ] **Step 2: Compute the readiness contract from canonical result files**

Run a small read-only script that asserts:

```text
ordinary_v2 == 11
ordinary_family_count == 3
fallback == 501
largest capability distinct_seed_count >= 4
at least one candidate single_capability_rescue_upper_bound > 0
```

The script must fail if any ordinary preservation condition fails.

- [ ] **Step 3: Compute bounded top-3 candidate seed union as a development-work upper bound**

Use `capability-occurrences.jsonl` only for measurement. Select the top three **different capability hashes** from `r46-candidates.json`, collect the full occurrence seed sets, and report:

```text
top3_affected_seed_union
top3_single_capability_rescue_upper_bound_sum
top3_domains
top3_family_union
```

Do not store the full seed list in the tracked handoff. Store counts and at most eight examples per candidate.

This number is not a prediction that R46 will reach 64/512.

- [ ] **Step 4: Assign the development verdict**

Use these exact rules:

```text
if any ordinary/protected/determinism regression:
    REJECTED_REGRESSION
elif no capability group has >=4 distinct seeds
     or no candidate has single_capability_rescue_upper_bound >0:
    BLOCKED_CAPABILITY_MODEL
else:
    READY_FOR_R46
```

Write the result to `r45_progress.md` under a dedicated section in this exact machine-readable form:

```markdown
## Final development verdict
- development_verdict: READY_FOR_R46
```

Use `BLOCKED_CAPABILITY_MODEL` or `REJECTED_REGRESSION` instead of `READY_FOR_R46` when those rules apply. Do not require the top-three union to be >=53; record it as planning evidence only. R46 will validate actual gains one capability at a time.

- [ ] **Step 5: Create compact tracked receipts**

Create `docs/diversity_refactor/comparison_sources/r45/` with compact JSON receipts for:

```text
baseline identity
post-scene reachability summary
capability summary
candidate ranking summary
protected-input comparison
focused/regression result summaries
reproduction hashes
```

Do not track large raw `rows.jsonl`/logs if repository policy excludes them. Every compact receipt must include the source commit/source-tree hash and SHA-256 of the underlying local artifact it summarizes.

- [ ] **Step 6: Run complete development verification before committing the verdict**

Run:

```bash
python tools/verify_realizer_v2_candidate.py --stage focused \
  --output-dir assets/results/diversity_refactor/r45/final-development/focused
python tools/verify_realizer_v2_candidate.py --stage regression \
  --output-dir assets/results/diversity_refactor/r45/final-development/regression
python -m pytest --rootdir=. -o addopts= -p no:cacheprovider -p tools.verify_realizer_v2_candidate -q \
  assets/test_r45_blocker_taxonomy.py \
  assets/test_r45_capability_projection.py \
  assets/test_r45_scene_provenance_separation.py \
  assets/test_r45_capability_audit.py
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python tools/verify_full_flow.py
```

Also parse all changed Python files with Python 3.10 AST:

```bash
python - <<'PY'
import ast
from pathlib import Path
for name in (
    'tools/realizer_blocker_taxonomy.py',
    'tools/realizer_capability_projection.py',
    'tools/audit_realizer_capabilities.py',
    'tools/select_r44_coverage_packets.py',
    'pipeline/v2_scene_provenance.py',
    'assets/test_r45_blocker_taxonomy.py',
    'assets/test_r45_capability_projection.py',
    'assets/test_r45_scene_provenance_separation.py',
    'assets/test_r45_capability_audit.py',
):
    ast.parse(Path(name).read_text(encoding='utf-8'), filename=name, feature_version=(3, 10))
print('python310 AST PASS')
PY
```

- [ ] **Step 7: Recheck protected V150 file hashes**

Re-run the exact R45-00 protected hash script and compare all entries. Any unexpected change is `REJECTED_REGRESSION`.

- [ ] **Step 8: Re-run final fixed512 reachability and capability audit on the exact candidate source**

Use new final directories after all source edits are complete. Do not reuse an earlier audit if source bytes changed.

Record:

```text
source commit candidate
audit rows SHA-256
normal pairs SHA-256
capability occurrences SHA-256
capability summary SHA-256
candidate manifest SHA-256
```

- [ ] **Step 9: Commit R45-05 verdict receipts**

Update `r45_progress.md`, `tasks.md`, and global `progress.md` with measured facts only.

Commit:

```bash
git add docs/diversity_refactor/r45_progress.md \
        docs/diversity_refactor/tasks.md \
        docs/diversity_refactor/progress.md \
        docs/diversity_refactor/comparison_sources/r45/
git commit -m "docs: record R45 capability readiness"
```

**Acceptance R45-05:**

- Verdict follows exact rules above.
- All verification is tied to the final source bytes.
- No formal adoption claim is made.
- No runtime grammar capability has been added.

---

# Task R45-06: Recoverable Checkpoint and Handoff

**Purpose:** Freeze R45 as a recoverable diagnostic checkpoint and define the exact R46 boundary.

**Files:**
- Create: `docs/diversity_refactor/r45_handoff.md`
- Modify: `CURRENT_STATUS.md`
- Modify: `docs/diversity_refactor/r45_progress.md`
- Modify: `docs/diversity_refactor/comparison_sources/r45/registry.json`

**Interfaces:**
- Consumes: final R45 source and R45-05 verdict.
- Produces: immutable source tag, restoration instructions, handoff to R46 or redesign.

- [ ] **Step 1: Mark R45-06 IN_PROGRESS**

- [ ] **Step 2: Perform an independent source-scope review before tagging**

Run:

```bash
git diff origin/refactor/realizer-v2-r44...HEAD --name-only
git diff origin/refactor/realizer-v2-r44...HEAD -- pipeline/family_capabilities.py pipeline/prompt_realizer.py pipeline/v2_candidate_bridge.py vocab/data/natural_language_realizer_v2.json
git diff --check
```

Expected second command: empty diff.

Verify no V150 protected data diff:

```bash
git diff origin/refactor/realizer-v2-r44...HEAD -- \
  vocab/data/variation_scope.json assets/compatibility_review.csv \
  vocab/data/action_pools.json vocab/source/action_pools/
```

Expected: empty.

- [ ] **Step 3: Create a recoverable annotated R45 tag**

Tag name depends on verdict:

```text
READY_FOR_R46      -> realizer-v2-r45-ready-20260913
BLOCKED_CAPABILITY_MODEL -> realizer-v2-r45-blocked-20260913
REJECTED_REGRESSION -> do not publish a success/checkpoint tag; record rejection only
```

For READY/BLOCKED:

```bash
VERDICT=$(python - <<'PY2'
from pathlib import Path
prefix = '- development_verdict: '
lines = Path('docs/diversity_refactor/r45_progress.md').read_text(encoding='utf-8').splitlines()
values = [line[len(prefix):].strip() for line in lines if line.startswith(prefix)]
if len(values) != 1 or values[0] not in {'READY_FOR_R46', 'BLOCKED_CAPABILITY_MODEL'}:
    raise SystemExit('R45 verdict is not uniquely taggable')
print(values[0])
PY2
)
if [ "$VERDICT" = "READY_FOR_R46" ]; then
  TAG=realizer-v2-r45-ready-20260913
else
  TAG=realizer-v2-r45-blocked-20260913
fi
git show-ref --tags --verify --quiet "refs/tags/$TAG" && { echo "tag already exists; choose a new immutable date/suffix and record it"; exit 1; } || true
git tag -a "$TAG" -m "R45 capability projection checkpoint"
git push origin refactor/realizer-v2-r45
git push origin "$TAG"
```

Never reuse or force-update the tag name. If the date/name already exists, choose a new suffix.

- [ ] **Step 4: Restore the tagged source into a clean directory and replay**

Use a new destination. Re-run:

```text
fixed512 reachability
root/package replay with different order/hashseed
capability audit
```

The restored source must reproduce canonical rows/records/pairs and capability result bytes, excluding only checkout-specific Git metadata/environment paths explicitly documented in the receipt.

- [ ] **Step 5: Write `r45_handoff.md` with measured facts**

The handoff must contain these sections:

```markdown
# R45 handoff

## Verdict
READY_FOR_R46 | BLOCKED_CAPABILITY_MODEL | REJECTED_REGRESSION

## Source identities
branch, commit, tree/source hash, tag, registry

## Preservation
ordinary 11/512, 3 families, 501 fallback, prior successes, protected inputs

## Provenance separation
R44 Scene source-bound count -> R45 Scene source-bound count
grammar-known / grammar-unknown counts

## Capability measurement
unique capabilities
largest groups
top candidates
single-capability upper bounds

## What R45 did not do
no runtime grammar expansion, no formal gates, no scheduler, no N2.8

## R46 boundary
exact top capability classes to investigate one at a time, or explanation of why the model remains blocked

## Reproduce
commands and compact receipt locations
```

Do not list a seed allowlist as the R46 implementation contract.

- [ ] **Step 6: Update `CURRENT_STATUS.md` and task ledger**

For `READY_FOR_R46`, state that ordinary Realizer v2 is still 11/512 and R46 is a bounded runtime capability wave.

For `BLOCKED_CAPABILITY_MODEL`, state that grouping/provenance diagnostics improved but no runtime work is justified yet.

Formal evaluation remains `NOT_RUN` in both cases.

- [ ] **Step 7: Final self-check and commit**

Run:

```bash
git diff --check
git status --short --branch
```

Then:

```bash
git add CURRENT_STATUS.md docs/diversity_refactor/r45_handoff.md \
        docs/diversity_refactor/r45_progress.md \
        docs/diversity_refactor/comparison_sources/r45/registry.json
git commit -m "docs: hand off R45 capability checkpoint"
```

If the tag was created before the final handoff-doc commit, do not move it. Either keep the tag explicitly scoped to the source checkpoint and record the later documentation commit separately, or create a new immutable documentation-complete tag with a different name. Never force-update an existing tag.

**Acceptance R45-06:**

- Exact final verdict is reproducible from tracked compact receipts plus regenerated fixed512 artifacts.
- R44 tags remain intact.
- Runtime authorization files remain unchanged relative to R44.
- Ordinary output/context remains 11/512, 3 families, 501 fallback and byte-compatible.
- R45 handoff defines the next action without lowering safety or coverage gates.

---

# Required R45 State Machine

Codex must follow this state machine and must not skip forward:

```text
R45-00 PASS
   |
   v
R45-01 PASS
   |
   v
R45-02 PASS
   |
   v
R45-03 PASS -------------------------> REJECTED_REGRESSION if ordinary/proof parity fails
   |
   +--> no provenance gain -> R45-05 assigns BLOCKED_CAPABILITY_MODEL
   |
   v
R45-04 PASS
   |
   +--> no >=4-seed reusable capability -> R45-05 assigns BLOCKED_CAPABILITY_MODEL
   |
   v
R45-05 READY_FOR_R46 or BLOCKED_CAPABILITY_MODEL
   |
   v
R45-06 recoverable handoff
```

A failure in Scene source separation that does not regress runtime but yields no provenance increase is `BLOCKED_CAPABILITY_MODEL`; proceed only through verdict/handoff documentation and do not continue to runtime grammar work.

---

# Verification Matrix

Every R45 final candidate must satisfy all rows below.

| Concern | Required evidence |
|---|---|
| Ordinary behavior | fixed512 canonical `normal-pairs.jsonl` byte-identical to R45-00/R44 |
| Ordinary v2 count | exactly 11/512 during R45 |
| Ordinary families | exactly 3 during R45 |
| Fallback | exactly 501 during R45 |
| Existing forced proof | all 6 real-input families retained |
| Blocker taxonomy | colon canonical + legacy dot compatibility tests |
| Capability privacy | no prompt/action/scene text or seed in identity |
| Capability independence | unrelated domain differences do not split another domain capability |
| Scene provenance | source-bound grammar-unknown represented distinctly |
| Fail-closed proof | grammar UNKNOWN never grants FamilyProof eligibility |
| Distinct seed accounting | set-union count separate from seed-family rows |
| Determinism | repeated capability audit canonical outputs byte-identical |
| Import/order/hashseed | root/package replay equivalence |
| Protected V150 data | all baseline hashes unchanged |
| Public API | no Context node I/O/context_json change |
| Dependencies | no new external dependency |
| Formal adoption | NOT_RUN / BLOCKED throughout R45 |

---

# R46 Handoff Contract if R45 Is READY_FOR_R46

R45 must not itself implement the ranked capabilities. Instead, the next plan must choose **one capability class at a time** from the measured R45 ranking.

Each R46 capability task must:

1. define the producer-side structural predicate, not a seed list;
2. write red tests using at least two independent source examples plus adversarial near misses;
3. prove source binding and grammatical fact separately;
4. preserve all old 11 v2 cases and all unaffected fallbacks;
5. run fixed512 immediately after the capability becomes green;
6. accept the capability only if it creates at least four new ordinary v2 applications or demonstrates a needed new ordinary family with multiple independent seeds;
7. re-run capability audit before choosing the next capability;
8. stop after at most three bounded capabilities and reassess the `64/512` + `5 family` development guide;
9. run formal N2.7 evaluation only after the development guide is actually met.

The R46 plan must not convert R45 `example_seeds` into a runtime allowlist.

---

# Final Plan Self-Review Checklist

Before Codex begins implementation, verify this plan against `R45_DESIGN.md`:

- [ ] R44 full signature is preserved rather than weakened.
- [ ] blocker delimiter mismatch is corrected diagnostically only.
- [ ] capability identity is atomic/domain-local and excludes text/seed.
- [ ] Scene source provenance can exist with grammar UNKNOWN.
- [ ] existing FamilyProof remains the authorization authority.
- [ ] no task edits family layout/catalog/Scheduler/runtime bridge.
- [ ] no task changes V150 protected variation data.
- [ ] ordinary runtime is required to remain 11/512 throughout R45.
- [ ] distinct seed counts are separated from seed-family row counts.
- [ ] R46 ranking is an upper-bound development aid, not a permission system.
- [ ] R45 can terminate cleanly as BLOCKED without inventing new packets or lowering gates.
- [ ] formal evaluation is explicitly outside R45.
- [ ] every task contains red/green tests, verification, progress update, and commit boundary.

