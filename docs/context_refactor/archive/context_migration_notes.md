# Context Workflow Migration Notes

## Goal

Replace the legacy field-by-field workflow with the new `context_json` based
workflow, then continue future feature work only on the new architecture.

Related documents:
- [Spec](../context_v2_spec.md)
- [Task Plan](../context_v2_tasks.md)
- [Bridge Workflow Note](../context_bridge_workflow.md)
- [Cutover Plan](../context_cutover_plan.md)

## Destination Architecture

The intended end state is:

1. `Context*` nodes are the only primary public workflow surface.
2. Shared logic lives in `pipeline/` and context helpers, not in duplicated
   legacy node branches.
3. Legacy nodes and bridge nodes exist only to support cutover and can be
   removed after migration gates are satisfied.

## Migration Stages

### Stage 1: Build New Work On Context-First Only

1. Start all new workflows from `ContextSource`.
2. Add new capabilities to `nodes_context.py`, `pipeline/`, and schema helpers.
3. Do not add feature-only sockets or widgets to legacy nodes.

### Stage 2: Convert Existing Graphs

Use this order for converting an old graph:

1. Replace the workflow entry point with `ContextSource`.
2. Add `ContextCharacterProfile` if the graph currently depends on
   `CharacterProfileNode`.
3. Replace legacy enrichment nodes with their context equivalents:
   - `SceneVariator` -> `ContextSceneVariator`
   - `ThemeClothingExpander` -> `ContextClothingExpander`
   - `ThemeLocationExpander` -> `ContextLocationExpander`
   - `DictionaryExpand` -> `ContextMoodExpander`
   - `GarnishSampler` -> `ContextGarnish`
4. Replace `SimpleTemplateBuilder` with `ContextPromptBuilder`.
5. Keep `PromptCleaner` as the final formatting step.

### Stage 3: Remove Temporary Compatibility Dependencies

1. Remove bridge helpers once the graph no longer crosses between old and new
   node families.
2. Keep compat regression fixtures only for retirement checking while existing
   user graphs are still being migrated.
3. Plan deletion of compat nodes only after feature parity and verification are
   both green.

## Temporary Bridge Patterns

### Context -> Legacy

Use this only when a graph is partially migrated and still blocked by compat
nodes:

1. `ContextSource`
2. `ContextCharacterProfile`
3. bridge helper fan-out
4. compat nodes

### Legacy -> Context

Use this when the workflow still starts from legacy fields but the downstream
assembly has already moved to context-first:

1. legacy field-producing nodes
2. bridge helper ingress
3. context-native nodes

### Structured Overrides

Use the bridge helper patch step for small structured overrides instead of
introducing more string sockets.

For the current bridge policy, see [Bridge Workflow Note](../context_bridge_workflow.md).
If you need the historical mixed-mode wiring appendix, follow the archive link
from that note.

## Workflow Assets

- Recommended sample: `ComfyUI-workflow-context.json`
- Compat regression fixtures:
  - `ComfyUI-workflow-compat-core.json`
  - `ComfyUI-workflow-compat-profile.json`
  - `ComfyUI-workflow-compat-mood.json`
  - `ComfyUI-workflow-compat-clothing.json`
  - `ComfyUI-workflow-compat-location.json`

## Transition Policy

1. Treat the `Context*` node family as the only preferred surface for new
   feature work.
2. Keep compat nodes available only for migration and bug compatibility during
   the cutover period.
3. When old behavior must change, implement the logic in shared `pipeline/` or
   context helpers first and keep the compat node as a thin wrapper.
4. Reduce bridge-node usage over time; do not treat bridge nodes as permanent
   architecture.
5. Preserve the compat workflow asset only until the removal gates in the task
   plan are satisfied.

## Removal Gates

Do not delete compat nodes or bridge nodes until all of the following are true:

1. The context-first workflow covers the required feature set.
2. Migration guidance exists for each legacy entry path being retired.
3. Python-side workflow checks, frontend CPU-only checks, and GUI round-trip
   checks are green.
4. The legacy sample workflow is no longer needed as the primary regression
   baseline for user migration.
   The same applies to the remaining compat regression fixtures.

## Validation Checklist

1. Run `python tools/check_widgets_values.py`
2. When touching compat assets, also run `python tools/check_widgets_values.py --include-compat`
3. Run `python tools/verify_full_flow.py`
4. Run `corepack pnpm exec vitest run --config ComfyUI_frontend/vitest.custom-node.config.mts`
5. When touching compat workflow validation, also run `corepack pnpm exec vitest run --config ComfyUI_frontend/vitest.custom-node-compat.config.mts`
6. Run focused unit tests covering the modified stage
7. Run `pwsh -File tools/run_custom_workflow_roundtrip.ps1`
8. When touching compat workflow persistence, re-run `pwsh -File tools/run_custom_workflow_roundtrip.ps1 -IncludeCompat`
