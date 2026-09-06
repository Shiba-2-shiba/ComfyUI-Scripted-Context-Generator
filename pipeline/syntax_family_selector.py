"""Conservative eligibility for concrete v2 plans; no selection or activation.

Unrecognized constructions stay on the baseline. This is a bounded structural
check, not an English parser or a replacement for upstream semantic/solo policy.
"""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any, TYPE_CHECKING

try:
    from ..core.schema import ActionFrame
    from ..core.semantic_policy import find_banned_terms
    from ..core.solo_safety import is_solo_safe_text
    from ..location_service import resolve_location_key
    from ..object_focus_service import ACTION_OBJECT_PATTERNS, extract_action_object_flags
    from ..vocab.loader import load_json
    from ..vocab.syntax_families import ACTION_SURFACES, BASELINE_FAMILY, CATALOG_FILENAME, SAFETY_FACTS, validate_syntax_family_catalog
except ImportError:
    from core.schema import ActionFrame
    from core.semantic_policy import find_banned_terms
    from core.solo_safety import is_solo_safe_text
    from location_service import resolve_location_key
    from object_focus_service import ACTION_OBJECT_PATTERNS, extract_action_object_flags
    from vocab.loader import load_json
    from vocab.syntax_families import ACTION_SURFACES, BASELINE_FAMILY, CATALOG_FILENAME, SAFETY_FACTS, validate_syntax_family_catalog

from .action_parser import CONTEXTUAL_SPLITTERS, GAZE_STARTERS, SECONDARY_SEGMENT_STARTERS, STANCE_STARTERS, normalize_action_phrase

if TYPE_CHECKING:
    from .prompt_realizer import ContentPlan

_GERUNDS = frozenset((*STANCE_STARTERS, *SECONDARY_SEGMENT_STARTERS, *GAZE_STARTERS))
# Deliberately small, tested finite forms; no speculative conjugation machinery.
_FINITE_FORMS = {"checks": "checking", "reads": "reading", "holds": "holding", "waits": "waiting"}
# Semantic match regexes also contain verbs (e.g. 'sipping' -> drink), so only
# their canonical noun keys and these two explicit transit nouns are grammar evidence.
_NOMINALS = frozenset(key.replace("_", " ") for key in ACTION_OBJECT_PATTERNS) | {"transit card", "ticket"}
_LOCATIVE = re.compile(r"^(?:at|in|on|near|beside|inside|outside|under|by)\s+(?:(?:the|a|an)\s+)?(.+)$")
_BOUNDARIES = re.compile(r"[{}.;:!?]|\b(?:because|when|as|if|although|but|that|which|who|where|whose)\b")
_OTHER_SUBJECT = re.compile(r"^(?:a|an|the|he|she|they|her|his|their|someone|another|hands?|eyes?|fingers?|brows?|shoulders?)\b")
# Explicitly bounded noun-phrase forms. Rich descriptive/relative clauses stay
# on baseline until supported by independently tested structure, not a blacklist.
_SUBJECT = re.compile(r"^(?:a|the) (?:calm )?(?:solo )?girl(?: in a (?:(?:navy|blue|black|white) )?(?:coat|dress|jacket|uniform))?$")
_CLAUSE_TAIL = re.compile(r"\b(?:he|she|they|someone|another|is|are|was|were|does|do|did|has|have|had|can|will|would|could|should|must)\b")


def _text(value: Any) -> str:
    return normalize_action_phrase(value).lower() if isinstance(value, str) else ""


def _nominal_object(value: str) -> bool:
    phrase = re.sub(r"^(?:a|an|the|her)\s+", "", value)
    return phrase in _NOMINALS


def _predicate_tail(tail: str) -> bool:
    if not tail or all(word in {"quietly", "briefly", "slowly", "gently"} for word in tail.split()):
        return True
    if _scene_anchor(tail) or _nominal_object(tail):
        return True
    match = re.search(r"\b(?:at|in|on|near|beside|inside|outside|under|by)\s+.+$", tail)
    return bool(match and _nominal_object(tail[:match.start()].strip()) and _scene_anchor(match.group()))


def _predicate(segment: str) -> tuple[str, str, bool | None]:
    """Return known verb/surface and explicit independent-subject evidence."""
    words = segment.split()
    if not words:
        return "", "", None
    head, tail = words[0], " ".join(words[1:])
    if head == "is" and words[1:2] and words[1] in _GERUNDS:
        verb, surface, tail = words[1], "clause", " ".join(words[2:])
    elif head in _GERUNDS:
        verb, surface = head, "gerund"
    elif head in _FINITE_FORMS:
        verb, surface = _FINITE_FORMS[head], "clause"
    else:
        return "", "", True if _OTHER_SUBJECT.match(segment) else None
    if _CLAUSE_TAIL.search(tail):
        return "", "", True
    if not _predicate_tail(tail):
        return "", "", None
    return verb, surface, False


def _action_structure(action: str) -> tuple[str, str, bool | None]:
    if (not action or _BOUNDARIES.search(action) or not re.fullmatch(r"[a-z0-9 ,'-]+", action)
            or any(re.search(rf"\b{re.escape(label)}\b", action) for _, label in CONTEXTUAL_SPLITTERS if label != "while")):
        return "", "", None
    pieces = re.split(r"\s*(,|\bwhile\b|\band\b)\s*", action)
    verb, surface, independent = _predicate(pieces[0])
    if independent is not False:
        return verb, surface, independent
    for connector, segment in zip(pieces[1::2], pieces[2::2]):
        _, part_surface, part_subject = _predicate(segment)
        if part_subject is not False:
            return "", "", part_subject
        expected = surface if connector == "and" else "gerund"
        if part_surface != expected:
            return "", "", None
    return verb, surface, False


def _scene_anchor(scene: str) -> tuple[str, str] | None:
    if not scene or _BOUNDARIES.search(scene) or "," in scene:
        return None
    match = _LOCATIVE.fullmatch(scene)
    if match is None:
        return None
    complement = match.group(1)
    canonical = resolve_location_key(complement)
    # Known locative aliases are positive evidence; unfamiliar poetic/free-form
    # scene fragments are not guessed into a safe noun phrase.
    return (complement, canonical) if canonical else None


def _overlap(action: str, anchor: tuple[str, str]) -> bool:
    complement, canonical = anchor
    if re.search(rf"(?<!\w){re.escape(complement)}(?!\w)", action):
        return True
    for clause in re.split(r",|\bwhile\b|\band\b", action):
        match = re.search(r"\b(?:at|in|on|near|beside|inside|outside|under|by)\s+.+$", clause.strip())
        if match:
            other = _scene_anchor(match.group())
            if other and other[1] == canonical:
                return True
    return False


def _facts(plan: ContentPlan, frame_value: ActionFrame | Mapping[str, Any] | None,
           surface_value: Mapping[str, Any] | None) -> tuple[dict[str, bool | None], str, list[str]]:
    facts: dict[str, bool | None] = dict.fromkeys(sorted(SAFETY_FACTS))
    slots = plan.semantic_slots
    subject, action, scene = (_text(slots.get(key)) for key in ("subject", "adjunct", "scene"))
    surface = surface_value if isinstance(surface_value, Mapping) else {}
    declared = surface.get("surface")
    declared = declared if isinstance(declared, str) and declared in ACTION_SURFACES else "unknown"
    reasons = []
    if any("{" in value or "}" in value for value in (subject, action, scene)):
        reasons.append("unresolved_placeholder")
    if "rendered_clause" in surface and _text(surface["rendered_clause"]) != action:
        reasons.append("rendered_clause_mismatch")
    if not _SUBJECT.fullmatch(subject) or len(re.findall(r"\bgirl\b", subject)) != 1 or _CLAUSE_TAIL.search(subject):
        reasons.append("unsupported_subject")
    joined = " ".join((subject, action, scene))
    if find_banned_terms(joined) or not is_solo_safe_text(joined):
        reasons.append("policy_or_solo_conflict")
    verb, actual, independent = _action_structure(action)
    facts["fragment_subject_action"] = declared == "fragment" if action else None
    facts["independent_action_subject"] = independent
    if not actual or actual != declared:
        reasons.append("unsupported_or_mismatched_surface")
    anchor = _scene_anchor(scene)
    scene_safe = bool(anchor)
    if not scene_safe:
        reasons.append("unsupported_scene_anchor")
    for key in ("standalone_scene_safe", "scene_lead_safe", "scene_adjunct_safe"):
        facts[key] = scene_safe
    if anchor and action:
        overlap = _overlap(action, anchor)
        facts["scene_action_overlap"] = overlap
        facts["scene_action_nonduplicative"] = not overlap

    frame = frame_value if isinstance(frame_value, ActionFrame) else ActionFrame.from_dict(frame_value)
    legacy = _text(frame.legacy_text)
    # An appended, validated shared-subject clause may extend the original action.
    bound_text = bool(legacy) and (legacy == action or any(action.startswith(legacy + boundary) for boundary in (",", " while ", " and ")))
    object_key = _text(frame.primary_object)
    object_present = not object_key or bool(re.search(rf"(?<!\w){re.escape(object_key)}(?!\w)", action)) or object_key in extract_action_object_flags(action)
    frame_safe = (frame.schema_version == "action-frame/v1" and bound_text and bool(verb)
                  and _text(frame.main_verb) == verb and _text(slots.get("predicate")) == verb
                  and _text(slots.get("object")) == object_key and object_present and not reasons)
    facts["frame_predicate_safe"] = frame_safe
    facts["same_subject_attachment_safe"] = frame_safe and actual == "gerund" and independent is False
    return facts, declared, sorted(reasons)


def eligible_syntax_families(
    plan: ContentPlan, action_frame: ActionFrame | Mapping[str, Any] | None,
    action_surface: Mapping[str, Any] | None, *, catalog: dict[str, Any] | None = None,
    return_debug: bool = False,
) -> list[str] | tuple[list[str], dict[str, Any]]:
    """Filter before selection; baseline is a fallback marker, not policy approval."""
    metadata = load_json(CATALOG_FILENAME) if catalog is None else catalog
    issues = validate_syntax_family_catalog(metadata)
    if issues:
        raise ValueError("Invalid syntax-family catalog: " + "; ".join(issues))
    facts, surface, common_reasons = _facts(plan, action_frame, action_surface)
    eligible = [BASELINE_FAMILY]
    rejected: dict[str, list[str]] = {}
    for family in sorted(metadata["families"], key=lambda item: item["key"]):
        key = family["key"]
        if key == BASELINE_FAMILY:
            continue
        reasons = list(common_reasons)
        if not set(plan.discourse_roles) & set(family["roles"]):
            reasons.append("role_mismatch")
        if surface not in family["allowed_action_surfaces"] or surface in family["avoid_action_surfaces"]:
            reasons.append("surface_not_allowed")
        reasons.extend("missing_slot:" + slot for slot in family["required_slots"] if not _text(plan.semantic_slots.get(slot)))
        reasons.extend("required_fact_not_true:" + fact for fact in family["requires"] if facts.get(fact) is not True)
        reasons.extend("forbidden_fact_not_false:" + fact for fact in family["forbids"] if facts.get(fact) is not False)
        if reasons:
            rejected[key] = sorted(set(reasons))
        else:
            eligible.append(key)
    if not return_debug:
        return eligible
    return eligible, {"eligible_syntax_families": eligible, "rejected_syntax_families": rejected,
                      "syntax_fallback_reason": "baseline_only" if len(eligible) == 1 else "",
                      "safety_facts": facts}
