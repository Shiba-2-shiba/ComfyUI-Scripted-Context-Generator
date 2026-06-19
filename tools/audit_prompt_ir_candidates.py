from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.prompt_ir import build_prompt_ir
from core.prompt_risk_policy import classify_risk_families
from core.prompt_ir_validator import validate_prompt_ir
from pipeline.prompt_candidate_generator import generate_prompt_candidates
from pipeline.prompt_candidate_selector import select_prompt_candidate, summarize_prompt_candidates


FIXTURE_PATH = ROOT / "assets" / "fixtures" / "prompt_ir_audit_cases.json"


def _load_cases() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _ir_from_prompt(prompt: str) -> dict:
    return build_prompt_ir(
        {
            "subject": "1girl, solo" if "1girl" in prompt.lower() or "solo" in prompt.lower() else "",
            "background_context": prompt,
        },
        source="prompt_ir_audit",
    )


def _expected_families(case: dict) -> set[str]:
    return {str(item) for item in case.get("expected_risk_families", [])}


def _detected_families(validator: dict) -> set[str]:
    families = {str(item.get("family", "")) for item in validator.get("issues", []) if item.get("family")}
    scores = validator.get("scores", {})
    if isinstance(scores, dict):
        if int(scores.get("layout_order", 0) or 0) > 0:
            families.add("location_first_template")
        if int(scores.get("semantic_family_overload", 0) or 0) > 0:
            families.add("semantic_family_overload")
        if int(scores.get("prompt_length_budget", 0) or 0) > 0:
            families.add("prompt_length_budget")
    return families


def _evaluate_case(case: dict, validator: dict, active_selection: dict) -> dict:
    expected = _expected_families(case)
    detected = _detected_families(validator)
    false_positive_families = sorted(detected - expected)
    false_negative_families = sorted(expected - detected)
    failures: list[str] = []

    total_risk = int(validator.get("total_risk", 0) or 0)
    if "expected_max_total_risk" in case and total_risk > int(case["expected_max_total_risk"]):
        failures.append("total_risk_above_expected_max")
    if "expected_min_total_risk" in case and total_risk < int(case["expected_min_total_risk"]):
        failures.append("total_risk_below_expected_min")

    expected_active = case.get("expected_active_applied")
    active_applied = bool(active_selection.get("applied"))
    if expected_active is not None and bool(expected_active) != active_applied:
        failures.append("active_application_mismatch")

    active_text = str(active_selection.get("rendered_text", "")).lower()
    removed_terms = [str(term).lower() for term in case.get("expected_removed_terms", [])]
    missing_removals = [term for term in removed_terms if term in active_text]
    if missing_removals:
        failures.append("expected_terms_not_removed")

    expected_prefix = str(case.get("expected_active_startswith", "")).lower()
    if expected_prefix and not active_text.startswith(expected_prefix):
        failures.append("active_prefix_mismatch")

    return {
        "expected_risk_families": sorted(expected),
        "detected_risk_families": sorted(detected),
        "false_positive_families": false_positive_families,
        "false_negative_families": false_negative_families,
        "missing_removed_terms": missing_removals,
        "passed": not (false_positive_families or false_negative_families or failures),
        "failures": failures,
    }


def _summarize_evaluations(records: list[dict]) -> dict:
    false_positive_cases = []
    false_negative_cases = []
    failed_expectation_cases = []
    true_negative_count = 0
    true_positive_count = 0

    for record in records:
        evaluation = record["expectation"]
        name = record["name"]
        if evaluation["false_positive_families"]:
            false_positive_cases.append(
                {"name": name, "families": evaluation["false_positive_families"]}
            )
        if evaluation["false_negative_families"]:
            false_negative_cases.append(
                {"name": name, "families": evaluation["false_negative_families"]}
            )
        residual_failures = [
            failure
            for failure in evaluation["failures"]
            if failure not in {"false_positive_families", "false_negative_families"}
        ]
        if residual_failures or evaluation["missing_removed_terms"]:
            failed_expectation_cases.append(
                {
                    "name": name,
                    "failures": residual_failures,
                    "missing_removed_terms": evaluation["missing_removed_terms"],
                }
            )
        expected = set(evaluation["expected_risk_families"])
        detected = set(evaluation["detected_risk_families"])
        if not expected and not detected:
            true_negative_count += 1
        if expected and expected <= detected:
            true_positive_count += 1

    return {
        "case_count": len(records),
        "passed_count": sum(1 for record in records if record["expectation"]["passed"]),
        "failed_count": sum(1 for record in records if not record["expectation"]["passed"]),
        "true_positive_count": true_positive_count,
        "true_negative_count": true_negative_count,
        "false_positive_cases": false_positive_cases,
        "false_negative_cases": false_negative_cases,
        "failed_expectation_cases": failed_expectation_cases,
    }


def build_report(seed_count: int = 8) -> dict:
    cases = _load_cases()
    records = []
    for index, case in enumerate(cases[: max(0, int(seed_count))] or cases):
        prompt = str(case.get("prompt", ""))
        prompt_ir = _ir_from_prompt(prompt)
        validator = validate_prompt_ir(prompt_ir, rendered_text=prompt)
        candidates = generate_prompt_candidates(
            prompt_ir,
            rendered_text=prompt,
            seed=index,
            max_candidates=2,
        )
        active_selected = select_prompt_candidate(candidates, mode="active_selection")
        active_text = str(active_selected.get("rendered_text", ""))
        active_validator = validate_prompt_ir(prompt_ir, rendered_text=active_text)
        active_selection = {
            "selected_candidate_id": active_selected.get("candidate_id"),
            "applied": active_selected.get("candidate_id") != f"seed:{index}:branch:0",
            "rendered_text": active_text,
            "risk_families": sorted(classify_risk_families(active_text)),
            "validator": active_validator,
            "dropped_components": active_selected.get("dropped_components", []),
        }
        records.append(
            {
                "name": case.get("name", f"case_{index}"),
                "category": case.get("category", ""),
                "prompt": prompt,
                "validator": validator,
                "candidate_summary": summarize_prompt_candidates(candidates, mode="passive_debug"),
                "active_selection": active_selection,
                "expectation": _evaluate_case(case, validator, active_selection),
            }
        )
    summary = _summarize_evaluations(records)
    return {
        "schema_version": "1.0",
        "mode": "read_only_with_active_preview",
        "case_count": len(records),
        "summary": summary,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Prompt IR validator and active candidate preview.")
    parser.add_argument("--seed-count", type=int, default=8)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report = build_report(args.seed_count)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output_path = args.output
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + os.linesep, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
