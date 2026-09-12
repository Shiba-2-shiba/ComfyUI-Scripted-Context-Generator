# EPIG-Informed Emotion Expression Task Board

Last updated: 2026-06-15

Legend:

- `[ ]` not started
- `[~]` in progress
- `[x]` done
- `[!]` blocked or needs decision

## P0: Documentation and Baseline

- [x] EE-000 Analyze current garnish / mood / prompt rendering pipeline
- [x] EE-001 Review `2606.13247v1.pdf` and extract EPIG implementation-relevant points
- [x] EE-002 Decide initial implementation shape: EPIG-lite / subject-only / no new dependency
- [x] EE-003 Create detailed implementation specification
- [x] EE-004 Create progress tracker
- [x] EE-005 Create task board
- [x] EE-006 Capture a small baseline sample fixture for representative moods
- [x] EE-007 Record exact focused test commands before implementation starts

Baseline sample candidates:

- `quiet_focused` + reading / studying
- `peaceful_relaxed` + sitting / waiting
- `energetic_joy` + running / dancing
- `melancholic_sadness` + standing / looking down
- `creepy_fear` + waiting / hiding
- `intense_anger` + arguing / battle

## P1: VAD Metadata Introduction

- [x] EE-101 Add small VAD profile data source
- [x] EE-102 Add loader/helper for VAD profiles
- [x] EE-103 Map all existing `EMOTION_CATEGORIES` to VAD coordinates
- [x] EE-104 Map legacy mood keys to VAD-aware categories
- [x] EE-105 Add tests for VAD coordinate range validation
- [x] EE-106 Add tests for complete category coverage
- [x] EE-107 Add tests for legacy mood resolution coverage
- [x] EE-108 Verify no runtime output changes except debug-only additions

Focused commands:

```bash
python -m unittest assets.test_personality_garnish
python -m unittest assets.test_mood_builder assets.test_mood_map_repetition_controls
```

## P2: VAD-Aware Target Emotion Resolution

- [x] EE-201 Add target VAD resolution helper
- [x] EE-202 Preserve existing direct legacy mood behavior where possible
- [x] EE-203 Apply `emotion_nuance` as VAD/category bias
- [x] EE-204 Apply `action_load` as arousal bias for tense/active/calm contexts
- [x] EE-205 Keep personality bias as weak category prior
- [x] EE-206 Add debug keys for `target_vad`, `target_source`, and `emotion_core`
- [x] EE-207 Add tests for calm/focus low-arousal behavior
- [x] EE-208 Add tests for fear/anxiety high-arousal behavior
- [x] EE-209 Add tests for tense action arousal increase
- [x] EE-210 Confirm determinism for repeated seed/input

Focused commands:

```bash
python -m unittest assets.test_personality_garnish
python -m unittest assets.test_determinism
```

## P3: VAD-Aware Descriptor Ranking

- [x] EE-301 Add descriptor-level VAD or inherit category VAD as first pass
- [x] EE-302 Implement Euclidean VAD distance helper
- [x] EE-303 Implement `alpha = exp(-gamma * distance)` debug scoring
- [x] EE-304 Use VAD ranking to build candidate pools before seeded selection
- [x] EE-305 Keep `max_items` enforcement unchanged
- [x] EE-306 Keep `_is_out_of_context()` filtering in the final path
- [x] EE-307 Keep `sanitize_sequence()` and dedupe behavior
- [x] EE-308 Add tests for `max_items=1/2/3/5`
- [x] EE-309 Add tests for descriptor ranking determinism
- [x] EE-310 Add tests that calm/focus do not overproduce face-forward tags

Focused commands:

```bash
python -m unittest assets.test_personality_garnish
python -m unittest assets.test_prompt_renderer
```

## P4: Role-Aware Debug and Guardrails

- [x] EE-401 Add debug field `emotion_role_mode: subject_only`
- [x] EE-402 Add debug fields for subject/stimulus/context source fields
- [x] EE-403 Confirm `ctx.action` is treated as stimulus for debug/filtering
- [x] EE-404 Confirm `ctx.loc` and `meta.mood` are treated as context for debug/filtering
- [x] EE-405 Add regression test that context descriptors are not inserted by default
- [x] EE-406 Add regression test that public node sockets are unchanged
- [x] EE-407 Add workflow widget compatibility check if node metadata changes

Focused commands:

```bash
python tools/check_widgets_values.py
python -m unittest assets.test_context_nodes assets.test_node_registry
```

## P5: Evaluation and Audit

- [x] EE-501 Define emotion embodiment rate checker
- [x] EE-502 Define arousal bucket consistency checker
- [x] EE-503 Define semantic drift proxy for unexpected context/style terms
- [x] EE-504 Add representative sample cases
- [x] EE-505 Add audit script or focused unittest
- [x] EE-506 Record before/after sample outputs in progress doc
- [x] EE-507 Confirm high-arousal categories differ from low-arousal categories in aggregate
- [x] EE-508 Confirm daily-life calm/focus prompts remain restrained

Candidate command:

```bash
python tools/audit_emotion_vad_alignment.py
```

If implemented as unittest:

```bash
python -m unittest assets.test_emotion_vad_alignment
```

## P6: Optional Context Descriptor Experiment

Do not begin until P1-P5 are verified.

- [ ] EE-601 Decide whether context descriptors are needed
- [ ] EE-602 Define explicit feature flag or hidden experiment path
- [ ] EE-603 Add context descriptor data separately from subject descriptors
- [ ] EE-604 Add semantic-drift guardrails before enabling any context descriptor
- [ ] EE-605 Test landscape/object-centered cases separately
- [ ] EE-606 Keep default behavior subject-only unless evaluation proves improvement

## Final Verification Gate

- [x] EE-900 Run focused garnish and mood tests
- [x] EE-901 Run prompt renderer and snapshot tests
- [x] EE-902 Run semantic policy and vocab lint tests
- [x] EE-903 Run prompt data validation
- [x] EE-904 Run full asset unittest discovery
- [x] EE-905 Run full flow verification
- [x] EE-906 Update `docs/emotion_epig/progress.md` with actual results
- [x] EE-907 Record remaining risks and deferred context descriptor work

Commands:

```bash
python -m unittest assets.test_personality_garnish
python -m unittest assets.test_mood_builder assets.test_mood_map_repetition_controls
python -m unittest assets.test_prompt_renderer assets.test_prompt_snapshots
python -m unittest assets.test_vocab_lint assets.test_semantic_policy assets.test_policy_alignment
python tools/validate_prompt_data.py
python -m unittest discover -s assets -p "test_*.py"
python tools/verify_full_flow.py
```
