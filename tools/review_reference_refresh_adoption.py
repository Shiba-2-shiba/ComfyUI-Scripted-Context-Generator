from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILES = {
    "alignment": "epig_reference_alignment.json",
    "overlay": "epig_reference_overlay.local.json",
    "subject_descriptors": "subject_centric_descriptor_candidates.json",
    "dimension_projection": "reference_dimension_projection.json",
    "llm_policy": "llm_expanded_prompt_policy_audit.json",
    "semantic_baseline": "semantic_epig_audit_reference_refresh_baseline.json",
}


def _load_json(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.exists():
        return {}, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, str(exc)
    return payload if isinstance(payload, dict) else {}, None


def _int(payload: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(payload.get(key, default) or 0)
    except (TypeError, ValueError):
        return default


def _nested_int(payload: dict[str, Any], path: tuple[str, ...], default: int = 0) -> int:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _input_status(results_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[dict[str, str]]]:
    loaded: dict[str, dict[str, Any]] = {}
    files = []
    warnings = []
    for key, filename in INPUT_FILES.items():
        path = results_dir / filename
        payload, error = _load_json(path)
        loaded[key] = payload
        status = "ok" if error is None else error
        files.append({"key": key, "file": filename, "status": status})
        if error is not None:
            warnings.append({"input": key, "file": str(path), "warning": error})
    missing_count = sum(1 for item in files if item["status"] != "ok")
    return {"results_dir": str(results_dir), "missing_count": missing_count, "files": files}, loaded, warnings


def _summaries(loaded: dict[str, dict[str, Any]]) -> dict[str, Any]:
    alignment = loaded.get("alignment", {})
    overlay = loaded.get("overlay", {})
    subject = loaded.get("subject_descriptors", {})
    projection = loaded.get("dimension_projection", {})
    llm_policy = loaded.get("llm_policy", {})
    baseline = loaded.get("semantic_baseline", {})
    return {
        "alignment": {
            "source_count": _nested_int(alignment, ("availability", "source_count")),
            "warning_count": _nested_int(alignment, ("availability", "warning_count")),
            "emotion_profile_matched_count": _nested_int(alignment, ("emotion_profile_alignment", "matched_count")),
            "exact_reference_match_count": _nested_int(alignment, ("current_vocabulary", "exact_reference_match_count")),
        },
        "overlay": {
            "tracked_policy": str(overlay.get("tracked_policy", "")),
            "extracted_term_count": _int(overlay, "extracted_term_count"),
            "matched_term_count": _int(overlay, "matched_term_count"),
            "unmatched_term_count": _int(overlay, "unmatched_term_count"),
            "warning_count": len(overlay.get("warnings", [])) if isinstance(overlay.get("warnings"), list) else 0,
        },
        "subject_descriptors": {
            "tracked_policy": str(subject.get("tracked_policy", "")),
            "descriptor_count": _int(subject, "descriptor_count"),
            "direct_count": _int(subject, "direct_count"),
            "needs_phrase_count": _int(subject, "needs_phrase_count"),
            "reject_count": _int(subject, "reject_count"),
            "unmatched_count": _int(subject, "unmatched_count"),
            "warning_count": _int(subject, "warning_count"),
        },
        "dimension_projection": {
            "matched_term_count": _nested_int(projection, ("current_vocabulary_coverage", "matched_term_count")),
            "comparison_count": _nested_int(projection, ("personality_dominance_projection", "comparison_count")),
            "high_risk_count": _nested_int(projection, ("personality_dominance_projection", "high_risk_count")),
            "runtime_axis_adoption": str(projection.get("dominance_decision", {}).get("runtime_axis_adoption", "")) if isinstance(projection.get("dominance_decision"), dict) else "",
        },
        "llm_policy": {
            "row_count": _int(llm_policy, "row_count"),
            "rows_with_policy_issues": _int(llm_policy, "rows_with_policy_issues"),
            "policy_issue_count": _int(llm_policy, "policy_issue_count"),
            "domain_counts": llm_policy.get("domain_counts", {}) if isinstance(llm_policy.get("domain_counts"), dict) else {},
        },
        "semantic_baseline": {
            "record_count": _int(baseline, "record_count"),
            "changed_count": _int(baseline, "changed_count"),
            "policy_issue_count": _int(baseline, "policy_issue_count"),
        },
    }


def _build_decisions(summary: dict[str, Any]) -> dict[str, Any]:
    llm_policy_issues = _nested_int(summary, ("llm_policy", "policy_issue_count"))
    direct_subject = _nested_int(summary, ("subject_descriptors", "direct_count"))
    needs_phrase = _nested_int(summary, ("subject_descriptors", "needs_phrase_count"))
    dominance_adoption = str(summary.get("dimension_projection", {}).get("runtime_axis_adoption", ""))
    overlay_policy = str(summary.get("overlay", {}).get("tracked_policy", ""))
    baseline_policy_issues = _nested_int(summary, ("semantic_baseline", "policy_issue_count"))

    return {
        "runtime_prompt_changes": {
            "adopt": False,
            "status": "deferred",
            "reason": "Reference audits found useful signals, but no audited lane is strong enough to justify active prompt changes without a separate active/passive plan.",
        },
        "score_bearing_overlay": {
            "adopt": False,
            "status": "local_generated_only",
            "reason": f"Overlay policy is {overlay_policy or 'unspecified'}; keep score-bearing reference overlay out of tracked runtime data.",
        },
        "subject_descriptor_subset": {
            "adopt": False,
            "status": "curation_needed",
            "direct_count": direct_subject,
            "needs_phrase_count": needs_phrase,
            "reason": "Exact matches can remain as existing repo-authored descriptors; needs_phrase items require repo-specific rewriting before any tracked data change.",
        },
        "dominance_runtime_axis": {
            "adopt": False,
            "status": "audit_only" if dominance_adoption in {"deferred", ""} else dominance_adoption,
            "reason": "Dominance projection remains audit-only until exact descriptor evidence and active/passive prompt audits justify runtime axis changes.",
        },
        "llm_expanded_prompts": {
            "adopt": False,
            "status": "negative_corpus_only",
            "policy_issue_count": llm_policy_issues,
            "reason": "Expanded prompts contain semantic-only policy violations and must not be used as prompt source data.",
        },
        "repo_authored_negative_fixture": {
            "adopt": True,
            "status": "tracked_test_fixture",
            "reason": "Small repo-authored negative examples are acceptable because they do not copy reference rows and only lock policy detection behavior.",
        },
        "current_runtime": {
            "sufficient_for_now": baseline_policy_issues == 0,
            "reason": "Existing runtime remains protected by active/passive audit and validator checks; no reference-driven runtime change is required now.",
        },
    }


def review_reference_refresh_adoption(results_dir: str | Path = ROOT / "assets" / "results") -> dict[str, Any]:
    results_path = Path(results_dir)
    input_status, loaded, warnings = _input_status(results_path)
    summary = _summaries(loaded)
    decisions = _build_decisions(summary)
    missing_required = input_status["missing_count"] > 0
    runtime_ok = bool(decisions["current_runtime"]["sufficient_for_now"])

    return {
        "schema_version": "1.0",
        "generated_kind": "reference_refresh_adoption_decision",
        "tracked_policy": "generated_local_only",
        "overall_decision": "no_runtime_adoption_now",
        "input_status": input_status,
        "warnings": warnings,
        "summary": summary,
        "decisions": decisions,
        "q9_acceptance": {
            "current_implementation_is_sufficient_for_now": runtime_ok,
            "small_derived_data_subsets_should_be_added_now": False,
            "dominance_remains_audit_only": decisions["dominance_runtime_axis"]["status"] == "audit_only",
            "active_passive_plan_required_before_runtime_change": True,
            "reference_raw_data_remains_untracked": True,
            "decision_is_complete": not missing_required,
        },
        "next_allowed_steps": [
            "Keep generated overlays and reference-derived score data local by default.",
            "Use subject needs_phrase records only as hints for repo-authored descriptor rewriting.",
            "Create a new active/passive behavior spec before any runtime prompt change.",
        ],
    }


def write_decision(decision: dict[str, Any], output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review reference refresh audit outputs and record adoption decisions.")
    parser.add_argument("--results-dir", default=str(ROOT / "assets" / "results"))
    parser.add_argument("--output", default=str(ROOT / "assets" / "results" / "reference_refresh_adoption_decision.json"))
    args = parser.parse_args(argv)

    decision = review_reference_refresh_adoption(args.results_dir)
    output_path = write_decision(decision, args.output)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "overall_decision": decision["overall_decision"],
                "missing_count": decision["input_status"]["missing_count"],
                "runtime_prompt_changes": decision["decisions"]["runtime_prompt_changes"]["status"],
                "dominance_runtime_axis": decision["decisions"]["dominance_runtime_axis"]["status"],
                "small_derived_data_subsets_should_be_added_now": decision["q9_acceptance"]["small_derived_data_subsets_should_be_added_now"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
