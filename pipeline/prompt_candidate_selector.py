from __future__ import annotations

from typing import Any

try:
    from ..core.prompt_ir_validator import validate_prompt_ir
except ImportError:
    from core.prompt_ir_validator import validate_prompt_ir


def score_prompt_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    report = validate_prompt_ir(candidate.get("ir", {}), rendered_text=str(candidate.get("rendered_text", "")))
    scored = dict(candidate)
    scored["scores"] = report["scores"]
    scored["total_risk"] = report["total_risk"]
    scored["quality_score"] = report["quality_score"]
    scored["issues"] = report["issues"]
    return scored


def select_prompt_candidate(candidates: list[dict[str, Any]], *, mode: str = "passive_debug") -> dict[str, Any]:
    scored = [score_prompt_candidate(candidate) for candidate in candidates]
    if not scored:
        raise ValueError("at least one prompt candidate is required")
    selected = min(
        scored,
        key=lambda candidate: (
            int(candidate.get("total_risk", 0)),
            0 if str(candidate.get("candidate_id", "")).endswith(":0") else 1,
            str(candidate.get("candidate_id", "")),
        ),
    )
    selected_id = selected["candidate_id"]
    selected["selection"] = {
        "selected_candidate_id": selected_id,
        "rejected_candidate_ids": [
            candidate["candidate_id"] for candidate in scored if candidate["candidate_id"] != selected_id
        ],
        "mode": mode,
    }
    return selected


def summarize_prompt_candidates(candidates: list[dict[str, Any]], *, mode: str = "passive_debug") -> dict[str, Any]:
    scored = [score_prompt_candidate(candidate) for candidate in candidates]
    selected = select_prompt_candidate(candidates, mode=mode)
    return {
        "mode": mode,
        "selected_candidate_id": selected["candidate_id"],
        "candidates": [
            {
                "candidate_id": candidate["candidate_id"],
                "branch_seed": candidate.get("branch_seed"),
                "scores": candidate["scores"],
                "total_risk": candidate["total_risk"],
                "quality_score": candidate["quality_score"],
                "dropped_components": candidate.get("dropped_components", []),
                "warnings": candidate.get("warnings", []),
            }
            for candidate in scored
        ],
    }
