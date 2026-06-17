from __future__ import annotations

from typing import Any

try:
    from .clothing_candidate_renderer import render_clothing_candidate
    from .clothing_semantics import score_clothing_decision
except ImportError:
    from pipeline.clothing_candidate_renderer import render_clothing_candidate
    from pipeline.clothing_semantics import score_clothing_decision


CLOTHING_CANDIDATE_ATTEMPTS = 5


def candidate_score_entry(decision: dict[str, Any], semantic_score: dict[str, Any], repeat_penalty: int, final_penalty: int) -> dict[str, Any]:
    return {
        "attempt_index": decision.get("attempt_index", 0),
        "score": semantic_score["score"],
        "distance": semantic_score["distance"],
        "semantic_penalty": semantic_score["semantic_penalty"],
        "repeat_penalty": repeat_penalty,
        "final_penalty": final_penalty,
    }


def annotate_clothing_candidate(decision: dict[str, Any], prompt: str, target_vector: dict[str, float], tpo_active: bool) -> tuple[int, dict[str, Any]]:
    semantic_score = score_clothing_decision(decision, prompt, target_vector)
    repeat_penalty = int(decision.get("repeat_guard_penalty", 0) or 0)
    final_penalty = repeat_penalty + (int(semantic_score["semantic_penalty"]) if tpo_active else 0)
    decision["semantic_tpo_score"] = semantic_score["score"]
    decision["semantic_tpo_penalty"] = semantic_score["semantic_penalty"]
    decision["semantic_tpo_distance"] = semantic_score["distance"]
    decision["semantic_tpo_final_penalty"] = final_penalty
    return final_penalty, candidate_score_entry(decision, semantic_score, repeat_penalty, final_penalty)


def select_clothing_candidate(
    theme_key,
    seed,
    outfit_mode,
    outerwear_chance,
    character_palette,
    loc,
    recent_packs,
    recent_types,
    recent_outerwear,
    recent_signatures,
    clothing_tpo_enabled: bool,
    clothing_tpo_active: bool,
    clothing_target_vector: dict[str, float],
) -> tuple[str, dict[str, Any], list[dict[str, Any]], int]:
    candidate_scores: list[dict[str, Any]] = []
    baseline_selected_attempt_index = 0
    baseline_best_score = None

    prompt, decision = render_clothing_candidate(
        theme_key,
        seed,
        outfit_mode,
        outerwear_chance,
        character_palette,
        loc=loc,
        recent_packs=recent_packs,
        recent_types=recent_types,
        recent_outerwear=recent_outerwear,
        recent_signatures=recent_signatures,
        attempt_index=0,
    )
    if clothing_tpo_enabled:
        final_penalty, score_entry = annotate_clothing_candidate(
            decision,
            prompt,
            clothing_target_vector,
            clothing_tpo_active,
        )
        baseline_best_score = score_entry["repeat_penalty"]
        candidate_scores.append(score_entry)
    best_score = int(decision.get("semantic_tpo_final_penalty", decision.get("repeat_guard_penalty", 0)) or 0)

    for attempt_index in range(1, CLOTHING_CANDIDATE_ATTEMPTS):
        candidate_prompt, candidate_decision = render_clothing_candidate(
            theme_key,
            seed,
            outfit_mode,
            outerwear_chance,
            character_palette,
            loc=loc,
            recent_packs=recent_packs,
            recent_types=recent_types,
            recent_outerwear=recent_outerwear,
            recent_signatures=recent_signatures,
            attempt_index=attempt_index,
        )
        if clothing_tpo_enabled:
            _final_penalty, score_entry = annotate_clothing_candidate(
                candidate_decision,
                candidate_prompt,
                clothing_target_vector,
                clothing_tpo_active,
            )
            repeat_penalty = int(score_entry["repeat_penalty"])
            if baseline_best_score is None or repeat_penalty < baseline_best_score:
                baseline_best_score = repeat_penalty
                baseline_selected_attempt_index = int(candidate_decision.get("attempt_index", attempt_index) or 0)
            candidate_scores.append(score_entry)
        candidate_score = int(candidate_decision.get("semantic_tpo_final_penalty", candidate_decision.get("repeat_guard_penalty", 0)) or 0)
        if candidate_score < best_score:
            prompt, decision = candidate_prompt, candidate_decision
            best_score = candidate_score
            if best_score == 0:
                break
    return prompt, decision, candidate_scores, baseline_selected_attempt_index
