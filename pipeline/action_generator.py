from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Sequence, Tuple

if __package__ and "." in __package__:
    from ..location_service import resolve_location_key
    from ..object_focus_service import (
        OBJECT_TOKENS,
        action_policy_weight,
        classify_object_hotspot,
        extract_action_object_flags,
        slot_object_policy_weight,
        summarize_slot_object_focus,
    )
else:
    from location_service import resolve_location_key
    from object_focus_service import (
        OBJECT_TOKENS,
        action_policy_weight,
        classify_object_hotspot,
        extract_action_object_flags,
        slot_object_policy_weight,
        summarize_slot_object_focus,
    )

DEFAULT_DAILY_LIFE_TAGS = {"school", "office", "urban", "domestic", "suburban", "resort", "japanese"}
TAG_BASED_DAILY_LIFE_PROFILES = {
    "school": {
        "purpose": ["study", "wait", "rest"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["before class starts", "during a lunch break", "after school"],
        "weather": ["sunlight reaching the windows", "rain tapping against the glass"],
        "obstacle": ["forgot", "delay"],
    },
    "office": {
        "purpose": ["work", "wait", "commute"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["before the meeting begins", "during a short break", "near the end of the workday"],
        "weather": ["the city light reflecting through the glass", "rain streaks showing on the windows"],
        "obstacle": ["delay", "forgot", "luggage"],
    },
    "urban": {
        "purpose": ["shop", "wait", "commute", "rest"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "stranger", "crowd", "acquaintance"],
        "time": ["in the late afternoon", "during the evening rush", "on the way home"],
        "weather": ["a cool breeze moving through the street", "light rain lingering in the air"],
        "obstacle": ["delay", "luggage", "spill"],
    },
    "domestic": {
        "purpose": ["rest", "work", "wait"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["in the quiet part of the morning", "late in the evening", "before heading to bed"],
        "weather": ["soft daylight coming through the window", "the room holding onto the rainy weather outside"],
        "obstacle": ["spill", "forgot"],
    },
    "suburban": {
        "purpose": ["commute", "shop", "rest", "wait"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "stranger", "acquaintance"],
        "time": ["before the next errand", "on the way back home", "as the neighborhood quiets down"],
        "weather": ["wind moving past the houses", "the road still damp from rain"],
        "obstacle": ["delay", "luggage", "forgot"],
    },
    "resort": {
        "purpose": ["rest", "wait", "shop"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance", "crowd"],
        "time": ["during a slow afternoon", "just before sunset", "after a long walk"],
        "weather": ["warm air drifting through the space", "sea light reflecting nearby"],
        "obstacle": ["luggage", "delay"],
    },
    "japanese": {
        "purpose": ["rest", "wait", "work"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["in the stillness of the morning", "late in the afternoon", "as the day starts winding down"],
        "weather": ["soft wind moving through the garden", "rain settling over the eaves"],
        "obstacle": ["wind", "forgot"],
    },
}
LOC_SPECIFIC_DAILY_LIFE_PROFILES = {
    "commuter_transport": {
        "purpose": ["commute", "wait"],
        "social_distance": ["stranger", "crowd", "alone"],
        "time": ["during the morning rush", "between train stops", "on the ride home"],
        "weather": ["the windows fogged from the weather outside", "rainwater shaking loose at each stop"],
        "obstacle": ["delay", "luggage"],
    },
    "street_cafe": {
        "purpose": ["rest", "wait", "shop"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["while the afternoon slows down", "before meeting someone", "between errands"],
        "weather": ["a light breeze stirring the parasol", "sunlight shifting across the table"],
        "obstacle": ["spill", "delay"],
    },
    "cozy_bookstore": {
        "purpose": ["shop", "rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["before the shop closes", "during a rainy afternoon", "while the store stays hushed"],
        "weather": ["rain muttering beyond the front window", "dusty sunlight slipping between the shelves"],
    },
    "shopping_mall_atrium": {
        "purpose": ["shop", "wait", "rest"],
        "social_distance": ["crowd", "stranger", "acquaintance"],
        "time": ["during the weekend rush", "between store visits", "after finishing most of the shopping"],
        "weather": ["light from the skylight shifting overhead", "the glass roof holding back the gray sky"],
        "obstacle": ["luggage", "delay"],
    },
    "fashion_boutique": {
        "purpose": ["shop", "wait"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["while deciding on one last item", "between trips to the fitting room", "before checking out"],
        "obstacle": ["delay", "luggage"],
    },
    "school_library": {
        "purpose": ["study", "rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["during the last quiet hour", "between classes", "after the rain drives everyone indoors"],
        "weather": ["soft rain dimming the windows", "late daylight stretching over the tables"],
    },
    "office_elevator": {
        "purpose": ["commute", "wait", "work"],
        "social_distance": ["stranger", "acquaintance"],
        "time": ["between floors on a busy morning", "after a long meeting", "on the way back down"],
        "obstacle": ["delay", "forgot", "luggage"],
    },
    "modern_office": {
        "purpose": ["work", "wait", "rest"],
        "social_distance": ["alone", "acquaintance", "crowd"],
        "time": ["before the inbox fills up", "in the middle of the afternoon slump", "after most people have left"],
        "obstacle": ["delay", "forgot"],
    },
    "boardroom": {
        "purpose": ["work", "wait"],
        "social_distance": ["acquaintance", "stranger"],
        "time": ["before the agenda starts", "while the discussion drags on", "as the meeting wraps up"],
        "obstacle": ["delay", "forgot"],
    },
    "bedroom_boudoir": {
        "purpose": ["rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["before getting ready to leave", "after finally coming home", "before sleeping"],
        "weather": ["rain-muted light on the curtains", "soft sunlight at the edge of the room"],
    },
    "messy_kitchen": {
        "purpose": ["work", "rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["while getting breakfast ready", "between chores", "after dinner is over"],
        "obstacle": ["spill", "forgot"],
    },
    "rainy_bus_stop": {
        "purpose": ["wait", "commute"],
        "social_distance": ["alone", "stranger"],
        "time": ["before the next bus arrives", "on the way home after dark", "during a long delay"],
        "weather": ["rain drumming on the shelter roof", "cold wind slipping under the awning"],
        "obstacle": ["delay", "wind"],
    },
    "suburban_neighborhood": {
        "purpose": ["commute", "rest", "shop"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["between errands", "on the walk back home", "as the sunset spreads over the houses"],
        "weather": ["wind moving along the hedges", "warm evening light over the street"],
    },
}

LOCATION_CONTEXT_HINTS = [
    (
        ("platform", "terminal", "ticket_gate", "transport", "crosswalk"),
        {
            "anchors": ["near the route display", "by the edge of the walkway", "close to the next exit"],
            "gaze_target": ["glancing toward the next arrival", "watching the flow of people ahead"],
        },
    ),
    (
        ("store", "aisle", "arcade", "market", "bakery", "restaurant", "food_court", "cinema_lobby", "game_arcade"),
        {
            "anchors": ["between the nearby displays", "by the counter", "along the busiest part of the aisle"],
            "gaze_target": ["checking what is available nearby", "looking over the next thing to choose"],
        },
    ),
    (
        ("library", "hallway", "courtyard", "cafeteria", "clubroom", "community_center"),
        {
            "anchors": ["near the side of the room", "along the quieter part of the space", "by the nearest table"],
            "gaze_target": ["looking toward the part of the room she needs", "checking the people moving around her"],
        },
    ),
    (
        ("balcony", "entryway", "laundry", "playground"),
        {
            "anchors": ["near the railing", "close to the doorway", "beside the open space in front of her"],
            "gaze_target": ["looking out over the space for a moment", "watching what is happening just ahead"],
        },
    ),
]

POSTURE_BY_PURPOSE = {
    "study": ["settled at the edge of her seat", "leaning in over what she is doing", "paused in a still working posture"],
    "work": ["keeping an upright working posture", "leaning in with quiet purpose", "holding herself steady while she works"],
    "commute": ["braced to move at any second", "keeping a balanced stance for the crowd", "holding herself ready to continue on"],
    "rest": ["letting her shoulders loosen", "taking on an easy unhurried posture", "settling into a quieter pace"],
    "shop": ["slowing down just enough to compare things", "hovering in place while she decides", "angling herself toward what she is considering"],
    "wait": ["holding still for the moment", "staying near where she needs to be", "lingering without fully relaxing"],
}
HAND_ACTION_BY_PURPOSE = {
    "study": ["fingers keeping her notes in order", "one hand resting near the page she needs", "hands busy with the material in front of her"],
    "work": ["one hand already reaching for the next task", "fingers gathering what she needs next", "hands staying precise and controlled"],
    "commute": ["one hand keeping hold of what matters", "fingers tightening briefly around her things", "hand shifting to keep her balance"],
    "rest": ["hands loosening at her sides", "fingers easing out of their tension", "one hand resting lightly where it lands"],
    "shop": ["one hand hovering over the next option", "fingers checking the item in front of her", "hand moving between two nearby choices"],
    "wait": ["fingers fidgeting for a second", "one hand keeping her place", "hands settling and then shifting again"],
}
GAZE_BY_PURPOSE = {
    "study": ["eyes following the detail she is working through", "looking over the exact thing that needs her attention"],
    "work": ["eyes fixed on what needs to happen next", "looking between the task and the space around it"],
    "commute": ["checking where the next movement will come from", "keeping an eye on the path ahead"],
    "rest": ["looking off for a quiet second", "letting her gaze drift before returning"],
    "shop": ["looking from one option to another", "checking the next thing that catches her eye"],
    "wait": ["watching for the moment to move", "keeping track of what might change nearby"],
}
PROGRESS_STATE_CLAUSES = {
    "preparing": ["before fully getting started", "as she gets herself ready", "while setting up the next step"],
    "midway": ["already in the middle of it", "while keeping the momentum going", "without losing her place"],
    "wrapping_up": ["near the point where she can move on", "while bringing it to a close", "as the last part falls into place"],
}
OBSTACLE_OR_TRIGGER_CLAUSES = {
    "delay": ["while the delay keeps stretching out", "because the timing still is not right"],
    "spill": ["after a small mess interrupts the rhythm", "while handling a minor spill without fuss"],
    "wind": ["while the moving air keeps getting in the way", "as the wind keeps tugging at the moment"],
    "luggage": ["while the extra things she is carrying slow her down", "because she still has too much to juggle"],
    "forgot": ["after realizing something is missing", "while trying to remember what she almost left behind"],
}
SOCIAL_DISTANCE_CLAUSES = {
    "alone": ["keeping to herself", "lost in her own rhythm"],
    "acquaintance": ["leaving room for casual conversation", "half-ready to answer someone nearby"],
    "stranger": ["keeping a polite distance", "avoiding getting in anyone's way"],
    "crowd": ["protecting her space in the crowd", "moving carefully around the people nearby"],
}
OPTIONAL_MICRO_ACTIONS = {
    "study": ["quietly marking her place", "rechecking a small detail", "staying with the line she was following"],
    "work": ["mentally lining up the next task", "pausing to reassess one detail", "moving on only after one more check"],
    "commute": ["counting the moment before she has to move", "adjusting to the movement around her", "keeping pace with the space around her"],
    "rest": ["taking one more easy breath", "letting the pause settle properly", "holding onto the quiet for a second longer"],
    "shop": ["weighing one choice against another", "double-checking what stands out", "lingering over the decision a little longer"],
    "wait": ["measuring the pause instead of rushing it", "checking whether anything has changed yet", "holding onto her place a little longer"],
}

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

def action_text(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("text", ""))
    return str(item)


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


def _action_clause_tokens(text: str) -> List[str]:
    first_clause = str(text or "").split(",", 1)[0].strip().lower()
    return re.findall(r"[a-z]+(?:-[a-z]+)*", first_clause)


def _action_all_tokens(text: str) -> List[str]:
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
        if (
            len(parts) >= 2
            and parts[0] in _GERUND_PREFIXES_TO_DROP
            and parts[-1].endswith("ing")
        ):
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


def action_object_flags(text: str) -> set[str]:
    return extract_action_object_flags(text)


def choose_action_with_bias_guard(pool, rng, loc="", recent_verbs=None, recent_objects=None):
    if not pool:
        return None, set(), {}
    recent_verbs = {str(item).lower() for item in (recent_verbs or []) if item}
    recent_objects = set(recent_objects or [])
    parsed = []
    object_hits = {k: 0 for k in OBJECT_TOKENS}
    for item in pool:
        text = action_text(item)
        flags = action_object_flags(text)
        parsed.append((item, flags))
        for flag in flags:
            object_hits[flag] += 1
    pool_size = len(parsed)
    dominant = {key for key, cnt in object_hits.items() if pool_size > 0 and (cnt / pool_size) >= 0.5}
    weights = []
    for item, flags in parsed:
        text = action_text(item)
        verb = action_verb(text)
        base_weight = 0.35 if flags & dominant else 1.0
        if verb and verb in recent_verbs:
            base_weight *= 0.35
        if flags & recent_objects:
            base_weight *= 0.55
        base_weight *= action_policy_weight(loc, text)
        weights.append(base_weight)
    total = sum(weights)
    if total <= 0:
        return rng.choice(pool), dominant, object_hits
    selected = rng.choices(parsed, weights=weights, k=1)[0][0]
    return selected, dominant, object_hits


def merge_profile(base_profile, override_profile):
    merged = {}
    for key in set(base_profile.keys()) | set(override_profile.keys()):
        values = []
        for source in (base_profile.get(key, []), override_profile.get(key, [])):
            for item in source:
                if item not in values:
                    values.append(item)
        merged[key] = values
    return merged


def get_loc_tags(loc, compat):
    tags = []
    for tag, locs in compat.get("loc_tags", {}).items():
        if loc in locs:
            tags.append(tag)
    return tags


def build_daily_life_profile(loc, compat):
    loc_tags = get_loc_tags(loc, compat)
    daily_life_tags = set(compat.get("daily_life_tags", [])) or set(DEFAULT_DAILY_LIFE_TAGS)
    matching_tags = [tag for tag in loc_tags if tag in daily_life_tags]
    profile = {}
    for tag in matching_tags:
        profile = merge_profile(profile, TAG_BASED_DAILY_LIFE_PROFILES.get(tag, {}))
    profile = merge_profile(profile, LOC_SPECIFIC_DAILY_LIFE_PROFILES.get(loc, {}))
    return profile, matching_tags


def is_daily_life_loc(loc, compat):
    explicit = set(compat.get("daily_life_locs", []))
    if loc in explicit:
        return True
    profile, matching_tags = build_daily_life_profile(loc, compat)
    return bool(profile or matching_tags)


def can_generate_action_for_location(loc, compat=None, action_pools=None):
    compat = compat or {}
    action_pools = action_pools or {}
    loc_key = resolve_location_key(loc) or str(loc or "").strip()
    if action_pools.get(loc_key):
        return True
    profile, matching_tags = build_daily_life_profile(loc_key, compat)
    if profile or matching_tags:
        return True
    return loc_key in set(compat.get("daily_life_locs", [])) or loc_key in set(compat.get("universal_locs", []))


def _pick_axis_value(options, rng):
    if not options:
        return ""
    return rng.choice(options)


def _pick_axis_micro_action(scene_axes, axis_name, axis_value, rng):
    axis_info = scene_axes.get(axis_name, {}).get(axis_value, {})
    micro_actions = axis_info.get("micro_actions", [])
    if not micro_actions:
        return ""
    return rng.choice(micro_actions)


def _location_context_profile(loc):
    lowered = str(loc or "").lower()
    for keywords, profile in LOCATION_CONTEXT_HINTS:
        if any(keyword in lowered for keyword in keywords):
            return profile
    return {
        "anchors": ["near the part of the scene she is using", "close to where she needs to be"],
        "gaze_target": ["checking what is happening nearby", "looking toward the next thing she needs"],
    }


def _weighted_slot_choice(options: Sequence[str], rng, loc="", recent_verbs=None, recent_objects=None, selected_objects=None):
    values = [str(item) for item in options if str(item).strip()]
    if not values:
        return ""
    recent_verbs = {str(item).lower() for item in (recent_verbs or []) if item}
    recent_objects = set(recent_objects or [])
    selected_objects = set(selected_objects or [])
    weights = []
    for value in values:
        weight = 1.0
        verb = action_verb(value)
        objects = action_object_flags(value)
        if verb and verb in recent_verbs:
            weight *= 0.35
        if objects & recent_objects:
            weight *= 0.55
        policy_weight, _policy_objects, _classifications = slot_object_policy_weight(loc, value, selected_objects=selected_objects)
        weight *= policy_weight
        weights.append(weight)
    return rng.choices(values, weights=weights, k=1)[0]


def _normalize_action_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip(" ,.\t\r\n"))


def _extract_anchor_from_phrase(text: str) -> str:
    clean = _normalize_action_phrase(text)
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
    return _normalize_action_phrase(anchor)


def _split_leading_posture_segment(segment: str) -> Tuple[str, str]:
    clean = _normalize_action_phrase(segment)
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
        posture = _normalize_action_phrase(clean[:earliest])
        remainder = _normalize_action_phrase(re.sub(r"^and\s+", "", clean[earliest:], flags=re.IGNORECASE))
        return posture, remainder
    return "", clean


def _split_contextual_clause(text: str) -> Tuple[str, str, str]:
    clean = _normalize_action_phrase(text)
    lowered = clean.lower()
    for splitter, kind in CONTEXTUAL_SPLITTERS:
        idx = lowered.find(splitter)
        if idx <= 0:
            continue
        head = _normalize_action_phrase(clean[:idx])
        tail = _normalize_action_phrase(clean[idx + 1 :])
        if head and tail:
            return head, tail, kind
    return clean, "", ""


def _infer_slot_value_from_hints(text: str, hint_map: Dict[str, Sequence[str]]) -> str:
    lowered = str(text or "").lower()
    for slot_value, hints in hint_map.items():
        if any(_text_matches_hint(lowered, hint) for hint in hints):
            return slot_value
    return ""


def _text_matches_hint(text: str, hint: str) -> bool:
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


def parse_pool_action_to_slots(action_text: str, loc: str = "", compat=None) -> Dict[str, str]:
    compat = compat or {}
    loc_key = resolve_location_key(loc) or str(loc or "").strip()
    clean = _normalize_action_phrase(action_text)
    if not clean:
        return {"location": loc_key} if loc_key else {}

    main_text, contextual_clause, contextual_kind = _split_contextual_clause(clean)
    segments = [_normalize_action_phrase(part) for part in main_text.split(",") if _normalize_action_phrase(part)]
    slots: Dict[str, str] = {"location": loc_key} if loc_key else {}
    if not segments:
        return slots

    posture, remainder = _split_leading_posture_segment(segments[0])
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
        anchor = _extract_anchor_from_phrase(source_text)
        if anchor:
            break
    if anchor:
        slots["anchor"] = anchor

    purpose = _infer_slot_value_from_hints(clean, PURPOSE_HINTS)
    progress_state = _infer_slot_value_from_hints(clean, PROGRESS_STATE_HINTS)
    social_distance = _infer_slot_value_from_hints(clean, SOCIAL_DISTANCE_HINTS)
    obstacle_or_trigger = _infer_slot_value_from_hints(clean, OBSTACLE_HINTS)

    if not purpose and loc_key:
        profile, _matching_tags = build_daily_life_profile(loc_key, compat)
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


def _slot_sources(slots: Dict[str, str], slot_overrides: Dict[str, str]) -> Dict[str, str]:
    sources = {}
    for key, value in slots.items():
        if key == "daily_life_tags":
            continue
        if not value:
            continue
        sources[key] = "pool" if slot_overrides.get(key) else "generated"
    return sources


def build_action_slots(loc, compat, scene_axes, rng, recent_verbs=None, recent_objects=None, slot_overrides=None):
    slot_overrides = {
        str(key): _normalize_action_phrase(value)
        for key, value in (slot_overrides or {}).items()
        if _normalize_action_phrase(value)
    }
    loc_key = slot_overrides.get("location") or resolve_location_key(loc) or str(loc or "").strip()
    profile, matching_tags = build_daily_life_profile(loc_key, compat)
    context_profile = _location_context_profile(loc_key)

    def pick_axis(name, fallback):
        return _pick_axis_value(list(profile.get(name, []) or fallback), rng)

    purpose = slot_overrides.get("purpose") or pick_axis("purpose", ["wait", "rest", "shop"])
    progress_state = slot_overrides.get("progress_state") or pick_axis("progress", ["midway", "preparing"])
    social_distance = slot_overrides.get("social_distance") or pick_axis("social_distance", ["alone", "acquaintance"])
    obstacle_or_trigger = slot_overrides.get("obstacle_or_trigger", "")
    if not obstacle_or_trigger and profile.get("obstacle") and rng.random() < 0.35:
        obstacle_or_trigger = _pick_axis_value(profile.get("obstacle", []), rng)

    selected_objects = set()
    for key in (
        "posture",
        "hand_action",
        "gaze_target",
        "purpose_clause",
        "progress_clause",
        "social_clause",
        "obstacle_clause",
        "optional_micro_action",
        "time_or_weather",
    ):
        selected_objects.update(action_object_flags(slot_overrides.get(key, "")))

    def choose_slot(name: str, options: Sequence[str]):
        value = slot_overrides.get(name) or _weighted_slot_choice(
            options,
            rng,
            loc=loc_key,
            recent_verbs=recent_verbs,
            recent_objects=recent_objects,
            selected_objects=selected_objects,
        )
        if value:
            selected_objects.update(action_object_flags(value))
        return value

    slots = {
        "location": loc_key,
        "purpose": purpose,
        "progress_state": progress_state,
        "social_distance": social_distance,
        "obstacle_or_trigger": obstacle_or_trigger,
        "daily_life_tags": list(matching_tags),
        "anchor": choose_slot("anchor", context_profile.get("anchors", [])),
        "posture": choose_slot("posture", POSTURE_BY_PURPOSE.get(purpose, [])),
        "hand_action": choose_slot("hand_action", HAND_ACTION_BY_PURPOSE.get(purpose, [])),
        "gaze_target": choose_slot(
            "gaze_target",
            list(GAZE_BY_PURPOSE.get(purpose, [])) + list(context_profile.get("gaze_target", [])),
        ),
        "purpose_clause": choose_slot(
            "purpose_clause",
            list(OPTIONAL_MICRO_ACTIONS.get(purpose, [])) + [
                _pick_axis_micro_action(scene_axes, "purpose", purpose, rng),
            ],
        ),
        "progress_clause": choose_slot(
            "progress_clause",
            PROGRESS_STATE_CLAUSES.get(progress_state, [""]),
        ),
        "social_clause": choose_slot("social_clause", SOCIAL_DISTANCE_CLAUSES.get(social_distance, [])),
        "obstacle_clause": choose_slot(
            "obstacle_clause",
            [
                OBSTACLE_OR_TRIGGER_CLAUSES.get(obstacle_or_trigger, [""])[0],
                _pick_axis_micro_action(scene_axes, "obstacle", obstacle_or_trigger, rng) if obstacle_or_trigger else "",
            ],
        ),
        "optional_micro_action": choose_slot("optional_micro_action", OPTIONAL_MICRO_ACTIONS.get(purpose, [])),
        "time_or_weather": choose_slot(
            "time_or_weather",
            list(profile.get("time", [])) or list(profile.get("weather", [])),
        ),
    }
    return slots


def render_action_slots(slots: Dict[str, str], activity_first: bool = False) -> str:
    anchor = slots.get("anchor", "")
    posture = str(slots.get("posture", "")).strip()
    hand_action = str(slots.get("hand_action", "")).strip()
    purpose_clause = str(slots.get("purpose_clause", "")).strip() or "holding onto the moment in front of her"
    primary_parts = []
    if activity_first:
        if hand_action:
            primary_parts.append(hand_action)
        elif posture:
            primary_parts.append(posture)
        elif purpose_clause:
            primary_parts.append(purpose_clause)
    else:
        if purpose_clause:
            primary_parts.append(purpose_clause)
        elif hand_action:
            primary_parts.append(hand_action)
    if anchor and all(anchor.lower() not in part.lower() for part in (posture, hand_action, purpose_clause) if part):
        primary_parts.append(anchor)
    primary = " ".join(primary_parts).strip()
    clauses = [primary] if primary else []
    for key in ("posture", "hand_action", "gaze_target", "optional_micro_action", "social_clause", "progress_clause", "obstacle_clause"):
        value = str(slots.get(key, "")).strip()
        if value and value.lower() not in primary.lower():
            clauses.append(value)
    time_or_weather = str(slots.get("time_or_weather", "")).strip()
    if time_or_weather:
        clauses.append(time_or_weather)
    deduped = []
    seen = []
    for clause in clauses:
        if not clause:
            continue
        lowered = clause.lower()
        if any(lowered == existing or lowered in existing or existing in lowered for existing in seen):
            continue
        seen.append(lowered)
        deduped.append(clause)
    return ", ".join(deduped)


def _append_clause(action_text: str, clause: str) -> str:
    if not clause:
        return action_text
    clean_action = str(action_text).strip().rstrip(".")
    clean_clause = str(clause).strip().rstrip(".")
    if not clean_action:
        return clean_clause
    if clean_clause.lower() in clean_action.lower():
        return clean_action
    return f"{clean_action}, {clean_clause}"


def generate_action_for_location(
    loc,
    compat,
    scene_axes,
    rng,
    pool=None,
    recent_verbs=None,
    recent_objects=None,
):
    loc_key = resolve_location_key(loc) or str(loc or "").strip()
    if pool:
        new_action_item, dominant_objects, object_hits = choose_action_with_bias_guard(
            pool,
            rng,
            loc_key,
            recent_verbs=recent_verbs,
            recent_objects=recent_objects,
        )
        if isinstance(new_action_item, dict):
            action_text = str(new_action_item.get("text", ""))
            action_load = new_action_item.get("load")
        else:
            action_text = str(new_action_item)
            action_load = ""
        pool_slots = parse_pool_action_to_slots(action_text, loc=loc_key, compat=compat)
        slots = build_action_slots(
            loc_key,
            compat,
            scene_axes,
            rng,
            recent_verbs=recent_verbs,
            recent_objects=recent_objects,
            slot_overrides=pool_slots,
        )
        normalized_action = render_action_slots(slots, activity_first=True)
        decision = {
            "generator_mode": "pool",
            "action_pool_size": len(pool),
            "action_pool_dominant_objects": sorted(dominant_objects) if dominant_objects else [],
            "action_pool_object_hits": {k: v for k, v in object_hits.items() if v > 0},
            "base_action": action_text,
            "normalized_action": normalized_action,
            "action_load": action_load,
            "pool_slots": pool_slots,
            "slot_sources": _slot_sources(slots, pool_slots),
            "object_focus": summarize_slot_object_focus(
                loc_key,
                slots,
                ("posture", "hand_action", "gaze_target", "purpose_clause", "optional_micro_action", "obstacle_clause", "time_or_weather"),
            ),
            "slots": slots,
        }
        return normalized_action, decision

    slots = build_action_slots(loc_key, compat, scene_axes, rng, recent_verbs=recent_verbs, recent_objects=recent_objects)
    action_text = render_action_slots(slots)
    decision = {
        "generator_mode": "compositional",
        "normalized_action": action_text,
        "pool_slots": {},
        "slot_sources": _slot_sources(slots, {}),
        "object_focus": summarize_slot_object_focus(
            loc_key,
            slots,
            ("posture", "hand_action", "gaze_target", "purpose_clause", "optional_micro_action", "obstacle_clause", "time_or_weather"),
        ),
        "slots": slots,
    }
    return action_text, decision
