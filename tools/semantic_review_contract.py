"""Version bindings and the prospectively approved v7 review boundary."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SEMANTIC_COMPARISON_TO_REVIEW = {
    "prompt-quality-comparison/v2": "prompt-quality-review/v4",
    "prompt-quality-comparison/v3": "prompt-quality-review/v5",
    "prompt-quality-comparison/v4": "prompt-quality-review/v6",
    "prompt-quality-comparison/v5": "prompt-quality-review/v7",
}
V7_TARGETS = ["naturalness", "image_prompt_suitability"]
V7_GUARDS = ["consistency", "protagonist_clarity", "redundancy", "diversity"]


def v7_dimension_eligibility(pair_ids: Sequence[str]) -> dict[str, Any]:
    return {
        dimension: {
            "authority": "current_source_corpus_confirmation" if dimension == "diversity" else "semantic_pairwise",
            "minimum_non_abstain_votes": 0 if dimension == "diversity" else 36,
            "minimum_directional_votes": 20 if dimension in V7_TARGETS else 0,
            "pair_ids": [] if dimension == "diversity" else list(pair_ids),
        }
        for dimension in V7_TARGETS + V7_GUARDS
    }


def validate_v7_review_contract(
    policy: Mapping[str, Any], *, targets: Sequence[str] | None = None,
    guards: Sequence[str] | None = None, dimensions: Mapping[str, Any] | None = None,
    pair_ids: Sequence[str] | None = None,
) -> None:
    """Reject scope/threshold edits even when an artifact was coherently rehashed."""
    expected = {
        "schema_version": "prompt-quality-review-contract/v7",
        "target_dimension_contract": {"max_candidate_worse_rate": 0.1, "min_improvement_support": 0.65, "require_lane_direction_agreement": True},
        "guard_dimension_contract": {"max_candidate_worse_rate": 0.1, "require_improvement": False, "require_lane_direction_agreement": False},
        "candidate_only_hard_defect_max": 0, "independent_lanes": 2, "paired_samples": 20,
        "sampling_strategy": "predeclared_semantic_pairing_20", "hypothesis_scoped": True,
        "require_prompt_and_rubric_hashes": True, "side_assignment": "comparison_hash_lane_pair_deterministic",
        "dimension_authority": {name: value["authority"] for name, value in v7_dimension_eligibility([]).items()},
        "hard_defect_codes": [
            "clothing_tpo_weather_conflict", "consistency_rule_conflict", "deterministic_replay_mismatch",
            "location_action_object_conflict", "male_pronoun_drift", "missing_female_protagonist",
            "mood_action_garnish_conflict", "non_girl_female_term", "other_person_solo_conflict",
            "person_demographic_descriptor", "runtime_error",
        ],
    }
    if dict(policy) != expected:
        raise ValueError("v7 review contract differs from the approved prospective thresholds")
    if (targets is not None and list(targets) != V7_TARGETS) or (guards is not None and list(guards) != V7_GUARDS):
        raise ValueError("v7 review scope differs from the approved targets and guards")
    if dimensions is not None:
        if pair_ids is None or len(pair_ids) != 20 or len(set(pair_ids)) != 20 or dict(dimensions) != v7_dimension_eligibility(pair_ids):
            raise ValueError("v7 dimension eligibility differs from the approved vote thresholds")
