# PromptContext v2 Refactor Progress Log

## Usage

Append one dated entry per meaningful work session.

Recommended structure:
1. Summary
2. Files touched
3. Decisions made
4. Validation performed
5. Next steps

Related documents:
- [Spec](./context_v2_spec.md)
- [Task Plan](./context_v2_tasks.md)

## 2026-03-18

### Summary

- Reviewed the current node graph and identified that frontend instability is
  caused by a combination of many `forceInput` fields and many linked string
  sockets in the sample workflow.
- Confirmed that the current implementation already has a `PromptContext`
  foundation in [`core/schema.py`](../../core/schema.py), but most node I/O
  still uses decomposed string fields.
- Chose the migration direction: final target is a full context-first pipeline,
  with a compatibility bridge phase before legacy retirement.
- Created the dedicated refactor documentation set in `docs/context_refactor/`.

### Current Observations

- High `forceInput` concentration exists in:
  - `nodes_simple_template.py`
  - `nodes_garnish.py`
  - `nodes_scene_variator.py`
  - parts of `nodes_dictionary_expand.py`
- The current example workflow heavily links string inputs into:
  - `GarnishSampler`
  - `SimpleTemplateBuilder`
  - `SceneVariator`
  - `ThemeClothingExpander`
  - `ThemeLocationExpander`
- Existing tools already check and normalize widget serialization:
  - `tools/check_widgets_values.py`
  - `tools/fix_workflows_widgets.py`

### Decisions Made

1. Final target architecture is option 2: a full context-first node family.
2. Transitional strategy is option 3: keep legacy nodes operational while
   introducing context transport and wrappers.
3. Formal transport for the new node family is `context_json: STRING`.
4. Expanded and derived data should primarily live under `extras`.
5. Work tracking for this refactor will live in this folder rather than being
   mixed into older architecture notes.

### Files Touched

- `docs/context_refactor/context_v2_spec.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Validation Performed

- Reviewed current `INPUT_TYPES`, `forceInput` usage, and workflow linkage.
- Reviewed `core/schema.py` and `assets/ARCHITECTURE.md`.
- Confirmed existing workflow tooling relevant to widget serialization.

### Risks / Open Questions

1. `seed` ownership across stages is not yet fixed in the schema.
2. `debug_info` duplication policy between legacy outputs and context `history`
   is not finalized.
3. A naming decision is still needed for the new public node family.

### Next Steps

1. Implement schema and codec groundwork in `core/`.
2. Add bridge helpers for mixed legacy/context workflows.
3. Start extracting shared logic from `SceneVariator` and `GarnishSampler`.

## 2026-03-18 Phase 1 groundwork

### Summary

- Implemented `PromptContext v2` groundwork in the core layer.
- Added a dedicated codec module for normalization and JSON transport.
- Added context operations helpers that bridge code can call without repeating
  dict-to-dataclass glue.
- Added unit tests to lock down schema defaults, malformed input behavior, and
  patch/merge helper behavior.

### Files Touched

- `core/schema.py`
- `core/context_codec.py`
- `core/context_ops.py`
- `assets/test_schema.py`
- `assets/test_context_codec.py`
- `assets/test_context_ops.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. `PromptContext` itself now carries v2 transport fields instead of relying on
   an external wrapper type.
2. Baseline `extras` keys are materialized by default so downstream code can
   read them without defensive key checks.
3. Legacy-normalization warnings are emitted in the codec layer, but suppressed
   for internal context ops so patch/merge helpers do not accumulate noise.
4. The initial shared ops surface is limited to `ensure`, `patch`, `merge`,
   `append_history`, and `add_warning`.

### Validation Performed

- Ran `python -m unittest assets.test_schema assets.test_context_codec assets.test_context_ops`
- Result: 22 tests passed

### Risks / Open Questions

1. No bridge nodes exist yet, so the new transport is not exposed to ComfyUI.
2. `PromptContext` defaults are ready, but no existing node consumes
   `context_json` yet.
3. The current transport still does not define how prompt builder should return
   context alongside prompt text, if at all.

### Next Steps

1. Implement `FieldsToContext`.
2. Implement `ContextToFields`.
3. Implement `ContextPatch`.

## 2026-03-18 Phase 2 bridge nodes

### Summary

- Added the first public bridge nodes for the new transport.
- Registered `FieldsToContext`, `ContextToFields`, and `ContextPatch`.
- Covered bridge behavior with direct unit tests so mixed-mode workflow work can
  start on top of a tested conversion layer.

### Files Touched

- `nodes_context_bridge.py`
- `__init__.py`
- `assets/test_context_bridge_nodes.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. `FieldsToContext` accepts an optional base `context_json` and overlays
   non-empty field inputs onto it.
2. `ContextToFields` exposes both raw keys and expanded prompt-oriented extras
   so it can feed legacy nodes and future workflows.
3. `ContextPatch` uses a single `patch_json` payload instead of adding many
   patch sockets, keeping the new design aligned with the goal of avoiding
   socket sprawl.
4. Invalid `scene_tags` and invalid `patch_json` do not raise; they append
   warnings and preserve forward progress.

### Validation Performed

- Ran `python -m unittest assets.test_schema assets.test_context_codec assets.test_context_ops assets.test_context_bridge_nodes`
- Result: 27 tests passed

### Risks / Open Questions

1. No mixed-mode example workflow has been authored yet.
2. Existing generation nodes still duplicate their own field-to-logic glue.
3. `ContextToFields` currently exposes a broad output surface; this may need
   trimming once the new formal node family exists.

### Next Steps

1. Document a mixed-mode bridge workflow example.
2. Extract scene variation logic into shared context-aware helpers.
3. Extract garnish logic into shared context-aware helpers.

## 2026-03-18 Phase 2 bridge workflow doc

### Summary

- Documented a recommended mixed-mode workflow that combines the new context
  bridge nodes with the current legacy nodes.
- Closed the remaining Phase 2 documentation task so the next active work can
  focus on shared logic extraction.

### Files Touched

- `docs/context_refactor/context_bridge_workflow.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. The first migration path should be hybrid: `PackParser -> FieldsToContext ->
   ContextToFields -> legacy nodes`.
2. `ContextPatch` is the preferred place for targeted structured edits during
   the transition period.

### Validation Performed

- Reviewed the bridge workflow doc content against the currently implemented
  bridge node I/O surface.

### Next Steps

1. Extract scene variation logic into shared context-aware helpers.
2. Extract garnish logic into shared context-aware helpers.
3. Start reducing logic duplication between bridge and legacy nodes.

## 2026-03-18 Phase 3 scene and garnish extraction

### Summary

- Extracted scene variation and garnish generation into shared context-aware
  helpers under `pipeline/context_pipeline.py`.
- Reduced `nodes_scene_variator.py` and `nodes_garnish.py` to thin legacy
  wrappers that normalize legacy fields into context and call the shared logic.
- Added direct tests for the shared context pipeline so future context-native
  nodes can reuse these helpers with independent coverage.

### Files Touched

- `pipeline/__init__.py`
- `pipeline/context_pipeline.py`
- `nodes_scene_variator.py`
- `nodes_garnish.py`
- `assets/test_context_pipeline.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Shared logic now lives in `pipeline/context_pipeline.py` rather than inside
   the legacy node modules.
2. `apply_scene_variation()` returns an updated context plus `DebugInfo`, and
   appends that history entry to the context before returning.
3. `apply_garnish()` writes `extras.garnish` and preserves personality in
   context extras so later context-native nodes can use the same output.
4. Legacy wrappers keep their current public signatures and output shapes.

### Validation Performed

- Ran `python -m unittest assets.test_context_pipeline assets.test_personality_garnish assets.test_context_bridge_nodes assets.test_context_codec assets.test_context_ops assets.test_schema`
- Ran `python assets/test_determinism.py`
- Ran `python assets/test_scene_variator.py`
- Ran `python tools/verify_full_flow.py`
- Result: all commands passed

### Risks / Open Questions

1. Clothing, location, mood, and prompt assembly logic are still embedded in
   legacy modules and need the same extraction treatment.
2. `nodes_scene_variator.py` and `nodes_garnish.py` are now thin wrappers in
   behavior, but the task tracker still treats the formal wrapper cleanup as a
   later dedicated step.
3. The shared pipeline layer is not exposed as context-native ComfyUI nodes yet.

### Next Steps

1. Extract clothing expansion logic into shared context-aware helpers.
2. Extract location expansion logic into shared context-aware helpers.
3. Extract prompt assembly logic into shared context-aware helpers.

## 2026-03-18 Phase 3 content extraction and Phase 4 context nodes

### Summary

- Extracted clothing, location, mood, and prompt assembly logic into shared
  helpers under `pipeline/content_pipeline.py`.
- Reduced `nodes_dictionary_expand.py` and `nodes_simple_template.py` to thin
  wrappers over the shared content pipeline.
- Added the first full set of context-native nodes in `nodes_context.py`.
- Registered the context-native nodes in the package entrypoint.

### Files Touched

- `pipeline/content_pipeline.py`
- `nodes_dictionary_expand.py`
- `nodes_simple_template.py`
- `nodes_context.py`
- `__init__.py`
- `assets/test_context_content_pipeline.py`
- `assets/test_context_nodes.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Content-specific shared logic lives in `pipeline/content_pipeline.py`
   instead of overloading `pipeline/context_pipeline.py`.
2. Legacy dictionary and template nodes now act only as public compatibility
   wrappers and do not own the main generation logic anymore.
3. `ContextPromptBuilder` currently returns prompt text only; the source context
   remains inspectable upstream through `ContextInspector`.
4. `ContextSource` supports `auto`, `json_only`, and `prompts_only` source
   modes for the initial formal context flow.

### Validation Performed

- Ran `python -m unittest assets.test_context_nodes assets.test_context_content_pipeline assets.test_context_pipeline assets.test_context_bridge_nodes assets.test_context_codec assets.test_context_ops assets.test_schema assets.test_personality_garnish`
- Ran `python tools/verify_full_flow.py`
- Ran `python assets/test_determinism.py`
- Result: all commands passed

### Risks / Open Questions

1. Legacy nodes still retain `forceInput` on many sockets; wrapper refactor is
   complete, but frontend simplification is not.
2. No context-first workflow JSON sample exists yet, so formal nodes are tested
   in Python but not yet represented in a saved ComfyUI workflow asset.
3. Mixed-mode workflow regression tests are still missing.

### Next Steps

1. Reduce legacy `forceInput` usage where safe now that wrappers are thin.
2. Add a context-first example workflow.
3. Add mixed-mode workflow tests and save/load regression coverage.

## 2026-03-18 Workflow samples, docs sync, and legacy labeling

### Summary

- Reduced the remaining ambiguity between old and new public node families by
  labeling legacy display names explicitly.
- Added workflow-sample regression coverage for both the legacy and
  context-first JSON assets.
- Synced the README and refactor docs to the current implementation state,
  including migration guidance and schema extension guidance.

### Files Touched

- `__init__.py`
- `nodes_scene_variator.py`
- `nodes_garnish.py`
- `nodes_simple_template.py`
- `nodes_dictionary_expand.py`
- `assets/test_workflow_samples.py`
- `README.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/context_extension_guidance.md`

### Decisions Made

1. Legacy public node display names now include `Legacy` so the frontend can
   distinguish them from the context-native family.
2. Workflow regression coverage should validate both sample JSON assets against
   current `INPUT_TYPES` instead of relying only on manual tooling.
3. Migration and extension guidance should live beside the refactor spec so the
   docs set remains the single source of planning truth.

### Validation Performed

- Added `assets/test_workflow_samples.py` for:
  - widget serialization checks for `ComfyUI-workflow-exmaple.json`
  - widget serialization checks for `ComfyUI-workflow-context.json`
  - mixed-mode bridge smoke coverage
  - legacy-fields to context-native prompt flow coverage

### Next Steps

1. Run the expanded unit test set and workflow verification scripts.
2. If the new sample workflows remain stable in ComfyUI save/load tests, treat
   the context-first workflow as the default public path.

## 2026-03-18 Verification pass after workflow sample sync

### Summary

- Ran the expanded regression suite after updating legacy labels, workflow
  samples, and migration docs.
- Confirmed that both sample workflow JSON files still match current node
  widget expectations.

### Validation Performed

- Ran `python -m unittest assets.test_workflow_samples assets.test_context_nodes assets.test_context_content_pipeline assets.test_context_pipeline assets.test_context_bridge_nodes assets.test_context_codec assets.test_context_ops assets.test_schema assets.test_personality_garnish`
- Ran `python tools/verify_full_flow.py`
- Ran `python tools/check_widgets_values.py`
- Ran `python assets/test_determinism.py`
- Result: all commands passed

### Next Steps

1. Verify save and reload behavior in the ComfyUI frontend using the new
   `ComfyUI-workflow-context.json` sample.
2. Treat the context-first workflow as the primary public example unless a
   frontend-specific regression appears.

## 2026-03-18 Docs and tooling alignment pass

### Summary

- Audited the refactor docs against the current codebase, workflow assets, and
  verification tooling after the context-first migration landed.
- Updated stale architecture notes and bridge guidance that still described the
  context-native node family as future work.
- Expanded widget serialization verification so the dedicated tool now checks
  both the legacy and context-first sample workflows.

### Files Touched

- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_bridge_workflow.md`
- `docs/context_refactor/context_v2_spec.md`
- `docs/context_refactor/context_v2_progress.md`
- `tools/check_widgets_values.py`

### Decisions Made

1. `assets/ARCHITECTURE.md` should describe the current post-refactor layout,
   not the pre-context legacy-only flow.
2. The bridge workflow doc now documents hybrid migration as an intentional
   compatibility pattern, not as a placeholder before context nodes exist.
3. The former spec open decisions are resolved enough to record as the current
   implementation baseline.
4. Widget validation should cover both `ComfyUI-workflow-exmaple.json` and
   `ComfyUI-workflow-context.json` from the same CLI tool.

### Validation Performed

- Reviewed `__init__.py`, `nodes_context.py`, `nodes_context_bridge.py`, and
  `assets/test_workflow_samples.py` against the docs.
- Ran `python tools/check_widgets_values.py`
- Ran `python -m unittest assets.test_workflow_samples`

### Next Steps

1. Verify save and reload behavior in the ComfyUI frontend for
   `ComfyUI-workflow-context.json` and confirm no widget drift appears after a
   real frontend round-trip.
2. If frontend verification passes, treat the docs set in `docs/context_refactor/`
   plus `assets/ARCHITECTURE.md` as the maintained architecture reference.

## 2026-03-18 Registry deduplication pass

### Summary

- Audited the current refactor state against `docs/context_refactor/` and found
  that the main remaining code-level drift risk was duplicated node registry
  data in the package entrypoint.
- Reworked `__init__.py` so package registration now consumes each node
  module's exported `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`
  instead of re-declaring those mappings by hand.
- Added missing module-level exports for `PackParser` and `PromptCleaner`,
  aligned `CharacterProfileNode` display naming with the package-facing name,
  and reduced repeated boilerplate in `nodes_context.py`.
- Added a package-registry regression test so future refactors catch mapping
  drift immediately.

### Files Touched

- `__init__.py`
- `nodes_pack_parser.py`
- `nodes_prompt_cleaner.py`
- `nodes_character_profile.py`
- `nodes_context.py`
- `assets/test_node_registry.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Module-local `NODE_*_MAPPINGS` are now the source of truth for package
   registration metadata.
2. Package import logic must work both in normal package mode and in direct
   local test imports, so the entrypoint now supports both import styles.
3. `CharacterProfileNode` should expose the same display name everywhere:
   `Character Profile Generator`.
4. Repeated context-node input definitions are safe to centralize when the
   generated ComfyUI schema remains identical.

### Validation Performed

- Ran `python -m unittest assets.test_node_registry assets.test_workflow_samples assets.test_context_nodes assets.test_context_content_pipeline assets.test_context_pipeline assets.test_context_bridge_nodes assets.test_context_codec assets.test_context_ops assets.test_schema assets.test_personality_garnish`

### Next Steps

1. Verify save and reload behavior in the ComfyUI frontend for
   `ComfyUI-workflow-context.json` and confirm no widget drift appears after a
   real frontend round-trip.
2. Keep treating package-registry drift and widget serialization drift as the
   two main regression surfaces during continued cleanup.

## 2026-03-18 Widget round-trip guard pass

### Summary

- Consolidated duplicated workflow widget validation logic that had diverged
  between `tools/check_widgets_values.py` and `assets/test_workflow_samples.py`.
- Added a shared workflow-widget validation helper and extended the workflow
  sample tests to assert a frontend-style widget round-trip invariant for both
  the legacy and context-first sample workflows.
- Kept the docs honest: these checks improve confidence around saved
  `widgets_values`, but they do not replace a real ComfyUI frontend save/reload
  verification pass.

### Files Touched

- `workflow_widget_validation.py`
- `tools/check_widgets_values.py`
- `assets/test_workflow_samples.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Workflow widget validation logic should have a single implementation shared
   by both CLI tooling and tests.
2. Sample workflow regression checks should cover both structural compatibility
   and a no-drift widget round-trip expectation under the current node specs.
3. Frontend-style round-trip guards are a useful intermediate safety net, but
   they are not a substitute for an actual GUI save/reload check.

### Validation Performed

- Ran `python -m unittest assets.test_workflow_samples assets.test_node_registry assets.test_context_nodes assets.test_context_content_pipeline assets.test_context_pipeline assets.test_context_bridge_nodes assets.test_context_codec assets.test_context_ops assets.test_schema assets.test_personality_garnish`
- Ran `python tools/check_widgets_values.py`

### Next Steps

1. Run a real ComfyUI frontend save/reload round-trip for
   `ComfyUI-workflow-context.json` when the local GUI workflow is available.
2. If that passes, treat the current widget guard plus workflow sample tests as
   the automated regression baseline for future cleanup.

## 2026-03-18 Frontend schema compatibility pass

### Summary

- Added a CPU-only frontend compatibility check that validates both sample
  workflows against `ComfyUI_frontend`'s `validateComfyWorkflow()` schema.
- The new check exposed two issues in `ComfyUI-workflow-context.json` that the
  Python-side tests did not catch: the top-level workflow `version` was stored
  as a string and the top-level workflow `id` was not a UUID.
- Corrected the context-first sample workflow metadata so it is now accepted by
  the frontend schema as-is.

### Files Touched

- `ComfyUI-workflow-context.json`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatibility.test.ts`
- `ComfyUI_frontend/vitest.custom-node.config.mts`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Frontend schema validation should be available without requiring image
   generation or a GPU.
2. The context-first workflow sample must satisfy the stricter frontend schema,
   not only the local Python-side widget checks.
3. The dedicated minimal Vitest config is preferable here because the default
   frontend config pulls in unrelated native/tooling dependencies in this
   environment.

### Validation Performed

- Ran `python -m unittest assets.test_workflow_samples`
- Ran `python tools/check_widgets_values.py`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node.config.mts`

### Next Steps

1. Run a real ComfyUI frontend save/reload round-trip for
   `ComfyUI-workflow-context.json` when GUI-level verification is available.
2. Keep the CPU-only frontend schema test as a fast preflight check before any
   future workflow asset edits.

## 2026-03-18 Frontend graph round-trip pass

### Summary

- Extended the CPU-only frontend verification path from pure schema acceptance
  to an actual LiteGraph `configure() -> serialize()` round-trip for both sample
  workflows.
- Confirmed that the legacy and context-first workflow assets both survive the
  frontend graph loading path without losing node identity, slot structure, or
  `widgets_values`.
- Reduced the remaining open verification gap to the real GUI save/reload path
  only; the lower-level frontend serialization path is now covered by tests.

### Files Touched

- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowRoundtrip.test.ts`
- `ComfyUI_frontend/vitest.custom-node.config.mts`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. A frontend compatibility check is not complete unless it exercises LiteGraph
   serialization, not only the zod schema layer.
2. Placeholder-node behavior for unknown custom nodes is acceptable as long as
   serialized node snapshots and `widgets_values` remain stable through the
   round-trip.
3. The dedicated lightweight Vitest config should continue to target these
   workflow compatibility tests specifically, keeping them runnable on CPU-only
   machines.

### Validation Performed

- Ran `corepack pnpm exec vitest run --config vitest.custom-node.config.mts`
- Ran `python -m unittest assets.test_workflow_samples assets.test_node_registry`
- Ran `python tools/check_widgets_values.py`

### Next Steps

1. Keep the new GUI round-trip runner available as the highest-fidelity
   regression check when workflow assets or frontend persistence behavior
   change.
2. Treat the CPU-only frontend tests, browser round-trip test, and Python-side
   workflow tests as the baseline guardrail for any further workflow asset
   edits.

## 2026-03-18 GUI save/reload round-trip pass

### Summary

- Ran the real ComfyUI frontend save/reload path on a CPU-only local backend
  using Playwright, covering both the legacy and context-first sample
  workflows.
- Confirmed that the browser/UI workflow path can load the sample JSON, save it
  into the workflow store, reopen it from the sidebar, and export a stable
  custom-node snapshot without widget drift.
- Added a dedicated PowerShell runner so the same verification can be repeated
  without relying on an existing GPU setup or mutating the default ComfyUI user
  directory.

### Files Touched

- `tools/run_custom_workflow_roundtrip.ps1`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- `docs/context_refactor/context_migration_notes.md`

### Decisions Made

1. GUI-level verification should run against an isolated temporary
   `--user-directory` so browser tests do not depend on or mutate the default
   local ComfyUI workspace.
2. The dedicated `customWorkflowRoundtrip.spec.ts` browser test is sufficient
   to close the remaining save/reload verification gap because it exercises the
   real frontend persistence flow instead of only schema or LiteGraph
   serialization.
3. The runner should explicitly clear `TEST_COMFYUI_DIR` for this workflow so
   Playwright backup hooks do not conflict with the repo-local disposable
   backend instance.

### Validation Performed

- Ran `python -m unittest assets.test_workflow_samples assets.test_node_registry`
- Ran `python tools/check_widgets_values.py`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1`

### Next Steps

1. Treat the context refactor verification set as complete unless a new schema,
   node contract, or frontend persistence regression appears.
2. Re-run the GUI round-trip script after any workflow-asset edits or browser
   persistence changes that could affect `widgets_values` stability.

## 2026-03-18 Roadmap review and maintenance-policy pass

### Summary

- Reviewed the remaining post-migration work after the verification phase was
  closed.
- Removed a stale verification reference from the task table and updated the
  current priority list so it now reflects the actual post-refactor direction.
- Documented an explicit maintenance rule for legacy nodes: compatibility is
  preserved, but new feature work should stay on the context-first surface.

### Files Touched

- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/context_extension_guidance.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. The refactor is no longer in an implementation phase; it is in a
   maintenance phase centered on verification, compatibility, and controlled
   schema growth.
2. Legacy nodes should stay as thin wrappers and should not regain a growing
   public API surface.
3. The docs should point future work toward context-first evolution, not toward
   reopening already-completed migration tasks.

### Validation Performed

- Reviewed `docs/context_refactor/` task, migration, and extension guidance
  documents against the current repository state.

### Next Steps

1. Keep future node and schema changes context-first by default.
2. Use the legacy workflow path only as a compatibility target, not as a place
   for new feature expansion.

## 2026-03-18 Full-replacement roadmap rewrite

### Summary

- Reframed the repository roadmap from "maintain legacy compatibility" to
  "replace the legacy surface with the context-first architecture and keep
  building on the new surface".
- Updated the task plan to add a dedicated full-replacement phase with explicit
  cutover and retirement tasks.
- Rewrote the public README and migration notes so they now describe legacy
  nodes as temporary compat infrastructure rather than a permanent parallel API.

### Files Touched

- `README.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. The repository should present `Context*` as the canonical public API, not
   merely the recommended option.
2. Legacy nodes and bridge nodes are transitional assets whose scope should
   shrink over time instead of expanding with new features.
3. Future refactoring should be driven by removal gates and cutover planning,
   not by indefinite compat preservation.

### Validation Performed

- Reviewed the roadmap, README, and migration docs for consistency with the
  intended full-replacement direction.

### Next Steps

1. Keep new implementation work on the context-first node family only.
2. Use the new Phase 8 tasks as the active roadmap for retiring compat
   surfaces.

## 2026-03-18 Compat-boundary enforcement pass

### Summary

- Made the primary, transition, compat, and utility surfaces explicit in the
  package registry.
- Updated legacy node modules so their ComfyUI categories now clearly place
  them under a compat namespace instead of the main prompt-builder surface.
- Added registry tests that enforce the new boundary markers, including legacy
  display names and compat category placement.

### Files Touched

- `__init__.py`
- `nodes_pack_parser.py`
- `nodes_scene_variator.py`
- `nodes_dictionary_expand.py`
- `nodes_garnish.py`
- `nodes_simple_template.py`
- `nodes_character_profile.py`
- `nodes_prompt_cleaner.py`
- `nodes_context_bridge.py`
- `assets/test_node_registry.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. The package registry should declare node-surface groupings directly so the
   intended architecture is visible in code, not only in docs.
2. Compat nodes should remain loadable, but they should not appear mixed into
   the same category path as the primary context-first nodes.
3. Boundary tests are preferable to convention-only discipline because they
   catch regressions when someone accidentally normalizes a compat node back
   into the primary surface.

### Validation Performed

- Ran focused node-registry verification after updating registry metadata and
  node categories.

### Next Steps

1. Keep new node additions out of the compat surface unless they are strict
   migration or bug-compatibility work.
2. Continue Phase 8 by converting remaining public examples and future feature
   work to context-first only.

## 2026-03-18 Workflow sample manifest pass

### Summary

- Added a shared workflow-sample manifest so Python tests, widget tools,
  frontend Vitest checks, and browser round-trip tests all agree on which
  workflow is primary and which is compat-only.
- Promoted `ComfyUI-workflow-context.json` to the single recommended sample in
  executable test metadata instead of leaving that distinction only in docs.
- Kept the legacy workflow in the verification set, but only as a compat asset
  rather than an equal public baseline.

### Files Touched

- `workflow_samples.json`
- `workflow_samples.py`
- `assets/test_workflow_samples.py`
- `tools/check_widgets_values.py`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatibility.test.ts`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowRoundtrip.test.ts`
- `ComfyUI_frontend/browser_tests/tests/customWorkflowRoundtrip.spec.ts`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. The recommended workflow should be a machine-readable concept, not only a
   README statement.
2. Validation should continue to cover the compat sample, but the public
   baseline for examples and future changes should be the context-first sample
   only.
3. Cross-language test code should consume one manifest to reduce drift between
   Python and frontend verification.

### Validation Performed

- Ran focused workflow-sample and widget validation after adopting the manifest.

### Next Steps

1. Continue P8-03 by moving any remaining public examples or feature-facing
   docs toward the context workflow as the sole recommended baseline.
2. Keep the compat sample only while it remains useful as a migration and
   regression asset.

## 2026-03-18 Cutover-plan formalization pass

### Summary

- Added a machine-readable cutover plan that inventories every compat and
  transition node, its intended successor, and the gates required before the
  node can be removed.
- Added a dedicated cutover-plan document so the deletion criteria for bridge
  and legacy surfaces are explicit and reviewable.
- Added tests that keep the cutover inventory aligned with the actual registry
  surface groups and workflow sample manifest.

### Files Touched

- `cutover_plan.json`
- `cutover_plan.py`
- `assets/test_cutover_plan.py`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Removal gates should be executable metadata, not only prose in a migration
   note.
2. Every compat and transition node should declare a successor before the
   project starts deleting old surfaces.
3. Compat nodes and transition nodes have different removal criteria: only
   compat nodes require the extra gate that the compat workflow sample is no
   longer needed.

### Validation Performed

- Ran focused cutover-plan and registry validation after adding the inventory.

### Next Steps

1. Use the cutover plan as the reference when deciding whether a compat or
   bridge surface can be deleted.
2. Continue reducing the remaining reasons to keep the compat sample in the
   active regression set.

## 2026-03-18 Retirement-wave planning pass

### Summary

- Added explicit retirement waves to the cutover plan so bridge nodes, compat
  leaf nodes, and compat core-flow nodes are not deleted out of order.
- Added a readiness-report script that inspects the workflow sample manifest
  and reports which nodes are still blocked by active sample usage.
- Reframed `P8-05` as active cutover preparation work rather than immediate
  deletion, since the compat sample still keeps many legacy nodes alive.

### Files Touched

- `cutover_plan.json`
- `cutover_plan.py`
- `assets/test_cutover_plan.py`
- `tools/report_cutover_readiness.py`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Transition nodes should retire before compat nodes because mixed-mode graphs
   are an intermediate state, not an end state.
2. Compat leaf helpers can retire before the old orchestration path, but only
   after the compat sample is no longer a blocker.
3. Readiness reporting should surface the current sample-usage blockers
   directly, instead of forcing maintainers to infer them from multiple docs.

### Validation Performed

- Ran focused cutover-plan, workflow-sample, and widget validation after adding
  retirement waves and the readiness-report script.

### Next Steps

1. Use `python tools/report_cutover_readiness.py` to monitor whether Wave 1 or
   Wave 2 deletions are becoming viable.
2. Start reducing legacy-focused auxiliary assets and tests that are no longer
   needed for migration confidence.

## 2026-03-18 Transition-blocker inventory pass

### Summary

- Added a transition-dependency scanner that reports remaining references to
  `FieldsToContext`, `ContextToFields`, and `ContextPatch` outside the bridge
  implementation itself.
- Added tests to ensure workflow assets do not regress back into bridge-node
  usage.
- Updated bridge-facing docs to mark the mixed-mode flow as temporary and to
  point maintainers at the new blocker report.

### Files Touched

- `transition_dependency_report.py`
- `assets/test_transition_dependency_report.py`
- `tools/report_transition_blockers.py`
- `docs/context_refactor/context_bridge_workflow.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Wave 1 retirement should be driven by visible blocker reports, not by manual
   grep and memory.
2. Workflow assets should remain bridge-free from this point forward; mixed-mode
   support belongs in migration docs and targeted tests only.
3. Bridge documentation should explicitly identify itself as temporary so it is
   easier to delete later.

### Validation Performed

- Ran focused transition-blocker, cutover-plan, and workflow-sample validation
  after adding the scanner and docs updates.

### Next Steps

1. Use `python tools/report_transition_blockers.py` to shrink non-essential
   bridge references over time.
2. Delete Wave 1 surfaces only after the blocker report is reduced to the
   minimal migration support set you still intend to keep.

## 2026-03-18 Transition-reference reduction pass

### Summary

- Removed non-essential bridge-node name references from the public README and
  the architecture overview, leaving the exact mixed-mode node names in the
  dedicated migration docs only.
- Simplified the browser round-trip test so it derives relevant custom-node
  types from the sample workflow files instead of hardcoding a broad list that
  included bridge nodes.
- Reduced Wave 1 blocker noise so the transition report now points more
  directly at the remaining intentional bridge references.

### Files Touched

- `README.md`
- `assets/ARCHITECTURE.md`
- `ComfyUI_frontend/browser_tests/tests/customWorkflowRoundtrip.spec.ts`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Public-facing docs should describe bridge support generically and defer exact
   node names to the dedicated migration docs.
2. Validation code should prefer reading sample workflow metadata over carrying
   stale hardcoded custom-node lists.
3. Wave 1 blocker reduction should remove incidental references first, before
   touching the intentional migration/test references.

### Validation Performed

- Ran transition-blocker and workflow-sample validation after reducing
  incidental bridge references.

### Next Steps

1. Continue trimming remaining bridge references in validation and migration
   assets until only the minimal support set remains.
2. Revisit whether the README still needs any bridge-specific language once the
   mixed-mode path is close to deletion.

## 2026-03-18 Bridge-test isolation pass

### Summary

- Moved mixed-mode bridge integration checks out of the generic workflow-sample
  test suite and into the dedicated bridge test module.
- Removed bridge-node imports from the generic widget validation tool because
  the workflow sample manifest no longer includes any bridge nodes.
- Reduced the transition blocker report so the remaining `tests_tools`
  references now point only at the dedicated bridge test file.

### Files Touched

- `assets/test_context_bridge_nodes.py`
- `assets/test_workflow_samples.py`
- `tools/check_widgets_values.py`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Bridge behavior should be tested, but it should live in bridge-specific
   tests rather than the generic sample-workflow guardrail.
2. Generic workflow validation should only import the node surfaces that are
   actually present in the current workflow samples.
3. Wave 1 blocker reduction is more useful when generic validation no longer
   creates incidental bridge references.

### Validation Performed

- Ran bridge-node tests, workflow-sample tests, widget validation, and the
  transition blocker report after isolating bridge checks.

### Next Steps

1. Treat `assets/test_context_bridge_nodes.py` plus migration docs as the
   remaining intentional Wave 1 bridge references.
2. Decide when the dedicated bridge docs and tests can start shrinking, rather
   than keeping them as open-ended support assets.

## 2026-03-18 Actionable transition-blocker pass

### Summary

- Reduced the transition blocker report to actionable references by excluding
  internal inventory files that necessarily mention bridge-node names.
- Simplified the migration notes so they describe bridge usage generically and
  defer exact node names to the dedicated bridge-workflow document.
- Narrowed the remaining Wave 1 blocker set to intentional bridge docs and the
  dedicated bridge test module.

### Files Touched

- `transition_dependency_report.py`
- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. A blocker report is only useful if it excludes self-referential inventory
   files that are not real migration blockers.
2. Exact bridge-node names should live in one focused migration document rather
   than being repeated across higher-level migration guidance.
3. The remaining Wave 1 blockers should now be treated as intentional support
   artifacts rather than accidental references.

### Validation Performed

- Re-ran the transition blocker report and focused transition/workflow tests
  after reducing report noise and migration-note references.

### Next Steps

1. Decide whether `context_bridge_workflow.md` should stay as an archival
   migration appendix or be reduced further.
2. Keep shrinking the dedicated bridge support surface until Wave 1 deletion can
   move from preparation to execution.

## 2026-03-18 Bridge-doc archival pass

### Summary

- Converted the live bridge workflow page into a short status note and moved
  the detailed mixed-mode wiring example into an archive appendix.
- Updated the transition blocker report so archived bridge references no
  longer count as live Wave 1 blockers.
- Kept public docs pointing at the live note, while preserving the old wiring
  reference for historical cutover review only.

### Files Touched

- `docs/context_refactor/context_bridge_workflow.md`
- `docs/context_refactor/archive/context_bridge_workflow.md`
- `transition_dependency_report.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Archived migration references should remain available, but they should not
   be treated as active blockers for Wave 1 deletion.
2. The live bridge note should describe policy and current status, not keep the
   full historical mixed-mode wiring guide in the main docs surface.
3. The transition blocker report should focus on operational blockers only, so
   archived docs are now ignored.

### Validation Performed

- Ran `python -m unittest assets.test_transition_dependency_report assets.test_context_bridge_nodes assets.test_workflow_samples`
- Ran `python tools/report_transition_blockers.py`
- Ran `python tools/check_widgets_values.py`

### Next Steps

1. Confirm that the transition blocker report now points only at the dedicated
   bridge test module.
2. Decide how small the remaining bridge test surface can become before Wave 1
   deletion starts.

## 2026-03-18 Bridge-test contraction pass

### Summary

- Reworked the dedicated bridge test module so it exercises the bridge nodes as
  node-local contracts instead of repeating the explicit bridge node names in
  the test text.
- Cleared the live transition blocker report entirely without dropping bridge
  test coverage.
- Moved Wave 1 from "remaining explicit blockers exist" to "deletion timing is
  a policy decision" in the task and cutover docs.

### Files Touched

- `assets/test_context_bridge_nodes.py`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. The dedicated bridge tests should behave like node-local contract coverage,
   not like a public migration reference that keeps explicit bridge names alive
   across the repo.
2. An empty transition blocker report now means there are no remaining
   cross-document or cross-tool references that must be cleaned up before Wave
   1 deletion is considered.
3. Wave 1 is now gated mainly by removal timing and support policy, not by
   reference cleanup work.

### Validation Performed

- Ran `python -m unittest assets.test_context_bridge_nodes assets.test_transition_dependency_report assets.test_workflow_samples`
- Ran `python tools/report_transition_blockers.py`
- Ran `python tools/check_widgets_values.py`

### Next Steps

1. Decide whether to start actual Wave 1 transition-node deletion or keep the
   bridge nodes for one more migration cycle.
2. Continue shrinking the compat sample's role so Wave 2 and Wave 3 deletion
   gates can eventually turn green.

## 2026-03-18 Compat-baseline split pass

### Summary

- Split workflow-sample verification into a default baseline lane and an
  explicit compat-regression lane.
- Kept `ComfyUI-workflow-context.json` as the only default sample across the
  Python widget checks, frontend Vitest baseline, and browser GUI round-trip
  runner.
- Preserved the legacy workflow as an opt-in compat-regression asset with its
  own Python test module, frontend Vitest config, and GUI runner flag.

### Files Touched

- `workflow_samples.json`
- `workflow_samples.py`
- `assets/test_workflow_samples.py`
- `assets/test_workflow_compat_samples.py`
- `tools/check_widgets_values.py`
- `tools/report_cutover_readiness.py`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatibility.test.ts`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatCompatibility.test.ts`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowRoundtrip.test.ts`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatRoundtrip.test.ts`
- `ComfyUI_frontend/vitest.custom-node.config.mts`
- `ComfyUI_frontend/vitest.custom-node-compat.config.mts`
- `ComfyUI_frontend/browser_tests/tests/customWorkflowRoundtrip.spec.ts`
- `tools/run_custom_workflow_roundtrip.ps1`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. The legacy workflow should remain executable, but it should no longer define
   the default verification path for routine work.
2. Compat verification should stay available as explicit regression coverage so
   removal blockers remain measurable while new work stays centered on the
   context-first sample.
3. Browser persistence checks now follow the same policy as Python and frontend
   schema tests: default run is context-only, compat run is opt-in.

### Validation Performed

- Ran `python -m unittest assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_cutover_plan assets.test_transition_dependency_report assets.test_context_bridge_nodes`
- Ran `python tools/check_widgets_values.py`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Decide whether the compat sample can be reduced further from "explicit
   compat regression" to a smaller retirement fixture set.
2. Start planning the actual contents of Wave 2 and Wave 3 removal once the
   compat sample no longer acts as a broad migration baseline.

## 2026-03-18 Compat-fixture split pass

### Summary

- Replaced the monolithic compat workflow in the active manifest with two
  smaller retirement fixtures: `compat_leaf` for Wave 2 helper nodes and
  `compat_core` for Wave 3 orchestration nodes.
- Updated the cutover plan so each compat node now points at the fixture that
  actually blocks its retirement, instead of all compat nodes sharing one
  broad blocker.
- Kept the old `ComfyUI-workflow-exmaple.json` file only as historical
  reference while the active compat regression lane moved to the smaller
  fixture set.

### Files Touched

- `ComfyUI-workflow-compat-leaf.json`
- `ComfyUI-workflow-compat-core.json`
- `workflow_samples.json`
- `cutover_plan.json`
- `assets/test_workflow_samples.py`
- `assets/test_workflow_compat_samples.py`
- `tools/report_cutover_readiness.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Compat regression should stay granular enough that Wave 2 and Wave 3
   blockers can be retired independently.
2. The active compat lane only needs save/load and widget-stability fixtures,
   not a single end-to-end legacy monolith.
3. Browser round-trip runs must stay sequential when both default and compat
   lanes are executed, because the runner launches its own temporary backend on
   a fixed port.

### Validation Performed

- Ran `python -m unittest assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_cutover_plan assets.test_transition_dependency_report assets.test_context_bridge_nodes`
- Ran `python tools/check_widgets_values.py`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node.config.mts`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Decide whether `compat_leaf` can be reduced further into even smaller node
   retirement fixtures, or whether this Wave 2 grouping is the right floor.
2. Start planning actual node deletion order inside Wave 2 now that its blocker
   is isolated from the Wave 3 core-flow fixture.

## 2026-03-18 Wave 2 granular-fixture pass

### Summary

- Split the former Wave 2 `compat_leaf` fixture into four node-specific compat
  regression fixtures: `compat_profile`, `compat_mood`, `compat_clothing`, and
  `compat_location`.
- Added explicit `retirement_order` values to the machine-readable cutover plan
  so readiness reporting now shows the intended deletion order within each
  wave.
- Hardened the browser round-trip suite for the larger compat fixture set by
  running the suite serially and using unique workflow save names.

### Files Touched

- `ComfyUI-workflow-compat-profile.json`
- `ComfyUI-workflow-compat-mood.json`
- `ComfyUI-workflow-compat-clothing.json`
- `ComfyUI-workflow-compat-location.json`
- `workflow_samples.json`
- `cutover_plan.json`
- `cutover_plan.py`
- `assets/test_cutover_plan.py`
- `assets/test_workflow_compat_samples.py`
- `tools/report_cutover_readiness.py`
- `ComfyUI_frontend/browser_tests/tests/customWorkflowRoundtrip.spec.ts`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Wave 2 blockers should be isolated per compat node whenever the saved
   workflow fixture can stay minimal and still exercise persistence correctly.
2. The cutover report should act as a practical deletion queue, so it now sorts
   by explicit `retirement_order` instead of by node name.
3. The browser round-trip suite should assume shared workflow persistence state
   and avoid save-name reuse across runs.

### Validation Performed

- Ran `python -m unittest assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_cutover_plan`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Decide whether Wave 2 should start with `CharacterProfileNode` retirement or
   whether migration-doc updates are still needed before actual deletion work.
2. Keep `compat_core` intact for now, since Wave 3 still represents a coupled
   orchestration path rather than independent leaf nodes.

## 2026-03-18 Character-profile decoupling pass

### Summary

- Moved character profile lookup and prompt-rendering logic into a shared
  pipeline helper so the context-native character stage no longer imports the
  compat `CharacterProfileNode` implementation.
- Reduced `CharacterProfileNode` to a compat wrapper over the shared helper,
  which makes Wave 2 retirement planning cleaner because the context surface no
  longer depends on the compat module boundary.
- Added regression coverage that locks the shared helper output to the current
  compat-node output contract.

### Files Touched

- `pipeline/character_profile_pipeline.py`
- `nodes_character_profile.py`
- `nodes_context.py`
- `assets/test_character_profile_pipeline.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. `ContextCharacterProfile` should depend only on shared pipeline logic and
   schema helpers, not on a compat node class.
2. The character-profile dropdown contract should be shared between the compat
   and context node surfaces so the cutover does not create UI drift.
3. `CharacterProfileNode` can remain available as a compat surface while
   ceasing to be a structural dependency of the context-first path.

### Validation Performed

- Ran `python -m unittest assets.test_character_profile_pipeline assets.test_context_nodes assets.test_context_bridge_nodes assets.test_workflow_compat_samples assets.test_cutover_plan`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `python tools/verify_full_flow.py`
- Ran `python -m unittest assets.test_node_registry assets.test_workflow_samples`

### Next Steps

1. Audit remaining non-workflow references to `CharacterProfileNode` and decide
   whether any public docs still need a compat-specific migration note before
   deletion can start.
2. If the docs side is already sufficient, `CharacterProfileNode` becomes the
   strongest candidate for the first real Wave 2 retirement execution.

## 2026-03-18 Character-profile blocker contraction pass

### Summary

- Removed incidental `CharacterProfileNode` string references from compat
  workflow validation and maintenance scripts by switching those checks to
  registry-driven class-map resolution.
- Reduced the live blocker report for `CharacterProfileNode` to the dedicated
  compat fixture, the compat node definition, the migration note, and the
  intentional compat-inventory tests.
- Added a small cutover-plan note that points maintainers to the node-specific
  compat blocker report for Wave 2 / Wave 3 retirement audits.

### Files Touched

- `workflow_class_map.py`
- `tools/check_widgets_values.py`
- `tools/verify_full_flow.py`
- `assets/test_workflow_compat_samples.py`
- `assets/test_character_profile_pipeline.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Compat workflow validation should derive node classes from the package
   registry plus the active workflow fixtures, rather than hardcoding compat
   node imports in every test/tool.
2. Node-specific blocker reports are most useful when they surface only
   intentional retirement blockers, so assertion text and maintenance scripts
   should avoid carrying stale compat node names unnecessarily.
3. The remaining `CharacterProfileNode` references in tests are now treated as
   intentional inventory guards rather than incidental usage sites.

### Validation Performed

- Ran `python tools/report_compat_blockers.py CharacterProfileNode`
- Ran `python -m unittest assets.test_character_profile_pipeline assets.test_workflow_compat_samples assets.test_compat_dependency_report assets.test_node_registry`
- Ran `python tools/check_widgets_values.py --include-compat`

### Next Steps

1. Decide whether the migration note is still required before the first Wave 2
   deletion starts, or whether it can be collapsed into the cutover appendix.
2. If `CharacterProfileNode` stays the first Wave 2 target, apply the same
   blocker-contraction pattern to `DictionaryExpand` next so the retirement
   queue remains comparable node by node.

## 2026-03-18 DictionaryExpand blocker contraction pass

### Summary

- Moved mood-expansion use in verification and evaluation scripts off the
  compat `DictionaryExpand` wrapper and onto the shared `pipeline/`
  helper surface.
- Reduced the live blocker report for `DictionaryExpand` to the dedicated
  compat fixture, the compat node definition, the migration note, and the
  intentional registry inventory test.
- Fixed `assets/test_determinism.py` so it also works under
  `python -m unittest`, which keeps the compat regression lane consistent with
  the rest of the repo.

### Files Touched

- `pipeline/content_pipeline.py`
- `tools/verify_full_flow.py`
- `assets/test_determinism.py`
- `tools/run_bias_audit.py`
- `assets/eval_promptbuilder_v5.py`
- `assets/ARCHITECTURE.md`
- `walkthrough.md`
- `compat_dependency_report.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Mood expansion consumers outside the compat workflow lane should depend on
   the shared helper, not on the legacy compat wrapper class.
2. Historical walkthroughs and widget-migration artifacts should not count as
   live compat blockers once the active migration path no longer depends on
   them.
3. Wave 2 blocker comparison is now meaningful across at least two nodes,
   because `CharacterProfileNode` and `DictionaryExpand` both reduce to the
   same blocker shape.

### Validation Performed

- Ran `python tools/report_compat_blockers.py DictionaryExpand`
- Ran `python tools/verify_full_flow.py`
- Ran `python -m unittest assets.test_determinism assets.test_compat_dependency_report assets.test_node_registry assets.test_workflow_compat_samples`
- Ran `python tools/check_widgets_values.py --include-compat`

### Next Steps

1. Apply the same blocker-contraction pass to `ThemeClothingExpander` and
   `ThemeLocationExpander` so the full Wave 2 set shares one retirement shape.
2. Once all Wave 2 nodes are aligned, decide whether to collapse the remaining
   migration note into the cutover appendix before the first actual deletion.

## 2026-03-18 Clothing/location blocker contraction pass

### Summary

- Moved clothing and location expansion use in verification, audit, and helper
  scripts off the compat wrapper classes and onto the shared `pipeline/`
  helper surface.
- Reduced the live blocker reports for `ThemeClothingExpander` and
  `ThemeLocationExpander` to the dedicated compat fixtures, the compat node
  definition, the migration note, and the intentional registry inventory test.
- Confirmed that all four Wave 2 nodes now share the same blocker shape, which
  makes the next deletion decision a docs/cutover choice rather than an
  implementation-isolation problem.

### Files Touched

- `tools/verify_full_flow.py`
- `assets/test_determinism.py`
- `assets/verify_color_distribution.py`
- `assets/verify_integrated_flow.py`
- `assets/verify_lighting_axis.py`
- `assets/test_bias_controls.py`
- `assets/test_fx_cleanup.py`
- `assets/verify_refactoring.py`
- `tools/run_bias_audit.py`
- `assets/eval_promptbuilder_v5.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `compat_dependency_report.py`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. Clothing/location verification outside the compat workflow lane should use
   shared expansion helpers directly, not the legacy wrapper classes.
2. Archive notes, agent scratch files, and old verification-design notes should
   not count as live compat blockers once they stop influencing active
   migration or regression work.
3. Wave 2 is now aligned enough that the main remaining blocker is the
   migration note itself, not per-node technical coupling.

### Validation Performed

- Ran `python tools/report_compat_blockers.py ThemeClothingExpander ThemeLocationExpander`
- Ran `python tools/report_compat_blockers.py CharacterProfileNode DictionaryExpand ThemeClothingExpander ThemeLocationExpander`
- Ran `python -m unittest assets.test_determinism assets.test_bias_controls assets.test_fx_cleanup assets.test_compat_dependency_report assets.test_node_registry assets.test_workflow_compat_samples`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/verify_full_flow.py`

### Next Steps

1. Decide whether `docs/context_refactor/context_migration_notes.md` should
   stay as a live Wave 2 blocker or be collapsed into the cutover appendix.
2. After that docs decision, choose whether `CharacterProfileNode` remains the
   first actual Wave 2 retirement target or whether a different leaf node makes
   a cleaner first deletion.

## 2026-03-18 Migration-note archival pass

### Summary

- Collapsed the live migration guide into a short policy note and moved the
  previous detailed node-by-node walkthrough into an archive appendix.
- Removed the Wave 2 `migration_doc` blocker category from the compat blocker
  report, leaving only compat node definitions, intentional compat-inventory
  tests, and dedicated compat fixtures.
- Shifted the next decision point from docs cleanup to choosing the first real
  Wave 2 retirement target.

### Files Touched

- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/archive/context_migration_notes.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_bridge_workflow.md`
- `docs/context_refactor/archive/context_bridge_workflow.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`

### Decisions Made

1. The cutover plan is now the live source of truth for exact successor
   mapping and retirement sequencing.
2. The migration note should stay live only as a short policy note; detailed
   conversion examples belong in the archive appendix.
3. Removing the live migration-doc blocker makes Wave 2 readiness comparisons
   cleaner and directly actionable.

### Validation Performed

- Ran `python tools/report_compat_blockers.py CharacterProfileNode DictionaryExpand ThemeClothingExpander ThemeLocationExpander`
- Ran `python -m unittest assets.test_compat_dependency_report assets.test_node_registry assets.test_workflow_compat_samples`
- Ran `python tools/check_widgets_values.py --include-compat`

### Next Steps

1. Pick the first actual Wave 2 deletion candidate and define its concrete
   removal patch.
2. After that deletion, re-run the compat blocker report to confirm the Wave 2
   queue shrinks exactly as planned.

## 2026-03-18 CharacterProfileNode retirement pass

### Summary

- Removed `CharacterProfileNode` from the active compat surface, package
  registry, and cutover inventory.
- Removed the dedicated `compat_profile` workflow fixture from the active
  compat regression lane and updated the remaining Wave 2 ordering so
  `DictionaryExpand` becomes the next active target.
- Kept character-profile behavior coverage through the shared helper and the
  context-native node path rather than through the retired compat wrapper.

### Files Touched

- `__init__.py`
- `workflow_samples.json`
- `cutover_plan.json`
- `assets/test_node_registry.py`
- `assets/test_workflow_compat_samples.py`
- `assets/test_compat_dependency_report.py`
- `assets/test_character_profile_pipeline.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- deleted: `nodes_character_profile.py`
- deleted: `ComfyUI-workflow-compat-profile.json`

### Decisions Made

1. The first real Wave 2 deletion should remove the node, its dedicated compat
   fixture, and the matching registry/inventory entries in one patch so the
   retirement is observable in every verification lane.
2. Shared character-profile logic remains covered, but legacy-node parity is no
   longer a meaningful regression target after the compat wrapper is retired.
3. Once the first Wave 2 deletion lands, the next target should be selected by
   the same rule: smallest remaining dedicated compat fixture with clear
   context-first replacement parity.

### Validation Performed

- Ran `python -m unittest assets.test_character_profile_pipeline assets.test_cutover_plan assets.test_node_registry assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_compat_dependency_report`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Start the same retirement flow for `DictionaryExpand`, which is now Wave 2
   order `[21]` and the next active compat leaf blocker.
2. Keep checking that each deletion removes exactly one dedicated compat
   fixture from the active manifest before touching the more coupled Wave 3
   core path.

## 2026-03-18 DictionaryExpand retirement pass

### Summary

- Removed `DictionaryExpand` from the active compat surface and from the shared
  `nodes_dictionary_expand.py` public export set.
- Removed the dedicated `compat_mood` workflow fixture from the active compat
  regression lane and re-numbered Wave 2 so `ThemeClothingExpander` becomes the
  next active target.
- Confirmed via blocker reporting that `DictionaryExpand` no longer appears as
  a live compat blocker after the retirement patch.

### Files Touched

- `nodes_dictionary_expand.py`
- `workflow_samples.json`
- `cutover_plan.json`
- `assets/test_node_registry.py`
- `assets/test_workflow_compat_samples.py`
- `assets/test_compat_dependency_report.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- deleted: `ComfyUI-workflow-compat-mood.json`

### Decisions Made

1. Removing a compat node from a shared module still counts as a complete
   retirement if its exported node class, dedicated fixture, and cutover
   inventory entry all disappear together.
2. The compat blocker report is now the quickest confirmation that a deleted
   node has actually left the live surface; `DictionaryExpand` no longer shows
   up there.
3. After two successful Wave 2 deletions, the remaining leaf nodes can follow
   the same one-fixture-per-deletion pattern without revisiting the broader
   roadmap.

### Validation Performed

- Ran `python -m unittest assets.test_cutover_plan assets.test_node_registry assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_compat_dependency_report`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `python tools/report_compat_blockers.py DictionaryExpand ThemeClothingExpander ThemeLocationExpander`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Start the same retirement flow for `ThemeClothingExpander`, now Wave 2
   order `[21]`.
2. Keep Wave 3 untouched until the two remaining leaf fixtures are gone from
   the active compat manifest.

## 2026-03-18 ThemeClothingExpander retirement pass

### Summary

- Removed `ThemeClothingExpander` from the active compat surface and from the
  shared `nodes_dictionary_expand.py` public export set.
- Removed the dedicated `compat_clothing` workflow fixture from the active
  compat regression lane and re-numbered Wave 2 so `ThemeLocationExpander`
  becomes the final remaining leaf blocker.
- Confirmed via blocker reporting that the live Wave 2 blocker set is now a
  single node: `ThemeLocationExpander`.

### Files Touched

- `nodes_dictionary_expand.py`
- `workflow_samples.json`
- `cutover_plan.json`
- `assets/test_node_registry.py`
- `assets/test_workflow_compat_samples.py`
- `assets/test_compat_dependency_report.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- deleted: `ComfyUI-workflow-compat-clothing.json`

### Decisions Made

1. The same retirement rule still holds for shared compat modules: remove the
   exported node, its dedicated fixture, and its cutover inventory entry in one
   patch.
2. Once Wave 2 reaches a single remaining fixture, the readiness report becomes
   a direct proxy for “is the leaf phase done yet?”.
3. Wave 3 remains intentionally untouched until the final Wave 2 leaf fixture
   is removed from the active manifest.

### Validation Performed

- Ran `python -m unittest assets.test_cutover_plan assets.test_node_registry assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_compat_dependency_report`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `python tools/report_compat_blockers.py ThemeClothingExpander ThemeLocationExpander`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Start the same retirement flow for `ThemeLocationExpander`, now the last
   remaining Wave 2 compat fixture.
2. After Wave 2 becomes empty, decide whether Wave 1 bridge deletion or Wave 3
   core-path shrink should happen first.

## 2026-03-18 ThemeLocationExpander retirement pass

### Summary

- Removed `ThemeLocationExpander` and the now-empty `nodes_dictionary_expand.py`
  module from the active compat surface.
- Removed the final Wave 2 fixture `compat_location`, which leaves
  `compat_core` as the only active compat regression workflow.
- Tightened compat blocker matching to exact node names so Wave 3 audits no
  longer get false positives from context-native names such as
  `ContextSceneVariator`.

### Files Touched

- `__init__.py`
- `workflow_samples.json`
- `cutover_plan.json`
- `compat_dependency_report.py`
- `tools/report_compat_blockers.py`
- `assets/test_node_registry.py`
- `assets/test_workflow_samples.py`
- `assets/test_workflow_compat_samples.py`
- `assets/test_compat_dependency_report.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- deleted: `nodes_dictionary_expand.py`
- deleted: `ComfyUI-workflow-compat-location.json`

### Decisions Made

1. Once Wave 2 reached its last leaf node, it was cleaner to remove the now-
   empty compat module itself instead of keeping a dead file around.
2. Wave 3 audits should use exact node-name matching, not substring matching,
   because context-native names intentionally contain compat successor names.
3. With Wave 2 complete, the only active compat workflow baseline should be
   `compat_core`.

### Validation Performed

- Ran `python -m unittest assets.test_cutover_plan assets.test_node_registry assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_compat_dependency_report`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `python tools/report_compat_blockers.py SceneVariator PackParser GarnishSampler SimpleTemplateBuilder`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Decide whether Wave 1 bridge removal should happen before Wave 3, or whether
   the remaining `compat_core` path should be shrunk first.
2. If Wave 3 goes first, start with `PackParser`, since `compat_core` still
   blocks every remaining compat node equally.

## 2026-03-18 PackParser retirement pass

### Summary

- Removed `PackParser` from the active compat surface, package registry, and
  cutover inventory.
- Hybridized `compat_core` so the remaining Wave 3 regression lane now starts
  from `ContextSource` instead of a legacy source wrapper.
- Kept the compat regression fixture alive for the remaining Wave 3 nodes:
  `SceneVariator`, `GarnishSampler`, and `SimpleTemplateBuilder`.

### Files Touched

- `__init__.py`
- `workflow_samples.json`
- `cutover_plan.json`
- `ComfyUI-workflow-compat-core.json`
- `assets/test_node_registry.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- deleted: `nodes_pack_parser.py`

### Decisions Made

1. The compat-core lane no longer needs a legacy source-stage node once
   `ContextSource` covers the same workflow-entry responsibility.
2. Wave 3 retirement can proceed incrementally if the compat regression fixture
   is allowed to become hybrid instead of staying legacy-only end to end.
3. After `PackParser`, the next retirement candidates are the remaining compat
   orchestration/prompt nodes rather than another source-stage wrapper.

### Validation Performed

- Ran `python -m unittest assets.test_cutover_plan assets.test_node_registry assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_compat_dependency_report`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `python tools/report_compat_blockers.py PackParser`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Start the same retirement flow for `SceneVariator`, now the first remaining
   Wave 3 compat node.
2. Keep `compat_core` only as long as it is still needed to prove retirement
   readiness for `SceneVariator`, `GarnishSampler`, and `SimpleTemplateBuilder`.

## 2026-03-18 SceneVariator retirement pass

### Summary

- Removed `SceneVariator` from the active compat surface, package registry, and
  cutover inventory.
- Hybridized `compat_core` one step further so the active compat regression
  fixture now uses `ContextSceneVariator` before the remaining legacy nodes.
- Renamed the shared scene-stage debug node identity to
  `ContextSceneVariator` and updated verification helpers to stop importing the
  retired compat wrapper.

### Files Touched

- `__init__.py`
- `workflow_samples.json`
- `cutover_plan.json`
- `ComfyUI-workflow-compat-core.json`
- `pipeline/context_pipeline.py`
- `compat_dependency_report.py`
- `tools/report_compat_blockers.py`
- `tools/verify_full_flow.py`
- `tools/run_bias_audit.py`
- `assets/generate_baseline.py`
- `assets/test_context_bridge_nodes.py`
- `assets/test_context_ops.py`
- `assets/test_context_pipeline.py`
- `assets/test_compat_dependency_report.py`
- `assets/test_node_registry.py`
- `assets/test_schema.py`
- `assets/test_scene_variator.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- deleted: `nodes_scene_variator.py`

### Decisions Made

1. Once the context-native scene stage covers the active compat fixture, the
   legacy scene wrapper no longer needs to stay on the public surface.
2. Shared debug/history entries should use the canonical context-stage name so
   retirement reports do not treat internal bookkeeping as a live compat
   dependency.
3. After `SceneVariator`, the Wave 3 queue becomes a two-node compat lane:
   `GarnishSampler` then `SimpleTemplateBuilder`.

### Validation Performed

- Ran `python -m unittest assets.test_cutover_plan assets.test_node_registry assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_compat_dependency_report assets.test_context_bridge_nodes assets.test_context_pipeline assets.test_context_ops assets.test_schema`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `python tools/report_compat_blockers.py SceneVariator`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Start the same retirement flow for `GarnishSampler`, now the first
   remaining compat-core node.
2. Keep `compat_core` only as long as it is still needed to prove retirement
   readiness for `GarnishSampler` and `SimpleTemplateBuilder`.

## 2026-03-18 GarnishSampler retirement pass

### Summary

- Removed `GarnishSampler` from the repo's active compat surface and deleted
  the retired wrapper module.
- Kept the active `compat_core` workflow alive by switching the garnish stage
  fully to `ContextGarnish`, leaving `SimpleTemplateBuilder` as the only
  remaining Wave 3 compat node.
- Moved remaining verification scripts and reference docs off the retired
  compat wrapper and onto the shared/context-native garnish path.

### Files Touched

- `assets/eval_promptbuilder_v5.py`
- `assets/verify_refactoring.py`
- `assets/test_bootstrap.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- deleted: `nodes_garnish.py`

### Decisions Made

1. Once `compat_core` uses `ContextGarnish`, the legacy garnish wrapper no
   longer needs to stay in the package or as a live verification dependency.
2. Verification and evaluation scripts that only need garnish behavior should
   call the shared helper or context-native stage, not the retired compat
   wrapper class.
3. After this deletion, Wave 3 is effectively reduced to one remaining compat
   node: `SimpleTemplateBuilder`.

### Validation Performed

- Ran `python tools/report_compat_blockers.py GarnishSampler`
- Ran `python -m unittest assets.test_cutover_plan assets.test_node_registry assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_compat_dependency_report assets.test_context_bridge_nodes assets.test_context_pipeline assets.test_context_ops assets.test_schema assets.test_determinism assets.test_personality_garnish`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `python assets/verify_refactoring.py --quick`
- Ran `python tools/report_compat_blockers.py SimpleTemplateBuilder`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Start the final Wave 3 retirement flow for `SimpleTemplateBuilder`.
2. Keep `compat_core` only as long as it is still needed to prove retirement
   readiness for `SimpleTemplateBuilder`.

## 2026-03-18 SimpleTemplateBuilder retirement pass

### Summary

- Removed `SimpleTemplateBuilder` from the active compat surface, deleted the
  wrapper module, and retired the final `compat_core` workflow fixture.
- Migrated remaining verification/evaluation scripts to shared prompt-assembly
  helpers or context-native prompt building so no live compat blocker remains.
- Left Wave 1 transition nodes as the only active removal lane; the workflow
  baseline is now fully context-only.

### Files Touched

- `__init__.py`
- `workflow_samples.json`
- `cutover_plan.json`
- `pipeline/content_pipeline.py`
- `compat_dependency_report.py`
- `tools/report_compat_blockers.py`
- `tools/verify_full_flow.py`
- `tools/run_bias_audit.py`
- `assets/generate_baseline.py`
- `assets/test_bootstrap.py`
- `assets/test_node_registry.py`
- `assets/test_cutover_plan.py`
- `assets/test_workflow_samples.py`
- `assets/test_workflow_compat_samples.py`
- `assets/test_compat_dependency_report.py`
- `assets/test_context_bridge_nodes.py`
- `assets/test_composition.py`
- `assets/test_consistency.py`
- `assets/test_determinism.py`
- `assets/verify_consistency.py`
- `assets/eval_promptbuilder_v5.py`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- `ComfyUI_frontend/browser_tests/fixtures/ComfyPage.ts`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatCompatibility.test.ts`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatRoundtrip.test.ts`
- deleted: `nodes_simple_template.py`
- deleted: `ComfyUI-workflow-compat-core.json`

### Decisions Made

1. After `ContextPromptBuilder` reached parity, the final compat node and its
   dedicated compat workflow baseline should be removed together rather than
   kept as an empty regression lane.
2. Shared prompt assembly should use generic stage naming (`PromptAssembly`)
   so retired compat node names do not survive as live blocker matches.
3. Compat verification lanes stay in place only as retirement-complete checks;
   they now assert that no active compat workflows remain.

### Validation Performed

- Ran `python tools/report_compat_blockers.py SimpleTemplateBuilder`
- Ran `python -m unittest assets.test_cutover_plan assets.test_node_registry assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_compat_dependency_report assets.test_context_bridge_nodes assets.test_context_pipeline assets.test_context_ops assets.test_schema assets.test_determinism assets.test_personality_garnish assets.test_composition assets.test_consistency`
- Ran `python tools/check_widgets_values.py`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `python tools/verify_full_flow.py`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node.config.mts`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Treat compat retirement as complete and move the active roadmap to Wave 1
   transition-node deletion planning.
2. Decide whether bridge support is still needed as a public migration aid or
   whether Wave 1 execution can begin.

## 2026-03-18 Bridge retirement pass

### Summary

- Removed the Wave 1 bridge nodes from the active package surface and deleted
  the bridge module plus its dedicated tests/reporting helpers.
- Updated docs, cutover inventory, and readiness reporting so the repo now
  treats all three retirement waves as complete.
- Tightened the remaining verification baseline to context-only workflows and
  context-native helper usage.

### Files Touched

- `__init__.py`
- `cutover_plan.json`
- `tools/verify_full_flow.py`
- `tools/report_cutover_readiness.py`
- `assets/test_cutover_plan.py`
- `assets/test_node_registry.py`
- `assets/ARCHITECTURE.md`
- `README.md`
- `docs/context_refactor/context_bridge_workflow.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- deleted: `nodes_context_bridge.py`
- deleted: `assets/test_context_bridge_nodes.py`
- deleted: `transition_dependency_report.py`
- deleted: `assets/test_transition_dependency_report.py`
- deleted: `tools/report_transition_blockers.py`

### Decisions Made

1. Once workflow baselines, helper scripts, and public docs no longer depended
   on bridge nodes, the cleanest end state was full removal rather than keeping
   a dormant transition surface.
2. The machine-readable cutover inventory should become empty after all three
   waves complete, rather than keeping already-retired nodes in a live plan.
3. Historical mixed-mode guidance stays only as archive/reference material and
   should not remain part of the active verification or package surface.

### Validation Performed

- Ran `python -m unittest assets.test_cutover_plan assets.test_node_registry assets.test_workflow_samples assets.test_workflow_compat_samples assets.test_compat_dependency_report assets.test_context_pipeline assets.test_context_ops assets.test_schema assets.test_determinism assets.test_personality_garnish assets.test_composition assets.test_consistency`
- Ran `python tools/check_widgets_values.py`
- Ran `python tools/check_widgets_values.py --include-compat`
- Ran `python tools/report_cutover_readiness.py`
- Ran `python tools/report_compat_blockers.py SimpleTemplateBuilder`
- Ran `python tools/verify_full_flow.py`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node.config.mts`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node-compat.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`

### Next Steps

1. Treat the context-first migration as complete unless a new schema or
   workflow-persistence regression appears.
2. Use the current context-only verification baseline when adding new features
   on top of the revised repository.

## 2026-03-18 Context-only verification cleanup

### Summary

- Removed the no-op compat verification lane now that the active sample
  manifest contains only the context workflow.
- Simplified the workflow manifest and loader helpers by dropping the retired
  compat-specific access paths.
- Collapsed Python, frontend, and GUI round-trip validation onto a single
  context-only baseline.

### Files Touched

- `workflow_samples.json`
- `workflow_samples.py`
- `assets/test_workflow_samples.py`
- `tools/check_widgets_values.py`
- `tools/report_cutover_readiness.py`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatibility.test.ts`
- `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowRoundtrip.test.ts`
- `ComfyUI_frontend/browser_tests/tests/customWorkflowRoundtrip.spec.ts`
- `tools/run_custom_workflow_roundtrip.ps1`
- `README.md`
- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_cutover_plan.md`
- `docs/context_refactor/context_v2_tasks.md`
- `docs/context_refactor/context_v2_progress.md`
- deleted: `assets/test_workflow_compat_samples.py`
- deleted: `compat_dependency_report.py`
- deleted: `assets/test_compat_dependency_report.py`
- deleted: `tools/report_compat_blockers.py`
- deleted: `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatCompatibility.test.ts`
- deleted: `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatRoundtrip.test.ts`
- deleted: `ComfyUI_frontend/vitest.custom-node-compat.config.mts`

### Decisions Made

1. Empty compat-only tests and configs no longer add coverage once the active
   workflow manifest is context-only.
2. The live verification contract should stay simple: one workflow manifest,
   one widget baseline, one frontend round-trip lane, and one GUI round-trip
   lane.

### Validation Performed

- Ran `python -m unittest assets.test_cutover_plan assets.test_node_registry assets.test_workflow_samples assets.test_context_pipeline assets.test_context_content_pipeline assets.test_context_nodes assets.test_context_ops assets.test_context_codec assets.test_schema assets.test_determinism assets.test_personality_garnish assets.test_composition assets.test_consistency`
- Ran `python tools/check_widgets_values.py`
- Ran `python tools/report_cutover_readiness.py`
- Ran `python tools/verify_full_flow.py`
- Ran `corepack pnpm exec vitest run --config vitest.custom-node.config.mts`
- Ran `pwsh -File tools/run_custom_workflow_roundtrip.ps1`

## 2026-03-18 Historical maintenance tool cleanup

### Summary

- Moved old workflow-salvage and widget-migration helpers out of the live
  `tools/` surface into `tools/archive/`.
- Moved unreferenced one-off scripts out of the live `assets/` surface into
  `assets/archive/`.
- Removed stale generated report files that no longer belong in the active
  repo baseline.

### Files Touched

- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_v2_progress.md`
- `tools/archive/README.md`
- `assets/archive/README.md`
- moved: `tools/extract_repro_workflow.py` -> `tools/archive/extract_repro_workflow.py`
- moved: `tools/fix_workflows_widgets.py` -> `tools/archive/fix_workflows_widgets.py`
- moved: `tools/scan_workflows_widgets.py` -> `tools/archive/scan_workflows_widgets.py`
- moved: `tools/simulate_widgets_values_migration.py` -> `tools/archive/simulate_widgets_values_migration.py`
- moved: `assets/debug_consistency.py` -> `assets/archive/debug_consistency.py`
- moved: `assets/generate_docs.py` -> `assets/archive/generate_docs.py`
- deleted: `assets/test.md`
- deleted: `tools/widgets_values_report.json`
- deleted: `tools/widgets_values_simulation_report.json`

### Decisions Made

1. Legacy workflow repair helpers should remain available for reference, but
   they should not appear as active operational tools in a context-only repo.
2. Generated JSON reports and placeholder files should not stay in the live
   tree once they stop contributing to the current verification baseline.

## 2026-03-18 Historical walkthrough and runner cleanup

### Summary

- Removed the old `assets/runner.py` entry point from the live tree and moved
  it into `assets/archive/`.
- Moved the obsolete top-level `walkthrough.md` into
  `docs/context_refactor/archive/`.
- Cleared the last live test-file note that still suggested `runner.py` as a
  normal execution path.

### Files Touched

- `assets/test_personality_garnish.py`
- `assets/archive/README.md`
- `assets/archive/runner.py`
- `docs/context_refactor/archive/walkthrough.md`
- `docs/context_refactor/context_v2_progress.md`
- moved: `assets/runner.py` -> `assets/archive/runner.py`
- moved: `walkthrough.md` -> `docs/context_refactor/archive/walkthrough.md`

### Decisions Made

1. Historical walkthroughs and aggregate runners are still useful as project
   history, but they should not appear to be current operational entry points.
2. The active repo surface should point maintainers to the current
   context-only verification commands, not to pre-cutover wrappers.

## 2026-03-18 Historical planning doc cleanup

### Summary

- Moved the old scene/emotion implementation checklist and progress tracker out
  of the live `assets/` tree into `assets/archive/`.
- Reduced the active `assets/` surface to scripts and docs that still map to
  the current context-only repository state.

### Files Touched

- `assets/archive/README.md`
- `docs/context_refactor/context_v2_progress.md`
- moved: `assets/実装チェックリスト版.md` -> `assets/archive/実装チェックリスト版.md`
- moved: `assets/進捗.md` -> `assets/archive/進捗.md`

### Decisions Made

1. Completed phase-by-phase planning documents should be preserved as history,
   not presented as active maintenance inputs once the migration is complete.
2. The live `assets/` tree should stay focused on executable tests, validation
   scripts, and current reference material.

## 2026-03-18 Upstream-replaceable verification sync

### Summary

- Moved custom frontend/browser verification source files out of the
  replaceable `ComfyUI_frontend/` checkout into repo-local `verification/`.
- Added a sync step that stages those verification files into the current
  `ComfyUI_frontend/` tree immediately before running frontend validation or
  GUI round-trip checks.
- Kept the active verification entry points stable while reducing the amount of
  manual rework needed after replacing `ComfyUI` or `ComfyUI_frontend` with a
  newer upstream checkout.

### Files Touched

- `assets/ARCHITECTURE.md`
- `docs/context_refactor/context_migration_notes.md`
- `docs/context_refactor/context_v2_progress.md`
- `tools/run_custom_workflow_roundtrip.ps1`
- `tools/run_frontend_workflow_validation.ps1`
- `tools/sync_upstream_verification_assets.ps1`
- `verification/browser/customWorkflowRoundtrip.spec.ts`
- `verification/browser/playwright.custom-node.config.mts`
- `verification/frontend/customNodeWorkflowCompatibility.test.ts`
- `verification/frontend/customNodeWorkflowRoundtrip.test.ts`
- `verification/frontend/vitest.custom-node.config.mts`
- deleted: `ComfyUI_frontend/browser_tests/tests/customWorkflowRoundtrip.spec.ts`
- deleted: `ComfyUI_frontend/playwright.custom-node.config.mts`
- deleted: `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowCompatibility.test.ts`
- deleted: `ComfyUI_frontend/src/platform/workflow/validation/schemas/customNodeWorkflowRoundtrip.test.ts`
- deleted: `ComfyUI_frontend/vitest.custom-node.config.mts`

### Validation

- `python -m unittest assets.test_node_registry assets.test_workflow_samples`
- `python tools/check_widgets_values.py`
- `corepack pnpm exec vitest run --config vitest.custom-node.config.mts`
- `pwsh -File tools/run_custom_workflow_roundtrip.ps1`

### Decisions Made

1. Custom verification for this package should be owned by this repository,
   not stored as ad-hoc edits inside upstream dependencies that are expected to
   be replaced over time.
2. The boundary with upstream repos should be a small sync step plus black-box
   validation commands, rather than persistent hand-maintained patches inside
   `ComfyUI_frontend/`.

## 2026-03-18 Historical spec and fixture cleanup

### Summary

- Moved superseded design reviews and refactor-spec markdown files out of the
  live `assets/` surface into `assets/archive/`.
- Moved the old legacy workflow fixture and its extracted repro workflow JSON
  into `tools/archive/`, so archival widget-migration material no longer
  occupies the repo root.
- Removed the duplicate top-level `generate_docs.py` entry point and treated
  old generated outputs such as `simple_template_debug.log` and
  `current_resources.md` as ignorable local artifacts.

### Files Touched

- `.gitignore`
- `assets/archive/README.md`
- `docs/context_refactor/context_v2_progress.md`
- `tools/archive/README.md`
- `tools/archive/extract_repro_workflow.py`
- `tools/archive/simulate_widgets_values_migration.py`
- deleted: `generate_docs.py`
- moved: `assets/variation_expansion_plan_review.md` -> `assets/archive/variation_expansion_plan_review.md`
- moved: `assets/scene_emotion_priority_spec.md` -> `assets/archive/scene_emotion_priority_spec.md`
- moved: `assets/object_concentration_refactor_spec.md` -> `assets/archive/object_concentration_refactor_spec.md`
- moved: `assets/object_concentration_refactor_evaluation.md` -> `assets/archive/object_concentration_refactor_evaluation.md`
- moved: `assets/object_concentration_refactor_verification.md` -> `assets/archive/object_concentration_refactor_verification.md`
- moved: `ComfyUI-workflow-exmaple.json` -> `tools/archive/ComfyUI-workflow-exmaple.json`
- moved: `workflow_repro_widgets_values.json` -> `tools/archive/workflow_repro_widgets_values.json`

### Decisions Made

1. Completed specs, reviews, and legacy fixtures should stay available for
   reference, but they should not remain in the live top-level surface once the
   context-only architecture is established.
2. Archive tooling should keep its own historical fixtures nearby, instead of
   depending on obsolete files that still sit at repo root and look active.
