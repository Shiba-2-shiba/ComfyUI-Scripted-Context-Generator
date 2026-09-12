from __future__ import annotations

import argparse
import json
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.context_ops import patch_context  # noqa: E402
from core.semantic_policy import find_banned_term_matches  # noqa: E402
from pipeline.clothing_builder import apply_clothing_expansion  # noqa: E402
from pipeline.context_pipeline import apply_garnish, apply_scene_variation  # noqa: E402
from pipeline.location_builder import apply_location_expansion  # noqa: E402
from pipeline.mood_builder import apply_mood_expansion  # noqa: E402
from pipeline.prompt_orchestrator import build_prompt_from_context  # noqa: E402
from pipeline.semantic_epig import KNOWN_DOMAINS  # noqa: E402


def _mode_functions(forced_mode: str):
    def semantic_mode(domain: str) -> str:
        return forced_mode if str(domain or "").strip() in KNOWN_DOMAINS else "off"

    def domain_enabled(domain: str, *, active_only: bool = False) -> bool:
        mode = semantic_mode(domain)
        return mode == "active" if active_only else mode in {"passive", "active"}

    return semantic_mode, domain_enabled


@contextmanager
def semantic_epig_mode(forced_mode: str):
    semantic_mode, domain_enabled = _mode_functions(forced_mode)
    module_names = [
        "pipeline.semantic_epig",
        "pipeline.action_semantics",
        "pipeline.action_generator",
        "pipeline.location_semantics",
        "pipeline.location_builder",
        "pipeline.clothing_semantics",
        "pipeline.clothing_builder",
        "vocab.garnish.logic",
    ]
    modules = [__import__(module_name, fromlist=["*"]) for module_name in module_names]
    with ExitStack() as stack:
        for module in modules:
            if hasattr(module, "semantic_mode"):
                stack.enter_context(patch.object(module, "semantic_mode", semantic_mode))
            if hasattr(module, "domain_enabled"):
                stack.enter_context(patch.object(module, "domain_enabled", domain_enabled))
        try:
            yield
        finally:
            context_pipeline = sys.modules.get("pipeline.context_pipeline")
            if context_pipeline is not None and hasattr(context_pipeline, "_garnish_vocab_module"):
                context_pipeline._garnish_vocab_module = None


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("semantic EPIG audit cases must be a JSON list")
    cases = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"case[{index}] must be an object")
        case_id = str(item.get("case_id", "")).strip()
        if not case_id:
            raise ValueError(f"case[{index}] missing case_id")
        cases.append(item)
    return cases


def _semantic_debug_from_history(ctx) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for entry in ctx.history:
        decision = entry.decision if isinstance(entry.decision, dict) else {}
        semantic_debug = decision.get("semantic_epig", {})
        if not isinstance(semantic_debug, dict):
            continue
        for domain, payload in semantic_debug.items():
            merged[str(domain)] = payload
    return merged


def _policy_issues(prompt: str) -> list[dict[str, str]]:
    return [
        {"domain": str(domain), "term": str(term)}
        for domain, term in find_banned_term_matches(prompt, ignore_hyphenated_body_type=True)
    ]


def _run_pipeline(case: dict[str, Any], seed: int, forced_mode: str) -> dict[str, Any]:
    with semantic_epig_mode(forced_mode):
        ctx = patch_context(
            {},
            updates={
                "subj": case.get("subj", ""),
                "costume": case.get("costume", ""),
                "loc": case.get("loc", ""),
                "action": case.get("action", ""),
                "seed": seed,
            },
            meta={
                "mood": case.get("mood", ""),
                "tags": case.get("scene_tags", {}),
            },
            extras={
                "personality": case.get("personality", ""),
                "raw_costume_key": case.get("costume", ""),
                "raw_loc_tag": case.get("loc", ""),
            },
        )
        ctx, _scene_debug = apply_scene_variation(ctx, seed, case.get("variation_mode", "full"))
        ctx, _clothing_prompt = apply_clothing_expansion(ctx, seed, case.get("outfit_mode", "random"), float(case.get("outerwear_chance", 0.3)))
        ctx, _location_prompt = apply_location_expansion(ctx, seed, case.get("location_mode", "detailed"), case.get("lighting_mode", "off"))
        ctx, _mood_text, _staging = apply_mood_expansion(ctx, seed, "mood_map.json", str(case.get("mood", "")))
        ctx, _garnish, _garnish_debug = apply_garnish(ctx, seed, int(case.get("max_garnish_items", 3)), False, personality=str(case.get("personality", "")))
        ctx, prompt = build_prompt_from_context(ctx, "", bool(case.get("composition_mode", True)), seed)
        return {
            "prompt": prompt,
            "semantic_debug": _semantic_debug_from_history(ctx),
            "history_nodes": [entry.node for entry in ctx.history],
        }


def _changed_domains(passive_debug: dict[str, Any], active_debug: dict[str, Any]) -> list[str]:
    domains = sorted(set(passive_debug) | set(active_debug))
    changed = []
    for domain in domains:
        passive_payload = passive_debug.get(domain, {})
        active_payload = active_debug.get(domain, {})
        active_changed = isinstance(active_payload, dict) and bool(active_payload.get("selection_changed_by_semantic"))
        if active_changed or json.dumps(passive_payload, sort_keys=True, ensure_ascii=False) != json.dumps(active_payload, sort_keys=True, ensure_ascii=False):
            changed.append(domain)
    return changed


def audit_case(case: dict[str, Any], seed: int) -> dict[str, Any]:
    passive = _run_pipeline(case, seed, "passive")
    active = _run_pipeline(case, seed, "active")
    passive_prompt = passive["prompt"]
    active_prompt = active["prompt"]
    return {
        "case_id": str(case["case_id"]),
        "seed": int(seed),
        "input": {
            "subj": case.get("subj", ""),
            "loc": case.get("loc", ""),
            "action": case.get("action", ""),
            "costume": case.get("costume", ""),
            "mood": case.get("mood", ""),
            "personality": case.get("personality", ""),
        },
        "passive_prompt": passive_prompt,
        "active_prompt": active_prompt,
        "changed": passive_prompt != active_prompt,
        "changed_domains": _changed_domains(passive["semantic_debug"], active["semantic_debug"]),
        "prompt_length_delta": len(active_prompt) - len(passive_prompt),
        "semantic_debug": {
            "passive": passive["semantic_debug"],
            "active": active["semantic_debug"],
        },
        "policy_issues": _policy_issues(active_prompt),
    }


def audit_cases(cases: list[dict[str, Any]], seed_start: int = 0, seed_count: int = 8) -> dict[str, Any]:
    records = []
    for case in cases:
        for seed in range(int(seed_start), int(seed_start) + int(seed_count)):
            records.append(audit_case(case, seed))
    changed_records = [record for record in records if record["changed"]]
    all_policy_issues = [issue for record in records for issue in record["policy_issues"]]
    return {
        "schema_version": "1.0",
        "seed_start": int(seed_start),
        "seed_count": int(seed_count),
        "case_count": len(cases),
        "record_count": len(records),
        "changed_count": len(changed_records),
        "changed_rate": (len(changed_records) / len(records)) if records else 0.0,
        "policy_issue_count": len(all_policy_issues),
        "records": records,
    }


def write_audit(result: dict[str, Any], output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit active/passive Semantic EPIG prompt differences.")
    parser.add_argument("--samples", default=str(ROOT / "assets" / "fixtures" / "semantic_epig_audit_cases.json"))
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seed-count", type=int, default=8)
    parser.add_argument("--output", default=str(ROOT / "assets" / "results" / "semantic_epig_audit.json"))
    args = parser.parse_args(argv)

    cases = load_cases(args.samples)
    result = audit_cases(cases, seed_start=args.seed_start, seed_count=args.seed_count)
    output_path = write_audit(result, args.output)
    print(json.dumps({
        "output": str(output_path),
        "record_count": result["record_count"],
        "changed_count": result["changed_count"],
        "policy_issue_count": result["policy_issue_count"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
