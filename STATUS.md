Project: ComfyUI-Scripted-Context-Generator
Date: 2026-02-22

Goal
- Evaluate whether the current workflow (ComfyUI-workflow-exmaple.json) fully exercises all custom node functionality.
- If gaps exist, propose and implement workflow corrections.
- Build a comprehensive verification script in tools/ to validate all node features.

Current State
- Custom node source files are present in repo root.
- Example workflow JSON exists at ComfyUI-workflow-exmaple.json.
- Node inventory created (from nodes_*.py) and workflow gaps identified.
- Existing verification assets are in assets/.
- No new verification script has been created yet in tools/.
- Verification script added at tools/verify_full_flow.py (run once, passed).
- Added widgets_values audit script: tools/check_widgets_values.py (run once, passed).
- Added notes: WIDGETS_VALUES_NOTES.md.
- Fixed PromptCleaner mode in ComfyUI-workflow-exmaple.json.
- Added workflow scan/fix scripts:
  - tools/scan_workflows_widgets.py
  - tools/fix_workflows_widgets.py
- Ran scan/fix over repo workflows; current report shows no issues.
- UI issue unresolved: control-after-generate widget values still misaligned in ComfyUI UI (e.g., GarnishSampler, ThemeClothingExpander).
- Latest attempted fix: reinserted explicit "randomize" control values immediately after seed in widgets_values for seed-bearing nodes in ComfyUI-workflow-exmaple.json.
- Added debug logging hook in ComfyUI_frontend to inspect widgets_values migration
  (guarded by `window.__WIDGETS_DEBUG__ = true`).
- Added minimal repro workflow generator:
  - tools/extract_repro_workflow.py
  - Output: workflow_repro_widgets_values.json
- Added widgets_values migration simulation (frontend-free):
  - tools/simulate_widgets_values_migration.py
  - Output: tools/widgets_values_simulation_report.json
- Applied workflow-side workaround for UI misalignment:
  - DictionaryExpand widgets_values -> ["mood_map.json", "", 0]
  - ThemeLocationExpander widgets_values -> [0, "randomize"]
  - PromptCleaner widgets_values -> ["", "nl", true]
- Hardened node scripts against bad values:
  - nodes_dictionary_expand.py: coerce seed to int; validate mode/outfit_mode
  - nodes_prompt_cleaner.py: validate mode; coerce drop_empty_lines

Recent Changes
- Updated ComfyUI-workflow-exmaple.json to add ActionMerge and PromptCleaner.
- Connected PackParser.meta_style into SimpleTemplateBuilder.
- Routed action through ActionMerge and cleaned final prompt with PromptCleaner.
 - Added widgets_values debug log hook (frontend) and repro workflow tool.
 - Added widgets_values migration simulation tool and applied workflow/node defensive fixes.

Planned Approach (High Level)
1. Inventory nodes and their inputs/outputs from code.
2. Map the example workflow against node capabilities and required inputs.
3. Design a full-coverage test flow (script in tools/) that exercises every node feature.
4. Compare test flow expectations vs. workflow JSON; identify missing or miswired nodes/params.
5. Update workflow JSON and document changes.
6. Validate widgets_values migration in ComfyUI_frontend using repro workflow.

Open Questions
- Are there any implicit assumptions about ComfyUI version or node categories?
- Should the verification script run under ComfyUI, or is a pure-Python simulation acceptable?
- Are there constraints on random seeds or fixed outputs required for validation?
- Does migrateWidgetsValues incorrectly drop values when seed control widgets are implicit?
- Are there any remaining UI misalignments after workflow-side workaround?
