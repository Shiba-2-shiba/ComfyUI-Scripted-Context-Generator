TODO
1. Read all node implementations to extract:
   - node name
   - inputs/outputs
   - parameters (including defaults and optional behaviors)
   - Done
2. Parse ComfyUI-workflow-exmaple.json and diagram the node graph.
3. Identify coverage gaps between node capabilities and workflow usage.
   - Done
4. Modify workflow JSON to close gaps.
   - Done (ActionMerge, PromptCleaner, meta_style wired)
5. Draft a comprehensive verification plan for tools/ test script:
   - deterministic seeds
   - expected data transformations
   - asserts for structural outputs
   - Done
6. Implement tools/ verification script that exercises all node features.
   - Done (tools/verify_full_flow.py)
7. Run the script and capture results.
   - Done (OK)
8. Re-run verification; record any remaining issues.
9. Update STATUS.md with findings and decisions.
10. Add widgets_values audit script and documentation.
    - Done (tools/check_widgets_values.py, WIDGETS_VALUES_NOTES.md)
11. Add workflow scan/fix tools for widgets_values and run them.
    - Done (tools/scan_workflows_widgets.py, tools/fix_workflows_widgets.py)
12. Create minimal repro workflow and enable frontend debug logging for widgets_values migration.
    - Done (tools/extract_repro_workflow.py, workflow_repro_widgets_values.json, debug hook in frontend)
13. Run repro workflow in ComfyUI_frontend with `window.__WIDGETS_DEBUG__ = true` and capture logs.
14. Add frontend-free migration simulation and validate workflow-side workaround.
    - Done (tools/simulate_widgets_values_migration.py, tools/widgets_values_simulation_report.json)
15. Validate UI after workflow-side workaround in ComfyUI.
