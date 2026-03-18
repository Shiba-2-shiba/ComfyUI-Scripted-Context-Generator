# PromptContext v2 Refactor Tasks

## Usage

Update this file as the execution checklist for the context-first refactor.

Rules:
1. Keep task ids stable once assigned.
2. Mark status as `todo`, `doing`, `blocked`, or `done`.
3. When a task changes meaning substantially, create a new task id instead of
   rewriting history.
4. Record implementation details and decisions in the progress log, not here.

Related documents:
- [Spec](./context_v2_spec.md)
- [Progress Log](./context_v2_progress.md)

## Phase 0: Planning And Scaffolding

| ID | Status | Task | Notes |
|----|--------|------|-------|
| P0-01 | done | Create dedicated refactor docs for spec, tasks, and progress | Initial scaffold created on 2026-03-18 |
| P0-02 | done | Review current node API surface and freeze legacy compatibility scope | Legacy public node classes stay exposed during migration; context-first family is the recommended path |
| P0-03 | done | Define naming rules for new context node family | Public context-native nodes keep the `Context*` prefix; legacy display names now include `Legacy` |

## Phase 1: Schema And Codec

| ID | Status | Task | Notes |
|----|--------|------|-------|
| P1-01 | done | Extend `core/schema.py` to represent PromptContext v2 defaults | Added `context_version`, `seed`, `warnings`, normalized extras/history handling |
| P1-02 | done | Create `core/context_codec.py` | Added parse, serialize, normalize, and legacy-warning handling |
| P1-03 | done | Create `core/context_ops.py` | Added patch, merge, ensure, history, and warning helpers |
| P1-04 | done | Add unit tests for empty, malformed, partial, and legacy context payloads | Covered in `assets/test_schema.py`, `assets/test_context_codec.py`, `assets/test_context_ops.py` |

## Phase 2: Bridge Helpers

| ID | Status | Task | Notes |
|----|--------|------|-------|
| P2-01 | done | Add `FieldsToContext` helper node | Implemented in `nodes_context_bridge.py` |
| P2-02 | done | Add `ContextToFields` helper node | Implemented in `nodes_context_bridge.py` |
| P2-03 | done | Add `ContextPatch` helper node | Implemented in `nodes_context_bridge.py` |
| P2-04 | done | Document bridge workflow examples | Live note kept at `docs/context_refactor/context_bridge_workflow.md`; detailed mixed-mode example archived under `docs/context_refactor/archive/` |

## Phase 3: Shared Logic Extraction

| ID | Status | Task | Notes |
|----|--------|------|-------|
| P3-01 | done | Extract scene variation logic into shared context-aware functions | Implemented in `pipeline/context_pipeline.py` and wired through `nodes_scene_variator.py` |
| P3-02 | done | Extract garnish logic into shared context-aware functions | Implemented in `pipeline/context_pipeline.py` and wired through `nodes_garnish.py` |
| P3-03 | done | Extract clothing expansion logic into shared context-aware functions | Implemented in `pipeline/content_pipeline.py` and wired through `nodes_dictionary_expand.py` |
| P3-04 | done | Extract location expansion logic into shared context-aware functions | Implemented in `pipeline/content_pipeline.py` and wired through `nodes_dictionary_expand.py` |
| P3-05 | done | Extract prompt assembly logic into shared context-aware functions | Implemented in `pipeline/content_pipeline.py` and wired through `nodes_simple_template.py` |
| P3-06 | done | Extract mood expansion logic into shared context-aware functions | Implemented in `pipeline/content_pipeline.py` and wired through `nodes_dictionary_expand.py` |

## Phase 4: New Context Node Family

| ID | Status | Task | Notes |
|----|--------|------|-------|
| P4-01 | done | Implement `ContextSource` | Added in `nodes_context.py` |
| P4-02 | done | Implement `ContextCharacterProfile` | Added in `nodes_context.py` |
| P4-03 | done | Implement `ContextSceneVariator` | Added in `nodes_context.py` |
| P4-04 | done | Implement `ContextClothingExpander` | Added in `nodes_context.py` |
| P4-05 | done | Implement `ContextLocationExpander` | Added in `nodes_context.py` |
| P4-06 | done | Implement `ContextMoodExpander` | Added in `nodes_context.py` |
| P4-07 | done | Implement `ContextGarnish` | Added in `nodes_context.py` |
| P4-08 | done | Implement `ContextPromptBuilder` | Added in `nodes_context.py` |
| P4-09 | done | Implement `ContextInspector` | Added in `nodes_context.py` |

## Phase 5: Legacy Wrapper Migration

| ID | Status | Task | Notes |
|----|--------|------|-------|
| P5-01 | done | Refactor `SceneVariator` into a thin wrapper over shared logic | `nodes_scene_variator.py` now delegates to `pipeline/context_pipeline.py` |
| P5-02 | done | Refactor `GarnishSampler` into a thin wrapper over shared logic | `nodes_garnish.py` now delegates to `pipeline/context_pipeline.py` |
| P5-03 | done | Refactor `SimpleTemplateBuilder` into a thin wrapper over shared logic | Completed before final Wave 3 retirement; shared prompt assembly remains in `pipeline/content_pipeline.py` |
| P5-04 | done | Refactor expanders into thin wrappers over shared logic | `nodes_dictionary_expand.py` now delegates to `pipeline/content_pipeline.py` |
| P5-05 | done | Reduce legacy `forceInput` usage where safe | Removed where thin wrappers can safely fall back to widget defaults |
| P5-06 | done | Rename legacy display names to include `Legacy` | Display names updated after the context workflow sample was added |
| P5-07 | done | Consolidate package node registration around module-level mappings | `__init__.py` now imports each node module's exported mappings to avoid display-name drift and duplicated registry literals |

## Phase 6: Workflow And Docs

| ID | Status | Task | Notes |
|----|--------|------|-------|
| P6-01 | done | Keep current example workflow as legacy sample | The original monolithic legacy sample remains available as historical reference; active compat regression now uses split Wave 2/3 fixtures |
| P6-02 | done | Add new context-first example workflow | Added `ComfyUI-workflow-context.json` as the recommended sample |
| P6-03 | done | Update README to recommend context-first workflow | README now distinguishes context-first vs legacy flows |
| P6-04 | done | Add migration notes from legacy workflow to context workflow | Added `docs/context_refactor/context_migration_notes.md` |
| P6-05 | done | Add developer guidance for extending context schema | Added `docs/context_refactor/context_extension_guidance.md` |

## Phase 7: Verification

| ID | Status | Task | Notes |
|----|--------|------|-------|
| P7-01 | done | Add tests for codec normalization and migration | Schema-focused tests added for schema, codec, and context ops |
| P7-02 | done | Add tests for shared context pipeline functions | Scene, garnish, clothing, location, mood, prompt tests added |
| P7-03 | done | Add mixed-mode workflow tests using bridge nodes | Covered in `assets/test_workflow_samples.py` |
| P7-04 | done | Add save/load workflow regression checks for sample workflows | Sample workflow widget serialization covered in `assets/test_workflow_samples.py` plus widget tools |
| P7-05 | done | Run existing verification scripts after each major stage | `verify_full_flow.py`, focused unit tests, widget round-trip guards, CPU-only `ComfyUI_frontend` schema validation, frontend `configure -> serialize` round-trip tests, and Playwright GUI save/reload round-trip checks for both sample workflows are passing |

## Phase 8: Full Replacement Roadmap

| ID | Status | Task | Notes |
|----|--------|------|-------|
| P8-01 | done | Reframe the public roadmap around context-first full replacement | README, tasks, and migration notes now treat `Context*` as the target public API and legacy nodes as transitional compat |
| P8-02 | done | Freeze compat node scope and stop feature growth on legacy nodes | Compat and bridge nodes are retired from the active public surface; future work lands on context-first nodes and shared helpers only |
| P8-03 | done | Migrate examples, docs, and future features to context-first only | Workflow samples, docs, Python/frontend/browser verification, and browser round-trip checks are now centered on `ComfyUI-workflow-context.json` only |
| P8-04 | done | Define removal gates for bridge and legacy nodes | Added `cutover_plan.json`, `context_cutover_plan.md`, and tests that inventory every compat/transition node, its successor, and the gates required before removal |
| P8-05 | done | Retire legacy workflow assets and wrappers when removal gates are met | Wave 1, Wave 2, and Wave 3 are complete: bridge nodes plus all compat/legacy wrappers are retired, and the active public surface is now context-first only |

## Current Priority

1. keep all new feature work on context-first nodes and shared helpers only
2. keep the workflow and round-trip verification baseline on `ComfyUI-workflow-context.json` only
3. re-run GUI round-trip verification after any workflow asset or frontend persistence edit
