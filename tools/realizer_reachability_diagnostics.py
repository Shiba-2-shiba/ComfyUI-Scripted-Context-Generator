"""Read-only R43 diagnostics of captured runtime evidence, never new permission.

Constructor recognition and producer-origin binding are separate measurements.
Exact final-output equality certifies only equivalence to this ordinary output;
it does not establish semantic safety of a different ordering or hidden atoms.
"""
from collections import Counter
from dataclasses import replace

from core.schema import ActionFrame
from nodes_prompt_cleaner import PromptCleaner
from pipeline.prompt_realizer import ContentPlan, _V2_IMPLEMENTED_FAMILIES, realize_content_plan
from pipeline import syntax_family_selector as selector
from pipeline import v2_direct_provenance as direct
from pipeline.v2_leaf_grammar import derive_action_grammar, gaze
from pipeline.v2_scene_provenance import producer_scene_parts
from pipeline.v2_structural_evidence import build_structural_evidence
from pipeline.v2_template_provenance import scene_template_kind
from vocab.loader import load_json
from vocab.syntax_families import BASELINE_FAMILY, CATALOG_FILENAME


def _domain(supported, binding=None, *, basis="NOT_AVAILABLE", blockers=()):
    return {
        "constructor_supported": supported, "grammar_known": True if supported else None,
        "binding_success": binding, "binding_basis": basis,
        "runtime_available": supported is True and binding is True,
        "audit_only": False, "unknown": supported is not True or binding is None,
        "blockers": sorted(set(blockers)),
    }


def _components(bridge):
    values = dict(bridge["replacements"])
    frame = ActionFrame.from_dict(bridge["frame"])
    action = values.get("{action}", "")
    replay = build_structural_evidence(frame, action)
    grammar = derive_action_grammar(replay)
    # Match the two existing action constructor paths independently of the
    # compound direct constructor, which can fail on unrelated clothes/scene.
    pieces = action.split(", ")
    legacy_action = bool(action) and (
        pieces[0] in direct._PRIMARY or direct.predicate(pieces[0])) and all(
            part in direct._SHARED | direct._TEMPORAL or direct.predicate(part) or direct.temporal(part)
            for part in pieces[1:])
    _, common_surface, independent_subject = selector._action_structure(selector._text(action))
    action_known = grammar.frame_predicate_safe is True or legacy_action or bool(common_surface)
    slots = bridge["input_plan"]["semantic_slots"]
    raw_subject = values.get("{subj}", "")
    subject = direct._subject(raw_subject) is not None
    # The existing common route has its own narrow subject constructor.
    if not subject:
        subject = bool(selector._SUBJECT.fullmatch(selector._text(raw_subject)))
    palette = (bridge.get("producer_context") or {}).get("character_palette", ())
    clothing = direct._clothes(values.get("{costume}", ""), character_palette=palette) is not None
    location, mood = values.get("{loc}", ""), values.get("{meta_mood}", "")
    location_key = frame.legacy_slots.get("location")
    scene = (direct._scene_parts(location, mood, location_key) is not None
             or producer_scene_parts(location, location_key) is not None
             or selector._scene_anchor(selector._text(location)) is not None)
    template = scene_template_kind(slots) is not None
    garnish_text = values.get("{garnish}", "")
    garnish = all(part in direct._GARNISH or gaze(part)
                  for part in (garnish_text.split(", ") if garnish_text else ()))
    mood_known = mood in direct._MOODS
    action_blockers = []
    binding = True if replay is not None else None
    if frame.legacy_text and frame.legacy_text != action:
        binding = False
        action_blockers.append("binding.frame_current_text_mismatch")
    elif replay is None:
        action_blockers.append("binding.replay_mismatch")
    if not action_known:
        action_blockers.append("action.leaf_grammar_unknown")
    if grammar.independent_action_subject is True or independent_subject is True:
        action_blockers.append("action.independent_subject")
    if grammar.same_subject_attachment_safe is None and not legacy_action and independent_subject is not False:
        action_blockers.append("action.same_subject_unknown")
    if not action_known:
        action_blockers.append("action.polarity_unproved")
    domains = {
        "subject": _domain(subject, blockers=() if subject else ("subject.unsupported_constructor",)),
        "clothing": _domain(clothing, blockers=() if clothing else
                            ("clothing.owner_unknown", "clothing.number_unknown")),
        "action": _domain(action_known, binding,
                          basis="exact_current_action_producer_replay" if replay else "NOT_AVAILABLE",
                          blockers=action_blockers),
        "scene": _domain(scene, blockers=() if scene else
                         ("scene.source_field_unknown", "scene.attachment_unknown")),
        "template": _domain(template, True if template else None,
                            basis="exact_catalog_topology" if template else "NOT_AVAILABLE",
                            blockers=() if template else ("template.topology_unsupported",)),
        "garnish": _domain(garnish, blockers=() if garnish else ("garnish.attachment_unknown",)),
        "mood": _domain(mood_known, blockers=() if mood_known else ("mood.attachment_unknown",)),
    }
    domains["action"]["facts"] = {
        key: getattr(grammar, key) for key in (
            "frame_predicate_safe", "same_subject_attachment_safe",
            "independent_action_subject", "no_place_reference")
    }
    domains["action"]["facts_basis"] = "structural_leaf_grammar_only"
    domains["action"]["constructor_paths"] = {
        "structural": grammar.frame_predicate_safe is True,
        "legacy_direct": bool(legacy_action), "simple_legacy_compatible": bool(common_surface),
    }
    return domains


def _reason_id(reason):
    aliases = {
        "unsupported_subject": "subject.unsupported_constructor",
        "policy_or_solo_conflict": "policy.conflict",
        "unsupported_scene_anchor": "scene.attachment_unknown",
        "unsupported_or_mismatched_surface": "action.leaf_grammar_unknown",
        "rendered_clause_mismatch": "binding.frame_current_text_mismatch",
        "direct_provenance_mismatch": "binding.source_ambiguity",
        "direct_scene_scope_not_proven": "family.legacy_route_ceiling",
        "surface_not_allowed": "action.surface_not_allowed",
        "role_mismatch": "family.role_mismatch",
        "unresolved_placeholder": "binding.unresolved_placeholder",
    }
    if reason in aliases:
        return aliases[reason]
    for prefix in ("required_fact_not_true:", "forbidden_fact_not_false:", "missing_slot:"):
        if reason.startswith(prefix):
            return "family." + prefix.rstrip(":") + "." + reason[len(prefix):]
    return "family.unclassified_rejection"


def _common_evidence(bridge):
    from pipeline.realization_evidence import build_realization_evidence

    return build_realization_evidence(bridge["common_inputs"])


def _common_components(bridge):
    """Read the current typed adapters; legacy text recognition grants no binding."""
    from pipeline.realization_evidence import Truth

    domains = {}
    for component in _common_evidence(bridge).components:
        bound = component.trace is not None
        known = (bool(component.atoms) or component.domain == "garnish") and all(
            atom.grammar_known is Truth.TRUE for atom in component.atoms)
        row = _domain(known, True if bound else None,
                      basis=component.trace.mode if bound else "NOT_AVAILABLE",
                      blockers=component.blockers)
        row.update(runtime_available=component.runtime_available,
                   unknown=not component.runtime_available or not known,
                   facts={key: {Truth.TRUE: True, Truth.FALSE: False, Truth.UNKNOWN: None}[value]
                          for key, value in component.facts},
                   facts_basis="common_typed_evidence")
        domains[component.domain] = row
    return domains


def _kind(identifier):
    if identifier == "policy.conflict":
        return "policy"
    if identifier in {"action.independent_subject", "binding.frame_current_text_mismatch"}:
        return "hard_rejection"
    if identifier in {"family.legacy_route_ceiling",
                      "family.role_mismatch", "family.composition_mode_disabled", "action.surface_not_allowed"}:
        return "route"
    if identifier in {"family.constructor_missing", "subject.unsupported_constructor",
                      "template.topology_unsupported"}:
        return "unimplemented"
    return "unknown"


def _force(snapshot, family):
    # Only the parent caller's captured eligible set reaches this function.
    from prompt_renderer import _finalize_prompt

    bridge = snapshot["bridge"]
    if bridge.get("common_route") is True:
        # Re-prove from the current source plan and inputs, never from the
        # selected family's already materialized slots or serialized proof.
        requested = replace(ContentPlan(**bridge["input_plan"]), syntax_family=family)
        template, debug = realize_content_plan(
            requested, realization_evidence=_common_evidence(bridge),
            builder_inputs=bridge["common_inputs"], return_debug=True,
        )
    else:
        plan = ContentPlan(**bridge["concrete_plan"])
        provenance = bridge.get("direct_provenance")
        evidence = None
        if bridge.get("structural_evidence_used"):
            evidence = build_structural_evidence(bridge["frame"], dict(bridge["replacements"]).get("{action}", ""))
        slots = plan.semantic_slots
        if provenance is not None:
            slots = direct.materialize_direct(provenance, bridge["frame"], syntax_family=family,
                                              structural_evidence=evidence)
            if slots is None:
                return {"status": "CONSTRUCTOR_FAILED", "constructor_v2": False}
        requested = replace(plan, syntax_family=family, semantic_slots=slots)
        template, debug = realize_content_plan(
            requested, action_frame=bridge["frame"], action_surface=bridge["surface"],
            direct_provenance=provenance, structural_evidence=evidence, return_debug=True,
        )
    actual_v2 = debug.get("realizer_version") == "v2" and debug.get("syntax_family") == family
    raw = _finalize_prompt(template, **snapshot["finalization"])
    cleaned = PromptCleaner().clean(text=raw)[0]
    ordinary_raw = snapshot["raw_prompt"]
    ordinary_cleaned = PromptCleaner().clean(text=ordinary_raw)[0]
    identical = raw == ordinary_raw and cleaned == ordinary_cleaned
    return {
        "status": "EXACT_ORDINARY_OUTPUT" if actual_v2 and identical else "NOT_AVAILABLE",
        "constructor_v2": actual_v2, "realizer_version": debug.get("realizer_version"),
        "syntax_family": debug.get("syntax_family"), "raw_prompt": raw, "cleaned_prompt": cleaned,
        "raw_exact_match": raw == ordinary_raw, "cleaned_exact_match": cleaned == ordinary_cleaned,
        "lexical_counter_equal_auxiliary": Counter(cleaned.split()) == Counter(ordinary_cleaned.split()),
        "semantic_scope": "Exact ordinary-output equivalence only; no atom/ownership certificate for changed output.",
    }


def diagnose_snapshot(snapshot, *, force_families=False):
    """Diagnose a detached Builder sink snapshot without mutating it or RNG."""
    bridge = snapshot["bridge"]
    if bridge is None:
        disabled = snapshot.get("finalization", {}).get("composition_mode") is False
        blocker = "family.composition_mode_disabled" if disabled else "transport.runtime_inputs_missing"
        families = {
            entry["key"]: {
                "declared": True, "constructor_present": entry["key"] in _V2_IMPLEMENTED_FAMILIES,
                "runtime_eligible": False, "baseline_marker": entry["key"] == BASELINE_FAMILY,
                "selected": False, "executed_v2": False, "constructor_v2": None,
                "forced_render_v2": None, "semantic_parity": "NOT_RUN", "forced": None,
                "blockers": [blocker],
            } for entry in sorted(load_json(CATALOG_FILENAME)["families"], key=lambda item: item["key"])
        }
        return {
            "domains": {domain: {**_domain(None), "status": "NOT_AVAILABLE"} for domain in
                        ("subject", "clothing", "action", "scene", "template", "garnish", "mood")},
            "families": families, "route": "fallback", "trace_mode": "none",
            "blockers": [{"id": blocker, "kind": _kind(blocker), "domains": [],
                          "families": list(families)}],
            "errors": [] if disabled else [{"id": blocker, "detail": "bridge snapshot unavailable"}],
        }
    common_route = bridge.get("common_route") is True
    domains = _common_components(bridge) if common_route else _components(bridge)
    common_proofs = {proof["family"]: proof for proof in bridge.get("common_proofs", ())}
    eligibility = bridge["eligibility"]
    direct_valid = eligibility.get("direct_provenance_valid", False)
    # The bridge has already filtered the baseline marker through its global
    # proof guard. A remaining baseline family is a genuine v2 constructor.
    selectable = set(bridge["selectable"])
    output = bridge.get("output_debug", {})
    actual_v2 = output.get("realizer_version") == "v2"
    route = ("common_evidence" if common_route else "legacy_direct" if direct_valid else
             "simple_legacy_compatible" if bridge["selectable"] else "fallback")
    trace_mode = ("common_evidence" if common_route else
                  "legacy_r4_structural" if bridge.get("structural_evidence_used") else "none")
    families, errors = {}, []
    ordinary_mismatch = bridge.get("selected") is not None and (
        not actual_v2 or output.get("syntax_family") != bridge["selected"])
    if ordinary_mismatch:
        errors.append({"id": "render.proof_constructor_mismatch", "family": bridge["selected"],
                       "detail": "ordinary_selected_constructor_not_executed_v2"})
    indexed = {}

    def record(identifier, *, domain=None, family=None):
        item = indexed.setdefault(identifier, {"id": identifier, "kind": _kind(identifier),
                                               "domains": [], "families": []})
        for field, value in (("domains", domain), ("families", family)):
            if value is not None and value not in item[field]:
                item[field].append(value)

    for domain, result in domains.items():
        for identifier in result["blockers"]:
            record(identifier, domain=domain)
    for entry in sorted(load_json(CATALOG_FILENAME)["families"], key=lambda item: item["key"]):
        family = entry["key"]
        eligible = family in selectable
        blockers = set()
        if not eligible and common_route:
            blockers.update(common_proofs.get(family, {}).get("blocker_ids", ()))
            blockers.update(identifier for result in domains.values() for identifier in result["blockers"])
        elif not eligible:
            blockers.update(_reason_id(reason) for reason in
                            eligibility.get("rejected_syntax_families", {}).get(family, ()))
            blockers.update(identifier for result in domains.values() for identifier in result["blockers"])
            if direct_valid and family not in eligibility.get("direct_supported_families", ()):
                blockers.add("family.legacy_route_ceiling")
            if eligibility.get("safety_facts", {}).get("scene_action_overlap") is None:
                blockers.add("scene.place_overlap_unknown")
            facts = eligibility.get("safety_facts", {})
            if facts.get("frame_predicate_safe") is not True:
                blockers.add("family.required_fact_not_true.frame_predicate_safe")
            if facts.get("scene_action_overlap") is True:
                blockers.add("family.forbidden_fact_not_false.scene_action_overlap")
        present = family in _V2_IMPLEMENTED_FAMILIES
        if not present:
            blockers.add("family.constructor_missing")
        if ordinary_mismatch and family == bridge["selected"]:
            blockers.add("render.proof_constructor_mismatch")
        row = {
            "declared": True, "constructor_present": present, "runtime_eligible": eligible,
            "baseline_marker": family == BASELINE_FAMILY and not eligible,
            "selected": bridge.get("selected") == family,
            "executed_v2": actual_v2 and output.get("syntax_family") == family,
            "constructor_v2": None, "forced_render_v2": None, "semantic_parity": "NOT_RUN",
            "forced": None,
        }
        if force_families:
            row["semantic_parity"] = "NOT_AVAILABLE"
            if not eligible:
                row["forced"] = {"status": "NOT_ELIGIBLE", "constructor_v2": None}
            else:
                try:
                    forced = _force(snapshot, family)
                except Exception as exc:
                    forced = {"status": "ERROR", "constructor_v2": False,
                              "error_type": type(exc).__name__}
                row["forced"] = forced
                row["constructor_v2"] = forced["constructor_v2"]
                if forced["constructor_v2"] is not True:
                    row["forced_render_v2"] = False
                    blockers.add("render.proof_constructor_mismatch")
                    if not any(error["id"] == "render.proof_constructor_mismatch" and
                               error.get("family") == family for error in errors):
                        errors.append({"id": "render.proof_constructor_mismatch", "family": family,
                                       "detail": forced["status"]})
                elif forced["status"] == "EXACT_ORDINARY_OUTPUT":
                    row["forced_render_v2"] = True
                    row["semantic_parity"] = "EXACT_ORDINARY_OUTPUT"
        row["blockers"] = sorted(blockers)
        families[family] = row
        for identifier in blockers:
            record(identifier, family=family)
    for item in indexed.values():
        item["domains"].sort()
        item["families"].sort()
    return {"domains": domains, "families": families, "route": route, "trace_mode": trace_mode,
            "blockers": [indexed[key] for key in sorted(indexed)], "errors": errors}
