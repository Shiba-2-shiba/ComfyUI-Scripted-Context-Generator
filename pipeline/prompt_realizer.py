"""Composition-mode content planning and final surface normalization."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any, Mapping, Sequence

try:
    from ..core.schema import ActionFrame
    from ..core.semantic_families import split_semantic_tags
    from ..core.semantic_policy import sanitize_text
    from ..vocab.seed_utils import mix_seed
except ImportError:
    from core.schema import ActionFrame
    from core.semantic_families import split_semantic_tags
    from core.semantic_policy import sanitize_text
    from vocab.seed_utils import mix_seed

from .action_parser import normalize_action_phrase
from .syntax_family_selector import candidate_family_safe, eligible_syntax_families
from .v2_template_provenance import scene_template_kind

_LEGACY_SYNTAX_FAMILIES = frozenset({"single-sentence-scene-tail", "two-sentence-scene-tail", "template-directed"})
_V2_IMPLEMENTED_FAMILIES = frozenset({
    "subject_action_scene", "subject_action__scene_tail", "scene_lead_subject_action",
    "action_lead_subject_scene", "subject_scene_action", "subject_action_scene_insert",
})
_V2_BASELINE = "subject_action_scene"


@dataclass(frozen=True)
class ContentPlan:
    semantic_slots: Mapping[str, str]
    discourse_roles: Sequence[str]
    clause_order: Sequence[str]
    syntax_family: str
    lexical_choice: str
    named_seed_streams: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_slots": dict(self.semantic_slots),
            "discourse_roles": list(self.discourse_roles),
            "clause_order": list(self.clause_order),
            "syntax_family": self.syntax_family,
            "lexical_choice": self.lexical_choice,
            "named_seed_streams": dict(self.named_seed_streams),
        }


def coerce_action_frame(value: ActionFrame | Mapping[str, Any] | None) -> ActionFrame:
    if isinstance(value, ActionFrame):
        return value
    return ActionFrame.from_dict(value)


def normalize_subject_to_girl(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\b1(?:woman|lady|female|girl)\b", "girl", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:woman|women|lady|female)\b", "girl", text, flags=re.IGNORECASE)
    return re.sub(r"\bgirl(?:\s+girl)+\b", "girl", text, flags=re.IGNORECASE)


_PERSON_DEMOGRAPHIC_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:black|african(?:[- ]american)?|afro(?:[- ]american)?|sub[- ]saharan(?: african)?|negro)\s+(?=(?:girl|woman|lady|female|person|people)\b)",
        r"\b(?:nigerian|ghanaian|kenyan|ethiopian|somali|sudanese|congolese|jamaican|haitian|caribbean|black british)\s+(?=(?:girl|woman|lady|female|person|people)\b)",
        r"\b(?:african[- ]american|afro[- ]american|sub[- ]saharan african|black person|black people)\b",
        r"\b(?:of\s+)?(?:african|nigerian|ghanaian|kenyan|ethiopian|somali|sudanese|congolese|jamaican|haitian|caribbean)\s+(?:descent|heritage|ancestry|features)\b",
        r"\b(?:afro[- ]textured|afrocentric)(?=\s+(?:hair|features|appearance)\b)",
        r"\b(?:dreadlocks?|cornrows?|box braids?|bantu knots?|afro(?: hairstyle)?|kinky hair|coily hair)\b",
        r"\b(?:very\s+)?(?:black|white|dark(?:er)?(?:[- ]brown)?|deep(?:ly)?(?:[- ]brown)?|light[- ]brown|brown|ebony|melanin[- ]rich|caramel|chocolate|mahogany|olive|tan(?:ned)?|light|fair|pale|porcelain|dusky|bronze|copper|golden|ruddy|beige|yellow)\s*(?:-| )skinned\b",
        r"\b(?:black|white|dark(?:[- ]brown)?|deep(?:[- ]brown)?|light[- ]brown|brown|ebony|melanin[- ]rich|caramel|chocolate|mahogany|olive|tan(?:ned)?|light|fair|pale|porcelain|dusky|bronze|copper|golden|ruddy|beige|yellow)\s+(?:skin(?:\s+tone)?|complexion)\b",
        r"\b(?:skin\s+(?:tone|color)|complexion)\s*(?::|is)?\s*(?:black|white|dark(?:[- ]brown)?|deep(?:[- ]brown)?|light[- ]brown|brown|ebony|caramel|chocolate|mahogany|olive|tan(?:ned)?|light|fair|pale|porcelain|dusky|bronze|copper|golden|ruddy|beige|yellow)\b",
    )
)


def find_person_demographic_descriptors(value: str) -> list[str]:
    text = str(value or "")
    return [match.group(0) for pattern in _PERSON_DEMOGRAPHIC_PATTERNS for match in pattern.finditer(text)]


def strip_person_demographic_descriptors(value: str) -> str:
    text = str(value or "")
    text = re.sub(
        r"\bwith\s+(?:dreadlocks?|cornrows?|box braids?|bantu knots?|afro(?: hairstyle)?|kinky hair|coily hair)\s*,\s*",
        "with ",
        text,
        flags=re.IGNORECASE,
    )
    for pattern in _PERSON_DEMOGRAPHIC_PATTERNS:
        text = pattern.sub("", text)
    return sanitize_text(text)


def filter_redundant_garnish(
    action: str,
    garnish: str,
    action_frame: ActionFrame | Mapping[str, Any] | None,
) -> tuple[str, list[str]]:
    frame = coerce_action_frame(action_frame)
    occupied = [
        str(action or "").strip().lower(),
        frame.posture.lower(),
        frame.hand_action.lower(),
        frame.gaze_target.lower(),
    ]
    kept: list[str] = []
    dropped: list[str] = []
    for tag in split_semantic_tags(garnish):
        lowered = tag.lower()
        if any(lowered == value or lowered in value for value in occupied if value):
            dropped.append(tag)
        else:
            kept.append(tag)
    return sanitize_text(", ".join(kept)), dropped


def build_content_plan(
    *,
    seed: int,
    subject_clause: str,
    action_clause: str,
    scene_clause: str,
    action_frame: ActionFrame | Mapping[str, Any] | None,
    template_roles: Mapping[str, Sequence[str]] | None = None,
    template_keys: Sequence[str] | None = None,
    action_surface: Mapping[str, Any] | None = None,
    syntax_family: str = "",
) -> ContentPlan:
    frame = coerce_action_frame(action_frame)
    roles = sorted(
        {
            str(role)
            for values in (template_roles or {}).values()
            for role in values
            if str(role)
        }
    )
    keys = [str(key) for key in (template_keys or ()) if str(key)]
    resolved_syntax_family = syntax_family or (
        "single-sentence-scene-tail" if len(keys) == 3 else "template-directed"
    )
    lexical_choice = str((action_surface or {}).get("surface", "")).strip() or "direct"
    return ContentPlan(
        semantic_slots={
            "subject": sanitize_text(subject_clause),
            "predicate": frame.main_verb or sanitize_text(action_clause).split(" ", 1)[0],
            "object": frame.primary_object,
            "adjunct": sanitize_text(action_clause),
            "scene": sanitize_text(scene_clause),
        },
        discourse_roles=roles or ["neutral"],
        clause_order=("subject", "action", "scene"),
        syntax_family=resolved_syntax_family,
        lexical_choice=lexical_choice,
        named_seed_streams={
            "lexical": mix_seed(int(seed), "prompt_lexical"),
            "syntax": mix_seed(int(seed), "prompt_syntax"),
            "template": mix_seed(int(seed), "prompt_template"),
        },
    )


def select_syntax_family(seed: int) -> str:
    syntax_seed = mix_seed(int(seed), "syntax_family_v0")
    return "two-sentence-scene-tail" if syntax_seed % 4 == 0 else "single-sentence-scene-tail"


def _standalone_scene_clause(value: str) -> str:
    if value.strip() == "{scene_clause}":
        return "The scene is set in {scene_anchor_clause}"
    replacements = (
        (r"^and the room around her staying in\s+", "The room around her remains in "),
        (r"^with the scene around her staying in\s+", "The scene around her remains in "),
        (r"^everything around her grounded in\s+", "Everything around her remains grounded in "),
        (r"^everything else widening into\s+", "Beyond her, the setting opens into "),
        (r"^the rest of the moment opening into\s+", "The rest of the moment opens into "),
        (r"^the moment lingering in\s+", "The moment lingers in "),
        (r"^with the next part of the day waiting in\s+", "The next part of the day unfolds in "),
        (r"^in\s+", "The scene is set in "),
    )
    for pattern, replacement in replacements:
        if re.search(pattern, value, flags=re.IGNORECASE):
            return re.sub(pattern, replacement, value, count=1, flags=re.IGNORECASE)
    return value[:1].upper() + value[1:]


def realize_template_parts(parts: Sequence[str], syntax_family: str) -> str:
    cleaned = [re.sub(r"[\s,.;:]+$", "", str(part or "").strip()) for part in parts]
    cleaned = [part for part in cleaned if part]
    if not cleaned:
        return ""
    if syntax_family == "two-sentence-scene-tail" and len(cleaned) >= 3:
        first_sentence = ", ".join(cleaned[:-1])
        return f"{first_sentence}. {_standalone_scene_clause(cleaned[-1])}."
    return ", ".join(cleaned) + "."


def _realize_content_plan_v1(plan: ContentPlan) -> str:
    slot_for_role = {
        "subject": "subject",
        "action": "adjunct",
        "scene": "scene",
    }
    parts = [
        plan.semantic_slots.get(slot_for_role[role], "")
        for role in plan.clause_order
        if role in slot_for_role
    ]
    return realize_template_parts(parts, plan.syntax_family)


def _initial_word(text: str, *, capitalize: bool = False) -> str:
    first, separator, rest = text.partition(" ")
    return (first.capitalize() if capitalize else first.lower()) + separator + rest


def realize_content_plan(
    plan: ContentPlan, *, action_frame: ActionFrame | Mapping[str, Any] | None = None,
    action_surface: Mapping[str, Any] | None = None, return_debug: bool = False,
    direct_provenance: Mapping[str, Any] | None = None,
    structural_evidence=None,
) -> str | tuple[str, dict[str, Any]]:
    """Realize explicit candidate families; legacy family calls stay byte-stable.

    V2 requires an explicit frame, concrete clauses and a validated surface
    (supplied separately or recorded in plan.lexical_choice). Plan-only calls
    remain v1. Baseline eligibility alone cannot authorize new grammar. The
    family determines output clause order; incoming v2 plans must retain all roles.
    """
    requested = plan.syntax_family
    if requested in _LEGACY_SYNTAX_FAMILIES or (action_frame is None and action_surface is None):
        text = _realize_content_plan_v1(plan)
        if not return_debug:
            return text
        composed_families = sorted(_LEGACY_SYNTAX_FAMILIES - {"template-directed"})
        return text, {"realizer_version": "v1", "syntax_family": requested,
                      "eligible_syntax_families": composed_families if requested in composed_families else [requested],
                      "syntax_fallback_reason": "",
                      "clause_order": list(plan.clause_order)}
    if len(plan.clause_order) != 3 or set(plan.clause_order) != {"subject", "action", "scene"}:
        raise ValueError("A v2 plan must retain subject, action and scene exactly once")

    surface = action_surface if action_surface is not None else {
        "surface": plan.lexical_choice, "rendered_clause": plan.semantic_slots.get("adjunct", ""),
    }
    structural, eligibility = eligible_syntax_families(plan, action_frame, surface, return_debug=True,
                                                     direct_provenance=direct_provenance,
                                                     structural_evidence=structural_evidence)
    eligible = [key for key in structural if key in _V2_IMPLEMENTED_FAMILIES]
    if eligibility['direct_provenance_valid']:
        eligible = [key for key in eligible if key in eligibility['direct_supported_families']]
    selected = requested if requested in eligible else _V2_BASELINE
    reason = "" if selected == requested else (
        "family_not_implemented" if requested not in _V2_IMPLEMENTED_FAMILIES else "family_ineligible")
    order = {
        "scene_lead_subject_action": ["scene", "subject", "action"],
        "action_lead_subject_scene": ["action", "subject", "scene"],
        "subject_scene_action": ["subject", "scene", "action"],
    }.get(selected, ["subject", "action", "scene"])
    facts = eligibility["safety_facts"]
    if (not candidate_family_safe(selected, eligibility, structural_evidence=structural_evidence)
            or (eligibility['direct_provenance_valid'] and selected not in eligible)):
        # Explicit baseline and rejected/unknown families share the same fallback.
        text = _realize_content_plan_v1(replace(plan, syntax_family="single-sentence-scene-tail",
                                              clause_order=("subject", "action", "scene")))
        version, selected, eligible = "v1", _V2_BASELINE, [_V2_BASELINE]
        order = ["subject", "action", "scene"]
        reason = ('family_ineligible' if eligibility['direct_provenance_valid'] else
                  "unsafe_for_v2" if facts["frame_predicate_safe"] is not True else "scene_action_overlap")
    else:
        subject, action, scene = (normalize_action_phrase(plan.semantic_slots[key]) for key in ("subject", "adjunct", "scene"))
        predicate = _initial_word(action)
        if surface.get("surface") == "gerund":
            predicate = "is " + predicate
        if selected == "subject_action__scene_tail":
            if (eligibility['direct_provenance_valid']
                    and scene_template_kind(direct_provenance['slots']) == 'owned_finite'):
                scene_sentence = _initial_word(scene, capitalize=True)
            else:
                scene_sentence = f"The scene is set {_initial_word(scene)}"
            text = f"{_initial_word(subject, capitalize=True)} {predicate}. {scene_sentence}."
        elif selected == "scene_lead_subject_action":
            text = f"{_initial_word(scene, capitalize=True)}, {_initial_word(subject)} {predicate}."
        elif selected == "action_lead_subject_scene":
            text = f"{_initial_word(action, capitalize=True)}, {_initial_word(subject)} is {_initial_word(scene)}."
        elif selected == "subject_scene_action":
            text = f"{_initial_word(subject, capitalize=True)}, {_initial_word(scene)}, {predicate}."
        elif selected == "subject_action_scene_insert":
            text = f"{_initial_word(subject, capitalize=True)} {predicate}, {_initial_word(scene)}."
        else:
            text = f"{_initial_word(subject, capitalize=True)} {predicate} {_initial_word(scene)}."
        # The shared normalizer trims terminal punctuation; this lower-level
        # realizer, like v1, returns a complete sentence before final prompt cleanup.
        text = normalize_composition_punctuation(text) + "."
        version = "v2"
    if not return_debug:
        return text
    return text, {"realizer_version": version, "requested_syntax_family": requested, "syntax_family": selected,
                  "eligible_syntax_families": eligible, "structurally_eligible_syntax_families": structural,
                  "syntax_fallback_reason": reason, "clause_order": order,
                  "rejected_syntax_families": eligibility["rejected_syntax_families"]}


def normalize_composition_punctuation(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"\.\s*,", ",", value)
    value = re.sub(r",\s*\.", ".", value)
    value = re.sub(r",(?:\s*,)+", ",", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"([,.;:!?]){2,}", r"\1", value)
    return sanitize_text(value)
