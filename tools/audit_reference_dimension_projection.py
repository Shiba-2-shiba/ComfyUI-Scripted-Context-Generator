from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.extract_epig_reference_overlay import (  # noqa: E402
    STOPWORDS,
    collect_current_vocabulary,
    load_reference_sources,
)
from vocab.epig_reference import lookup_term, normalize_term  # noqa: E402


PERSONALITY_AXES = (
    "sociability",
    "restraint",
    "confidence",
    "curiosity",
    "meticulousness",
    "warmth",
)
PROJECTION_AXES = ("sociability", "restraint", "confidence", "warmth")
VAD_AXES = ("valence", "arousal", "dominance")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _clamp01(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _normalize_vector(vector: dict[str, Any] | None, axes: tuple[str, ...]) -> dict[str, float]:
    source = vector if isinstance(vector, dict) else {}
    return {axis: _clamp01(source.get(axis, 0.5)) for axis in axes}


def _distance(left: dict[str, float], right: dict[str, float], axes: tuple[str, ...]) -> float:
    if not axes:
        return 0.0
    return math.sqrt(sum((float(left.get(axis, 0.5)) - float(right.get(axis, 0.5))) ** 2 for axis in axes) / len(axes))


def _relevance(distance: float, gamma: float = 2.0) -> float:
    return math.exp(-float(gamma) * max(0.0, float(distance)))


def _reference_matches(term: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches = []
    for source in sources:
        record = lookup_term(term, source.get("records", {}))
        if record is None:
            continue
        item = dict(record)
        item["source"] = source["name"]
        matches.append(item)
    return matches


def _meaningful_tokens(text: str) -> list[str]:
    return [token for token in normalize_term(text).split() if token not in STOPWORDS and len(token) >= 3]


def _average_records(records: list[dict[str, Any]]) -> dict[str, float]:
    averages: dict[str, float] = {}
    for axis in VAD_AXES:
        values = []
        for record in records:
            if axis not in record:
                continue
            try:
                values.append(float(record[axis]))
            except (TypeError, ValueError):
                continue
        if values:
            averages[axis] = round(sum(values) / len(values), 4)
    return averages


def _lookup_reference_vad(term: str, sources: list[dict[str, Any]]) -> tuple[str, dict[str, float], list[dict[str, Any]]]:
    exact = _reference_matches(term, sources)
    exact_vad = _average_records(exact)
    if exact_vad:
        return "exact", exact_vad, exact

    token_records = []
    for token in _meaningful_tokens(term):
        for match in _reference_matches(token, sources):
            token_records.append({"token": token, **match})
    token_vad = _average_records(token_records)
    if token_vad:
        return "token_fallback", token_vad, token_records
    return "none", {}, []


def _project_vad_to_personality(vad: dict[str, float]) -> dict[str, float] | None:
    if "dominance" not in vad:
        return None
    dominance = _clamp01(vad.get("dominance"))
    valence = _clamp01(vad.get("valence", 0.5))
    return {
        "sociability": valence,
        "restraint": 1.0 - dominance,
        "confidence": dominance,
        "warmth": valence,
    }


def _load_personality_payload(repo_root: Path) -> dict[str, Any]:
    payload = _load_json(repo_root / "vocab" / "data" / "personality_behavior_profiles.json")
    return payload if isinstance(payload, dict) else {}


def _personality_descriptors(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    descriptors = payload.get("descriptors", {}) if isinstance(payload, dict) else {}
    result: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(descriptors, dict):
        return result
    for slot, items in sorted(descriptors.items()):
        if not isinstance(items, list):
            continue
        result[str(slot)] = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            result[str(slot)].append(
                {
                    "text": text,
                    "vector": item.get("vector", {}),
                    "source": f"personality_behavior_profiles:{slot}[{index}]",
                }
            )
    return result


def _rank_descriptors(descriptors: list[dict[str, Any]], target: dict[str, float], axes: tuple[str, ...], vector_key: str) -> list[dict[str, Any]]:
    ranked = []
    for descriptor in descriptors:
        vector = _normalize_vector(descriptor.get(vector_key, {}), axes)
        distance = _distance(vector, target, axes)
        item = dict(descriptor)
        item["distance"] = distance
        item["score"] = _relevance(distance)
        ranked.append(item)
    ranked.sort(key=lambda item: (-(item.get("score") or 0.0), str(item.get("text", ""))))
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    return ranked


def _personality_projection(payload: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
    profiles = payload.get("profiles", {}) if isinstance(payload, dict) else {}
    descriptors_by_slot = _personality_descriptors(payload)
    records = []
    high_risk_examples = []
    if not isinstance(profiles, dict):
        return {"comparison_count": 0, "high_risk_count": 0, "high_risk_examples": [], "records": []}

    for personality, profile in sorted(profiles.items()):
        if not isinstance(profile, dict):
            continue
        target_current = _normalize_vector(profile.get("vector", {}), PERSONALITY_AXES)
        target_projected = _normalize_vector(profile.get("vector", {}), PROJECTION_AXES)
        for slot, descriptors in descriptors_by_slot.items():
            current_ranked = _rank_descriptors(descriptors, target_current, PERSONALITY_AXES, "vector")
            current_rank_by_text = {str(item["text"]): int(item["rank"]) for item in current_ranked}
            projected_descriptors = []
            for descriptor in descriptors:
                match_type, vad, matches = _lookup_reference_vad(str(descriptor.get("text", "")), sources)
                projection = _project_vad_to_personality(vad)
                if projection is None:
                    continue
                projected = dict(descriptor)
                projected["match_type"] = match_type
                projected["reference_vad"] = vad
                projected["projected_vector"] = projection
                projected["reference_match_preview"] = matches[:4]
                projected_descriptors.append(projected)

            projected_ranked = _rank_descriptors(projected_descriptors, target_projected, PROJECTION_AXES, "projected_vector")
            for item in projected_ranked:
                text = str(item.get("text", ""))
                current_rank = current_rank_by_text.get(text)
                if current_rank is None:
                    continue
                rank_delta = int(item["rank"]) - int(current_rank)
                record = {
                    "personality": str(personality),
                    "slot": slot,
                    "text": text,
                    "current_rank": current_rank,
                    "projected_rank": int(item["rank"]),
                    "rank_delta": rank_delta,
                    "match_type": item.get("match_type", ""),
                    "reference_vad": item.get("reference_vad", {}),
                    "projected_vector": item.get("projected_vector", {}),
                    "source": item.get("source", ""),
                }
                records.append(record)
                if abs(rank_delta) >= 2:
                    high_risk_examples.append({**record, "risk": "dominance_projection_rank_shift"})

    records.sort(key=lambda item: (abs(int(item["rank_delta"])), item["personality"], item["slot"], item["text"]), reverse=True)
    high_risk_examples.sort(key=lambda item: (abs(int(item["rank_delta"])), item["personality"], item["slot"], item["text"]), reverse=True)
    return {
        "comparison_count": len(records),
        "high_risk_count": len(high_risk_examples),
        "high_risk_examples": high_risk_examples[:20],
        "records": records[:200],
    }


def _coverage_for_vocabulary(vocabulary: dict[str, dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    exact_records = []
    token_records = []
    exact_match_count = 0
    token_match_count = 0
    for term in sorted(vocabulary):
        match_type, vad, matches = _lookup_reference_vad(term, sources)
        if match_type == "exact":
            exact_match_count += 1
            exact_records.extend(matches)
        elif match_type == "token_fallback":
            token_match_count += 1
            token_records.extend(matches)
    all_records = exact_records + token_records
    return {
        "extracted_term_count": len(vocabulary),
        "exact_match_count": exact_match_count,
        "token_fallback_match_count": token_match_count,
        "matched_term_count": exact_match_count + token_match_count,
        "average_vad": _average_records(all_records),
    }


def _descriptor_group_averages(payload: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
    groups = []
    for slot, descriptors in _personality_descriptors(payload).items():
        records = []
        matched = 0
        for descriptor in descriptors:
            match_type, vad, matches = _lookup_reference_vad(str(descriptor.get("text", "")), sources)
            if match_type == "none":
                continue
            matched += 1
            records.extend(matches)
        groups.append(
            {
                "group": f"personality.{slot}",
                "descriptor_count": len(descriptors),
                "matched_descriptor_count": matched,
                "average_vad": _average_records(records),
            }
        )
    return {
        "group_count": len(groups),
        "groups": groups,
    }


def _optional_lexicons(reference_root: Path) -> dict[str, Any]:
    worry_candidates = [
        reference_root / "WorryWords",
        reference_root / "worrywords",
        reference_root / "NRC-WorryWords",
    ]
    warmth_candidates = [
        reference_root / "WordsOfWarmth",
        reference_root / "Words-of-Warmth",
        reference_root / "NRC-Words-of-Warmth",
        reference_root / "warmth",
    ]
    return {
        "worrywords_available": any(path.exists() for path in worry_candidates),
        "words_of_warmth_available": any(path.exists() for path in warmth_candidates),
        "worrywords_candidates": [str(path) for path in worry_candidates],
        "words_of_warmth_candidates": [str(path) for path in warmth_candidates],
    }


def audit_reference_dimension_projection(repo_root: str | Path = ROOT, reference_root: str | Path | None = None) -> dict[str, Any]:
    repo_path = Path(repo_root)
    ref_path = Path(reference_root) if reference_root is not None else repo_path.parent / "参考"
    sources, warnings = load_reference_sources(ref_path)
    vocabulary = collect_current_vocabulary(repo_path)
    personality_payload = _load_personality_payload(repo_path)
    return {
        "schema_version": "1.0",
        "generated_kind": "reference_dimension_projection_audit",
        "tracked_policy": "generated_local_only",
        "policy": {
            "runtime_output_unchanged": True,
            "audit_only": True,
            "no_new_dependencies": True,
            "raw_reference_rows_not_reused_as_runtime_data": True,
        },
        "reference": {
            "source_count": len(sources),
            "loaded_record_count": sum(len(source.get("records", {})) for source in sources),
            "warning_count": len(warnings),
            "warnings": warnings,
        },
        "optional_lexicons": _optional_lexicons(ref_path),
        "current_vocabulary_coverage": _coverage_for_vocabulary(vocabulary, sources),
        "descriptor_group_averages": _descriptor_group_averages(personality_payload, sources),
        "personality_dominance_projection": _personality_projection(personality_payload, sources),
        "dominance_decision": {
            "runtime_axis_adoption": "deferred",
            "reason": "Dominance is evaluated as an audit-only projection before any personality/runtime axis change.",
        },
    }


def write_audit(result: dict[str, Any], output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit dominance projection and EmotionDynamics-style coverage without changing runtime behavior.")
    parser.add_argument("--reference-root", default=str(ROOT.parent / "参考"))
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--output", default=str(ROOT / "assets" / "results" / "reference_dimension_projection.json"))
    args = parser.parse_args(argv)

    result = audit_reference_dimension_projection(args.repo_root, args.reference_root)
    output_path = write_audit(result, args.output)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "exact_match_count": result["current_vocabulary_coverage"]["exact_match_count"],
                "matched_term_count": result["current_vocabulary_coverage"]["matched_term_count"],
                "projection_comparison_count": result["personality_dominance_projection"]["comparison_count"],
                "high_risk_count": result["personality_dominance_projection"]["high_risk_count"],
                "warning_count": result["reference"]["warning_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
