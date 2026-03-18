# Bridge Workflow Note

Bridge helper support is retired. This page remains only as a historical note
after the Wave 1 cutover completed.

Current status:

1. New workflows stay on the `Context*` surface end to end.
2. No bridge nodes remain in the active package surface.
3. The historical mixed-mode wiring reference lives only in
   [archive/context_bridge_workflow.md](./archive/context_bridge_workflow.md).

Related documents:
- [Migration Note](./context_migration_notes.md)
- [Cutover Plan](./context_cutover_plan.md)
- [Progress Log](./context_v2_progress.md)

## Operational Rule

Do not restore mixed-mode patterns into the active surface. If old graphs need
to be studied, use the archive note only as historical reference.
