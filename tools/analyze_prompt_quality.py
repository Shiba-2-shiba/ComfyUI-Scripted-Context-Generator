"""Deterministic quality analysis for canonical prompt workflow records.

This module is intentionally read-only with respect to repository source.  Its
core entry point, :func:`analyze_records`, accepts in-memory values and returns
canonical metrics and evidence-bearing issues without performing file I/O.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.semantic_families import semantic_families_for_text
from core.solo_safety import has_other_person_conflict
from pipeline.prompt_realizer import find_person_demographic_descriptors
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


ANALYZER_VERSION = "prompt-quality-analyzer/v1"
METRICS_SCHEMA_VERSION = "prompt-quality-analysis-metrics/v1"
ISSUES_SCHEMA_VERSION = "prompt-quality-issues/v1"
DEFAULT_POLICY_PATH = ROOT / "vocab" / "data" / "prompt_quality_policy.json"
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
CONSISTENCY_DOMAINS = ("location_action_object", "clothing_tpo_weather", "mood_action_garnish")
WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.IGNORECASE)
NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
PUNCTUATION_ANOMALY_RE = re.compile(r"(?:[,.!?;:])\s*[,.!?;:]|\s+[,.!?;:]|[,.!?;:]{2,}")
DANGLING_END_RE = re.compile(r"\b(?:and|as|at|because|but|for|from|in|of|or|the|to|with)\s*[,.!?;:]*$", re.I)


def _round(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def _rate(count: int, total: int, digits: int) -> float:
    return _round(count / total, digits) if total else 0.0


def _percentile(values: Sequence[int | float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def _entropy(counter: Counter[str], digits: int) -> float:
    total = sum(counter.values())
    if not total or len(counter) <= 1:
        return 0.0
    return _round(-sum((count / total) * math.log2(count / total) for count in counter.values()), digits)


def _normalise(text: str) -> str:
    return NORMALIZE_RE.sub(" ", str(text or "").lower()).strip()


def _words(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(str(text or ""))]


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(str(term).lower())}\b", text.lower()) is not None


def _walk(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            child = value[key]
            yield str(key), child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _trace_nodes(record: Mapping[str, Any], preferred: Sequence[str]) -> list[str]:
    available = [
        str(item.get("node_type"))
        for item in record.get("execution_trace", [])
        if isinstance(item, Mapping) and item.get("node_type")
    ]
    selected = [node for node in preferred if node in available]
    if not selected:
        selected = available or list(preferred) or ["canonical_record"]
    return list(dict.fromkeys(selected))


def _context(record: Mapping[str, Any]) -> Mapping[str, Any]:
    value = record.get("final_context", record.get("context", {}))
    return value if isinstance(value, Mapping) else {}


def _signature(context: Mapping[str, Any], name: str) -> str:
    extras = context.get("extras", {}) if isinstance(context.get("extras"), Mapping) else {}
    meta = context.get("meta", {}) if isinstance(context.get("meta"), Mapping) else {}
    choices = {
        "character": (extras.get("character_id"), extras.get("source_subj_key"), context.get("subj")),
        "location": (extras.get("raw_loc_tag"), context.get("loc"), extras.get("location_prompt")),
        "action": (context.get("action"),),
        "object": (extras.get("object_focus"), extras.get("selected_object"), _values_for_keys(context, {"detected_objects", "objects"})),
        "mood": (meta.get("mood"), extras.get("personality")),
    }
    for value in choices[name]:
        if value not in (None, "", [], {}):
            if isinstance(value, (Mapping, list)):
                return canonical_json_bytes(value).decode("utf-8").strip()
            return _normalise(str(value))
    return "unknown"


def _values_for_keys(value: Any, names: set[str]) -> list[str]:
    values: list[str] = []
    for key, child in _walk(value):
        if key not in names or child in (None, "", [], {}):
            continue
        if isinstance(child, list):
            values.extend(str(item) for item in child if item not in (None, ""))
        elif not isinstance(child, Mapping):
            values.append(str(child))
    return sorted(set(values))


def _action_verb(context: Mapping[str, Any]) -> str:
    action_words = _words(str(context.get("action", "")))
    for word in action_words:
        if word.endswith("ing"):
            return word
    return action_words[0] if action_words else "unknown"


def _reason_codes(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return sorted(set(str(item) for item in value if str(item)))
    return []


def _constraint_observations(value: Any) -> list[dict[str, Any]]:
    """Read the shared result protocol without inventing domain outcomes.

    Domain selectors remain responsible for producing these fields.  Until a
    selector exposes them, the corresponding metric is explicitly marked
    ``not_observed`` rather than being treated as a successful evaluation.
    """

    observations: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        domain = str(value.get("constraint_domain", value.get("domain", "")))
        has_protocol_field = any(
            key in value
            for key in ("hard_reason_codes", "soft_reason_codes", "reason_codes", "survivor_count")
        )
        if domain in CONSISTENCY_DOMAINS and has_protocol_field:
            hard = _reason_codes(value.get("hard_reason_codes"))
            soft = _reason_codes(value.get("soft_reason_codes"))
            unclassified = _reason_codes(value.get("reason_codes"))
            severity = str(value.get("severity", "")).lower()
            if unclassified and severity == "hard":
                hard.extend(unclassified)
                unclassified = []
            elif unclassified and severity == "soft":
                soft.extend(unclassified)
                unclassified = []
            survivor = value.get("survivor_count")
            if isinstance(survivor, bool) or not isinstance(survivor, (int, float)):
                survivor = None
            observations.append(
                {
                    "domain": domain,
                    "hard_reason_codes": sorted(set(hard)),
                    "soft_reason_codes": sorted(set(soft)),
                    "unclassified_reason_codes": sorted(set(unclassified)),
                    "survivor_count": int(survivor) if survivor is not None else None,
                }
            )
        for child in value.values():
            observations.extend(_constraint_observations(child))
    elif isinstance(value, list):
        for child in value:
            observations.extend(_constraint_observations(child))
    return observations


def _syntax_signature(text: str) -> str:
    words = _words(text)
    opening = " ".join(words[:3])
    sentence_count = len(
        [segment for segment in re.split(r"[.!?]+", str(text or "")) if _words(segment)]
    )
    return f"{opening}|commas:{min(text.count(','), 12)}|sentences:{max(1, sentence_count)}"


def _top_concentration(counter: Counter[str], count: int, total: int, digits: int) -> float:
    if not total:
        return 0.0
    return _round(sum(value for _key, value in counter.most_common(count)) / total, digits)


def load_policy(path: str | Path | None = None) -> dict[str, Any]:
    """Load and resolve the versioned analyzer policy."""

    policy_path = Path(path) if path is not None else DEFAULT_POLICY_PATH
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or not isinstance(policy.get("policy_version"), str):
        raise WorkflowValidationError("invalid_quality_policy", "quality policy must be a versioned object")
    rules_path = policy.get("consistency_rules_path")
    if rules_path:
        resolved = Path(rules_path)
        if not resolved.is_absolute():
            resolved = ROOT / resolved
        rules = json.loads(resolved.read_text(encoding="utf-8"))
        policy["resolved_consistency_rules"] = rules.get("conflicts", []) if isinstance(rules, Mapping) else []
    return policy


def load_records(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise WorkflowValidationError(
                    "invalid_quality_record", "record must be a JSON object", line_number=line_number
                )
            records.append(value)
    return records


def _issue(
    code: str,
    seeds: Iterable[int],
    evidence_by_seed: Mapping[int, str],
    records_by_seed: Mapping[int, Mapping[str, Any]],
    policy: Mapping[str, Any],
    total: int,
    digits: int,
    *,
    confidence: float,
    preferred_nodes: Sequence[str],
    owners: Sequence[str],
    test_surface: str,
) -> dict[str, Any] | None:
    affected = sorted(set(int(seed) for seed in seeds))
    if not affected:
        return None
    nodes: list[str] = []
    for seed in affected:
        nodes.extend(_trace_nodes(records_by_seed[seed], preferred_nodes))
    evidence = [f"seed={seed}: {evidence_by_seed[seed]}" for seed in affected[:5]]
    return {
        "affected_seeds": affected,
        "confidence": _round(confidence, digits),
        "evidence": evidence,
        "frequency": _rate(len(affected), total, digits),
        "issue_code": code,
        "recommended_test_surface": test_surface,
        "severity": str(policy.get("issue_severity", {}).get(code, "medium")),
        "suspected_owners": list(owners),
        "trace_nodes": list(dict.fromkeys(nodes)),
    }


def analyze_records(
    records: Sequence[Mapping[str, Any]], policy: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return deterministic metrics and ranked issues for canonical records."""

    selected_policy = dict(policy or load_policy())
    analyzer = selected_policy.get("analyzer", {})
    digits = int(selected_policy.get("threshold_review", {}).get("rounding_digits", 6))
    normalized_records = sorted((dict(record) for record in records), key=lambda item: int(item.get("run_seed", 0)))
    seeds = [int(record.get("run_seed", 0)) for record in normalized_records]
    if len(seeds) != len(set(seeds)):
        raise WorkflowValidationError("duplicate_seed", "quality records must contain unique run seeds")
    total = len(normalized_records)
    records_by_seed = dict(zip(seeds, normalized_records))
    findings: dict[str, dict[int, str]] = defaultdict(dict)
    prompts: list[str] = []
    normalized_prompts: list[str] = []
    word_lengths: list[int] = []
    context_sizes: list[int] = []
    fallback_records = 0
    warning_count = 0
    error_count = 0
    record_contract_error_count = 0
    signatures = {name: Counter() for name in ("character", "location", "action", "object", "mood")}
    syntax_counter: Counter[str] = Counter()
    semantic_counter: Counter[str] = Counter()
    template_counter: Counter[str] = Counter()
    verb_counter: Counter[str] = Counter()
    domain_evaluated_seeds = {domain: set() for domain in CONSISTENCY_DOMAINS}
    domain_hard_reasons = {domain: Counter() for domain in CONSISTENCY_DOMAINS}
    domain_soft_reasons = {domain: Counter() for domain in CONSISTENCY_DOMAINS}
    domain_unclassified_reasons = {domain: Counter() for domain in CONSISTENCY_DOMAINS}
    domain_hard_affected = {domain: set() for domain in CONSISTENCY_DOMAINS}
    domain_soft_affected = {domain: set() for domain in CONSISTENCY_DOMAINS}
    survivor_counts: list[int] = []
    survivor_observed_seeds: set[int] = set()

    female_terms = [str(term) for term in analyzer.get("female_terms", [])]
    disallowed_female_terms = [str(term) for term in analyzer.get("disallowed_female_terms", [])]
    male_terms = [str(term) for term in analyzer.get("male_terms", [])]
    consistency_rules = selected_policy.get("resolved_consistency_rules", selected_policy.get("consistency_rules", []))
    rule_annotations = selected_policy.get("consistency_rule_annotations", {})

    for seed, record in zip(seeds, normalized_records):
        prompt = str(record.get("cleaned_prompt") or record.get("raw_prompt") or "")
        normalized = _normalise(prompt)
        words = _words(prompt)
        context = _context(record)
        prompts.append(prompt)
        normalized_prompts.append(normalized)
        word_lengths.append(len(words))
        context_size = int(record.get("context_json_bytes", len(canonical_json_bytes(context))))
        context_sizes.append(context_size)
        if (
            not isinstance(record.get("execution_trace"), list)
            or not isinstance(record.get("resolved_seeds"), Mapping)
            or not record.get("base_workflow_hash")
            or not context
            or not prompt
        ):
            record_contract_error_count += 1

        if not any(_contains_term(prompt, term) for term in female_terms):
            findings["missing_female_protagonist"][seed] = "no configured female protagonist term in cleaned prompt"
        disallowed_hits = sorted(term for term in disallowed_female_terms if _contains_term(prompt, term))
        if disallowed_hits:
            findings["non_girl_female_term"][seed] = f"disallowed female identity terms={disallowed_hits}"
        demographic_hits = sorted(set(find_person_demographic_descriptors(prompt)), key=str.lower)
        if demographic_hits:
            findings["person_demographic_descriptor"][seed] = f"race or skin descriptors={demographic_hits}"
        male_hits = sorted(term for term in male_terms if _contains_term(prompt, term))
        if male_hits:
            findings["male_pronoun_drift"][seed] = f"male identity terms={male_hits}"
        if has_other_person_conflict(prompt):
            findings["other_person_solo_conflict"][seed] = "solo-safety audit detected another-person language"
        subject_hits = sum(len(re.findall(rf"\b{re.escape(term)}\b", prompt.lower())) for term in female_terms)
        if subject_hits > int(analyzer.get("max_duplicate_subject_terms", 1)):
            findings["duplicate_protagonist_mention"][seed] = f"female protagonist noun mentions={subject_hits}"

        combined = " ".join(
            [prompt, str(context.get("loc", "")), str(context.get("action", "")), str(context.get("costume", ""))]
        ).lower()
        for rule in consistency_rules if isinstance(consistency_rules, list) else []:
            if not isinstance(rule, Mapping):
                continue
            left, right = str(rule.get("input_term", "")), str(rule.get("template_term", ""))
            annotation = rule_annotations.get(f"{left}|{right}", {}) if isinstance(rule_annotations, Mapping) else {}
            domain = str(annotation.get("domain", ""))
            reason_code = str(annotation.get("reason_code", "consistency_rule_conflict"))
            if domain in CONSISTENCY_DOMAINS:
                domain_evaluated_seeds[domain].add(seed)
            if left and right and _contains_term(combined, left) and _contains_term(combined, right):
                reason = str(rule.get("reason") or f"{left} conflicts with {right}")
                prior = findings["consistency_rule_conflict"].get(seed)
                findings["consistency_rule_conflict"][seed] = f"{prior}; {reason}" if prior else reason
                if domain in CONSISTENCY_DOMAINS:
                    domain_hard_reasons[domain][reason_code] += 1
                    domain_hard_affected[domain].add(seed)
                    issue_code = f"{domain}_conflict"
                    domain_evidence = f"reason_code={reason_code}; {reason}"
                    prior_domain = findings[issue_code].get(seed)
                    findings[issue_code][seed] = f"{prior_domain}; {domain_evidence}" if prior_domain else domain_evidence

        for observation in _constraint_observations(context):
            domain = observation["domain"]
            domain_evaluated_seeds[domain].add(seed)
            hard_codes = observation["hard_reason_codes"]
            soft_codes = observation["soft_reason_codes"]
            unknown_codes = observation["unclassified_reason_codes"]
            domain_hard_reasons[domain].update(hard_codes)
            domain_soft_reasons[domain].update(soft_codes)
            domain_unclassified_reasons[domain].update(unknown_codes)
            if hard_codes:
                domain_hard_affected[domain].add(seed)
            if soft_codes:
                domain_soft_affected[domain].add(seed)
            if hard_codes or soft_codes:
                issue_code = f"{domain}_conflict"
                evidence_parts = []
                if hard_codes:
                    evidence_parts.append(f"hard_reason_codes={hard_codes}")
                if soft_codes:
                    evidence_parts.append(f"soft_reason_codes={soft_codes}")
                findings[issue_code][seed] = "; ".join(evidence_parts)
            survivor = observation["survivor_count"]
            if survivor is not None:
                survivor_counts.append(survivor)
                survivor_observed_seeds.add(seed)

        if not words or DANGLING_END_RE.search(prompt):
            findings["sentence_fragment"][seed] = "empty prompt or dangling terminal connector"
        anomaly = PUNCTUATION_ANOMALY_RE.search(prompt)
        if anomaly:
            findings["punctuation_anomaly"][seed] = f"punctuation sequence={anomaly.group(0)!r}"
        comma_density = prompt.count(",") / max(1, len(words))
        if comma_density > float(analyzer.get("comma_density_max", 0.12)):
            findings["high_comma_density"][seed] = f"comma_density={_round(comma_density, digits)}"
        repeated: list[str] = []
        min_occurrences = int(analyzer.get("repeated_ngram_min_occurrences", 3))
        for width in (2, 3, 4):
            counts = Counter(" ".join(words[index:index + width]) for index in range(max(0, len(words) - width + 1)))
            repeated.extend(f"{width}-gram {gram!r} x{count}" for gram, count in counts.items() if count >= min_occurrences)
        if repeated:
            findings["repeated_ngram"][seed] = "; ".join(sorted(repeated)[:3])
        family_counts: Counter[str] = Counter()
        for clause in re.split(r"[,.;]+", prompt):
            family_counts.update(semantic_families_for_text(clause))
        repeated_families = sorted(
            f"{family}={count}" for family, count in family_counts.items()
            if count > int(analyzer.get("semantic_family_max_mentions", 2))
        )
        if repeated_families:
            findings["semantic_family_repetition"][seed] = ", ".join(repeated_families)
        minimum = int(analyzer.get("prompt_length_words_min", 12))
        maximum = int(analyzer.get("prompt_length_words_max", 220))
        if len(words) < minimum or len(words) > maximum:
            findings["prompt_length_outlier"][seed] = f"word_count={len(words)} outside [{minimum},{maximum}]"

        fallback_hits = [value for key, value in _walk(context) if key == "fallback_used" and value is True]
        if fallback_hits:
            fallback_records += 1
        warnings = [value for key, value in _walk(context) if key == "warnings" and isinstance(value, list) and value]
        record_warnings = record.get("warnings", [])
        warning_items = sum(len(value) for value in warnings) + (len(record_warnings) if isinstance(record_warnings, list) else 0)
        if warning_items:
            warning_count += warning_items
            findings["runtime_warning"][seed] = f"warning_count={warning_items}"
        is_error = bool(record.get("error")) or str(record.get("status", "")).lower() in {"error", "failed", "failure"}
        if is_error:
            error_count += 1
            findings["runtime_error"][seed] = f"status={record.get('status', 'error')}"
        if record.get("replay_mismatch") is True:
            findings["deterministic_replay_mismatch"][seed] = "record is marked as a deterministic replay mismatch"
        if context_size > int(analyzer.get("context_json_bytes_max", 262144)):
            findings["context_size_exceeded"][seed] = f"context_json_bytes={context_size}"

        for name in signatures:
            signatures[name][_signature(context, name)] += 1
        syntax_counter[_syntax_signature(prompt)] += 1
        template_keys = _values_for_keys(context, {"template_key"})
        template_counter["|".join(template_keys) if template_keys else "unknown"] += 1
        verb_counter[_action_verb(context)] += 1
        for family in semantic_families_for_text(prompt):
            semantic_counter[family] += 1

    exact_counts = Counter(prompts)
    normalized_counts = Counter(normalized_prompts)
    for prompt, count in exact_counts.items():
        if prompt and count > 1:
            for seed, value in zip(seeds, prompts):
                if value == prompt:
                    findings["exact_duplicate_prompt"][seed] = f"identical prompt occurs {count} times"
    for prompt, count in normalized_counts.items():
        if prompt and count > 1:
            for seed, value in zip(seeds, normalized_prompts):
                if value == prompt:
                    findings["normalized_duplicate_prompt"][seed] = f"normalized prompt occurs {count} times"
    fallback_rate = _rate(fallback_records, total, digits)
    if fallback_rate > float(analyzer.get("fallback_rate_max", 0.05)):
        for seed, record in records_by_seed.items():
            context = _context(record)
            if any(key == "fallback_used" and value is True for key, value in _walk(context)):
                findings["high_fallback_rate"][seed] = f"cohort fallback_rate={fallback_rate}"

    identity_counts = {code: len(findings[code]) for code in (
        "missing_female_protagonist", "non_girl_female_term", "person_demographic_descriptor", "male_pronoun_drift",
        "other_person_solo_conflict", "duplicate_protagonist_mention"
    )}
    domain_metrics: dict[str, Any] = {}
    for domain in CONSISTENCY_DOMAINS:
        evaluated = len(domain_evaluated_seeds[domain])
        hard_affected = len(domain_hard_affected[domain])
        soft_affected = len(domain_soft_affected[domain])
        domain_metrics[domain] = {
            "evaluated_record_count": evaluated,
            "hard_affected_record_count": hard_affected,
            "hard_conflict_count": sum(domain_hard_reasons[domain].values()),
            "hard_conflict_rate": _rate(hard_affected, evaluated, digits),
            "hard_reason_code_counts": dict(sorted(domain_hard_reasons[domain].items())),
            "not_observed_record_count": total - evaluated,
            "soft_conflict_count": sum(domain_soft_reasons[domain].values()),
            "soft_affected_record_count": soft_affected,
            "soft_conflict_rate": _rate(soft_affected, evaluated, digits),
            "soft_reason_code_counts": dict(sorted(domain_soft_reasons[domain].items())),
            "status": "observed" if evaluated else "not_observed",
            "unclassified_reason_code_counts": dict(sorted(domain_unclassified_reasons[domain].items())),
        }
    survivor_metrics = {
        "count_max": max(survivor_counts, default=None),
        "count_min": min(survivor_counts, default=None),
        "count_p50": _round(_percentile(survivor_counts, 0.50), digits) if survivor_counts else None,
        "count_p95": _round(_percentile(survivor_counts, 0.95), digits) if survivor_counts else None,
        "not_observed_record_count": total - len(survivor_observed_seeds),
        "observed_record_count": len(survivor_observed_seeds),
        "status": "observed" if survivor_counts else "not_observed",
        "zero_survivor_observation_count": sum(1 for value in survivor_counts if value == 0),
    }
    consistency_hard_affected = set(findings["consistency_rule_conflict"])
    consistency_soft_affected: set[int] = set()
    for domain in CONSISTENCY_DOMAINS:
        consistency_hard_affected.update(domain_hard_affected[domain])
        consistency_soft_affected.update(domain_soft_affected[domain])
    metrics = {
        "analyzer_version": ANALYZER_VERSION,
        "cohorts": dict(sorted(Counter(str(record.get("cohort", "unspecified")) for record in normalized_records).items())),
        "consistency": {
            "domains": domain_metrics,
            "hard_affected_record_count": len(consistency_hard_affected),
            "hard_conflict_count": sum(sum(counter.values()) for counter in domain_hard_reasons.values()),
            "hard_conflict_rate": _rate(len(consistency_hard_affected), total, digits),
            "soft_affected_record_count": len(consistency_soft_affected),
            "soft_conflict_count": sum(sum(counter.values()) for counter in domain_soft_reasons.values()),
            "soft_conflict_rate": _rate(len(consistency_soft_affected), total, digits),
        },
        "diversity": {
            "exact_unique_ratio": _rate(len(exact_counts), total, digits),
            "normalized_unique_ratio": _rate(len(normalized_counts), total, digits),
            "semantic_family_entropy": _entropy(semantic_counter, digits),
            "semantic_family_top1_concentration": _top_concentration(semantic_counter, 1, sum(semantic_counter.values()), digits),
            "semantic_family_top5_concentration": _top_concentration(semantic_counter, 5, sum(semantic_counter.values()), digits),
            "syntax_entropy": _entropy(syntax_counter, digits),
            "syntax_top1_concentration": _top_concentration(syntax_counter, 1, total, digits),
            "survivor": survivor_metrics,
            "template_entropy": _entropy(template_counter, digits),
            "template_top1_concentration": _top_concentration(template_counter, 1, total, digits),
            "verb_entropy": _entropy(verb_counter, digits),
            "verb_top1_concentration": _top_concentration(verb_counter, 1, total, digits),
            **{
                f"{name}_signature_coverage": _rate(len(counter), total, digits)
                for name, counter in signatures.items()
            },
            **{f"{name}_signature_entropy": _entropy(counter, digits) for name, counter in signatures.items()},
        },
        "identity": {
            **{f"{code}_count": count for code, count in identity_counts.items()},
            **{f"{code}_rate": _rate(count, total, digits) for code, count in identity_counts.items()},
            "single_female_coverage": _round(1.0 - _rate(identity_counts["missing_female_protagonist"], total, digits), digits) if total else 0.0,
        },
        "naturalness": {
            "high_comma_density_count": len(findings["high_comma_density"]),
            "prompt_length_words_p50": _round(_percentile(word_lengths, 0.50), digits),
            "prompt_length_words_p95": _round(_percentile(word_lengths, 0.95), digits),
            "punctuation_anomaly_count": len(findings["punctuation_anomaly"]),
            "repeated_ngram_count": len(findings["repeated_ngram"]),
            "semantic_family_repetition_count": len(findings["semantic_family_repetition"]),
            "sentence_fragment_count": len(findings["sentence_fragment"]),
        },
        "policy_version": str(selected_policy.get("policy_version", "unknown")),
        "record_count": total,
        "runtime": {
            "context_json_bytes_max": max(context_sizes, default=0),
            "context_json_bytes_p50": _round(_percentile(context_sizes, 0.50), digits),
            "context_json_bytes_p95": _round(_percentile(context_sizes, 0.95), digits),
            "deterministic_replay_mismatch_count": sum(1 for record in normalized_records if record.get("replay_mismatch") is True),
            "error_count": error_count,
            "fallback_count": fallback_records,
            "fallback_rate": fallback_rate,
            "record_contract_error_count": record_contract_error_count,
            "unique_config_hash_count": len({str(record.get("config_hash", "")) for record in normalized_records if record.get("config_hash")}),
            "unique_profile_hash_count": len({str(record.get("profile_hash", "")) for record in normalized_records if record.get("profile_hash")}),
            "unique_workflow_hash_count": len({str(record.get("base_workflow_hash", "")) for record in normalized_records if record.get("base_workflow_hash")}),
            "warning_count": warning_count,
        },
        "schema_version": METRICS_SCHEMA_VERSION,
    }

    issue_specs = {
        "missing_female_protagonist": (0.99, ["ContextPromptBuilder"], ["pipeline/character_profile_pipeline.py", "character_service.py"], "assets/test_character_profiles.py"),
        "non_girl_female_term": (1.0, ["ContextPromptBuilder"], ["pipeline/prompt_realizer.py", "prompt_renderer.py"], "assets/test_action_frame_realizer.py"),
        "person_demographic_descriptor": (1.0, ["ContextPromptBuilder"], ["pipeline/prompt_realizer.py", "prompt_renderer.py"], "assets/test_action_frame_realizer.py"),
        "male_pronoun_drift": (0.99, ["ContextPromptBuilder", "ContextGarnish"], ["core/solo_safety.py", "prompt_renderer.py"], "assets/test_solo_female_invariants.py"),
        "other_person_solo_conflict": (0.98, ["ContextLocationExpander", "ContextActionGenerator", "ContextPromptBuilder"], ["core/solo_safety.py", "pipeline/location_builder.py", "pipeline/action_generator.py"], "assets/test_solo_safety.py"),
        "duplicate_protagonist_mention": (0.9, ["ContextPromptBuilder", "ContextGarnish"], ["prompt_renderer.py", "vocab/garnish/logic.py"], "assets/test_prompt_renderer.py"),
        "consistency_rule_conflict": (0.99, ["ContextLocationExpander", "ContextActionGenerator", "ContextClothingExpander"], ["rules/consistency_rules.json", "pipeline/location_builder.py"], "assets/test_consistency_rules.py"),
        "location_action_object_conflict": (0.99, ["ContextLocationExpander", "ContextActionGenerator"], ["pipeline/location_builder.py", "pipeline/action_generator.py"], "assets/test_prompt_quality_analyzer.py"),
        "clothing_tpo_weather_conflict": (0.99, ["ContextClothingExpander", "ContextLocationExpander"], ["pipeline/clothing_candidate_selector.py", "pipeline/location_builder.py"], "assets/test_prompt_quality_analyzer.py"),
        "mood_action_garnish_conflict": (0.99, ["ContextActionGenerator", "ContextGarnish"], ["pipeline/action_generator.py", "vocab/garnish/logic.py"], "assets/test_prompt_quality_analyzer.py"),
        "sentence_fragment": (0.8, ["ContextPromptBuilder", "PromptCleaner"], ["prompt_renderer.py", "nodes_prompt_cleaner.py"], "assets/test_prompt_renderer.py"),
        "repeated_ngram": (0.96, ["ContextPromptBuilder", "ContextGarnish"], ["prompt_renderer.py", "vocab/garnish/logic.py"], "assets/test_prompt_repetition.py"),
        "punctuation_anomaly": (0.99, ["ContextPromptBuilder", "PromptCleaner"], ["prompt_renderer.py", "nodes_prompt_cleaner.py"], "assets/test_prompt_renderer.py"),
        "high_comma_density": (0.85, ["ContextPromptBuilder"], ["prompt_renderer.py"], "assets/test_prompt_renderer.py"),
        "semantic_family_repetition": (0.9, ["ContextGarnish", "ContextPromptBuilder"], ["vocab/garnish/logic.py", "prompt_renderer.py"], "assets/test_prompt_repetition.py"),
        "prompt_length_outlier": (0.99, ["ContextPromptBuilder"], ["prompt_renderer.py"], "assets/test_prompt_renderer.py"),
        "exact_duplicate_prompt": (1.0, ["ContextPromptBuilder"], ["prompt_renderer.py", "vocab/data/template_catalog.json"], "assets/test_template_diversity.py"),
        "normalized_duplicate_prompt": (1.0, ["ContextPromptBuilder", "PromptCleaner"], ["prompt_renderer.py", "nodes_prompt_cleaner.py"], "assets/test_template_diversity.py"),
        "high_fallback_rate": (1.0, ["ContextGarnish", "ContextLocationExpander", "ContextActionGenerator"], ["pipeline/context_pipeline.py", "pipeline/location_builder.py", "pipeline/action_generator.py"], "assets/test_prompt_quality_analyzer.py"),
        "runtime_warning": (1.0, [], ["tools/workflow_prompt_runner.py"], "assets/test_workflow_prompt_runner.py"),
        "runtime_error": (1.0, [], ["tools/workflow_prompt_runner.py"], "assets/test_workflow_prompt_runner.py"),
        "deterministic_replay_mismatch": (1.0, [], ["tools/workflow_prompt_runner.py"], "assets/test_prompt_quality_loop.py"),
        "context_size_exceeded": (1.0, ["ContextToJSON"], ["nodes_context.py"], "assets/test_context_schema.py"),
    }
    issues = []
    for code, (confidence, nodes, owners, surface) in issue_specs.items():
        item = _issue(
            code, findings[code], findings[code], records_by_seed, selected_policy, total, digits,
            confidence=confidence, preferred_nodes=nodes, owners=owners, test_surface=surface,
        )
        if item:
            if code.endswith("_conflict") and code.removesuffix("_conflict") in CONSISTENCY_DOMAINS:
                domain = code.removesuffix("_conflict")
                if not (set(item["affected_seeds"]) & domain_hard_affected[domain]):
                    item["severity"] = "medium"
            issues.append(item)
    issues.sort(
        key=lambda item: (
            SEVERITY_ORDER.get(item["severity"], 99),
            -item["frequency"],
            -item["confidence"],
            item["issue_code"],
        )
    )
    issues_artifact = {
        "analyzer_version": ANALYZER_VERSION,
        "issue_count": len(issues),
        "issues": issues,
        "policy_version": str(selected_policy.get("policy_version", "unknown")),
        "record_count": total,
        "schema_version": ISSUES_SCHEMA_VERSION,
    }
    return {"issues": issues_artifact, "metrics": metrics}


def analyze_records_file(records_path: str | Path, policy_path: str | Path | None = None) -> dict[str, Any]:
    return analyze_records(load_records(records_path), load_policy(policy_path))


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.parent / ".staging"
    staging.mkdir(parents=True, exist_ok=True)
    temporary = staging / f"{path.name}.{uuid.uuid4().hex}.tmp"
    temporary.write_bytes(canonical_json_bytes(value))
    os.replace(temporary, path)


def write_analysis(
    records_path: str | Path,
    metrics_path: str | Path,
    issues_path: str | Path,
    policy_path: str | Path | None = None,
) -> dict[str, Any]:
    result = analyze_records_file(records_path, policy_path)
    _atomic_write(Path(metrics_path), result["metrics"])
    _atomic_write(Path(issues_path), result["issues"])
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze canonical prompt-quality records.")
    parser.add_argument("--records", required=True)
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--output-dir")
    parser.add_argument("--metrics")
    parser.add_argument("--issues")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir) if args.output_dir else None
    metrics_path = Path(args.metrics) if args.metrics else (output_dir / "metrics.json" if output_dir else None)
    issues_path = Path(args.issues) if args.issues else (output_dir / "issues.json" if output_dir else None)
    if metrics_path is None or issues_path is None:
        raise SystemExit("provide --output-dir or both --metrics and --issues")
    try:
        result = write_analysis(args.records, metrics_path, issues_path, args.policy)
        print(json.dumps({"issue_count": result["issues"]["issue_count"], "metrics": str(metrics_path), "issues": str(issues_path)}, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, WorkflowValidationError) as exc:
        if isinstance(exc, WorkflowValidationError):
            envelope = exc.to_envelope()
        else:
            envelope = WorkflowValidationError(
                "analysis_input_error", "could not analyze prompt records", exception_type=type(exc).__name__
            ).to_envelope()
        sys.stderr.buffer.write(canonical_json_bytes(envelope))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
