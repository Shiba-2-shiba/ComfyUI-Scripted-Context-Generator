# PromptContext v2 Refactor Spec

## Purpose

This document defines the target architecture for migrating the custom node pack
from many field-to-field string connections to a context-first pipeline.

The end state is a new formal node family that passes a single serialized
`PromptContext` object between stages, with legacy nodes retained only as
compatibility wrappers during the transition.

Related documents:
- [Task Plan](./context_v2_tasks.md)
- [Progress Log](./context_v2_progress.md)
- [Architecture Snapshot](../../assets/ARCHITECTURE.md)

## Goals

1. Replace wide string-based node I/O with a single `context_json` transport.
2. Reduce frontend workflow load/save instability caused by many `forceInput`
   fields and many linked string sockets.
3. Preserve deterministic generation behavior and seed semantics.
4. Keep old workflows usable during migration through compatibility wrappers.
5. Make future features additive by extending context fields instead of adding
   more node sockets.

## Non-Goals

1. Removing all legacy nodes immediately.
2. Switching the whole package to ComfyUI V3 registration in the same change.
3. Redesigning vocabulary content or generation heuristics as part of the
   transport refactor.

## Design Principles

1. New formal transport is `context_json: STRING`.
2. Nodes must tolerate empty or malformed context input and recover with a
   default empty context rather than raising exceptions.
3. Core generation logic should become context-to-context helper functions
   independent of node wrapper shape.
4. Top-level schema should stay small and stable; fast-changing or optional
   fields belong in `extras`.
5. Debug and trace data should be preserved, but must not be required for
   successful generation.

## Transport Choice

### Formal Transport

- Type: `STRING`
- Name: `context_json`
- Serialization: UTF-8 JSON

### Why `STRING` instead of `DICT`

1. Existing workflow/frontend compatibility is better with plain string inputs.
2. The current codebase already handles JSON string transport safely in several
   places.
3. Save/load behavior is more predictable than custom dict-heavy workflows.

`DICT` outputs remain allowed for debug or temporary helpers, but are not the
primary transport for the new pipeline.

## PromptContext v2 Schema

```json
{
  "context_version": "2.0",
  "seed": 0,
  "subj": "",
  "costume": "",
  "loc": "",
  "action": "",
  "meta": {
    "mood": "",
    "style": "",
    "tags": {}
  },
  "extras": {
    "character_name": "",
    "hair_color": "",
    "eye_color": "",
    "personality": "",
    "color_palette": [],
    "character_palette_str": "",
    "clothing_prompt": "",
    "location_prompt": "",
    "garnish": "",
    "staging_tags": "",
    "raw_costume_key": "",
    "raw_loc_tag": ""
  },
  "history": [],
  "warnings": []
}
```

## Field Semantics

### Required top-level keys

- `context_version`
  - String version marker for migration logic.
- `seed`
  - Canonical seed value for context-aware stages.
- `subj`
  - Main subject description.
- `costume`
  - Short costume key or short costume phrase.
- `loc`
  - Short location tag or short location phrase.
- `action`
  - Main action phrase.
- `meta`
  - Structured mood/style/tags object.
- `extras`
  - Optional detail storage for expanded or derived fields.
- `history`
  - Ordered per-stage trace entries.
- `warnings`
  - Top-level non-fatal warnings.

### `meta`

- `mood`
  - Short mood key or mood phrase.
- `style`
  - Style hint or style phrase.
- `tags`
  - Arbitrary scene metadata dict.

### `extras`

The following keys are part of the initial v2 baseline and should be treated as
stable public keys for the first migration wave.

- `character_name`
- `hair_color`
- `eye_color`
- `personality`
- `color_palette`
- `character_palette_str`
- `clothing_prompt`
- `location_prompt`
- `garnish`
- `staging_tags`
- `raw_costume_key`
- `raw_loc_tag`

Additional keys may be added later, but new top-level keys should be avoided
unless they are transport-wide concerns.

### `history` entry format

```json
{
  "node": "SceneVariator",
  "seed": 0,
  "decision": {},
  "warnings": []
}
```

History is for traceability, diagnostics, and evaluation. It must not be the
only place where business-critical output is stored.

## Validation Rules

All context-aware nodes must apply these rules when reading `context_json`.

1. Empty string input produces an empty default context.
2. Invalid JSON produces an empty default context and appends a warning.
3. Missing `context_version` is treated as legacy input and normalized.
4. Missing `meta` becomes `{ "mood": "", "style": "", "tags": {} }`.
5. Non-dict `meta.tags` becomes `{}`.
6. Missing `extras` becomes `{}`.
7. Missing `history` becomes `[]`.
8. Missing `warnings` becomes `[]`.
9. All scalar text fields are coerced to strings.

## New Node Family

These nodes define the target formal pipeline.

### `ContextSource`

Inputs:
- `json_string`
- `seed`
- `source_mode`

Outputs:
- `context_json`

Responsibilities:
- Create v2 context from raw JSON or `prompts.jsonl`
- Normalize to v2 schema

### `ContextCharacterProfile`

Inputs:
- `context_json` optional
- `mode`
- `character_name`
- `seed`

Outputs:
- `context_json`

Responsibilities:
- Update subject and character-related extras

### `ContextSceneVariator`

Inputs:
- `context_json`
- `seed`
- `variation_mode`

Outputs:
- `context_json`

Responsibilities:
- Update scene-compatible `loc` and `action`
- Append history entry

### `ContextClothingExpander`

Inputs:
- `context_json`
- `seed`
- `outfit_mode`
- `outerwear_chance`

Outputs:
- `context_json`

Responsibilities:
- Read `costume` or `extras.raw_costume_key`
- Write `extras.clothing_prompt`

### `ContextLocationExpander`

Inputs:
- `context_json`
- `seed`
- `mode`
- `lighting_mode`

Outputs:
- `context_json`

Responsibilities:
- Read `loc` or `extras.raw_loc_tag`
- Write `extras.location_prompt`

### `ContextMoodExpander`

Inputs:
- `context_json`
- `seed`
- `json_path`
- `default_value`

Outputs:
- `context_json`

Responsibilities:
- Expand mood-related fields
- Update `meta.mood` and `extras.staging_tags`

### `ContextGarnish`

Inputs:
- `context_json`
- `seed`
- `max_items`
- `include_camera`
- `emotion_nuance`

Outputs:
- `context_json`

Responsibilities:
- Read action/mood/location/costume from context
- Write `extras.garnish`
- Append history entry

### `ContextPromptBuilder`

Inputs:
- `context_json`
- `template`
- `composition_mode`
- `seed`

Outputs:
- `prompt_text`

Responsibilities:
- Build final prompt from normalized context
- Prefer expanded prompt fields in `extras` when present

### `ContextInspector`

Inputs:
- `context_json`

Outputs:
- `pretty_json`
- `summary_text`

Responsibilities:
- Human-readable debugging

## Compatibility Layer

Legacy nodes remain during migration, but should become thin wrappers over the
new context-based pipeline functions.

Wrapper policy:
1. Accept legacy field inputs.
2. Convert fields to context.
3. Call shared context-aware logic.
4. Convert results back to legacy field outputs if needed.

Target legacy wrappers:
- `SceneVariator`
- `GarnishSampler`
- `SimpleTemplateBuilder`
- `DictionaryExpand`
- `ThemeClothingExpander`
- `ThemeLocationExpander`

## Shared Code Layout

Target file split:

- `core/schema.py`
  - v2 dataclasses and schema defaults
- `core/context_codec.py`
  - parse, serialize, migrate, normalize helpers
- `core/context_ops.py`
  - patch/merge/update helpers
- `pipeline/context_pipeline.py`
  - reusable context-to-context business logic
- `nodes_context.py`
  - new formal context node family
- existing `nodes_*.py`
  - legacy wrappers only

## Workflow Strategy

Two workflow examples should exist during migration.

1. Legacy sample
   - Current field-based workflow
   - Kept for compatibility and bug reproduction

2. Context sample
   - New one-line context pipeline
   - Becomes the recommended workflow in README

## Migration Strategy

### Phase A

- Reduce `forceInput` usage in legacy nodes.
- Add bridge helpers and schema utilities.

### Phase B

- Extract shared context-based logic from existing nodes.
- Add new context node family.

### Phase C

- Publish new workflow and documentation.
- Mark legacy nodes as `Legacy` in display names.

### Phase D

- Retire legacy nodes only after the new workflow is stable and documented.

## Resolved Decisions

These implementation decisions were finalized during the refactor and should be
treated as the current baseline unless a later follow-up reopens them.

1. `seed` mirrors the latest stage seed provided to the context-aware node that
   produced the current payload.
2. `ContextPromptBuilder` emits prompt text only; the context remains available
   upstream for inspection or reuse.
3. `history` stores stage-level trace entries, but full legacy `debug_info`
   payloads are not duplicated wholesale when the summary signal is sufficient.
4. `ContextMoodExpander` remains a separate node so mood/staging expansion can
   be inserted, omitted, or reordered independently.
