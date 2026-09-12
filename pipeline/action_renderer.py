from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RenderedActionPart:
    slot_key: str
    text: str


def _leading_bigram(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split()[:2])


def _render_action_parts(
    slots: Mapping[str, str], activity_first: bool = False,
) -> tuple[RenderedActionPart, ...]:
    anchor = slots.get("anchor", "")
    posture = str(slots.get("posture", "")).strip()
    hand_action = str(slots.get("hand_action", "")).strip()
    primary_action = str(slots.get("primary_action", "")).strip()
    purpose_clause = str(slots.get("purpose_clause", "")).strip()
    purpose_key = "purpose_clause" if purpose_clause else "default_purpose"
    purpose_clause = purpose_clause or "holding onto the moment in front of her"
    primary_parts = []
    if activity_first:
        if primary_action:
            primary_parts.append(RenderedActionPart("primary_action", primary_action))
        elif hand_action:
            primary_parts.append(RenderedActionPart("hand_action", hand_action))
        elif posture:
            primary_parts.append(RenderedActionPart("posture", posture))
        elif purpose_clause:
            primary_parts.append(RenderedActionPart(purpose_key, purpose_clause))
    else:
        if purpose_clause:
            primary_parts.append(RenderedActionPart(purpose_key, purpose_clause))
        elif hand_action:
            primary_parts.append(RenderedActionPart("hand_action", hand_action))
    if not activity_first and anchor and all(anchor.lower() not in part.lower() for part in (posture, hand_action, purpose_clause) if part):
        primary_parts.append(RenderedActionPart("anchor", anchor))
    primary = " ".join(part.text for part in primary_parts).strip()
    # A joined primary cannot be attributed to one slot. Keep the composite
    # source explicit so evidence consumers do not infer unsupported grammar.
    primary_key = "+".join(part.slot_key for part in primary_parts)
    clauses = [RenderedActionPart(primary_key, primary)] if primary else []
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
            support_key = "social_clause"
        else:
            clause_keys = ("posture", "object_relation", "object_state", "gaze_target")
            support_key = next(
                (
                    key
                    for key in ("obstacle_clause", "progress_clause", "optional_micro_action")
                    if str(slots.get(key, "")).strip()
                ),
                "",
            )
            support_clause = str(slots.get(support_key, "")).strip() if support_key else ""
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
        support_key = ""
    for key in clause_keys:
        value = str(slots.get(key, "")).strip()
        if value and value.lower() not in primary.lower():
            clauses.append(RenderedActionPart(key, value))
    if support_clause and support_clause.lower() not in primary.lower():
        clauses.append(RenderedActionPart(support_key, support_clause))
    time_or_weather = str(slots.get("time_or_weather", "")).strip()
    repeated_opening = (
        activity_first
        and _leading_bigram(time_or_weather)
        and any(_leading_bigram(time_or_weather) == _leading_bigram(clause.text) for clause in clauses)
    )
    if time_or_weather and not repeated_opening:
        clauses.append(RenderedActionPart("time_or_weather", time_or_weather))
    deduped = []
    seen = []
    for clause in clauses:
        if not clause.text:
            continue
        lowered = clause.text.lower()
        if any(lowered == existing or lowered in existing or existing in lowered for existing in seen):
            continue
        seen.append(lowered)
        deduped.append(clause)
    return tuple(deduped)


def render_action_slots(slots: Mapping[str, str], activity_first: bool = False) -> str:
    return ", ".join(part.text for part in _render_action_parts(slots, activity_first))


def trace_action_slots(
    slots: Mapping[str, str], activity_first: bool = False,
) -> tuple[RenderedActionPart, ...]:
    """Return the immutable emitted parts without changing producer rendering."""
    return _render_action_parts(slots, activity_first)


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
