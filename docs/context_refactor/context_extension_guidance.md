# Context Schema Extension Guidance

## Goal

Keep future feature work aligned with the context-first architecture and avoid
reintroducing socket sprawl.

Related documents:
- [Context Refactor Summary](./README.md)
- [Archive Index](./archive/README.md)

## Rules For New Data

1. Prefer extending `extras` over adding new top-level fields.
2. Add a new top-level field only when many nodes need the value as a primary
   concept and it materially changes routing or semantics.
3. Keep transport fields serializable to plain JSON without custom encoders.
4. Avoid adding new string sockets to multiple nodes when the same value can be
   stored in `context_json`.

## Where To Put Data

- Use top-level fields for primary scene concepts:
  - `subj`
  - `costume`
  - `loc`
  - `action`
- Use `meta` for lightweight control data:
  - `mood`
  - `style`
  - `tags`
- Use `extras` for derived or optional data:
  - expanded prompts
  - palettes
  - garnish text
  - staging tags
  - future negative or camera descriptors

## Implementation Pattern

When adding a new stage:

1. Extend `core/schema.py` defaults if the new field should always exist.
2. Add codec normalization if legacy payloads need migration support.
3. Implement shared logic in `pipeline/` first.
4. Add or update a context-native node in `nodes_context.py`.
5. Only then decide whether a legacy wrapper is still necessary.

## Backward Compatibility

1. New context-native nodes should not rely on `forceInput` unless there is a
   hard technical requirement.
2. Legacy wrappers should preserve their public output shapes.
3. If a legacy node must accept new data, prefer reading it from context via a
   bridge node instead of widening its public socket surface.
4. Do not add new feature-only widgets or sockets to legacy wrappers; add the
   capability to the context-first flow first and backport only when a
   compatibility fix truly requires it.
5. If a legacy wrapper becomes hard to maintain, document the migration path
   instead of re-expanding the wrapper API.

## Validation Expectations

For schema-affecting changes:

1. Add or update unit tests for schema, codec, and pipeline logic.
2. Add or update workflow sample checks when widget serialization can change.
3. Update the current documentation entry points if the public architecture changed.
4. Add detailed rationale to `docs/context_refactor/archive/` only when the change needs historical traceability.
