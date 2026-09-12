from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SCHEMA = "variation-semantic-pair-contract/v1"
TAXONOMY_SCHEMA = "variation-semantic-comparator-taxonomy/v1"
CLASSIFIER_SCHEMA = "variation-action-semantic-classifier/v1"
ALGORITHM_VERSION = "compatibility-constrained-bipartite-sha256/v1"
PAIRING_SEED = "v150-semantic-pairing-001"
ALLOWED_DELTA = ["action_key", "action_text", "location_key", "location_prompt", "subject_key", "bound_resource_hashes"]
SHARED_FIELDS = ["protagonist_role", "character_profile", "costume_theme", "place_class", "indoor_outdoor", "location_family_tags", "action_family", "action_intent", "purpose", "progress", "social_distance", "action_load", "primary_object_family", "emotion_core", "emotion_intensity", "time_phase", "weather_class"]


class SemanticPairError(ValueError):
    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details

    def envelope(self) -> dict[str, Any]:
        return {"schema_version": "variation-semantic-pair-error/v1", "code": self.code, "message": self.message, "details": self.details}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def value_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, schema: str | None = None) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or (schema and value.get("schema_version") != schema):
        raise SemanticPairError("schema_mismatch", "JSON input has an unsupported schema", path=str(path), expected=schema)
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SemanticPairError("invalid_jsonl", "row authority is invalid JSONL", row_index=index) from exc
        if not isinstance(row, dict) or not all(isinstance(row.get(key), str) and row[key] for key in ("subj", "loc", "action", "costume")):
            raise SemanticPairError("invalid_row", "row authority lacks a required concrete binding", row_index=index)
        rows.append(row)
    if not rows:
        raise SemanticPairError("empty_row_authority", "row authority is empty")
    return rows


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def classify_action(text: str, load: str, classifier: Mapping[str, Any]) -> dict[str, str]:
    if classifier.get("schema_version") != CLASSIFIER_SCHEMA:
        raise SemanticPairError("action_classifier_schema_mismatch", "unsupported action classifier schema")
    normalized = normalize_text(text).rstrip(".!?")
    verb_match = re.match(r"([a-z]+)", normalized)
    verb = verb_match.group(1) if verb_match else ""
    matches = [rule for rule in classifier.get("rules", []) if verb in rule.get("verbs", [])]
    if len(matches) != 1:
        raise SemanticPairError("action_classification_not_unique", "action must match exactly one closed classifier rule", action=text, match_count=len(matches))
    rule = matches[0]
    if load not in {"calm", "active", "tense"}:
        raise SemanticPairError("unknown_action_load", "action load is outside the closed taxonomy", load=load)
    return {"action_family": str(rule["action_family"]), "action_intent": str(rule["id"]), "purpose": str(rule["purpose"]), "action_load": load, "primary_object_family": str(rule["primary_object_family"])}


def authored_action(text: str, location: str, pools: Mapping[str, Any]) -> tuple[str, str]:
    matches = []
    for item in pools.get(location, []):
        if not isinstance(item, Mapping) or not isinstance(item.get("text"), str):
            continue
        authored = str(item["text"])
        if normalize_text(text) == normalize_text(authored) or normalize_text(text).startswith(normalize_text(authored) + ","):
            matches.append(item)
    if len(matches) != 1:
        raise SemanticPairError("authored_action_binding_not_unique", "selected action must bind one authored pool row", location=location, action=text, match_count=len(matches))
    item = dict(matches[0])
    return str(item["text"]), str(item.get("load", ""))


def indoor_outdoor(location: str, taxonomy: Mapping[str, Any]) -> str:
    hits = [key for key, values in taxonomy.get("location_classes", {}).items() if location in values]
    if len(hits) != 1:
        raise SemanticPairError("location_classification_not_unique", "location must have exactly one indoor/outdoor class", location=location, match_count=len(hits))
    return hits[0]


def semantic_identity(row: Mapping[str, Any], action_class: Mapping[str, str], taxonomy: Mapping[str, Any], *, candidate_location: str) -> dict[str, Any]:
    defaults = taxonomy.get("shared_defaults", {})
    aliases = taxonomy.get("aliases", {})
    costume = aliases.get("costume_theme", {}).get(str(row["costume"]), str(row["costume"]))
    location_class = indoor_outdoor(candidate_location, taxonomy)
    return {
        "protagonist_role": defaults.get("protagonist_role"), "character_profile": defaults.get("character_profile"),
        "costume_theme": costume, "place_class": "daily_life", "indoor_outdoor": location_class,
        "location_family_tags": ["daily_life"], **action_class,
        "progress": defaults.get("progress"), "social_distance": defaults.get("social_distance"),
        "emotion_core": defaults.get("emotion_core"), "emotion_intensity": defaults.get("emotion_intensity"),
        "time_phase": defaults.get("time_phase"), "weather_class": defaults.get("weather_class"),
    }


def validate_taxonomy(taxonomy: Mapping[str, Any], candidate_rows: Sequence[Mapping[str, Any]], baseline_rows: Sequence[Mapping[str, Any]]) -> None:
    if taxonomy.get("schema_version") != TAXONOMY_SCHEMA:
        raise SemanticPairError("taxonomy_schema_mismatch", "unsupported semantic comparator taxonomy")
    subject_map, location_map = taxonomy.get("candidate_subject_comparators", {}), taxonomy.get("candidate_location_comparators", {})
    missing_subjects = sorted({str(row["subj"]) for row in candidate_rows} - set(subject_map))
    missing_locations = sorted({str(row["loc"]) for row in candidate_rows} - set(location_map))
    active_subjects, active_locations = {str(row["subj"]) for row in baseline_rows}, {str(row["loc"]) for row in baseline_rows}
    invalid_subjects = sorted({item for values in subject_map.values() for item in values} - active_subjects)
    invalid_locations = sorted({item for values in location_map.values() for item in values} - active_locations)
    all_subjects = active_subjects | {str(row["subj"]) for row in candidate_rows}
    all_locations = active_locations | {str(row["loc"]) for row in candidate_rows}
    subject_class_hits = {item: sum(item in values for values in taxonomy.get("subject_classes", {}).values()) for item in all_subjects}
    location_class_hits = {item: sum(item in values for values in taxonomy.get("location_classes", {}).values()) for item in all_locations}
    unclosed_subjects = sorted(item for item, count in subject_class_hits.items() if count != 1)
    unclosed_locations = sorted(item for item, count in location_class_hits.items() if count != 1)
    if missing_subjects or missing_locations or invalid_subjects or invalid_locations or unclosed_subjects or unclosed_locations:
        raise SemanticPairError("taxonomy_authority_mismatch", "taxonomy does not close over real candidate and active IDs", missing_subjects=missing_subjects, missing_locations=missing_locations, invalid_subjects=invalid_subjects, invalid_locations=invalid_locations)


def _side(row: Mapping[str, Any], row_index: int, action_text: str, action_hash: str) -> dict[str, Any]:
    bound = dict(row); bound["action"] = action_text
    return {"subject_key": row["subj"], "location_key": row["loc"], "action_text": action_text, "row_index": row_index, "row_sha256": value_hash(row), "action_row_sha256": action_hash, "workflow_overrides": {"1": {"source_mode": "json_only", "json_string": json.dumps(bound, ensure_ascii=False, sort_keys=True, separators=(",", ":"))}, "3": {"variation_mode": "original"}}}


def plan_pairs(*, experiment_id: str, coverage_path: Path, baseline_prompts_path: Path, candidate_action_pools_path: Path, baseline_action_pools_path: Path, taxonomy_path: Path, classifier_path: Path, automatic_comparison_path: Path, candidate_snapshot: Mapping[str, Any], data_intent_path: Path, pairing_seed: str = PAIRING_SEED) -> dict[str, Any]:
    schedule = load_json(coverage_path)
    candidate_rows = schedule.get("candidate_rows")
    if not isinstance(candidate_rows, list) or len(candidate_rows) != 19:
        raise SemanticPairError("candidate_row_authority_mismatch", "coverage authority must contain exactly 19 candidate rows")
    baseline_rows = load_jsonl(baseline_prompts_path)
    taxonomy, classifier = load_json(taxonomy_path, TAXONOMY_SCHEMA), load_json(classifier_path, CLASSIFIER_SCHEMA)
    candidate_pools, baseline_pools = load_json(candidate_action_pools_path), load_json(baseline_action_pools_path)
    validate_taxonomy(taxonomy, candidate_rows, baseline_rows)
    authorities = {
        "data_intent": {"path": str(data_intent_path), "sha256": file_hash(data_intent_path)},
        "candidate_rows": {"path": str(coverage_path), "sha256": file_hash(coverage_path), "rows_sha256": value_hash(candidate_rows)},
        "baseline_rows": {"path": str(baseline_prompts_path), "sha256": file_hash(baseline_prompts_path)},
        "comparator_taxonomy": {"path": str(taxonomy_path), "sha256": file_hash(taxonomy_path)},
        "action_classifier": {"path": str(classifier_path), "sha256": file_hash(classifier_path)},
        "selection_algorithm": ALGORITHM_VERSION, "pairing_seed": pairing_seed,
    }
    salt = value_hash({"schema": CONTRACT_SCHEMA, "authorities": authorities})
    edges = []
    for ci, candidate in enumerate(candidate_rows):
        candidate_actions = candidate_pools.get(str(candidate["loc"]), [])
        if not isinstance(candidate_actions, list) or not candidate_actions:
            raise SemanticPairError("candidate_action_pool_missing", "candidate tuple lacks an authored action pool", location=candidate["loc"])
        classified_candidate_actions = []
        for candidate_action in candidate_actions:
            if not isinstance(candidate_action, Mapping) or not isinstance(candidate_action.get("text"), str):
                raise SemanticPairError("invalid_candidate_action_row", "candidate action pool contains an invalid row", location=candidate["loc"])
            ca, cload = str(candidate_action["text"]), str(candidate_action.get("load", ""))
            classified_candidate_actions.append((ca, cload, classify_action(ca, cload, classifier)))
        for bi, baseline in enumerate(baseline_rows):
            if baseline["subj"] not in taxonomy["candidate_subject_comparators"][candidate["subj"]] or baseline["loc"] not in taxonomy["candidate_location_comparators"][candidate["loc"]]:
                continue
            allowed_costumes = taxonomy.get("candidate_location_costumes", {}).get(str(candidate["loc"]), [])
            if allowed_costumes and str(baseline.get("costume", "")) not in allowed_costumes:
                continue
            if indoor_outdoor(str(candidate["loc"]), taxonomy) != indoor_outdoor(str(baseline["loc"]), taxonomy):
                continue
            baseline_actions = baseline_pools.get(str(baseline["loc"]), [])
            if not isinstance(baseline_actions, list):
                continue
            for baseline_action in baseline_actions:
                if not isinstance(baseline_action, Mapping) or not isinstance(baseline_action.get("text"), str):
                    continue
                ba, bload = str(baseline_action["text"]), str(baseline_action.get("load", ""))
                try:
                    bc = classify_action(ba, bload, classifier)
                except SemanticPairError:
                    continue
                for ca, cload, cc in classified_candidate_actions:
                    if cc != bc:
                        continue
                    edge_hash = value_hash([salt, value_hash(candidate), value_hash(baseline), value_hash([ca, cload]), value_hash([ba, bload])])
                    edges.append((edge_hash, ci, bi, ca, cload, ba, bload, cc))
    graph_hash = value_hash([edge[0] for edge in sorted(edges)])
    by_candidate: dict[int, list[tuple[Any, ...]]] = {i: [] for i in range(19)}
    for edge in sorted(edges): by_candidate[edge[1]].append(edge)
    if any(not values for values in by_candidate.values()):
        raise SemanticPairError("semantic_pair_coverage_infeasible", "at least one frozen candidate row has no eligible active edge", missing_candidate_rows=[i for i, values in by_candidate.items() if not values])
    order = sorted(by_candidate, key=lambda i: (len(by_candidate[i]), i))
    def match(pos: int, used: set[tuple[int, str]], chosen: list[tuple[Any, ...]]) -> list[tuple[Any, ...]] | None:
        if pos == len(order): return chosen
        for edge in by_candidate[order[pos]]:
            baseline_binding = (edge[2], edge[5])
            if baseline_binding not in used:
                result = match(pos + 1, used | {baseline_binding}, chosen + [edge])
                if result is not None: return result
        return None
    selected = match(0, set(), [])
    if selected is None:
        raise SemanticPairError("semantic_pair_matching_infeasible", "maximum matching cannot cover all 19 candidate rows")
    selected = sorted(selected, key=lambda edge: edge[1])
    selected_baseline_bindings = {(item[2], item[5]) for item in selected}
    selected_candidate_bindings = {(item[1], item[3]) for item in selected}
    unused = [edge for edge in sorted(edges) if (edge[2], edge[5]) not in selected_baseline_bindings and (edge[1], edge[3]) not in selected_candidate_bindings]
    if not unused: raise SemanticPairError("semantic_pair_twentieth_infeasible", "no unused exact-class edge exists for pair twenty")
    selected.append(unused[0])
    control_seeds = list(schedule.get("cohort", {}).get("control_seeds", []))
    exploration_seeds = list(schedule.get("cohort", {}).get("exploration_seeds", []))
    if len(control_seeds) < 16 or len(exploration_seeds) < 4: raise SemanticPairError("pair_seed_authority_short", "coverage cohort lacks 16 control and 4 exploration immutable seeds")
    seeds = control_seeds[:16] + exploration_seeds[:4]
    pairs = []
    for index, edge in enumerate(selected):
        edge_hash, ci, bi, ca, cload, ba, bload, action_class = edge
        candidate, baseline = candidate_rows[ci], baseline_rows[bi]
        candidate_binding_row = dict(candidate)
        candidate_binding_row["costume"] = baseline["costume"]
        candidate_binding_row["meta"] = json.loads(json.dumps(baseline.get("meta", {})))
        identity = semantic_identity(baseline, action_class, taxonomy, candidate_location=str(candidate["loc"]))
        if set(identity) != set(SHARED_FIELDS): raise SemanticPairError("shared_identity_incomplete", "shared semantic identity is incomplete")
        body = {"cohort": "control" if index < 16 else "exploration", "run_seed": int(seeds[index]), "shared_semantic_identity": identity,
                "intervention_binding": {"baseline": _side(baseline, bi, ba, value_hash([ba, bload])), "candidate": _side(candidate_binding_row, ci, ca, value_hash([ca, cload]))},
                "allowed_delta": ALLOWED_DELTA, "allowed_seed_delta": ["1:seed"], "selection_edge_sha256": edge_hash}
        body["pair_id"] = "vsp-" + value_hash(body)[:16]
        pairs.append(body)
    coverage = {"candidate_locations": sorted({p["intervention_binding"]["candidate"]["location_key"] for p in pairs}), "candidate_subjects": sorted({p["intervention_binding"]["candidate"]["subject_key"] for p in pairs})}
    if len(pairs) != 20 or len(coverage["candidate_locations"]) != 19 or len(coverage["candidate_subjects"]) != 15:
        raise SemanticPairError("semantic_pair_coverage_incomplete", "planned contract misses required 19/15/20 feasibility", coverage=coverage)
    contract = {"schema_version": CONTRACT_SCHEMA, "experiment_id": experiment_id,
        "automatic_comparison": {"path": str(automatic_comparison_path), "sha256": file_hash(automatic_comparison_path)}, "candidate_snapshot": dict(candidate_snapshot),
        "authorities": authorities, "selection_salt_sha256": salt, "compatibility_graph_sha256": graph_hash, "pair_count": 20,
        "coverage": coverage, "allowed_delta": ALLOWED_DELTA, "allowed_seed_delta": ["1:seed"], "pairs": pairs}
    contract["contract_id"] = "v150-spc-" + value_hash(contract)[:16]
    contract["contract_sha256"] = value_hash(contract)
    return contract


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in ("experiment-id", "coverage", "baseline-prompts", "candidate-action-pools", "baseline-action-pools", "taxonomy", "classifier", "automatic-comparison", "candidate-snapshot", "data-intent", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        contract = plan_pairs(experiment_id=args.experiment_id, coverage_path=Path(args.coverage), baseline_prompts_path=Path(args.baseline_prompts), candidate_action_pools_path=Path(args.candidate_action_pools), baseline_action_pools_path=Path(args.baseline_action_pools), taxonomy_path=Path(args.taxonomy), classifier_path=Path(args.classifier), automatic_comparison_path=Path(args.automatic_comparison), candidate_snapshot=load_json(Path(args.candidate_snapshot)), data_intent_path=Path(args.data_intent))
        Path(args.output).write_bytes(canonical_bytes(contract))
        sys.stdout.buffer.write(canonical_bytes(contract)); return 0
    except (OSError, json.JSONDecodeError, SemanticPairError) as exc:
        error = exc if isinstance(exc, SemanticPairError) else SemanticPairError("semantic_pair_planning_failed", "semantic pair planning failed", exception_type=type(exc).__name__)
        sys.stderr.buffer.write(canonical_bytes(error.envelope())); return 2


if __name__ == "__main__": raise SystemExit(main())
