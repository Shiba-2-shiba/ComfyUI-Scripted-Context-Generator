# Context Workflow Migration Note

## Goal

Keep one short live note for the migration policy while the detailed node-by-
node conversion guide moves to the archive appendix.

Related documents:
- [Spec](./context_v2_spec.md)
- [Task Plan](./context_v2_tasks.md)
- [Archived Cutover Plan](./archive/context_cutover_plan.md)
- [Archived Detailed Notes](./archive/context_migration_notes.md)

## Live Policy

1. New workflow work starts from the context-first surface.
2. Shared behavior changes land in `pipeline/` or context helpers first.
3. Retired compat and bridge surfaces stay in archive material only.
4. Validation assets should live in this repo, not inside replaceable upstream
   `ComfyUI` or `ComfyUI_frontend` trees.

## Active Guidance

For the completed retirement waves and removal-gate record, use the archived
[Cutover Plan](./archive/context_cutover_plan.md).

For historical mixed-mode examples, use the bridge appendix referenced from
[Bridge Workflow Note](./context_bridge_workflow.md).

For the previous detailed stage-by-stage migration walkthrough, use the archive
appendix at [archive/context_migration_notes.md](./archive/context_migration_notes.md).

## Validation Checklist

1. Run `python tools/check_widgets_values.py`
2. Run `python tools/verify_full_flow.py`
3. Run `pwsh -File tools/run_frontend_workflow_validation.ps1`
4. Run focused unit tests covering the modified stage
5. Run `pwsh -File tools/run_custom_workflow_roundtrip.ps1`
