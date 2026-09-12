# Prospective V150 scene-detail amendment

The v7 release review remains rejected and immutable. Its redundancy guard
reported 7 worse votes out of 40 (0.175, above the unchanged 0.10 limit).
The reviewer notes identified repeated readiness wording, greenhouse plants and
roof descriptions, plaza landmarks, and cabin porch descriptions. This directory
is a new preparation from `v150-final-v7-20260905`, with the actual recursive
input origins and hashes recorded in `preparation.json`.

## Cleanup plan and authoring choices

Keep place labels concise and give details separate roles: core describes fixed
fixtures, props names movable objects, texture describes surfaces, time supplies
the time of day, and crowd describes occupancy. Preserve setting richness and
all counted candidate inputs. The targeted assertions were added before editing
and first exposed 12 failing checks; all three tests now pass.

All 19 location packs retain two identity labels and at least four core fixtures,
four props, two textures, two time options and two occupancy descriptions. The
main repairs are:

- Fire station: readiness remains on the equipment board; time and occupancy
  describe evening and the interval between dispatches instead of repeating it.
- Greenhouse: seedlings and roof panels belong to individual core choices.
  Labels, lighting, surface and occupancy choices contribute other information.
- Public plaza: fountain and monument each belong to one core choice; paving
  geometry belongs to texture. The label no longer inventories these objects.
- Forest cabin: porch and firewood each have one core choice. Fireplace and stove
  are separate choices, preserving both fixtures without a compound inventory.
- Maker space and rooftop cafe: compound fixtures and tool lists were separated
  into complementary entries. Clear repeated occupancy descriptions in other
  packs were simplified using the same field roles.

`background-amendment.json` records all 50 changed fields, before/after values,
the changed override hash, and final effective catalog hash. The initial
preparation receipt describes the initial copied state; the amendment describes
the subsequent prospective authoring state. Historical authoring was not edited.
The initial snapshot-plan draft was removed because its input bindings preceded
the amendment; `build_prepared_snapshot_plan()` creates a fresh plan on demand.

## Validation and remaining work

Fresh structural analysis passes. Tests compare every subject definition and
every non-background location field with the source catalog, including all
19 location identities, compatibility tags and all 380 action records. Aliases
are unchanged. Therefore the inputs determining the existing exact
135 subjects / 109 locations / 8,227 rows / 150,184 variations remain unchanged.
The tests also preserve minimum richness and require the reviewed anchors to
remain present in exactly one background field, rather than deleting them.

No runtime code, policy, seed, review result or active data was changed. No full
suite, snapshot, generation or new review has run for this amendment. Rebuild
the source-bound snapshot plan after the independent attention-tail fix and
source freeze, then run the unchanged release checks. This amendment is not
quality approval or evidence of a passing review.
