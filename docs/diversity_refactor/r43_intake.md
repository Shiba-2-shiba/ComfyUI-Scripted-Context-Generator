# R43-00 — Intake and baseline preservation

State: PASS (intake acceptance only, 2026-09-11 JST).

Execution contract: [the supplied implementation plan](./r43_implementation_plan.md),
copied byte-for-byte from the user's original document.
This first task changes documentation and external evidence only.

## Pre-edit cleanup plan

1. Preserve the clean `refactor/realizer-v2` worktree at
   `9a2aa32c1e3a48d1d7ea51eb91aee42843dba021`, candidate07 and stable main
   comparison sources, and inventory existing user changes in the main checkout.
2. Bind source manifests, protected V150 data, public signatures, the A1.6 lock,
   historical evidence and collected test IDs to explicit hashes.
3. Run existing focused tests without exclusions, related regressions and the
   existing validators. Record known failures without changing assertions.
4. Document the actual Builder transport boundary for each producer and the
   distinction between runtime proof, audit-only replay and unavailable input.
5. Verify preservation and record acceptance before starting R43-01.

Boundary defects and duplicated family decisions are later R43 tasks. No runtime
cleanup, new dependency, vocabulary expansion or formal evaluation is part of
this intake. Existing success/fallback behavior will be locked before those edits.

Adoption: BLOCKED. N2.8 and D3 remain unstarted; no merge or push to main.

## Source and preservation

The initial working directory was stable `main`, HEAD
`10d7d8dd6a6dd006f7269bf09aedc5e3624f5c51`. The existing development worktree is
`assets/results/candidate-branch-migration/worktree` beneath that checkout.
All tracked documentation changes in this task belong to that worktree's
`refactor/realizer-v2` branch, not main. No branch switch/reset/clean was needed.
Git ownership required command-scoped `-c safe.directory=<worktree>`; no global
Git configuration was changed.

Development HEAD was `9a2aa32c1e3a48d1d7ea51eb91aee42843dba021`, exactly the
design baseline, and its worktree was clean before intake. The difference from
candidate07 commit `24bbbfbfb7ef7a66d2997f47149d870dfb84e79a` is confined to
`CURRENT_STATUS.md`, `README.md`, and `docs/diversity_refactor/development_branch.md`.
There are no newer runtime changes to reconcile.

The original main checkout's untracked files were inventoried and remain intact:
`.omx/notepad.md`, `.omx/state/ralph-state.json`, `.omx/state/v150-resume.json`, and
`docs/SCG_R4_3_Codex_Implementation_Plan.md`. Existing mode-state files were not
treated as a request to resume their unrelated tasks.

Evidence root (relative to the original main checkout):
`assets/results/diversity_refactor/r43/intake-20260911-01/`.
This is ignored local evidence, not a portable tracked artifact. Retain this
directory and the original historical evidence when moving the experiment.
The tracked `r43_intake_summary.json` inventories receipt hashes.

Three fresh Git archives and extracted read-only source trees were saved:

| Comparison | Commit | Prompt-quality source-tree SHA-256 |
|---|---|---|
| candidate07 | `24bbbfbfb7ef7a66d2997f47149d870dfb84e79a` | `b8a99c2fa84cc59e2ade7378d6614527a3bfe672d42e474d0dbaca6078c57472` |
| R43 actual start | `9a2aa32c1e3a48d1d7ea51eb91aee42843dba021` | `b8a99c2fa84cc59e2ade7378d6614527a3bfe672d42e474d0dbaca6078c57472` |
| stable main | `10d7d8dd6a6dd006f7269bf09aedc5e3624f5c51` | `01f94274e237597b032f708dd246066b66ee8660bb58d1dbdf7ac159c12b45ba` |

Both candidate snapshots contain the same 580 manifest entries as the live
development source. Stable main contains 551. Git tree IDs, archive hashes,
absolute paths and counts are in `baseline-identity.json`; full entry hashes are
in the corresponding manifests. Runtime/data manifests were unchanged after
verification. Git trees and prompt-quality manifests use different scopes and
hash algorithms; these identities are not interchangeable.

All 120 protected V150 files match stable main, including the compatibility CSV
which the prompt-quality source manifest deliberately omits. Fresh sizing:
135 subjects, 109 locations, 8,227 compatibility rows, 150,184 base variations.
`public-signatures.json` captures source/AST signatures;
`public-runtime-contract.json` captures actual public node input/return contracts,
function signatures and default ActionFrame/ContentPlan/PromptContext serialization.

## A1.6 and available historical baselines

The complete section 7 lock remains byte-equivalent after UTF-8 newline
normalization: `A1.6-2026-09-06/v1`, SHA-256
`6742b1b735de2e3ef9b53b732e51d54d260434a500ab84f32249334c24cfb7bd`.
No threshold, missing-value rule, normalizer or family mapping was changed.

Fresh hash checks verified the following **historical artifacts**, without
rerunning their measurements:

| Evidence | Availability / integrity |
|---|---|
| Original pre-N2 V150 source | All 1,120 files in `v150-before-n2/baseline-root` match `snapshot-manifest.json`; sealed ZIP and manifest match their archive receipt |
| Original A1.5 gate and replay | Both match `6c6bef1911ba9b9921f62b0f64adf4172ced2f9e32b0e4922cdd226e6267f733` |
| Original 8,192 reference | Matches `6de5aa646d40882ff52291d2b1b9ad86ef94785353001da9943928b21d4cd207` |
| Historical V150 paired2,048/fixed80 | All eight files referenced by candidate03's `baseline-reuse.json` match in `n27-candidate-02/evaluation/baseline` |
| candidate07 development | All artifacts referenced by `verdict.json` match, including intake512 observations and receipts |
| Fixed development intake512 | `n27-candidate-03/intake-cases.json` matches `413112343e5624820e632a2d538f22f771b666f72d7b56b447d02a103479375b` |

Original V150 formal baseline evidence is therefore **present locally**; it was
not reconstructed from stable main or guessed from old prose. Availability/hash
integrity is not a new source-bound formal comparison. A1.5 audit source hash
`448e4240b6f8321e1ba9332f9f624b7bf9419d255f715f438fd87b13dd556214`
uses the audit's source definition, not the prompt-quality manifest definition.

Historical candidate07 execution: 9/512 actual v2 applications, with family counts
scene-lead 1, standalone scene 7, subject-scene-action 1; four observed structure
names **including fallback**. R43-00 does not newly measure any of those counts.
The R43 candidate's reference8192, gate2048, fixed80 and release8192 are NOT_RUN.
Presence of old fixed80 files supplies no current candidate quality score.

Foundation work can proceed using the saved candidate07 baseline and unchanged
development cohort. If these ignored historical artifacts are absent elsewhere,
formal comparison must be BLOCKED until their exact sources/receipts are restored.
The checkpoint archive alone is not a complete substitute for original V150
formal evidence. Adoption also remains BLOCKED here because R43 family/runtime
evidence and candidate formal comparison have not been produced.

## Builder transport audit

References below are to this branch's source at the start HEAD.
Public Builder inputs are `template`, `composition_mode`, `seed`, `context_json`
(`nodes_context.py:250`). The node returns only prompt (`:269`); its internal
updated context is not an upstream public output. Current `producer_context`
contains only `character_palette` (`pipeline/prompt_orchestrator.py:93`). Other
received history is accessible to the orchestrator but is not yet wired into
the candidate bridge.

`execution_trace[].inputs` records each node's actual kwargs after seed/widget
resolution and overrides (`tools/workflow_prompt_runner.py:543`, `:586`). It can
include prior context and settings absent from Builder input. It does not contain
source bytes or producer-internal part traces. `node_outputs` is a separate runner
return value, omitted by `build_canonical_record()` (`:634`, `:670`). Even audit
replay needs a fixed source/config. History consists of appended DebugInfo, not
complete prior context snapshots (`core/context_ops.py:89`); current `ctx.seed`
cannot stand in for every upstream node seed.

| Domain | Runtime fields actually available | Audit-only additional input / runtime missing input | Permitted reconstruction boundary |
|---|---|---|---|
| Action | Current action; matching `extras.action_frame.legacy_text/legacy_slots`; SceneVariator history seed/slots/frame/selection (`core/context_state.py:76`, `pipeline/context_pipeline.py:460`) | Runner has pre-SceneVariator context, seed and variation_mode. Complete generation needs historical state/config; renderer activity-first mode is not stored | Shared `_render_action_parts()` replay must match text and unique part attribution; existing evidence tries both rendering modes and rejects ambiguous traces (`pipeline/action_renderer.py:17`, `pipeline/v2_structural_evidence.py:28`). Parser-derived slots alone do not prove producer origin; grammatical subject/owner remain separate |
| Clothing | `extras.clothing_prompt/raw_costume_key`, costume, palette; history seed/theme/type/pack/variant/outerwear/signature/attempt and diagnostics (`pipeline/clothing_builder.py:121`, `pipeline/clothing_candidate_renderer.py:248`, `:329`) | Runner has original outfit_mode, outerwear_chance, seed and input context/palette/location/action/history. The two settings and original full state are not preserved in history | Compatible history may narrow pack/type; ordered source parts and current text must reconstruct uniquely. A lowercased signature is not a text binding (`pipeline/clothing_candidate_renderer.py:90`). Detail/outerwear ownership and grammar need separate proof; seed+pack+attempt do not establish exact generation replay |
| Scene | `extras.location_prompt/raw_loc_tag`, loc; LocationExpander seed/pack/objects/selected_props/template_key and conditional semantic choices (`pipeline/location_builder.py:163`, `:226`, `:247`, `:456`) | Runner has mode, lighting_mode, seed and original context/action/mood/recent_objects. History lacks lighting_mode and may lack full selected parts/shuffle order; subsequent mood can change | Bind selected pack/props and complete emitted constituent order, including joins, shuffle, dedupe and sanitization (`:290`, `:321`, `:428`). Normal template_key can identify simple/detailed mode; it cannot restore all settings. Source membership cannot authorize nominal grammar or movement |
| Template | Builder's current args/content/history; selected intro/body/end entries inside this call (`prompt_renderer.py:783`, `:797`, `:834`, `:850`) | Runner adds node ID/control context, but no missing producer input is needed for current selection with fixed source/config | Bind current entry key and exact text/topology, accounting for attention-suffix preprocessing (`:837`). Past Builder history is not current-entry evidence. Existing constructor only recognizes direct or owned-finite scene topologies (`pipeline/v2_template_provenance.py:22`) |
| Subject | subj; extras selected character name/ID, hair/eye color, personality, palette, source_subj_key (`nodes_context.py:130`) | Runner has requested profile mode/name/seed and original context. Dedicated selection history and hair_style extra are absent | Selected identity can bind to source and the same pure subject constructor only if current subj matches (`pipeline/character_profile_pipeline.py:76`, `:95`, `:102`). Current bounded text matcher (`pipeline/v2_direct_provenance.py:84`) does not itself bind a selected profile |
| Garnish | `extras.garnish`; history seed/final_tags/emotion diagnostics/stimulus_role/context_role, current personality and raw_mood_key (`pipeline/context_pipeline.py:531`, `vocab/garnish/logic.py:768`, `:933`) | Runner has original max_items/emotion_nuance/seed/context. Diagnostics do not uniquely recover requested nuance or prior state | Require exact ordered final_tags join, then source/rule and ownership proof per tag. A subject_only diagnostic label is not English grammar evidence; retain conservative behavior where proof is missing |
| Mood | meta.mood, extras raw_mood_key/staging_tags. MoodExpander appends no history (`pipeline/mood_builder.py:188`) | Runner has original json_path/default_value/seed/context. Runtime lacks original node settings; retained raw_mood_key can predate a repeated expansion | Bind only an identifiable actual source/key/description and staging composition. Do not assume default mood_map.json when custom json_path is unknown, or infer grammar from source membership |

Only evidence closed over the received context/history and this Builder invocation
is `runtime_proof`. Replay requiring runner inputs is `audit_only_replay`; otherwise
record `unavailable`. None of the latter two can increase runtime eligible counts.
No global cache, extra serialized metadata or implicit trace transport is proposed.

Future scope, not modifications made by this intake: R43-04 may share a private
constructor in `clothing_candidate_renderer.py`; any `clothing_builder.py` change
must be limited to transient internal plumbing. R43-06 may extract the existing
subject assembly from `character_profile_pipeline.py` into a pure shared
constructor. No new profile/clothing history fields or public I/O are authorized
as a shortcut around missing historical inputs.

## Fresh verification and test-set boundary

Commands, cwd, exit status, timing, log path and log SHA-256 are in `commands.json`.
The existing Python environment was used; no dependency was installed.

| Check | Result |
|---|---|
| Sorted `assets/test_n27*.py` + selector + prompt_realizer_v2 collection | 152 test IDs; collection exit 0; IDs and canonical hash retained |
| Same focused group, **no exclusions** | 151 passed, 1 failed; 1,888 subtests passed; exit 1 |
| context codec/state adapter/nodes/ops + vocabulary lint | 29 tests passed; exit 0 |
| calc_variations, prompt-data, variation-scope, action-pool/compatibility generation checks | All exit 0; V150 counts unchanged, no validation errors/warnings |
| Asset validation and full flow | Empty issue list / PASS; exit 0 |
| Typecheck | NOT_CONFIGURED; no new checker installed |
| Full suite, frontend/browser, formal gates | NOT_RUN |

The failing ID is
`assets/test_prompt_realizer_v2.py::TestRealizerBuilderDebug::test_actual_v1_family_metadata_and_seed_replay`.
It expects old v1 aliases while the candidate bridge reports mapped structure names:
`single-sentence-scene-tail` vs `subject_action_scene`, and
`two-sentence-scene-tail` vs `subject_action__scene_tail`. This reproduces the
documented R43-01 issue. It was not skipped, marked expected failure, or repaired
within this documentation-only intake. These results are not an all-tests PASS.

The branch-native historical group was 151 passed + one deselected + 1,888 subtests.
The current group includes that previously excluded ID and reproduces its failure.
The older candidate07 checkpoint reports 160 passed + one deselected + 1,890
subtests; its aggregate log does not identify the exact additional nine test IDs
and two subtests. Do not infer identical collection from either aggregate count.
This intake retains the full current collection; the historical exact set delta
remains unavailable, rather than being filled with guessed IDs.

## Acceptance and next task

- [x] Start source and existing user changes preserved; fresh read-only comparison snapshots exist.
- [x] Historical observations and new verification are explicitly distinguished.
- [x] Runtime/audit-only/missing fields are documented for all seven domains.
- [x] Original V150 formal baseline availability checked against recorded hashes.
- [x] Foundation work and formal-comparison blockers are separated.

R43-00 acceptance is PASS. Architecture/development implementation status remains
NOT_RUN and adoption remains BLOCKED. The inherited focused-test failure is an
explicit input to R43-01, not an intake-source preservation failure.

Next task: **R43-01** — lock root/package import, independent checkout identity,
and separate low-level v1 aliases from bridge metadata; then add the minimal
verification entry point. Preserve raw/cleaned text, public I/O and family mapping.
The saved start source supports the later fixed512 parity check; no newly measured
paired512 preservation or six-family runtime gain is claimed in this intake.
