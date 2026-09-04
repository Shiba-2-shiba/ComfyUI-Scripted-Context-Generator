from __future__ import annotations

from typing import Mapping


def _leading_bigram(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split()[:2])


def render_action_slots(slots: Mapping[str, str], activity_first: bool = False) -> str:
    anchor = slots.get("anchor", "")
    posture = str(slots.get("posture", "")).strip()
    hand_action = str(slots.get("hand_action", "")).strip()
    primary_action = str(slots.get("primary_action", "")).strip()
    purpose_clause = str(slots.get("purpose_clause", "")).strip() or "holding onto the moment in front of her"
    primary_parts = []
    if activity_first:
        if primary_action:
            primary_parts.append(primary_action)
        elif hand_action:
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
    if not activity_first and anchor and all(anchor.lower() not in part.lower() for part in (posture, hand_action, purpose_clause) if part):
        primary_parts.append(anchor)
    primary = " ".join(primary_parts).strip()
    clauses = [primary] if primary else []
    if activity_first:
        if primary_action:
            clause_keys = (
                "posture",
                "object_relation",
                "object_state",
                "gaze_target",
                "obstacle_clause",
                "purpose_clause",
            )
            support_clause = str(slots.get("social_clause", "")).strip()
        else:
            clause_keys = ("posture", "object_relation", "object_state", "gaze_target")
            support_clause = next(
                (
                    str(slots.get(key, "")).strip()
                    for key in ("obstacle_clause", "progress_clause", "optional_micro_action")
                    if str(slots.get(key, "")).strip()
                ),
                "",
            )
    else:
        clause_keys = (
            "posture",
            "hand_action",
            "object_relation",
            "object_state",
            "gaze_target",
            "optional_micro_action",
            "social_clause",
            "progress_clause",
            "obstacle_clause",
        )
        support_clause = ""
    for key in clause_keys:
        value = str(slots.get(key, "")).strip()
        if value and value.lower() not in primary.lower():
            clauses.append(value)
    if support_clause and support_clause.lower() not in primary.lower():
        clauses.append(support_clause)
    time_or_weather = str(slots.get("time_or_weather", "")).strip()
    repeated_opening = (
        activity_first
        and _leading_bigram(time_or_weather)
        and any(_leading_bigram(time_or_weather) == _leading_bigram(clause) for clause in clauses)
    )
    if time_or_weather and not repeated_opening:
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


def append_clause(action_text: str, clause: str) -> str:
    if not clause:
        return action_text
    clean_action = str(action_text).strip().rstrip(".")
    clean_clause = str(clause).strip().rstrip(".")
    if not clean_action:
        return clean_clause
    if clean_clause.lower() in clean_action.lower():
        return clean_action
    return f"{clean_action}, {clean_clause}"
