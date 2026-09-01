# Variation Target Planner Refactor Specification

Last updated: 2026-09-01

This is the implementation specification for P13 L1-L3. The objective is to
extend `tools/plan_variation_target.py` from a current-repository enumerator into
a deterministic long-horizon projection tool while preserving every existing
default result and test.

## 1. Baseline Contract

The current code path remains authoritative for real repository data:

- `scenario_metrics()` continues to use generated compatibility rows.
- `subject_candidate_deltas()` and `location_candidate_deltas()` continue to
  report only candidates backed by current repository data.
- `build_target_report()` with no new projection input preserves its existing
  fields, values, default target, and action-floor behavior.
- Existing callers do not need to provide a schema or migrate output parsing.

The locked L0 evidence is under
`docs/variation_expansion/experiments/v150-planner-l0/`.

## 2. Refactor Boundary

Add a parallel pure-projection path. Do not mix hypothetical rows into
`build_generated_rows()` and do not create temporary vocabulary data merely to
measure a scenario.

Proposed internal boundaries:

```python
def load_projection_manifest(path: str | Path) -> dict: ...

def validate_projection_scenario(payload: Mapping[str, Any]) -> list[dict]: ...

def project_hypothetical_scenario(
    payload: Mapping[str, Any],
    *,
    baseline: Mapping[str, Any],
) -> dict: ...

def build_projection_report(
    manifest: Mapping[str, Any],
    *,
    target: int,
    baseline: Mapping[str, Any] | None = None,
) -> dict: ...
```

These functions must be deterministic and side-effect free. They cannot write
scope, compatibility, action-pool, result, or source files.

## 3. CLI Compatibility

Keep all current flags and defaults. Add one optional entry point:

```text
--scenario-file <path>
```

Without `--scenario-file`, output remains the legacy/current report. With it,
the report adds a `projection` object and content hashes; current metrics and
current-repository scenarios remain present for comparison.

Do not add separate subject/location/density flags. A versioned scenario file is
reviewable, hashable, and reusable across analysis, review, and promotion.

## 4. Projection Manifest v1

```json
{
  "schema_version": "variation-target-scenarios/v1",
  "stage_id": "V150",
  "baseline_manifest_sha256": "<sha256>",
  "scenarios": [
    {
      "id": "balanced-growth-001",
      "subject_count": 135,
      "location_count": 105,
      "compatibility_density_basis_points": 5600,
      "action_depth_row_distribution": [
        {"actions": 12, "row_share_basis_points": 1500},
        {"actions": 16, "row_share_basis_points": 4500},
        {"actions": 20, "row_share_basis_points": 3000},
        {"actions": 24, "row_share_basis_points": 1000}
      ],
      "subject_utility_groups": ["<group-id>"],
      "location_utility_groups": ["<group-id>"],
      "notes": "<bounded hypothesis>"
    }
  ]
}
```

Counts model distinct canonical utilities, not aliases. Basis points avoid
floating-point drift.

## 5. Deterministic Projection Math

For each scenario:

```text
eligible_pairs = subject_count * location_count
projected_rows = floor(
  eligible_pairs * compatibility_density_basis_points / 10,000
)
```

Allocate projected rows across action-depth buckets using the largest-remainder
method. Ties are resolved by ascending `actions`, making the allocation stable.

```text
projected_base_variations = sum(bucket_rows * bucket.actions)
target_gap = target - projected_base_variations
```

The report must expose eligible pairs, projected rows, realized density after
integer allocation, per-bucket rows/contribution, total variations, delta from
the locked baseline, and target status.

## 6. Validation And Fail-Closed Rules

Reject the complete manifest when:

- schema/stage/scenario IDs are missing or duplicated
- subject or location count is below the current locked baseline
- compatibility density is outside `1..10,000` basis points
- action depth is non-positive or a bucket is duplicated
- row-share basis points do not sum to exactly `10,000`
- a utility group is duplicated within its dimension
- the baseline manifest hash differs from the requested experiment
- an alias-compatible or legacy-only pool is counted as a distinct location
- a quality-excluded pool is promoted without a new locked review hypothesis
- an unknown field would affect projection math

Errors use stable machine-readable codes. No partial scenario report is emitted
as promotion evidence when validation fails.

## 7. Output And Content Addressing

Projection output adds:

```text
schema_version
stage_id
baseline_manifest_sha256
scenario_manifest_sha256
planner_sha256
projection_model_version
hypothetical_scenarios[]
```

Every hash is lowercase SHA-256. Paths are recorded relative to the repository
root. The planner does not promote or mutate data; it creates evidence for the
variation loop.

## 8. L1 Test Contract

Keep current `assets/test_variation_target_planner.py` assertions unchanged and
add focused cases for:

1. default report remains equal to the locked 103,212 baseline
2. a valid mixed scenario produces exact deterministic rows and contributions
3. manifest and scenario order do not change mathematical results
4. largest-remainder ties use ascending action depth
5. shares not totaling 10,000 fail
6. density outside bounds fails
7. duplicate scenario IDs, buckets, and utility groups fail
8. subject/location counts below baseline fail
9. baseline hash drift fails
10. alias-compatible, legacy-only, and unreviewed quality-excluded locations fail
11. repeated runs produce byte-equivalent canonical JSON
12. invalid input never mutates repository source/data files

Property-oriented table tests should cover boundary values without adding a new
dependency.

## 9. L2 Quality Handoff

Projection is only a quantitative pre-screen. A selected scenario must produce a
candidate manifest describing distinct prompt utility and owned data files. Once
candidate data exists, generation and review use the completed G010 baseline in
`docs/prompt_quality/README.md`:

- deterministic 64-control + 16-exploration iteration cohort
- semantic consistency, naturalness, and diversity target/guard checks
- comparison-bound blind review
- three independent 256-seed confirmations
- evidence-bound verification and promotion verdict

Planner success cannot override a prompt-quality rejection.

## 10. L3 Stage Handoff

L3 emits a frozen, non-mutating V150 candidate manifest containing:

- scenario and planner hashes
- exact owned files and proposed additions
- expected contribution by subject/location/action-depth dimension
- excluded aliases and rejected inflation routes
- prompt-quality cohort and policy hashes
- validation, review, and promotion requirements

Only a `PROMOTED` V150 data wave becomes the V250 baseline. V250, V350, and V500
repeat the same contract without skipping or rewriting failed iterations.

## 11. Stop Conditions

- Stop L1 when projection math and validation are regression-locked.
- Stop L2 when one V150 scenario is selected or all are rejected with reasons.
- Stop L3 when a hash-bound candidate manifest is reviewable; do not mutate data
  inside the planner refactor.
- Abort on baseline, policy, cohort, or candidate drift.
