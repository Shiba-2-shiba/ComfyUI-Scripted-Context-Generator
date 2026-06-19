from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

try:
    from ..core.prompt_ir import OPTIONAL_BRANCH_COMPONENTS, PromptIR, render_layout_first_prompt_ir
    from ..core.prompt_risk_policy import classify_risk_families
    from ..core.semantic_policy import sanitize_text
    from ..core.solo_safety import has_location_first_template_conflict
    from ..vocab.seed_utils import mix_seed
except ImportError:
    from core.prompt_ir import OPTIONAL_BRANCH_COMPONENTS, PromptIR, render_layout_first_prompt_ir
    from core.prompt_risk_policy import classify_risk_families
    from core.semantic_policy import sanitize_text
    from core.solo_safety import has_location_first_template_conflict
    from vocab.seed_utils import mix_seed


DROP_RISK_FAMILIES = {
    "crowd",
    "family_artifact",
    "foreground_background_conflict",
    "ineffective_motion",
    "other_person",
    "plural_prop_overload",
}

PERSON_CONTEXT_RISK_FAMILIES = {
    "crowd",
    "foreground_background_conflict",
    "other_person",
}


_LOCAL_RISK_REWRITES = (
    re.compile(
        r"\b(?:with|near|beside|among|around)\s+(?:a\s+)?"
        r"(?:crowd|people|customers?|friends?|classmates?|companions?|staff|employees?|bystanders?|commuters?)"
        r"(?:\s+(?:in|near|around|beside|by|at|on|sharing|working|standing|moving|passing)\b[^,.;]*)?",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:framed\s+)?family\s+photos?(?:\s+on\s+the\s+wall)?\b", re.IGNORECASE),
    re.compile(r"\bgroup\s+photos?(?:\s+on\s+the\s+wall)?\b", re.IGNORECASE),
    re.compile(r"\b(?:with\s+)?(?:piles?|pile)\s+of\s+decorative\s+pillows\b", re.IGNORECASE),
    re.compile(r"\bdecorative\s+pillows\b", re.IGNORECASE),
    re.compile(r"\bquick\s+steps?\b", re.IGNORECASE),
)

_PERSON_CONTEXT_SOCIAL_REWRITES = (
    re.compile(r"\b(?:talking|chatting)\s+(?:quietly|nearby|together)\b", re.IGNORECASE),
    re.compile(r"\b(?:talking|chatting)\b", re.IGNORECASE),
    re.compile(r"\b(?:mid\s+)?conversation\b", re.IGNORECASE),
)


def _clean_clause(text: str) -> str:
    cleaned = sanitize_text(str(text or ""))
    cleaned = re.sub(r"\b(?:with|near|beside|among|around)\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" ,.;:")


def _sanitize_risky_clause(text: str, risks: set[str]) -> str:
    cleaned = str(text or "")
    for pattern in _LOCAL_RISK_REWRITES:
        cleaned = pattern.sub("", cleaned)
    if set(risks) & PERSON_CONTEXT_RISK_FAMILIES:
        for pattern in _PERSON_CONTEXT_SOCIAL_REWRITES:
            cleaned = pattern.sub("", cleaned)
    return _clean_clause(cleaned)


def _sanitize_rendered_text(rendered_text: str) -> tuple[str, list[dict[str, Any]]]:
    kept_clauses: list[str] = []
    dropped: list[dict[str, Any]] = []
    for raw_clause in re.split(r",|;", str(rendered_text or "")):
        clause = _clean_clause(raw_clause)
        if not clause:
            continue
        risks = sorted(classify_risk_families(clause) & DROP_RISK_FAMILIES)
        if not risks:
            kept_clauses.append(clause)
            continue
        sanitized = _sanitize_risky_clause(clause, set(risks))
        remaining_risks = sorted(classify_risk_families(sanitized) & DROP_RISK_FAMILIES)
        if sanitized and not remaining_risks:
            kept_clauses.append(sanitized)
            dropped.append(
                {
                    "component": "rendered_clause",
                    "text": clause,
                    "replacement": sanitized,
                    "risk_families": risks,
                }
            )
        else:
            dropped.append({"component": "rendered_clause", "text": clause, "risk_families": risks})
    return sanitize_text(", ".join(kept_clauses)), dropped


def _copy_without_risky_optional_components(prompt_ir: PromptIR) -> tuple[PromptIR, list[dict[str, Any]]]:
    copied = deepcopy(prompt_ir)
    dropped: list[dict[str, Any]] = []
    for name in OPTIONAL_BRANCH_COMPONENTS:
        kept = []
        for component in copied.get(name, []):
            risks = sorted(set(component.risk_families) & DROP_RISK_FAMILIES)
            if risks:
                dropped.append({"component": name, "text": component.text, "risk_families": risks})
            else:
                kept.append(component)
        copied[name] = kept
    return copied, dropped


def generate_prompt_candidates(
    prompt_ir: PromptIR,
    *,
    rendered_text: str,
    seed: int,
    max_candidates: int = 2,
) -> list[dict[str, Any]]:
    candidate_count = max(1, min(int(max_candidates), 2))
    candidates = [
        {
            "candidate_id": f"seed:{seed}:branch:0",
            "branch_seed": mix_seed(int(seed), "prompt_candidate:0:baseline"),
            "rendered_text": str(rendered_text or ""),
            "ir": prompt_ir,
            "dropped_components": [],
            "warnings": [],
            "active": False,
        }
    ]
    if candidate_count == 1:
        return candidates

    pruned_ir, dropped_components = _copy_without_risky_optional_components(prompt_ir)
    sanitized_text, dropped_clauses = _sanitize_rendered_text(rendered_text)
    warnings: list[str] = []
    if has_location_first_template_conflict(rendered_text):
        layout_text = render_layout_first_prompt_ir(pruned_ir)
        candidate_text = layout_text or sanitized_text
        warnings.append("layout_first_repair")
    else:
        candidate_text = sanitized_text or render_layout_first_prompt_ir(pruned_ir)
    candidates.append(
        {
            "candidate_id": f"seed:{seed}:branch:1",
            "branch_seed": mix_seed(int(seed), "prompt_candidate:1:risk_prune"),
            "rendered_text": candidate_text,
            "ir": pruned_ir,
            "dropped_components": dropped_components + dropped_clauses,
            "warnings": warnings,
            "active": False,
        }
    )
    return candidates
