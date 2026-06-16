from __future__ import annotations

import re
from typing import Any, Callable, Dict, Mapping, Sequence, Tuple

try:
    from ..location_service import resolve_location_key
except ImportError:
    from location_service import resolve_location_key


STANCE_STARTERS = ("sitting", "standing", "walking", "leaning", "kneeling", "crouching", "lying", "running")
SECONDARY_SEGMENT_STARTERS = (
    "working",
    "straightening",
    "looking",
    "gazing",
    "watching",
    "following",
    "checking",
    "typing",
    "waiting",
    "pinning",
    "stretching",
    "holding",
    "reviewing",
    "arguing",
    "rearranging",
    "sorting",
    "whispering",
    "carrying",
    "feeling",
    "writing",
    "reading",
    "browsing",
    "packing",
    "erasing",
    "cleaning",
    "eating",
    "reaching",
    "taking",
    "chatting",
    "choosing",
    "singing",
    "playing",
    "sipping",
    "cooking",
    "wiping",
    "lifting",
    "warming",
    "listening",
    "dozing",
    "relaxing",
    "resting",
    "surveying",
    "searching",
    "avoiding",
    "tuning",
)
GAZE_STARTERS = ("looking", "gazing", "watching", "glancing", "staring", "following", "surveying")
PURPOSE_HINTS = {
    "study": ("study", "textbook", "notes", "folder", "reading", "bookshelves", "shelf", "librarian", "highlighted"),
    "work": ("working", "document", "documents", "printouts", "typing", "printer", "monitor", "agenda", "contract", "copier", "badge"),
    "commute": ("hallway", "elevator", "platform", "door", "route", "train", "bus", "floor numbers", "walkway"),
    "rest": ("break", "sky", "wind", "lost in thought", "stretching"),
    "shop": ("browsing", "titles", "shelf", "shopping", "fitting room", "checking out", "compare"),
    "wait": ("waiting", "watch", "arrives", "before everyone arrives", "holding the door open"),
}
SOCIAL_DISTANCE_HINTS = {
    "crowd": ("crowd", "people", "others"),
    "acquaintance": ("friends", "librarian"),
    "stranger": ("someone",),
}
PROGRESS_STATE_HINTS = {
    "preparing": ("before ", "getting ready", "arrives", "begins", "open"),
    "wrapping_up": ("after ", "wraps up", "closes", "finally", "last "),
    "midway": ("while ", "during ", "mid-", "ongoing"),
}
OBSTACLE_HINTS = {
    "delay": ("delay", "late"),
    "spill": ("spill", "wet"),
    "wind": ("wind", "breeze"),
    "luggage": ("bag", "bags", "luggage", "cart"),
    "forgot": ("forgot", "missing", "left behind"),
}
ANCHOR_PREPOSITION_PATTERN = re.compile(
    r"\b(?:by|at|near|between|beside|along|against|close to|in front of|on|through|across|inside|outside|under|over)\b.+",
    re.IGNORECASE,
)
CONTEXTUAL_SPLITTERS = (
    (" while ", "while"),
    (" before ", "before"),
    (" after ", "after"),
    (" during ", "during"),
)

_ACTION_VERB_STOPWORDS = {
    "a",
    "an",
    "the",
    "her",
    "his",
    "their",
    "my",
    "our",
    "its",
    "this",
    "that",
    "these",
    "those",
    "what",
    "which",
    "who",
    "whom",
    "whose",
    "and",
    "then",
    "just",
    "again",
    "still",
    "busy",
    "using",
    "lightly",
    "quietly",
    "softly",
    "gently",
    "slowly",
    "hurriedly",
    "mentally",
    "briefly",
    "slightly",
    "more",
    "easy",
    "with",
    "without",
    "into",
    "onto",
    "over",
    "under",
    "near",
    "by",
    "at",
    "beside",
    "between",
    "along",
    "through",
    "across",
    "around",
}
_ACTION_FRAGMENT_SUBJECT_TOKENS = {
    "hand",
    "hands",
    "finger",
    "fingers",
    "eye",
    "eyes",
    "brow",
    "brows",
    "shoulder",
    "shoulders",
}
_ACTION_NOUN_TO_VERB = {
    "sigh": "sighing",
    "glance": "glancing",
    "look": "looking",
    "breath": "breathing",
    "pause": "pausing",
}
_GERUND_PREFIXES_TO_DROP = {"double", "re"}


def action_text(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("text", ""))
    return str(item)


def _action_clause_tokens(text: str) -> list[str]:
    first_clause = str(text or "").split(",", 1)[0].strip().lower()
    return re.findall(r"[a-z]+(?:-[a-z]+)*", first_clause)


def _action_all_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+(?:-[a-z]+)*", str(text or "").lower())


def _normalize_action_verb_candidate(token: str) -> str:
    candidate = str(token or "").strip().lower()
    if not candidate or candidate in _ACTION_VERB_STOPWORDS:
        return ""
    if candidate in _ACTION_FRAGMENT_SUBJECT_TOKENS:
        return ""
    if candidate in _ACTION_NOUN_TO_VERB:
        return _ACTION_NOUN_TO_VERB[candidate]
    if "-" in candidate:
        parts = [part for part in candidate.split("-") if part]
        if len(parts) >= 2 and parts[0] in _GERUND_PREFIXES_TO_DROP and parts[-1].endswith("ing"):
            return parts[-1]
    return candidate


def _is_action_verb_like(candidate: str) -> bool:
    value = str(candidate or "").strip().lower()
    if not value:
        return False
    if value.endswith("ing"):
        return True
    if value in STANCE_STARTERS:
        return True
    return False


def _pick_action_verb_from_tokens(tokens: Sequence[str], allow_fallback: bool = True) -> str:
    if not tokens:
        return ""
    if len(tokens) >= 2 and tokens[0] == "deep" and tokens[1] in _ACTION_NOUN_TO_VERB:
        return _ACTION_NOUN_TO_VERB[tokens[1]]
    if len(tokens) >= 3 and tokens[0] in STANCE_STARTERS and tokens[1] == "and":
        for token in tokens[2:]:
            normalized = _normalize_action_verb_candidate(token)
            if normalized:
                return normalized
    index = 0
    fallback = ""
    while index < len(tokens):
        token = tokens[index]
        if token == "one" and index + 1 < len(tokens) and tokens[index + 1] in _ACTION_FRAGMENT_SUBJECT_TOKENS:
            index += 2
            continue
        normalized = _normalize_action_verb_candidate(token)
        if normalized and _is_action_verb_like(normalized):
            return normalized
        if normalized and not fallback:
            fallback = normalized
        index += 1
    return fallback if allow_fallback else ""


def action_verb(text: str) -> str:
    clause_tokens = _action_clause_tokens(text)
    normalized = _pick_action_verb_from_tokens(clause_tokens, allow_fallback=False)
    if normalized:
        return normalized
    all_tokens = _action_all_tokens(text)
    normalized = _pick_action_verb_from_tokens(all_tokens)
    if normalized:
        return normalized
    return all_tokens[0] if all_tokens else ""


def normalize_action_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip(" ,.\t\r\n"))


def extract_anchor_from_phrase(text: str) -> str:
    clean = normalize_action_phrase(text)
    if not clean:
        return ""
    match = ANCHOR_PREPOSITION_PATTERN.search(clean)
    if not match:
        return ""
    anchor = match.group(0)
    for splitter in (" while ", ",", " looking ", " gazing ", " watching ", " checking ", " straightening ", " holding "):
        idx = anchor.lower().find(splitter.strip().lower() if splitter == "," else splitter.lower())
        if idx > 0:
            anchor = anchor[:idx]
            break
    return normalize_action_phrase(anchor)


def split_leading_posture_segment(segment: str) -> Tuple[str, str]:
    clean = normalize_action_phrase(segment)
    lowered = clean.lower()
    for starter in STANCE_STARTERS:
        if not lowered.startswith(starter):
            continue
        remainder_text = clean[len(starter) :]
        earliest = None
        remainder_lowered = remainder_text.lower()
        for keyword in SECONDARY_SEGMENT_STARTERS:
            match = re.search(rf"\b(?:and\s+)?{re.escape(keyword)}\b", remainder_lowered, re.IGNORECASE)
            if not match:
                continue
            absolute_start = len(starter) + match.start()
            if earliest is None or absolute_start < earliest:
                earliest = absolute_start
        if earliest is None:
            return clean, ""
        posture = normalize_action_phrase(clean[:earliest])
        remainder = normalize_action_phrase(re.sub(r"^and\s+", "", clean[earliest:], flags=re.IGNORECASE))
        return posture, remainder
    return "", clean


def split_contextual_clause(text: str) -> Tuple[str, str, str]:
    clean = normalize_action_phrase(text)
    lowered = clean.lower()
    for splitter, kind in CONTEXTUAL_SPLITTERS:
        idx = lowered.find(splitter)
        if idx <= 0:
            continue
        head = normalize_action_phrase(clean[:idx])
        tail = normalize_action_phrase(clean[idx + 1 :])
        if head and tail:
            return head, tail, kind
    return clean, "", ""


def infer_slot_value_from_hints(text: str, hint_map: Mapping[str, Sequence[str]]) -> str:
    lowered = str(text or "").lower()
    for slot_value, hints in hint_map.items():
        if any(text_matches_hint(lowered, hint) for hint in hints):
            return slot_value
    return ""


def text_matches_hint(text: str, hint: str) -> bool:
    if not hint:
        return False
    stripped = hint.strip()
    if not stripped:
        return False
    pattern = re.escape(stripped)
    if stripped[0].isalnum():
        pattern = r"\b" + pattern
    if stripped[-1].isalnum():
        pattern = pattern + r"\b"
    if hint.endswith(" "):
        pattern = pattern + r"\s"
    return re.search(pattern, text, re.IGNORECASE) is not None


def parse_pool_action_to_slots(
    action_text_value: str,
    loc: str = "",
    compat: Mapping[str, Any] | None = None,
    daily_life_profile_resolver: Callable[[str, Mapping[str, Any]], Mapping[str, Sequence[str]]] | None = None,
) -> Dict[str, str]:
    compat = compat or {}
    loc_key = resolve_location_key(loc) or str(loc or "").strip()
    clean = normalize_action_phrase(action_text_value)
    if not clean:
        return {"location": loc_key} if loc_key else {}

    main_text, contextual_clause, contextual_kind = split_contextual_clause(clean)
    segments = [normalize_action_phrase(part) for part in main_text.split(",") if normalize_action_phrase(part)]
    slots: Dict[str, str] = {"location": loc_key} if loc_key else {}
    if not segments:
        return slots

    posture, remainder = split_leading_posture_segment(segments[0])
    if posture:
        slots["posture"] = posture
        if remainder:
            segments = [posture, remainder] + segments[1:]

    if contextual_clause:
        if contextual_kind == "while":
            slots["optional_micro_action"] = contextual_clause
        elif contextual_kind == "before":
            slots["progress_state"] = "preparing"
            slots.setdefault("optional_micro_action", contextual_clause)
        elif contextual_kind == "after":
            slots["progress_state"] = "wrapping_up"
            slots.setdefault("optional_micro_action", contextual_clause)
        elif contextual_kind == "during":
            slots["progress_state"] = "midway"
            slots.setdefault("optional_micro_action", contextual_clause)

    for segment in segments:
        if not segment or segment == slots.get("posture", ""):
            continue
        lowered = segment.lower()
        if not slots.get("gaze_target") and any(lowered.startswith(prefix) for prefix in GAZE_STARTERS):
            slots["gaze_target"] = segment
            continue
        if not slots.get("optional_micro_action") and (
            lowered.startswith("waiting")
            or "break" in lowered
            or "lost in thought" in lowered
            or "on a call" in lowered
            or "feeling the wind" in lowered
        ):
            slots["optional_micro_action"] = segment
            continue
        if not slots.get("hand_action"):
            slots["hand_action"] = segment
            continue
        if not slots.get("gaze_target") and any(prefix in lowered for prefix in GAZE_STARTERS):
            slots["gaze_target"] = segment
            continue
        if not slots.get("optional_micro_action"):
            slots["optional_micro_action"] = segment

    anchor = ""
    for source_text in (slots.get("posture", ""), slots.get("hand_action", ""), main_text):
        anchor = extract_anchor_from_phrase(source_text)
        if anchor:
            break
    if anchor:
        slots["anchor"] = anchor

    purpose = infer_slot_value_from_hints(clean, PURPOSE_HINTS)
    progress_state = infer_slot_value_from_hints(clean, PROGRESS_STATE_HINTS)
    social_distance = infer_slot_value_from_hints(clean, SOCIAL_DISTANCE_HINTS)
    obstacle_or_trigger = infer_slot_value_from_hints(clean, OBSTACLE_HINTS)

    if not purpose and loc_key and daily_life_profile_resolver:
        profile = dict(daily_life_profile_resolver(loc_key, compat) or {})
        if len(profile.get("purpose", [])) == 1:
            purpose = str(profile["purpose"][0])

    if purpose:
        slots["purpose"] = purpose
    if progress_state:
        slots["progress_state"] = progress_state
    if social_distance:
        slots["social_distance"] = social_distance
    if obstacle_or_trigger:
        slots["obstacle_or_trigger"] = obstacle_or_trigger
    return slots
