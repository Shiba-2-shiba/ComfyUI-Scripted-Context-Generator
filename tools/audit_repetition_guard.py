from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.context_ops import patch_context  # noqa: E402
from pipeline.action_generator import action_verb  # noqa: E402
from pipeline.clothing_builder import apply_clothing_expansion  # noqa: E402
from pipeline.location_builder import apply_location_expansion  # noqa: E402
from pipeline.prompt_orchestrator import build_prompt_from_context  # noqa: E402
from pipeline.context_pipeline import apply_scene_variation  # noqa: E402
from pipeline.source_pipeline import parse_prompt_source_fields  # noqa: E402


STEP_COUNT_DEFAULT = 32
SCENARIO_COUNT_DEFAULT = 8
MAX_AVG_ADJ_LOC_REPEAT = 0.12
MAX_AVG_ADJ_ACTION_VERB_REPEAT = 0.22
MAX_AVG_ADJ_COSTUME_REPEAT = 0.35
MAX_AVG_ADJ_TEMPLATE_REPEAT = 0.12
MAX_AVG_RECENT4_LOC_REPEAT = 0.30
MAX_AVG_RECENT4_ACTION_VERB_REPEAT = 0.45
MAX_AVG_RECENT4_COSTUME_REPEAT = 0.65
MAX_AVG_RECENT4_TEMPLATE_REPEAT = 0.25
MAX_AVG_ADJ_OBJECT_OVERLAP = 0.28
MAX_AVG_RECENT4_OBJECT_OVERLAP = 0.35
CLOTHING_SCENARIO_HIGHLIGHT_LIMIT = 3


def _latest_decision(ctx: Any, node_name: str) -> Dict[str, Any]:
    for entry in reversed(getattr(ctx, "history", [])):
        if entry.node == node_name:
            return dict(entry.decision or {})
    return {}


def _adjacent_repeat_rate(values: Sequence[str]) -> float:
    if len(values) < 2:
        return 0.0
    repeats = 0
    total = 0
    for prev, curr in zip(values, values[1:]):
        if not prev or not curr:
            continue
        total += 1
        if prev == curr:
            repeats += 1
    return (repeats / total) if total else 0.0


def _recent_window_repeat_rate(values: Sequence[str], window: int = 4) -> float:
    if len(values) < 2:
        return 0.0
    repeats = 0
    total = 0
    for idx in range(1, len(values)):
        value = str(values[idx] or "").strip()
        if not value:
            continue
        previous = {str(item).strip() for item in values[max(0, idx - window) : idx] if str(item).strip()}
        if not previous:
            continue
        total += 1
        if value in previous:
            repeats += 1
    return (repeats / total) if total else 0.0


def _adjacent_object_overlap_rate(object_sets: Sequence[Set[str]]) -> float:
    if len(object_sets) < 2:
        return 0.0
    overlaps = 0
    total = 0
    for prev, curr in zip(object_sets, object_sets[1:]):
        if not prev or not curr:
            continue
        total += 1
        if prev & curr:
            overlaps += 1
    return (overlaps / total) if total else 0.0


def _recent_window_object_overlap_rate(object_sets: Sequence[Set[str]], window: int = 4) -> float:
    if len(object_sets) < 2:
        return 0.0
    overlaps = 0
    total = 0
    for idx in range(1, len(object_sets)):
        current = set(object_sets[idx] or set())
        if not current:
            continue
        previous_union: Set[str] = set()
        for prev in object_sets[max(0, idx - window) : idx]:
            previous_union.update(prev or set())
        if not previous_union:
            continue
        total += 1
        if current & previous_union:
            overlaps += 1
    return (overlaps / total) if total else 0.0


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return (sum(values) / len(values)) if values else 0.0


def _sorted_clothing_scenarios(
    scenario_reports: Sequence[Dict[str, Any]],
    metric_name: str,
    limit: int = CLOTHING_SCENARIO_HIGHLIGHT_LIMIT,
) -> List[Dict[str, Any]]:
    ranked = sorted(
        scenario_reports,
        key=lambda item: (-float(item.get(metric_name, 0.0)), int(item.get("base_seed", 0))),
    )
    rows: List[Dict[str, Any]] = []
    for item in ranked[:limit]:
        source = item.get("source", {}) or {}
        rows.append(
            {
                "base_seed": int(item.get("base_seed", 0)),
                "source_costume": str(source.get("costume", "")),
                "source_subj": str(source.get("subj", "")),
                "source_loc": str(source.get("loc", "")),
                "adjacent_pack_repeat_rate": round(float(item.get("adjacent_costume_repeat_rate", 0.0)), 4),
                "adjacent_signature_repeat_rate": round(float(item.get("adjacent_costume_signature_repeat_rate", 0.0)), 4),
                "recent4_pack_repeat_rate": round(float(item.get("recent4_costume_repeat_rate", 0.0)), 4),
                "recent4_signature_repeat_rate": round(float(item.get("recent4_costume_signature_repeat_rate", 0.0)), 4),
                "unique_costume_packs": int(item.get("unique_costume_packs", 0)),
                "unique_costume_signatures": int(item.get("unique_costume_signatures", 0)),
            }
        )
    return rows


def _build_clothing_repetition_summary(
    scenario_reports: Sequence[Dict[str, Any]],
    overall_summary: Dict[str, Any],
) -> Dict[str, Any]:
    avg_unique_costume_packs = round(_mean(item.get("unique_costume_packs", 0) for item in scenario_reports), 4)
    avg_unique_costume_signatures = round(_mean(item.get("unique_costume_signatures", 0) for item in scenario_reports), 4)
    summary = {
        "artifact_version": 1,
        "kpi": {
            "avg_adjacent_pack_repeat_rate": round(float(overall_summary.get("avg_adjacent_costume_repeat_rate", 0.0)), 4),
            "avg_adjacent_signature_repeat_rate": round(float(overall_summary.get("avg_adjacent_costume_signature_repeat_rate", 0.0)), 4),
            "avg_recent4_pack_repeat_rate": round(float(overall_summary.get("avg_recent4_costume_repeat_rate", 0.0)), 4),
            "avg_recent4_signature_repeat_rate": round(float(overall_summary.get("avg_recent4_costume_signature_repeat_rate", 0.0)), 4),
            "max_adjacent_signature_repeat_rate": round(float(overall_summary.get("max_adjacent_costume_signature_repeat_rate", 0.0)), 4),
            "max_recent4_signature_repeat_rate": round(
                max(float(item.get("recent4_costume_signature_repeat_rate", 0.0)) for item in scenario_reports),
                4,
            )
            if scenario_reports
            else 0.0,
            "avg_unique_costume_packs": avg_unique_costume_packs,
            "avg_unique_costume_signatures": avg_unique_costume_signatures,
        },
        "thresholds": {
            "max_avg_adjacent_signature_repeat_rate": MAX_AVG_ADJ_COSTUME_REPEAT,
            "max_avg_recent4_signature_repeat_rate": MAX_AVG_RECENT4_COSTUME_REPEAT,
        },
        "worst_recent4_signature_scenarios": _sorted_clothing_scenarios(
            scenario_reports,
            "recent4_costume_signature_repeat_rate",
        ),
        "worst_adjacent_signature_scenarios": _sorted_clothing_scenarios(
            scenario_reports,
            "adjacent_costume_signature_repeat_rate",
        ),
        "lowest_unique_signature_scenarios": sorted(
            _sorted_clothing_scenarios(scenario_reports, "recent4_costume_signature_repeat_rate", limit=len(scenario_reports)),
            key=lambda item: (int(item["unique_costume_signatures"]), int(item["base_seed"])),
        )[:CLOTHING_SCENARIO_HIGHLIGHT_LIMIT],
    }
    return summary


def _build_seed_scenarios(count: int, seed_start: int) -> List[Dict[str, Any]]:
    scenarios = []
    for offset in range(count):
        seed = seed_start + offset
        subj, costume, loc, action, meta_mood, _legacy_style, scene_tags = parse_prompt_source_fields("{}", seed)
        scenarios.append(
            {
                "seed": seed,
                "subj": subj,
                "costume": costume,
                "loc": loc,
                "action": action,
                "meta_mood": meta_mood,
                "scene_tags": scene_tags,
            }
        )
    return scenarios


def _run_repetition_sequence(base_seed: int, step_count: int) -> Dict[str, Any]:
    subj, costume, loc, action, meta_mood, _legacy_style, scene_tags = parse_prompt_source_fields("{}", base_seed)
    ctx = patch_context(
        {},
        updates={"subj": subj, "costume": costume, "loc": loc, "action": action, "seed": base_seed},
        meta={"mood": meta_mood},
        extras={"source_subj_key": subj, "raw_costume_key": costume, "raw_loc_tag": loc, "scene_tags": scene_tags},
    )

    locs: List[str] = []
    action_verbs: List[str] = []
    costume_packs: List[str] = []
    costume_signatures: List[str] = []
    template_keys: List[str] = []
    object_sets: List[Set[str]] = []
    steps: List[Dict[str, Any]] = []

    for offset in range(step_count):
        seed = base_seed + offset
        ctx, scene_debug = apply_scene_variation(ctx, seed, "full")
        ctx, _clothing_prompt = apply_clothing_expansion(ctx, seed, "random", 0.3)
        ctx, _location_prompt = apply_location_expansion(ctx, seed, "detailed", "off")
        ctx, prompt = build_prompt_from_context(ctx, "", True, seed)

        clothing_decision = _latest_decision(ctx, "ContextClothingExpander")
        location_decision = _latest_decision(ctx, "ContextLocationExpander")
        builder_decision = _latest_decision(ctx, "ContextPromptBuilder")
        scene_decision = scene_debug.decision or {}

        object_focus = (((scene_decision.get("object_focus") or {}).get("detected_objects")) or [])
        location_objects = location_decision.get("objects", []) or []
        current_objects = {str(item) for item in [*location_objects, *object_focus] if item}

        locs.append(str(ctx.loc))
        action_verbs.append(action_verb(ctx.action))
        costume_packs.append(str(clothing_decision.get("base_pack", "")).strip())
        costume_signatures.append(str(clothing_decision.get("signature", "")).strip())
        template_keys.append(str(builder_decision.get("template_key", "")).strip())
        object_sets.append(current_objects)
        steps.append(
            {
                "seed": seed,
                "loc": str(ctx.loc),
                "action": str(ctx.action),
                "action_verb": action_verb(ctx.action),
                "costume_pack": str(clothing_decision.get("base_pack", "")).strip(),
                "costume_signature": str(clothing_decision.get("signature", "")).strip(),
                "template_key": str(builder_decision.get("template_key", "")).strip(),
                "objects": sorted(current_objects),
                "prompt": prompt,
            }
        )

    return {
        "base_seed": base_seed,
        "step_count": step_count,
        "adjacent_loc_repeat_rate": round(_adjacent_repeat_rate(locs), 4),
        "adjacent_action_verb_repeat_rate": round(_adjacent_repeat_rate(action_verbs), 4),
        "adjacent_costume_repeat_rate": round(_adjacent_repeat_rate(costume_packs), 4),
        "adjacent_costume_signature_repeat_rate": round(_adjacent_repeat_rate(costume_signatures), 4),
        "adjacent_template_repeat_rate": round(_adjacent_repeat_rate(template_keys), 4),
        "recent4_loc_repeat_rate": round(_recent_window_repeat_rate(locs, window=4), 4),
        "recent4_action_verb_repeat_rate": round(_recent_window_repeat_rate(action_verbs, window=4), 4),
        "recent4_costume_repeat_rate": round(_recent_window_repeat_rate(costume_packs, window=4), 4),
        "recent4_costume_signature_repeat_rate": round(_recent_window_repeat_rate(costume_signatures, window=4), 4),
        "recent4_template_repeat_rate": round(_recent_window_repeat_rate(template_keys, window=4), 4),
        "adjacent_object_overlap_rate": round(_adjacent_object_overlap_rate(object_sets), 4),
        "recent4_object_overlap_rate": round(_recent_window_object_overlap_rate(object_sets, window=4), 4),
        "unique_locs": len(set(item for item in locs if item)),
        "unique_action_verbs": len(set(item for item in action_verbs if item)),
        "unique_costume_packs": len(set(item for item in costume_packs if item)),
        "unique_costume_signatures": len(set(item for item in costume_signatures if item)),
        "unique_templates": len(set(item for item in template_keys if item)),
        "steps": steps[:8],
    }


def build_repetition_guard_report(step_count: int = STEP_COUNT_DEFAULT, scenario_count: int = SCENARIO_COUNT_DEFAULT, seed_start: int = 0) -> Dict[str, Any]:
    scenario_reports = []
    scenarios = _build_seed_scenarios(scenario_count, seed_start)
    for scenario in scenarios:
        report = _run_repetition_sequence(int(scenario["seed"]), step_count)
        report["source"] = {
            "subj": scenario["subj"],
            "costume": scenario["costume"],
            "loc": scenario["loc"],
            "action": scenario["action"],
        }
        scenario_reports.append(report)

    summary = {
        "scenario_count": len(scenario_reports),
        "step_count": int(step_count),
        "avg_adjacent_loc_repeat_rate": round(_mean(item["adjacent_loc_repeat_rate"] for item in scenario_reports), 4),
        "avg_adjacent_action_verb_repeat_rate": round(_mean(item["adjacent_action_verb_repeat_rate"] for item in scenario_reports), 4),
        "avg_adjacent_costume_repeat_rate": round(_mean(item["adjacent_costume_repeat_rate"] for item in scenario_reports), 4),
        "avg_adjacent_costume_signature_repeat_rate": round(_mean(item["adjacent_costume_signature_repeat_rate"] for item in scenario_reports), 4),
        "avg_adjacent_template_repeat_rate": round(_mean(item["adjacent_template_repeat_rate"] for item in scenario_reports), 4),
        "avg_recent4_loc_repeat_rate": round(_mean(item["recent4_loc_repeat_rate"] for item in scenario_reports), 4),
        "avg_recent4_action_verb_repeat_rate": round(_mean(item["recent4_action_verb_repeat_rate"] for item in scenario_reports), 4),
        "avg_recent4_costume_repeat_rate": round(_mean(item["recent4_costume_repeat_rate"] for item in scenario_reports), 4),
        "avg_recent4_costume_signature_repeat_rate": round(_mean(item["recent4_costume_signature_repeat_rate"] for item in scenario_reports), 4),
        "avg_recent4_template_repeat_rate": round(_mean(item["recent4_template_repeat_rate"] for item in scenario_reports), 4),
        "avg_adjacent_object_overlap_rate": round(_mean(item["adjacent_object_overlap_rate"] for item in scenario_reports), 4),
        "avg_recent4_object_overlap_rate": round(_mean(item["recent4_object_overlap_rate"] for item in scenario_reports), 4),
        "max_adjacent_loc_repeat_rate": round(max(item["adjacent_loc_repeat_rate"] for item in scenario_reports), 4) if scenario_reports else 0.0,
        "max_adjacent_action_verb_repeat_rate": round(max(item["adjacent_action_verb_repeat_rate"] for item in scenario_reports), 4) if scenario_reports else 0.0,
        "max_adjacent_costume_repeat_rate": round(max(item["adjacent_costume_repeat_rate"] for item in scenario_reports), 4) if scenario_reports else 0.0,
        "max_adjacent_costume_signature_repeat_rate": round(max(item["adjacent_costume_signature_repeat_rate"] for item in scenario_reports), 4) if scenario_reports else 0.0,
        "max_adjacent_template_repeat_rate": round(max(item["adjacent_template_repeat_rate"] for item in scenario_reports), 4) if scenario_reports else 0.0,
    }
    clothing_repetition = _build_clothing_repetition_summary(scenario_reports, summary)
    return {
        "scenario_seed_start": seed_start,
        "summary": summary,
        "clothing_repetition": clothing_repetition,
        "scenarios": scenario_reports,
    }


def evaluate_repetition_guard_thresholds(report: Dict[str, Any]) -> Dict[str, Any]:
    summary = report.get("summary", {}) or {}
    failures = []
    checks = [
        ("avg_adjacent_loc_repeat_rate", float(summary.get("avg_adjacent_loc_repeat_rate", 0.0)), MAX_AVG_ADJ_LOC_REPEAT),
        ("avg_adjacent_action_verb_repeat_rate", float(summary.get("avg_adjacent_action_verb_repeat_rate", 0.0)), MAX_AVG_ADJ_ACTION_VERB_REPEAT),
        ("avg_adjacent_costume_signature_repeat_rate", float(summary.get("avg_adjacent_costume_signature_repeat_rate", 0.0)), MAX_AVG_ADJ_COSTUME_REPEAT),
        ("avg_adjacent_template_repeat_rate", float(summary.get("avg_adjacent_template_repeat_rate", 0.0)), MAX_AVG_ADJ_TEMPLATE_REPEAT),
        ("avg_recent4_loc_repeat_rate", float(summary.get("avg_recent4_loc_repeat_rate", 0.0)), MAX_AVG_RECENT4_LOC_REPEAT),
        ("avg_recent4_action_verb_repeat_rate", float(summary.get("avg_recent4_action_verb_repeat_rate", 0.0)), MAX_AVG_RECENT4_ACTION_VERB_REPEAT),
        ("avg_recent4_costume_signature_repeat_rate", float(summary.get("avg_recent4_costume_signature_repeat_rate", 0.0)), MAX_AVG_RECENT4_COSTUME_REPEAT),
        ("avg_recent4_template_repeat_rate", float(summary.get("avg_recent4_template_repeat_rate", 0.0)), MAX_AVG_RECENT4_TEMPLATE_REPEAT),
        ("avg_adjacent_object_overlap_rate", float(summary.get("avg_adjacent_object_overlap_rate", 0.0)), MAX_AVG_ADJ_OBJECT_OVERLAP),
        ("avg_recent4_object_overlap_rate", float(summary.get("avg_recent4_object_overlap_rate", 0.0)), MAX_AVG_RECENT4_OBJECT_OVERLAP),
    ]
    for code, actual, threshold in checks:
        if actual > threshold:
            failures.append(
                {
                    "code": code,
                    "expected_lte": threshold,
                    "actual": actual,
                }
            )
    return {
        "passed": not failures,
        "thresholds": {
            "max_avg_adjacent_loc_repeat_rate": MAX_AVG_ADJ_LOC_REPEAT,
            "max_avg_adjacent_action_verb_repeat_rate": MAX_AVG_ADJ_ACTION_VERB_REPEAT,
            "max_avg_adjacent_costume_signature_repeat_rate": MAX_AVG_ADJ_COSTUME_REPEAT,
            "max_avg_adjacent_template_repeat_rate": MAX_AVG_ADJ_TEMPLATE_REPEAT,
            "max_avg_recent4_loc_repeat_rate": MAX_AVG_RECENT4_LOC_REPEAT,
            "max_avg_recent4_action_verb_repeat_rate": MAX_AVG_RECENT4_ACTION_VERB_REPEAT,
            "max_avg_recent4_costume_signature_repeat_rate": MAX_AVG_RECENT4_COSTUME_REPEAT,
            "max_avg_recent4_template_repeat_rate": MAX_AVG_RECENT4_TEMPLATE_REPEAT,
            "max_avg_adjacent_object_overlap_rate": MAX_AVG_ADJ_OBJECT_OVERLAP,
            "max_avg_recent4_object_overlap_rate": MAX_AVG_RECENT4_OBJECT_OVERLAP,
        },
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit repetition guard behavior across 32-step history runs")
    parser.add_argument("--step-count", type=int, default=STEP_COUNT_DEFAULT)
    parser.add_argument("--scenario-count", type=int, default=SCENARIO_COUNT_DEFAULT)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--output", default="")
    parser.add_argument("--enforce-thresholds", action="store_true")
    args = parser.parse_args()

    report = build_repetition_guard_report(
        step_count=args.step_count,
        scenario_count=args.scenario_count,
        seed_start=args.seed_start,
    )
    report["threshold_evaluation"] = evaluate_repetition_guard_thresholds(report)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    print(text)
    if args.enforce_thresholds and not report["threshold_evaluation"]["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
