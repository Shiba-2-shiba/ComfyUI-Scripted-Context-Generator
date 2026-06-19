from __future__ import annotations

import re
from typing import Iterable, List, Set

from .prompt_risk_policy import classify_risk_families, solo_flags_for_risk_families


SOLO_PEOPLE_PATTERNS = (
    re.compile(r"\bcrowd\w*\b", re.IGNORECASE),
    re.compile(r"\bpeople\b", re.IGNORECASE),
    re.compile(r"\bsomeone\b", re.IGNORECASE),
    re.compile(r"\bcustomers?\b", re.IGNORECASE),
    re.compile(r"\bemployees?\b", re.IGNORECASE),
    re.compile(r"\bbystanders?\b", re.IGNORECASE),
    re.compile(r"\bcommuters\b", re.IGNORECASE),
    re.compile(r"\bfamily\s+photos?\b", re.IGNORECASE),
    re.compile(r"\bgroup\s+photos?\b", re.IGNORECASE),
    re.compile(
        r"\bstaff\s+(?:working|guiding|arranging|restocking|wiping|waiting|moving|standing)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:cleaning|gallery|shop|store|cafe|restaurant)\s+staff\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bstudents?\s+(?:pass|passes|passing)\b", re.IGNORECASE),
    re.compile(r"\bpass(?:es|ing)?\s+by\b", re.IGNORECASE),
    re.compile(r"\bpass(?:es|ing)?\s+through\b", re.IGNORECASE),
)
SOLO_OTHER_PERSON_PATTERNS = (
    re.compile(r"\bfriends?\b", re.IGNORECASE),
    re.compile(r"\bclassmates?\b", re.IGNORECASE),
    re.compile(r"\bcompanions?\b", re.IGNORECASE),
)
SOLO_SOCIAL_TALK_PATTERNS = (
    re.compile(r"\btalks?\b", re.IGNORECASE),
    re.compile(r"\btalking\b", re.IGNORECASE),
    re.compile(r"\bchat(?:s|ting)?\b", re.IGNORECASE),
    re.compile(r"\bconversation\b", re.IGNORECASE),
)
SOLO_MIRROR_CLONE_PATTERNS = (
    re.compile(r"\bmirrors?\b", re.IGNORECASE),
    re.compile(r"\bmirrored\b", re.IGNORECASE),
    re.compile(r"\breflections?\b", re.IGNORECASE),
)
LOCATION_FIRST_TEMPLATE_PATTERNS = (
    re.compile(r"(?:^|,\s*)(?:at\s+the\s+edge\s+of|in|inside|against)\s+(?:\{?loc\}?|[a-z])", re.IGNORECASE),
)
MULTI_ACTION_DENSITY_PATTERNS = (
    re.compile(
        r"\b(?:waving|checking|holding|keeping|moving|tapping|leaning|settling|looking|"
        r"brushing|adjusting|wiping|hands?\s+moving|open\s+posture|quick\s+step)\b",
        re.IGNORECASE,
    ),
)

ROUTINE_ARTIFACT_PATTERNS = (
    re.compile(r"\bspill(?:s|ed)?\b", re.IGNORECASE),
    re.compile(r"\bstain(?:s|ed)?\b", re.IGNORECASE),
    re.compile(r"\bwet\s+sleeve\b", re.IGNORECASE),
    re.compile(r"\bnapkins?\b", re.IGNORECASE),
)
INEFFECTIVE_STAGING_PATTERNS = (
    re.compile(r"\bquick\s+steps?\b", re.IGNORECASE),
)


def has_solo_people_conflict(text: str) -> bool:
    source = str(text or "")
    policy_families = classify_risk_families(source)
    return bool(policy_families & {"crowd", "family_artifact", "foreground_background_conflict"}) or any(
        pattern.search(source) for pattern in SOLO_PEOPLE_PATTERNS
    )


def has_other_person_conflict(text: str) -> bool:
    source = str(text or "")
    policy_flags = solo_flags_for_risk_families(classify_risk_families(source))
    return (
        "other_person" in policy_flags
        or has_solo_people_conflict(source)
        or any(pattern.search(source) for pattern in SOLO_OTHER_PERSON_PATTERNS)
    )


def has_social_talk_conflict(text: str) -> bool:
    source = str(text or "")
    return "social_talk" in solo_flags_for_risk_families(classify_risk_families(source)) or any(
        pattern.search(source) for pattern in SOLO_SOCIAL_TALK_PATTERNS
    )


def has_mirror_clone_conflict(text: str) -> bool:
    source = str(text or "")
    return "mirror_clone" in solo_flags_for_risk_families(classify_risk_families(source)) or any(
        pattern.search(source) for pattern in SOLO_MIRROR_CLONE_PATTERNS
    )


def has_location_first_template_conflict(text: str) -> bool:
    source = str(text or "")
    lowered = source.lower()
    if "{subject_clause}" in lowered and "{loc}" in lowered:
        return lowered.find("{loc}") < lowered.find("{subject_clause}")
    primary_subject_positions = [
        pos
        for pos in (
            lowered.find("a solo "),
            lowered.find("solo girl"),
            lowered.find("solo woman"),
        )
        if pos >= 0
    ]
    subject_positions = primary_subject_positions or [
        pos
        for pos in (
            lowered.find("1girl"),
            lowered.find("solo"),
            lowered.find("girl"),
        )
        if pos >= 0
    ]
    subject_index = min(subject_positions) if subject_positions else -1
    for pattern in LOCATION_FIRST_TEMPLATE_PATTERNS:
        match = pattern.search(source)
        if match and (subject_index < 0 or match.start() < subject_index):
            return True
    return False


def _multi_action_hit_count(text: str) -> int:
    source = str(text or "")
    return sum(1 for pattern in MULTI_ACTION_DENSITY_PATTERNS for _match in pattern.finditer(source))


def solo_duplicate_risk_flags(text: str) -> Set[str]:
    source = str(text or "")
    flags: Set[str] = solo_flags_for_risk_families(classify_risk_families(source))
    if has_other_person_conflict(source):
        flags.add("other_person")
    if has_social_talk_conflict(source):
        flags.add("social_talk")
    if has_mirror_clone_conflict(source):
        flags.add("mirror_clone")
    if has_location_first_template_conflict(source):
        flags.add("location_first_template")
    if _multi_action_hit_count(source) >= 3:
        flags.add("multi_action_density")
    return flags


def has_routine_artifact_conflict(text: str) -> bool:
    source = str(text or "")
    return any(pattern.search(source) for pattern in ROUTINE_ARTIFACT_PATTERNS)


def has_ineffective_staging_conflict(text: str) -> bool:
    source = str(text or "")
    return "ineffective_motion" in classify_risk_families(source) or any(
        pattern.search(source) for pattern in INEFFECTIVE_STAGING_PATTERNS
    )


def is_solo_safe_text(text: str, *, block_routine_artifacts: bool = True) -> bool:
    if has_other_person_conflict(text):
        return False
    if block_routine_artifacts and has_routine_artifact_conflict(text):
        return False
    return True


def is_solo_action_safe_text(text: str, *, block_routine_artifacts: bool = True) -> bool:
    if not is_solo_safe_text(text, block_routine_artifacts=block_routine_artifacts):
        return False
    if has_ineffective_staging_conflict(text):
        return False
    risks = solo_duplicate_risk_flags(text)
    return not (risks & {"other_person", "social_talk", "mirror_clone"})


def filter_solo_safe_candidates(
    values: Iterable[str],
    *,
    block_routine_artifacts: bool = True,
) -> List[str]:
    return [
        str(value)
        for value in values
        if str(value).strip() and is_solo_safe_text(str(value), block_routine_artifacts=block_routine_artifacts)
    ]


def filter_solo_action_safe_candidates(
    values: Iterable[str],
    *,
    block_routine_artifacts: bool = True,
) -> List[str]:
    return [
        str(value)
        for value in values
        if str(value).strip() and is_solo_action_safe_text(str(value), block_routine_artifacts=block_routine_artifacts)
    ]
