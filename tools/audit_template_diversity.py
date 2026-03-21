from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.context_ops import patch_context  # noqa: E402
from pipeline.clothing_builder import apply_clothing_expansion  # noqa: E402
from pipeline.location_builder import apply_location_expansion  # noqa: E402
from pipeline.prompt_orchestrator import build_prompt_from_context  # noqa: E402
from pipeline.context_pipeline import apply_garnish  # noqa: E402
from pipeline.source_pipeline import parse_prompt_source_fields  # noqa: E402


SEED_COUNT_DEFAULT = 32
MIN_UNIQUE_INTRO_COUNT = 5
MIN_UNIQUE_BODY_COUNT = 7
MIN_UNIQUE_END_COUNT = 6
MIN_UNIQUE_TEMPLATE_COUNT = 24
MAX_INTRO_DOMINANCE_RATE = 0.30
MAX_BODY_DOMINANCE_RATE = 0.26
MAX_END_DOMINANCE_RATE = 0.28
MIN_LEADING_BODY_ROLE_COUNT = 2
MIN_ACTION_SURFACE_CATEGORY_COUNT = 2


def _dominance_rate(counter: Counter[str], seed_count: int) -> float:
    if not counter or seed_count <= 0:
        return 0.0
    return max(counter.values()) / float(seed_count)


def build_template_diversity_report(seed_count: int = SEED_COUNT_DEFAULT, seed_start: int = 0) -> Dict[str, Any]:
    intro_counter: Counter[str] = Counter()
    body_counter: Counter[str] = Counter()
    end_counter: Counter[str] = Counter()
    template_counter: Counter[str] = Counter()
    body_role_counter: Counter[str] = Counter()
    surface_counter: Counter[str] = Counter()
    surface_body_counter: Dict[str, Counter[str]] = {}
    surface_examples: Dict[str, List[Dict[str, Any]]] = {}
    rows: List[Dict[str, Any]] = []

    for offset in range(seed_count):
        seed = seed_start + offset
        subj, costume, loc, action, meta_mood, _legacy_style, scene_tags = parse_prompt_source_fields("{}", seed)
        ctx = patch_context(
            {},
            updates={"subj": subj, "costume": costume, "loc": loc, "action": action, "seed": seed},
            meta={"mood": meta_mood},
            extras={"source_subj_key": subj, "raw_costume_key": costume, "raw_loc_tag": loc, "scene_tags": scene_tags},
        )
        ctx, _clothing = apply_clothing_expansion(ctx, seed, "random", 0.3)
        ctx, _location = apply_location_expansion(ctx, seed, "detailed", "off")
        ctx, _garnish, _garnish_debug = apply_garnish(ctx, seed, 3, False)
        ctx, prompt = build_prompt_from_context(ctx, "", True, seed)
        decision = dict((ctx.history[-1].decision or {}))

        intro_key = str(decision.get("intro_key", "")).strip()
        body_key = str(decision.get("body_key", "")).strip()
        end_key = str(decision.get("end_key", "")).strip()
        template_key = str(decision.get("template_key", "")).strip()
        body_roles = decision.get("template_roles", {}).get("body_roles", []) or []
        leading_body_role = str(body_roles[0]).strip() if body_roles else "neutral"
        surface_name = str(decision.get("action_surface", {}).get("surface", "")).strip() or "unknown"

        intro_counter[intro_key] += 1
        body_counter[body_key] += 1
        end_counter[end_key] += 1
        template_counter[template_key] += 1
        body_role_counter[leading_body_role] += 1
        surface_counter[surface_name] += 1
        surface_body_counter.setdefault(surface_name, Counter())[body_key] += 1
        surface_examples.setdefault(surface_name, [])
        if len(surface_examples[surface_name]) < 3:
            surface_examples[surface_name].append(
                {
                    "seed": seed,
                    "body_key": body_key,
                    "template_key": template_key,
                    "prompt": prompt,
                }
            )
        rows.append(
            {
                "seed": seed,
                "intro_key": intro_key,
                "body_key": body_key,
                "end_key": end_key,
                "template_key": template_key,
                "leading_body_role": leading_body_role,
                "action_surface": surface_name,
                "prompt": prompt,
            }
        )

    summary = {
        "seed_count": int(seed_count),
        "seed_start": int(seed_start),
        "unique_intro_count": len([key for key in intro_counter if key]),
        "unique_body_count": len([key for key in body_counter if key]),
        "unique_end_count": len([key for key in end_counter if key]),
        "unique_template_count": len([key for key in template_counter if key]),
        "intro_dominance_rate": round(_dominance_rate(intro_counter, seed_count), 4),
        "body_dominance_rate": round(_dominance_rate(body_counter, seed_count), 4),
        "end_dominance_rate": round(_dominance_rate(end_counter, seed_count), 4),
        "unique_leading_body_role_count": len([key for key in body_role_counter if key]),
        "leading_body_role_counts": dict(body_role_counter),
        "action_surface_counts": dict(surface_counter),
        "action_surface_body_key_counts": {
            surface_name: dict(counter)
            for surface_name, counter in surface_body_counter.items()
        },
        "action_surface_examples": surface_examples,
        "top_intro_keys": [{"key": key, "count": count} for key, count in intro_counter.most_common(5)],
        "top_body_keys": [{"key": key, "count": count} for key, count in body_counter.most_common(5)],
        "top_end_keys": [{"key": key, "count": count} for key, count in end_counter.most_common(5)],
        "top_template_keys": [{"key": key, "count": count} for key, count in template_counter.most_common(5)],
    }
    return {
        "summary": summary,
        "samples": rows[:8],
    }


def evaluate_template_diversity_thresholds(
    report: Dict[str, Any],
    min_unique_intro_count: int = MIN_UNIQUE_INTRO_COUNT,
    min_unique_body_count: int = MIN_UNIQUE_BODY_COUNT,
    min_unique_end_count: int = MIN_UNIQUE_END_COUNT,
    min_unique_template_count: int = MIN_UNIQUE_TEMPLATE_COUNT,
    max_intro_dominance_rate: float = MAX_INTRO_DOMINANCE_RATE,
    max_body_dominance_rate: float = MAX_BODY_DOMINANCE_RATE,
    max_end_dominance_rate: float = MAX_END_DOMINANCE_RATE,
    min_leading_body_role_count: int = MIN_LEADING_BODY_ROLE_COUNT,
    min_action_surface_category_count: int = MIN_ACTION_SURFACE_CATEGORY_COUNT,
) -> Dict[str, Any]:
    summary = report.get("summary", {}) or {}
    failures = []

    checks_gte = [
        ("unique_intro_count", int(summary.get("unique_intro_count", 0)), int(min_unique_intro_count)),
        ("unique_body_count", int(summary.get("unique_body_count", 0)), int(min_unique_body_count)),
        ("unique_end_count", int(summary.get("unique_end_count", 0)), int(min_unique_end_count)),
        ("unique_template_count", int(summary.get("unique_template_count", 0)), int(min_unique_template_count)),
        ("unique_leading_body_role_count", int(summary.get("unique_leading_body_role_count", 0)), int(min_leading_body_role_count)),
        (
            "action_surface_category_count",
            len([key for key in (summary.get("action_surface_counts", {}) or {}) if str(key).strip()]),
            int(min_action_surface_category_count),
        ),
    ]
    for code, actual, expected in checks_gte:
        if actual < expected:
            failures.append({"code": code, "expected_gte": expected, "actual": actual})

    checks_lte = [
        ("intro_dominance_rate", float(summary.get("intro_dominance_rate", 0.0)), float(max_intro_dominance_rate)),
        ("body_dominance_rate", float(summary.get("body_dominance_rate", 0.0)), float(max_body_dominance_rate)),
        ("end_dominance_rate", float(summary.get("end_dominance_rate", 0.0)), float(max_end_dominance_rate)),
    ]
    for code, actual, expected in checks_lte:
        if actual > expected:
            failures.append({"code": code, "expected_lte": expected, "actual": actual})

    return {
        "passed": not failures,
        "thresholds": {
            "min_unique_intro_count": int(min_unique_intro_count),
            "min_unique_body_count": int(min_unique_body_count),
            "min_unique_end_count": int(min_unique_end_count),
            "min_unique_template_count": int(min_unique_template_count),
            "max_intro_dominance_rate": float(max_intro_dominance_rate),
            "max_body_dominance_rate": float(max_body_dominance_rate),
            "max_end_dominance_rate": float(max_end_dominance_rate),
            "min_leading_body_role_count": int(min_leading_body_role_count),
            "min_action_surface_category_count": int(min_action_surface_category_count),
        },
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit 32-seed template diversity for Phase 5 quality checks")
    parser.add_argument("--seed-count", type=int, default=SEED_COUNT_DEFAULT)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--output", default="")
    parser.add_argument("--enforce-thresholds", action="store_true")
    args = parser.parse_args()

    report = build_template_diversity_report(seed_count=args.seed_count, seed_start=args.seed_start)
    report["threshold_evaluation"] = evaluate_template_diversity_thresholds(report)
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
