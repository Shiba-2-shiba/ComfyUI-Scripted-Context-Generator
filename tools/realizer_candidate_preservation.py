"""Compare intentional ordinary v2 expansion using the existing projections.

This is preservation evidence, not prose-quality or formal adoption approval.
Source manifests must be bound by the calling verifier; pair files carry the
canonical workflow inputs and replayed Builder context, not source manifests.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_realizer_reachability import builder_inputs
from tools.effective_diversity_signatures import build_semantic_signatures
from tools.workflow_prompt_runner import canonical_json_bytes


IDENTITY = ("base_workflow_hash", "effective_workflow_hash", "config_hash",
            "override_hash", "profile_hash", "profile_id", "schema_version")
CONTEXT_FIELDS = {"action", "context_version", "costume", "extras", "history", "loc",
                  "meta", "notes", "seed", "subj", "warnings"}
# Only realization diagnostics may change. Unknown decision keys remain protected.
REALIZATION_FIELDS = {"prompt", "syntax_family", "syntax_fallback_reason", "realizer_version",
                      "candidate_eligibility", "eligible_syntax_families", "candidate_v2_applied",
                      "requested_syntax_family", "fallback_origin_syntax_family"}
SOURCE_DECISION_FIELDS = {"action_frame", "action_frame_matches_debug_slots", "action_slots",
                          "action_surface", "body_key", "clause_order", "composition_mode", "end_key",
                          "intro_key", "semantic_family_budget", "solo_support_dropped_tags",
                          "solo_template_filter_applied", "solo_template_filtered_keys", "template_key",
                          "template_roles"}
RECORD_FIELDS = {*IDENTITY, "cleaned_prompt", "context", "context_json", "context_json_bytes",
                 "excluded_terminal_nodes", "execution_trace", "final_context", "final_context_json",
                 "output_selectors", "raw_prompt", "resolved_seeds", "run_seed", "summary_text"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _validate_context(context, label):
    _require(isinstance(context, dict) and CONTEXT_FIELDS <= context.keys(), f"{label}: incomplete context")
    for key in ("extras", "meta"):
        _require(isinstance(context[key], dict), f"{label}: invalid {key}")
    for key in ("history", "notes", "warnings"):
        _require(isinstance(context[key], list), f"{label}: invalid {key}")
    for key in ("action", "context_version", "costume", "loc", "subj"):
        _require(isinstance(context[key], str), f"{label}: invalid {key}")
    _require(type(context["seed"]) is int, f"{label}: invalid context seed")
    for entry in context["history"]:
        _require(isinstance(entry, dict) and {"node", "seed", "decision", "warnings"} <= entry.keys()
                 and isinstance(entry["node"], str) and type(entry["seed"]) is int
                 and isinstance(entry["decision"], dict) and isinstance(entry["warnings"], list),
                 f"{label}: invalid history entry")


def _validate_pair(pair, seed, label):
    _require(isinstance(pair, dict) and {"record", "builder_context"} <= pair.keys(), f"{label}: invalid pair")
    record, context = pair["record"], pair["builder_context"]
    _require(isinstance(record, dict) and RECORD_FIELDS <= record.keys(), f"{label}: incomplete record")
    _require(type(record["run_seed"]) is int and record["run_seed"] == seed,
             f"{label}: expected unique consecutive seed {seed}")
    for key in IDENTITY:
        _require(isinstance(record[key], str) and record[key], f"{label}: missing identity {key}")
        if key.endswith("_hash"):
            _require(re.fullmatch(r"[0-9a-f]{64}", record[key]) is not None, f"{label}: invalid hash {key}")
    for key in ("raw_prompt", "cleaned_prompt", "context_json", "final_context_json", "summary_text"):
        _require(isinstance(record[key], str), f"{label}: invalid {key}")
    _require(bool(record["raw_prompt"].strip()) and bool(record["cleaned_prompt"].strip()), f"{label}: empty prompt")
    _validate_context(record["final_context"], label)
    _validate_context(context, label)
    _require(record["context"] == record["final_context"]
             and json.loads(record["context_json"]) == record["final_context"]
             and json.loads(record["final_context_json"]) == record["final_context"]
             and type(record["context_json_bytes"]) is int
             and record["context_json_bytes"] == len(record["context_json"].encode("utf-8")),
             f"{label}: unbound context encoding")
    _require(isinstance(record["resolved_seeds"], dict) and isinstance(record["output_selectors"], dict)
             and isinstance(record["excluded_terminal_nodes"], list), f"{label}: invalid runner metadata")
    traces = record["execution_trace"]
    _require(isinstance(traces, list) and traces, f"{label}: missing execution trace")
    ids = []
    for trace in traces:
        _require(isinstance(trace, dict) and {"controls", "function", "inputs", "node_id", "node_type"} <= trace.keys()
                 and isinstance(trace["inputs"], dict) and isinstance(trace["controls"], dict)
                 and isinstance(trace["node_type"], str) and isinstance(trace["function"], str)
                 and type(trace["node_id"]) in (str, int), f"{label}: invalid execution trace")
        ids.append(str(trace["node_id"]))
    _require(len(ids) == len(set(ids)), f"{label}: duplicate trace node")
    _require(sum(t["node_type"] == "ContextPromptBuilder" for t in traces) == 1, f"{label}: ambiguous builder")
    try:
        args = builder_inputs(record)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid builder source inputs") from exc
    cleaners = [t for t in traces if t["node_type"] == "PromptCleaner"]
    selector = record["output_selectors"].get("cleaned_prompt", {})
    _require(len(cleaners) == 1 and isinstance(selector, dict)
             and cleaners[0]["node_id"] == selector.get("node_id") and selector.get("slot") == 0
             and cleaners[0]["function"] == "clean"
             and cleaners[0]["inputs"].get("text") == record["raw_prompt"], f"{label}: unbound cleaner trace")
    _require(bool(context["history"]), f"{label}: missing builder history")
    entry = context["history"][-1]
    _require(entry["node"] == "ContextPromptBuilder" and entry["seed"] == args["seed"], f"{label}: unbound builder header")
    decision = entry["decision"]
    _require(SOURCE_DECISION_FIELDS <= decision.keys(), f"{label}: missing source-selection decision proof")
    _require(decision.get("realizer_version") in ("v1", "v2")
             and type(decision.get("candidate_v2_applied")) is bool
             and decision["candidate_v2_applied"] == (decision["realizer_version"] == "v2")
             and isinstance(decision.get("syntax_family"), str) and decision["syntax_family"]
             and decision.get("prompt") == record["raw_prompt"], f"{label}: unbound builder decision")
    _require(isinstance(decision.get("content_plan"), dict)
             and {"clause_order", "discourse_roles", "lexical_choice", "named_seed_streams", "semantic_slots", "syntax_family"}
             <= decision["content_plan"].keys()
             and isinstance(decision["content_plan"].get("semantic_slots"), dict)
             and {"subject", "predicate", "object", "scene", "adjunct"}
             <= decision["content_plan"]["semantic_slots"].keys(), f"{label}: missing content plan")
    return decision, build_semantic_signatures(record, builder_decision=decision)


def _upstream_pair(pair):
    """Remove only specifically licensed realization differences."""
    value = copy.deepcopy(pair)
    record = value["record"]
    record.pop("raw_prompt")
    record.pop("cleaned_prompt")
    for trace in record["execution_trace"]:
        if trace["node_type"] == "PromptCleaner":
            trace["inputs"].pop("text")
    decision = value["builder_context"]["history"][-1]["decision"]
    for key in REALIZATION_FIELDS:
        decision.pop(key, None)
    plan = decision["content_plan"]
    plan.pop("syntax_family", None)
    for key in ("subject", "adjunct", "scene"):
        plan["semantic_slots"].pop(key, None)
    return value


def compare_pairs(before, after, *, expected_count=512, require_baseline_v2=9):
    """Return a canonical preservation report; malformed/unbound cohorts raise.

    Preservation regressions produce FAIL. A PASS establishes at least one new
    ordinary v1 -> v2 application with all previous successes/fallbacks intact.
    """
    _require(type(expected_count) is int and expected_count > 0, "expected_count must be positive")
    _require(require_baseline_v2 is None or (type(require_baseline_v2) is int
             and 0 <= require_baseline_v2 <= expected_count), "invalid required baseline v2 count")
    _require(isinstance(before, (list, tuple)) and isinstance(after, (list, tuple))
             and len(before) == len(after) == expected_count, "pair cohort count mismatch")
    validated = []
    for seed, (old, now) in enumerate(zip(before, after)):
        try:
            old_decision, old_signature = _validate_pair(old, seed, f"baseline[{seed}]")
            new_decision, new_signature = _validate_pair(now, seed, f"current[{seed}]")
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError(f"seed {seed}: invalid pair schema or source proof") from exc
        _require(all(old["record"][key] == now["record"][key] for key in IDENTITY),
                 f"seed {seed}: workflow/config cohort changed")
        _require(old["record"].get("cohort") == now["record"].get("cohort"), f"seed {seed}: cohort changed")
        validated.append((old_decision, new_decision, old_signature, new_signature))
    baseline_count = sum(d[0]["realizer_version"] == "v2" for d in validated)
    _require(require_baseline_v2 is None or baseline_count == require_baseline_v2, "baseline v2 count mismatch")
    mismatches, new_cases, preserved, unchanged = [], [], [], 0
    signature_count, upstream_count = 0, 0
    for seed, (old, now, details) in enumerate(zip(before, after, validated)):
        old_decision, new_decision, old_signature, new_signature = details
        fields = [key for key in ("core", "frame", "valid", "diagnostics") if old_signature[key] != new_signature[key]]
        if fields:
            signature_count += 1
            mismatches.append({"run_seed": seed, "kind": "semantic_projection", "fields": fields})
        if _upstream_pair(old) != _upstream_pair(now):
            upstream_count += 1
            mismatches.append({"run_seed": seed, "kind": "upstream_or_metadata"})
        if old_decision["realizer_version"] == "v2":
            if old == now:
                preserved.append(seed)
            else:
                mismatches.append({"run_seed": seed, "kind": "prior_success_changed"})
        elif new_decision["realizer_version"] == "v1":
            if old == now:
                unchanged += 1
            else:
                mismatches.append({"run_seed": seed, "kind": "remaining_fallback_changed"})
        else:
            left, right = old["record"], now["record"]
            if left["raw_prompt"] == right["raw_prompt"] or left["cleaned_prompt"] == right["cleaned_prompt"]:
                mismatches.append({"run_seed": seed, "kind": "new_application_without_changed_prose"})
            new_cases.append({"run_seed": seed, "family": new_decision["syntax_family"],
                "before_raw": left["raw_prompt"], "after_raw": right["raw_prompt"],
                "before_cleaned": left["cleaned_prompt"], "after_cleaned": right["cleaned_prompt"]})
    if not new_cases:
        mismatches.append({"kind": "no_new_ordinary_application"})
    return {"status": "FAIL" if mismatches else "PASS", "scope": "expansion-preservation/v1",
        "sample_count": expected_count, "baseline_v2_count": baseline_count,
        "current_v2_count": sum(d[1]["realizer_version"] == "v2" for d in validated),
        "new_cases": new_cases, "new_ordinary_v2_count": len(new_cases),
        "preserved_success_seeds": preserved, "prior_successes_preserved": preserved,
        "unchanged_fallback_count": unchanged, "mismatches": mismatches,
        "signature_mismatch_count": signature_count, "upstream_mismatch_count": upstream_count,
        "core_frame_mismatches": signature_count, "upstream_context_mismatches": upstream_count,
        "semantic_scope": "Same selected facts/projections; changed prose requires separate source-atom and ownership review."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-pairs", type=Path, required=True)
    parser.add_argument("--current-pairs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _require(not args.output.exists(), "output already exists")
        before, after = ([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                         for path in (args.baseline_pairs, args.current_pairs))
        report = compare_pairs(before, after)
        with args.output.open("xb") as stream:
            stream.write(canonical_json_bytes(report))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
