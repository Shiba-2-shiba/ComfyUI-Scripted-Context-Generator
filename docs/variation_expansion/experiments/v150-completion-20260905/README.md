# Prospective V150 completion candidate

This is a new authoring preparation from the current tracked iteration-019 inputs,
not a reconstruction of missing historical runtime evidence. `preparation.json`
records the actual source bytes and recursively rebound copies in `authoring/`.
`baseline-manifest.json` explicitly binds the current protected inputs and existing
pool-counting policy. Projection and structural analysis are freshly computed.
No historical review receipt or test fixture is used as production evidence.

The preparation command refuses an existing destination. Reproduce with a new
experiment identity and destination:

```powershell
python tools/prepare_variation_candidate.py --iteration docs/variation_expansion/experiments/v150-candidate-shape-iteration-019/candidate-iteration.json --destination docs/variation_expansion/experiments/<new-id> --experiment-id <new-id>
```

Preparation emits `snapshot-plan.json` with `baseline_prompt_mode: active`.
Immediately before materialization, `build_prepared_snapshot_plan(destination,
quality_contract=...)` rebuilds the plan against current source bytes. It does not
refresh drifted protected baseline data or historical quality evidence. Such drift
requires another prospective preparation. Legacy callers retain synthetic baseline
mode for their existing contracts.

## Compatibility repair

The materializer previously generated compatibility CSV before replacing runtime
prompts with the candidate cohort. Regeneration then lost two prompt-only pairs
(`cyberpunk hacker` / `surveillance_room`, `gothic doll` / `messy_copy_room`) and
changed metadata on 98 other rows. Existing prompt pairs are now copied directly
from the original `prompts.jsonl`, retaining only subject, location and costume,
into candidate scope `compatibility_review_generation.existing_prompt_rows`.
These are authoring inputs, not copies of generated CSV rows. The candidate cohort
is written before CSV generation; its metadata takes precedence, while original
prompt-only pairs remain available. Exclusions continue to apply to both sources.

The isolated exploratory snapshot at `assets/results/v150-completion-active-probe/`
realized exactly **135 subjects / 109 locations / 8,227 rows / 150,184 variations**.
Fresh compatibility regeneration reports zero missing/extra rows or pairs and
no warnings. Candidate data validation reports zero errors and warnings. Candidate
prompts remain the 80-row evaluation cohort; no extra runtime prompt population
was introduced. The baseline preserves all 104 active prompt rows byte-for-byte,
so its source corpus matches promotion preflight. Evaluation still samples its
own 80 output records. Active data was not promoted.

Regression tests first reproduced the missing pair and missing materializer seed
capture, then passed after the repair. Preparation also rejects overwrite and
destinations outside the experiment directory. This probe is preliminary and must
be rematerialized after source freeze; it is not a quality review or promotion.

## Candidate-root test repairs

Full discovery on the first active-baseline probe ran 721 tests and exposed 12
failures plus seven errors. The exact failure log is
`assets/results/v150-completion-active-probe-python.log`.

`authoring-amendment.json` records the subsequent real authoring edits and hashes:
11 subject costumes now use the existing `street_casual` theme instead of the
unresolved `casual` key; two forbidden lighting phrases and one dust-family FX
entry were replaced with concrete setting details. Only prospective copies were
edited, followed by recursive rebinding and fresh structural analysis. The initial
preparation receipt remains the record of the initial copy; the amendment records
the later authoring state. Shape remained exactly 135 / 109 / 8,227 / 150,184 in
`assets/results/v150-completion-authoring-probe/`.

Tests now provide explicit legacy-style and karaoke inputs for those specific
behaviors. Live data integrity checks compare their computed metrics with the
committed scope contract; historical arithmetic/model tests retain an immutable
baseline fixture. Action lint retains an explicit visible-action verb vocabulary,
extended for valid new actions such as reading, folding and latching, with negative
examples rejecting abstract or non-action starts.

The historical 24-seed template regression remains bound to its immutable source
corpus. An additional current-source audit uses a predetermined 80 runs, starting
at seed zero in the original order. The end-template dominance limit remains
0.28, including a negative test for concentrated templates. The unmodified candidate
renderer measured 0.25 at that fixed volume (and 0.2305 in a diagnostic 256-run
measurement); no renderer tuning or seed resampling was applied. This lightweight
audit has no 64+16 cohort API and does not replace formal quality or holdout checks.

The next full candidate run executed 827 tests with only two failures: adding
casual-clothed professions made the named Rin/Zara profiles select `nurse` because
the resolver broke costume-match ties by name length. The existing preferred
archetype mapping now explicitly keeps `street_casual` associated with `street girl`.
A focused regression verifies both stable named-profile resolution and explicit
`source_subj_key="nurse"` precedence. All 20 focused character tests passed.
