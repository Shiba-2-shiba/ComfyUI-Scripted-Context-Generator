# Variation Candidate L3 Snapshot Contract

Last updated: 2026-09-01

Status: `Materializer and authenticated prompt comparator implemented; shape iteration 004 rejected at COMPARED`

L3 uses `tools/materialize_variation_candidate_snapshot.py` to create separate
baseline and candidate runnable source roots under `assets/results/`. Active
runtime files are never edited.

## Evidence Boundary

The materializer:

- rebuilds its plan from four exact L2 inputs and rejects derived-field drift;
- hashes the complete active source plus runtime extras;
- copies a filtered executable baseline tree;
- materializes candidate compatibility, background, semantic profile, action
  source/runtime, scope, CSV, and deterministic prompt rows only in the candidate
  snapshot;
- permits only the declared file delta;
- rebuilds action pools and compatibility rows inside the candidate child root;
- recomputes realized variation metrics;
- revalidates state, quantitative result, allowlist, hashes, and prompt-generation
  decision from snapshot contents.

Prompt generation is allowed only when the stored manifest validates and both:

```text
state == SNAPSHOT_READY
prompt_generation_allowed == true
```

## Iteration 001 Result

The L2 iteration-002 catalog materialized correctly but did not meet V150:

```text
subjects: 135
locations: 105
compatibility rows: 7,817
candidate pools: 15 × 20 actions
projected base variations: 155,920
realized base variations: 141,984
projection delta: -13,936
target gap: 8,016
state: REJECTED
prompt generation allowed: false
```

The mismatch occurs because the L1 projection applied the candidate 20-action
depth to all projected rows. In materialized data, new-subject rows paired with
existing locations retain those locations' existing 12/16/20 action depths.

`tools/model_variation_candidate_contributions.py` now models those contribution
classes separately and reproduces the isolated snapshot exactly.

No 64+16 prompt artifacts were generated. The next iteration must correct the
contribution model or candidate shape before prompt-quality evaluation.

## Shape Iteration 003

The runtime-equivalent contribution model selected four additional locations:

- `community_theater_backstage`
- `greenhouse_nursery`
- `postal_service_counter`
- `vehicle_repair_garage`

```text
added rows: 410
added base variations: 8,200
estimated total: 150,184
target overshoot: 184
subjects added: 0
```

Independent review approved isolated authoring of 20 location-specific actions
per location. This approval does not authorize active data mutation or promotion.

## Shape Iteration 004

The four approved locations were composed with the prior 15-location catalog,
materialized in an isolated q5 snapshot, and evaluated on the fixed 64-control +
16-exploration cohort. The authenticated comparator recomputes snapshot,
workflow, profile, override, source, run-artifact, replay, metric, issue, and
actual `(location, action)` coverage bindings.

```text
realized base variations: 150,184
candidate subjects: 15 / unseen: 0
candidate locations: 19 / unseen: 8
candidate location-action pools unseen: 13
location entropy: 4.831091 -> 5.242171
repeated n-grams: 12 -> 16
context bytes max: 29,094 -> 30,430
context bytes p95: 28,692.15 -> 29,297.5
prompt quality state: COMPARED
terminal state: REJECTED
promotion ready: false
```

The quantity and diversity target passed, but coverage and three non-regression
guards failed. Blind review and 256-seed confirmation were therefore not run.
Active variation data remains unchanged. The next iteration must improve cohort
coverage and remediate repetition/context size before those downstream gates.

## Coverage Schedule Iteration 005

The next attempt preserved the exact fixed 64+16 cohort and replaced selected
seed search with a hash-bound 19-row diagnostic schedule. It assigned all 15
candidate subjects and 19 locations, used 19 unique direct actions, and proved
that `ContextSource` could select every row from control64.

The full workflow correctly failed the stronger gate:

```text
source rows reachable: 19 / 19
final candidate locations observed: 12 / 19
final candidate action-pool locations observed: 9 / 19
exact scheduled final location-action pairs: 9 / 19
coverage verdict: reject
fixed quality verdict: reject
promotion ready: false
```

`ContextSceneVariator` in full mode can replace the source location and action,
so source-selector reachability is not final workflow coverage. The next
schedule must be planned against complete workflow outcomes and bind actual
final witness pairs. The diagnostic improved repeated n-grams (`12 -> 9`) but
context p95/max still regressed; neither result changes the parent rejection.
After the q6 receipt, CLI exit authority was further hardened to follow only the
fixed quality verdict. Because comparator source is snapshot-bound, the next
attempt must rematerialize before executing another coverage comparison.

## Full-Workflow Coverage Iteration 006

VE-1315 models the complete fixed-cohort path through `ContextSource`,
`ContextCharacterProfile`, and `ContextSceneVariator`. It probes only the locked
64+16 seeds, builds a hash-bound row/slot witness matrix, and finds a
deterministic 19-row assignment without adding seeds or using quality metrics.

```text
fixed seeds: 80 / extra: 0
full-workflow probes: 13,760
valid witnesses: 2,801
matched final locations: 19 / 19
candidate subjects: 15 / 15
final action-pool locations: 19 / 19
exact planned final location-actions: 19 / 19
coverage verdict: pass
fixed quality verdict: reject
promotion ready: false
```

The q9 formal auto-workflow run reproduced all 19 witnesses. Coverage is now a
completed eligibility capability, not quality evidence. Quality remains
rejected because semantic-family repetition rose `3 -> 5`, context maximum rose
`29,094 -> 30,570`, and context p95 rose `28,692.15 -> 28,922.05` bytes.
The schedule is frozen before remediation.

## Guard Remediation Iteration 007

The frozen coverage schedule was retained while debug-only context payloads and
semantic-family tokenization were repaired:

- semantic-family matching now uses token boundaries, removing false positives
  from `overlooking` and plural `sleeves`;
- SceneVariator candidate preview is capped at 24 while retaining total and
  truncated counts;
- duplicated clothing prompt history is removed;
- unselected clothing semantic scores retain compact index/score evidence;
- clothing repetition signatures use a stable SHA-256 digest.

The q13 fixed80 diagnostic reproduced all coverage witnesses and changed zero
cleaned prompts relative to q9:

```text
semantic-family repetition: 3 -> 3
repeated n-grams: 12 -> 10
context max: 27,636 -> 27,624
context p95: 27,077.15 -> 26,679.5
location entropy: 4.831091 -> 5.291360
diagnostic failures: 0
```

This verifies remediation on the selected coverage surface. It remains
non-promotable evidence: fixed quality verdict is still `reject`, and the next
quality validation must use a separately declared non-selected surface.

## Non-Selected Quality Validation Iteration 008

VE-1316 refreshes the 19/19 coverage certificate on current source, then
materializes a separate default 80-row candidate surface with no coverage
schedule. Prior coverage is eligibility evidence only; quality metrics are
recomputed from the declared 64 control records.

```text
surface: default_fixed_64_16 / default_unselected
generation and replay: 64 control + 16 exploration
quality metric scope: control64
location entropy: 4.626124 -> 4.956344
repeated n-grams: 0 -> 0
semantic-family repetition: 2 -> 2
context max: 27,812 -> 27,736
context p95: 27,225.2 -> 26,318.55
quality failures: 0
quality verdict: pass
coverage eligibility: pass
review ready: true
promotion ready: false
```

Default-surface coverage remains informational (8 locations and 8 action-pool
locations unseen); the separately hash-bound current-source certificate proves
19/19 reachability. Automatic validation is complete, but blind review, fresh
3x256 confirmation, and full verification remain required before promotion.

Once those gates pass, VE-1319 owns the active-data mutation. No earlier task
may copy isolated candidate subjects, locations, compatibility, backgrounds, or
action pools into the active source tree. VE-1319 must reproduce the frozen
`150,184` result and emit the terminal promotion/rollback receipt.

## Blind Review Attempt 001

The q19 comparison-bound review used two independent blinded 20-pair lanes.
Hash and lane validation passed, but the aggregate verdict was `reject`:

```text
candidate-only hard-defect observations: 8
unique affected candidate seeds: 5
location/action/object observations: 3
mood/action/garnish observations: 5
blind review verdict: reject
```

VE-1317 remains active for remediation. VE-1318 and VE-1319 are blocked until a
fresh comparison and blind-review attempt pass; attempt-001 votes cannot be
reused.
