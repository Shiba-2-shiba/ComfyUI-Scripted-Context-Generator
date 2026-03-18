# Mixed-Mode Bridge Workflow Archive

This appendix preserves the original mixed-mode bridge workflow reference for
historical migration work. It is not part of the active public workflow
guidance and should not be treated as a long-term supported architecture.

## Purpose

This archived note describes a practical mixed-mode workflow that combined the
context transport with the legacy field-based nodes during the migration phase.

Use this only when reviewing historical cutover steps or maintaining the
remaining dedicated bridge tests.

Related documents:
- [Current Migration Note](../context_migration_notes.md)
- [Archived Detailed Migration Notes](./context_migration_notes.md)
- [Cutover Plan](./context_cutover_plan.md)
- [Progress Log](../context_v2_progress.md)

## Archived Mixed-Mode Flow

1. `PackParser`
2. `FieldsToContext`
3. Optional `ContextPatch`
4. `ContextToFields`
5. Existing legacy generation nodes
6. `SimpleTemplateBuilder`
7. `PromptCleaner`

## Archived Connection Example

### Stage 1: Build context from legacy source

`PackParser` outputs:
- `subj`
- `costume`
- `loc`
- `action`
- `meta_mood`
- `meta_style`
- `scene_tags`

Connect these into `FieldsToContext`:
- `subj -> subj`
- `costume -> costume`
- `costume -> raw_costume_key`
- `loc -> loc`
- `loc -> raw_loc_tag`
- `action -> action`
- `meta_mood -> meta_mood`
- `meta_style -> meta_style`
- `scene_tags -> scene_tags`
- same seed source -> `seed`

Result:
- `FieldsToContext.context_json`

### Stage 2: Optional structured edits

Use `ContextPatch` when you want to adjust the context without adding many
string sockets.

Example `patch_json`:

```json
{
  "meta": {
    "tags": {
      "time": "golden hour"
    }
  },
  "extras": {
    "staging_tags": "warm backlight, quiet framing"
  }
}
```

Recommended connection:
- `FieldsToContext.context_json -> ContextPatch.context_json`

If no patch is needed, connect `FieldsToContext.context_json` directly into
`ContextToFields`.

### Stage 3: Expand context back into legacy fields

Use `ContextToFields` as the fan-out point for legacy nodes.

Important outputs:
- `subj`
- `costume`
- `raw_costume_key`
- `loc`
- `raw_loc_tag`
- `action`
- `meta_mood`
- `meta_style`
- `scene_tags`
- `garnish`
- `staging_tags`
- `clothing_prompt`
- `location_prompt`
- `personality`
- `character_palette_str`

### Stage 4: Feed legacy nodes

#### ThemeClothingExpander

Connect:
- `ContextToFields.raw_costume_key -> ThemeClothingExpander.theme_key`
- `ContextToFields.character_palette_str -> ThemeClothingExpander.character_palette`
- shared seed -> `seed`

#### ThemeLocationExpander

Connect:
- `ContextToFields.raw_loc_tag -> ThemeLocationExpander.loc_tag`
- shared seed -> `seed`

#### GarnishSampler

Connect:
- `ContextToFields.action -> action_text`
- `ContextToFields.meta_mood -> meta_mood_key`
- `ContextToFields.loc -> context_loc`
- `ContextToFields.raw_costume_key -> context_costume`
- `ContextToFields.scene_tags -> scene_tags`
- `ContextToFields.personality -> personality`
- shared seed -> `seed`

### Stage 5: Build prompt with legacy builder

Connect into `SimpleTemplateBuilder`:
- `ContextToFields.subj -> subj`
- `ThemeClothingExpander.clothing_prompt -> costume`
- `ThemeLocationExpander.location_prompt -> loc`
- `ContextToFields.action -> action`
- `GarnishSampler.garnish_string -> garnish`
- `ContextToFields.meta_mood -> meta_mood`
- `ContextToFields.meta_style -> meta_style`
- `ContextToFields.staging_tags -> staging_tags`
- shared seed -> `seed`

Then:
- `SimpleTemplateBuilder.built_prompt -> PromptCleaner.text`

## Why this was useful

1. Existing workflows could start carrying a context object without replacing
   all current nodes at once.
2. Context edits became possible through a single `patch_json` field.
3. Later context-native nodes could be swapped in stage by stage while
   preserving the surrounding graph.

## Historical Limitations

1. This was still a hybrid graph and kept the fan-out back into legacy fields.
2. `ContextToFields` exposed a broad output surface because the legacy nodes
   did not share a single context API.
3. Legacy nodes still exposed field-based public interfaces, so mixed-mode
   graphs kept some socket sprawl even though the core generation logic lived
   in shared context-aware helpers.

## Historical Exit Condition

After validating this mixed-mode setup, each `ContextToFields -> legacy node`
segment was expected to be replaced with the corresponding `Context*` node so
the graph could stay on `context_json` end to end.
