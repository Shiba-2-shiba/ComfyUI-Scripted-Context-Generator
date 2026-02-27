# Decisions Log (Common)

Format:
- Date
- Decision
- Rationale
- Impacted Files

## Entries
- 2026-02-26: Initialized decisions log.
- 2026-02-27: Added `tools/run_bias_audit.py` to emit 8 audit CSVs in a single deterministic run.
  - Rationale: Keep bias diagnosis reproducible by seed and stage, matching the agreed audit schema.
  - Impacted Files: `tools/run_bias_audit.py`
- 2026-02-27: Reduced object concentration via both logic and data changes (ThemeLocationExpander/SceneVariator + vocab pools).
  - Rationale: Lower repeated surfboard/book/phone-style object bursts without breaking deterministic generation.
  - Impacted Files: `nodes_dictionary_expand.py`, `nodes_scene_variator.py`, `vocab/data/scene_compatibility.json`, `vocab/data/background_packs.json`, `vocab/data/action_pools.json`
