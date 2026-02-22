RUNBOOK

Purpose
This runbook defines how to validate that the example workflow fully exercises
all custom node functionality, and how to update the workflow if gaps are found.

Prerequisites
- Python available on PATH
- Repo root as working directory

Inputs
- ComfyUI-workflow-exmaple.json
- workflow_repro_widgets_values.json
- Node implementations in repo root (nodes_*.py)
- Vocab and templates in vocab/ and templates.txt
 - (Optional) ComfyUI_frontend for debug logging
- tools/widgets_values_simulation_report.json

Procedure
1. Inventory nodes
   - Inspect nodes_*.py files.
   - Record each node's inputs/outputs and behavioral branches.

2. Workflow mapping
   - Parse ComfyUI-workflow-exmaple.json.
   - Build a node graph (IDs, types, connections).
   - Compare against the node inventory.

3. Verification script
   - Create tools/verify_full_flow.py (name may change).
   - For each node, build test cases to hit:
     - default behavior
     - optional parameters
     - edge conditions (empty inputs, missing keys)
   - Ensure deterministic seeds.

4. Execute verification
   - Run the verification script from repo root.
   - Capture outputs and failures.

5. Workflow corrections
   - Update ComfyUI-workflow-exmaple.json to reflect any missing nodes or
     parameters needed to fully use functionality.
   - Re-run verification to confirm coverage.

6. widgets_values UI misalignment debug (ComfyUI_frontend)
   - Enable debug flag in DevTools console:
     - `window.__WIDGETS_DEBUG__ = true`
   - Load `workflow_repro_widgets_values.json`
   - Inspect Console log entries: `widgets_values debug`
   - Confirm whether migrate removes forceInput dummy values incorrectly
     for nodes with implicit seed control widgets.

7. widgets_values migration simulation (frontend-free)
   - Run `python tools/simulate_widgets_values_migration.py`
   - Review `tools/widgets_values_simulation_report.json`
   - If misalignment is detected, apply workflow-side workaround:
     - DictionaryExpand widgets_values -> ["mood_map.json", "", 0]
     - ThemeLocationExpander widgets_values -> [0, "randomize"]
     - PromptCleaner widgets_values -> ["", "nl", true]
   - Re-run simulation to confirm assigned widgets match expectations.

Commands (placeholders)
- Inspect repo contents:
  - `rg --files`
- Run verification (once implemented):
  - `python tools/verify_full_flow.py`
- Build minimal repro workflow:
  - `python tools/extract_repro_workflow.py`
- Simulate migration (frontend-free):
  - `python tools/simulate_widgets_values_migration.py`

Outputs
- Verification report in stdout (and optionally a file if implemented).
- Updated ComfyUI-workflow-exmaple.json.
