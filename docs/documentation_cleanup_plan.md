# Documentation Cleanup Plan

Last updated: 2026-05-08

## Goal

Reduce stale planning surfaces before the next implementation wave.

This cleanup is documentation-only. It should not change ComfyUI node runtime,
prompt generation, variation sizing, or validation behavior.

## Behavior Lock

Before and after cleanup, use these checks to confirm no data/runtime behavior
changed:

```bash
python assets/calc_variations.py --json
python tools/check_variation_scope.py
python tools/build_compatibility_review.py --check
python tools/build_action_pools.py --check
python -m unittest assets.test_calc_variations assets.test_variation_scope assets.test_build_compatibility_review assets.test_build_action_pools
```

## Scope

### `リファクタリング/`

Status: `delete redirect`

This directory only contained a redirect README pointing to
`docs/context_refactor/`. It was useful during migration, but it no longer owns
any current planning or reference material.

Decision:

- remove the root-level redirect directory from the tracked docs surface
- keep historical mentions inside archive files unchanged
- use `docs/context_refactor/README.md` as the context refactor entry point

### `docs/context_refactor/`

Status: `keep, but keep narrow`

Live files:

- `docs/context_refactor/README.md`
- `docs/context_refactor/context_extension_guidance.md`

Archive files:

- `docs/context_refactor/archive/*`

Decision:

- keep the two live files as the active entry points
- keep archive files only as historical records
- do not use archived task boards as active implementation plans
- add new rationale to archive only when a future context-schema change needs
  traceability

### `agent/`

Status: `deleted legacy inert docs`

The current repo does not show runtime or validation code reading `agent/`.
Search results show only documentation references outside the directory:

- `REPO_STRUCTURE.md` describes it as work logs / agent helper materials

The directory appears to be a historical agent package produced by older
workflow tooling. It does not appear to be the source of current Codex behavior;
current behavior is governed by `AGENTS.md` and the local `.codex` setup.

Decision:

- remove `agent/` from the tracked repo surface
- do not treat old archived references to `agent/` as active instructions
- do not reintroduce `agent/` logs for normal future code changes
- leave historical mentions in archived docs alone

## Cleanup Order

1. Remove obsolete redirect-only docs.
2. Tighten current docs so active entry points are clear.
3. Mark legacy agent docs as non-runtime and deletion-candidate.
4. Run behavior-lock checks.
5. Only then proceed with implementation work.

## Repo Policy After Cleanup

The repo policy is:

```text
Keep current project docs in docs/.
Keep implementation history in docs/*/archive/.
Do not keep old agent package state in repo.
```

`agent/` has been removed and should not be considered an active control
surface.
