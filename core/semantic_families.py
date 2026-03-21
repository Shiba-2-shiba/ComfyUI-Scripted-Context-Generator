from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Set, Tuple


SEMANTIC_FAMILY_KEYWORDS: Dict[str, Sequence[str]] = {
    "breath": ("breath", "breathing", "exhale", "inhale", "sigh"),
    "gaze": ("gaze", "eyes", "eye", "glance", "looking", "watching", "stare", "staring"),
    "posture": ("posture", "stance", "shoulders", "leaning", "upright", "slumped", "hunched"),
    "hands": ("hands", "hand", "fingers", "fists", "knuckles", "gripping", "sleeve"),
    "smile_mouth": ("smile", "grin", "mouth", "lips", "jaw", "teeth", "frown"),
    "expression": ("expression", "face"),
}


def split_semantic_tags(text: str) -> List[str]:
    return [part.strip() for part in str(text or "").split(",") if part.strip()]


def semantic_families_for_text(text: str) -> Set[str]:
    lowered = str(text or "").lower()
    families = set()
    for family, keywords in SEMANTIC_FAMILY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            families.add(family)
    return families


def semantic_families_for_tags(tags: Iterable[str]) -> Set[str]:
    families: Set[str] = set()
    for tag in tags or []:
        families.update(semantic_families_for_text(tag))
    return families


def filter_semantic_family_tags(
    tags: Sequence[str],
    *,
    blocked_families: Set[str] | None = None,
    per_family_limit: int = 1,
) -> Tuple[List[str], List[str], Set[str]]:
    blocked = set(blocked_families or set())
    family_counts = {family: 0 for family in SEMANTIC_FAMILY_KEYWORDS}
    kept: List[str] = []
    dropped: List[str] = []
    kept_families: Set[str] = set()

    for raw_tag in tags or []:
        tag = str(raw_tag or "").strip()
        if not tag:
            continue
        families = semantic_families_for_text(tag)
        if families:
            if families & blocked:
                dropped.append(tag)
                continue
            if any(family_counts.get(family, 0) >= int(per_family_limit) for family in families):
                dropped.append(tag)
                continue
        kept.append(tag)
        for family in families:
            family_counts[family] = family_counts.get(family, 0) + 1
            kept_families.add(family)

    return kept, dropped, kept_families
