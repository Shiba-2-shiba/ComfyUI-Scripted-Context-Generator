from __future__ import annotations

import re
from typing import Iterable, List


SOLO_PEOPLE_PATTERNS = (
    re.compile(r"\bcrowd\w*\b", re.IGNORECASE),
    re.compile(r"\bpeople\b", re.IGNORECASE),
    re.compile(r"\bsomeone\b", re.IGNORECASE),
    re.compile(r"\bstudents?\s+(?:pass|passes|passing)\b", re.IGNORECASE),
    re.compile(r"\bpass(?:es|ing)?\s+by\b", re.IGNORECASE),
    re.compile(r"\bpass(?:es|ing)?\s+through\b", re.IGNORECASE),
)

ROUTINE_ARTIFACT_PATTERNS = (
    re.compile(r"\bspill(?:s|ed)?\b", re.IGNORECASE),
    re.compile(r"\bstain(?:s|ed)?\b", re.IGNORECASE),
    re.compile(r"\bwet\s+sleeve\b", re.IGNORECASE),
    re.compile(r"\bnapkins?\b", re.IGNORECASE),
)


def has_solo_people_conflict(text: str) -> bool:
    source = str(text or "")
    return any(pattern.search(source) for pattern in SOLO_PEOPLE_PATTERNS)


def has_routine_artifact_conflict(text: str) -> bool:
    source = str(text or "")
    return any(pattern.search(source) for pattern in ROUTINE_ARTIFACT_PATTERNS)


def is_solo_safe_text(text: str, *, block_routine_artifacts: bool = True) -> bool:
    if has_solo_people_conflict(text):
        return False
    if block_routine_artifacts and has_routine_artifact_conflict(text):
        return False
    return True


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
