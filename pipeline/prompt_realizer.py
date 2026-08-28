"""Composition-mode content planning and final surface normalization."""

from __future__ import annotations

from dataclasses import dataclass
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


def realize_content_plan(plan: ContentPlan) -> str:
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


def normalize_composition_punctuation(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"\.\s*,", ",", value)
    value = re.sub(r",\s*\.", ".", value)
    value = re.sub(r",(?:\s*,)+", ",", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"([,.;:!?]){2,}", r"\1", value)
    return sanitize_text(value)
