from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .prompt_ir import PromptIR, render_layout_first_prompt_ir
from .prompt_risk_policy import classify_risk_families, risk_family_matches
from .semantic_families import semantic_families_for_text
from .solo_safety import has_location_first_template_conflict, solo_duplicate_risk_flags


def _source_text(prompt_or_ir: str | PromptIR) -> str:
    if isinstance(prompt_or_ir, str):
        return prompt_or_ir
    return render_layout_first_prompt_ir(prompt_or_ir)


def solo_conflict_score(prompt_or_ir: str | PromptIR) -> int:
    text = _source_text(prompt_or_ir)
    families = classify_risk_families(text)
    flags = solo_duplicate_risk_flags(text)
    return len(
        (
            families
            & {
                "other_person",
                "crowd",
                "family_artifact",
                "mirror_clone",
                "social_interaction",
                "ineffective_motion",
            }
        )
        | flags
    )


def plural_artifact_score(prompt_or_ir: str | PromptIR) -> int:
    text = _source_text(prompt_or_ir)
    families = classify_risk_families(text)
    score = 1 if "plural_prop_overload" in families else 0
    score += len(re.findall(r"\b(?:pillows|photos|mirrors|reflections)\b", text, flags=re.IGNORECASE))
    return score


def foreground_background_alignment_score(prompt_or_ir: str | PromptIR) -> int:
    text = _source_text(prompt_or_ir).lower()
    families = classify_risk_families(text)
    score = 0
    if "foreground_background_conflict" in families:
        score += 2
    if re.search(r"\bsolo\b|\b1girl\b", text) and re.search(r"\bbackground\s+(?:people|crowd|customers|staff)\b", text):
        score += 2
    return score


def semantic_family_overload_score(prompt_or_ir: str | PromptIR) -> int:
    if isinstance(prompt_or_ir, str):
        parts = [part.strip() for part in prompt_or_ir.split(",") if part.strip()]
        families = [family for part in parts for family in semantic_families_for_text(part)]
    else:
        families = [
            family
            for components in prompt_or_ir.values()
            for component in components
            for family in component.families
        ]
    counts = Counter(families)
    return sum(max(0, count - 1) for count in counts.values())


def layout_order_score(prompt_or_ir: str | PromptIR) -> int:
    text = _source_text(prompt_or_ir)
    lowered = text.lower()
    score = 0
    if "{" in lowered and has_location_first_template_conflict(text):
        score += 2
    subject_positions = [pos for pos in (lowered.find("1girl"), lowered.find("solo"), lowered.find("girl")) if pos >= 0]
    location_positions = [
        pos
        for pos in (
            lowered.find("in "),
            lowered.find(" in "),
            lowered.find("at "),
            lowered.find(" at "),
            lowered.find("inside "),
            lowered.find("against "),
        )
        if pos >= 0
    ]
    if subject_positions and location_positions and min(location_positions) < min(subject_positions):
        score += 1
    return score


def location_object_consistency_score(prompt_or_ir: str | PromptIR) -> int:
    text = _source_text(prompt_or_ir).lower()
    checks = (
        (r"\bswimm(?:ing)?\b", ("library", "office", "classroom")),
        (r"\bcooking\b|\bstirring\b", ("library", "train station", "gallery")),
        (r"\btyping\b", ("beach", "forest", "bath")),
    )
    score = 0
    for action_pattern, bad_locations in checks:
        if re.search(action_pattern, text) and any(location in text for location in bad_locations):
            score += 1
    return score


def prompt_length_budget_score(prompt_or_ir: str | PromptIR, *, max_clauses: int = 9, max_words: int = 70) -> int:
    text = _source_text(prompt_or_ir)
    clauses = [part for part in re.split(r",|;", text) if part.strip()]
    words = re.findall(r"[A-Za-z0-9']+", text)
    return max(0, len(clauses) - max_clauses) + max(0, len(words) - max_words) // 10


def validate_prompt_ir(prompt_or_ir: str | PromptIR, *, rendered_text: str | None = None) -> dict[str, Any]:
    text = rendered_text if rendered_text is not None else _source_text(prompt_or_ir)
    scores = {
        "solo_conflict": solo_conflict_score(text),
        "plural_artifact": plural_artifact_score(text),
        "foreground_background_alignment": foreground_background_alignment_score(text),
        "semantic_family_overload": semantic_family_overload_score(prompt_or_ir),
        "layout_order": layout_order_score(text),
        "location_object_consistency": location_object_consistency_score(text),
        "prompt_length_budget": prompt_length_budget_score(text),
    }
    total_risk = sum(scores.values())
    matches = risk_family_matches(text)
    issues = [
        {"family": family, "patterns": patterns}
        for family, patterns in sorted(matches.items())
    ]
    return {
        "scores": scores,
        "total_risk": total_risk,
        "quality_score": max(0, 100 - total_risk),
        "issues": issues,
        "mutated": False,
    }
