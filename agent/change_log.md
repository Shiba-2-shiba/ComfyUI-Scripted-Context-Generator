# Change Log (Common)

Format:
- Date
- Summary
- Files

## Entries
- 2026-02-26: Initialized change log.
- 2026-02-27: Fixed evaluation runner and implemented bias-audit + bias-control changes.
  - Files: `assets/eval_promptbuilder_v5.py`, `tools/run_bias_audit.py`, `nodes_dictionary_expand.py`, `nodes_scene_variator.py`, `vocab/data/scene_compatibility.json`, `vocab/data/background_packs.json`, `vocab/data/action_pools.json`, `assets/test_bias_controls.py`
- 2026-03-06: Added scene/emotion refactoring planning docs and agent tracking entries for the next implementation session.
  - Files: `assets/scene_emotion_priority_spec.md`, `assets/実装チェックリスト版.md`, `assets/進捗.md`, `agent/memory/session_notes.md`, `agent/decisions_log.md`, `agent/change_log.md`
- 2026-03-06: Implemented phases P0-P4 of the scene/emotion refactor and paused with P5 pending for the next chat.
  - Files: `assets/進捗.md`, `nodes_simple_template.py`, `templates.txt`, `vocab/templates_intro.txt`, `vocab/templates_body.txt`, `vocab/templates_end.txt`, `tools/run_bias_audit.py`, `vocab/garnish/logic.py`, `nodes_scene_variator.py`, `nodes_dictionary_expand.py`, `nodes_prompt_cleaner.py`, `mood_map.json`, `vocab/data/scene_compatibility.json`, `vocab/data/background_packs.json`, `vocab/data/action_pools.json`, `vocab/data/garnish_base_vocab.json`, `vocab/data/background_loc_tag_map.json`, `vocab/data/background_alias_overrides.json`, `assets/test_fx_cleanup.py`, `assets/test_vocab_lint.py`, `agent/memory/session_notes.md`, `agent/decisions_log.md`, `agent/change_log.md`
- 2026-03-06: Completed P5 by shifting default/composition templates from explanatory fragments to visual sentence assembly.
  - Files: `assets/進捗.md`, `nodes_simple_template.py`, `templates.txt`, `vocab/templates_intro.txt`, `vocab/templates_body.txt`, `vocab/templates_end.txt`, `agent/memory/session_notes.md`, `agent/decisions_log.md`, `agent/change_log.md`
- 2026-03-06: Completed P6 by extending bias audit with final-prompt quality metrics, per-sample quality CSVs, and gate reporting.
  - Files: `tools/run_bias_audit.py`, `assets/test_bias_audit_metrics.py`, `vocab/data/background_packs.json`, `assets/進捗.md`, `agent/memory/session_notes.md`, `agent/decisions_log.md`, `agent/change_log.md`
- 2026-03-06: Ran a new object-concentration evaluation for the next refactor and documented hotspot classification for spec drafting.
  - Files: `assets/object_concentration_refactor_evaluation.md`, `agent/memory/session_notes.md`, `agent/decisions_log.md`, `agent/change_log.md`
- 2026-03-06: Implemented the object-concentration refactor with policy-based redistribution, phrase-aware audit normalization, and staged verification.
  - Files: `assets/object_concentration_refactor_spec.md`, `assets/object_concentration_refactor_verification.md`, `vocab/data/object_concentration_policy.json`, `nodes_dictionary_expand.py`, `nodes_scene_variator.py`, `tools/run_bias_audit.py`, `vocab/data/background_packs.json`, `vocab/data/action_pools.json`, `vocab/data/scene_axis.json`, `assets/test_bias_audit_metrics.py`, `assets/test_bias_controls.py`, `agent/memory/session_notes.md`, `agent/decisions_log.md`, `agent/change_log.md`
