from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.semantic_policy import find_banned_term_matches  # noqa: E402
from tools.extract_epig_reference_overlay import STOPWORDS  # noqa: E402
from vocab.epig_reference import normalize_term, read_epig_subject_centric_csv  # noqa: E402


SUBJECT_GARNISH_KEYS = {
    "POSE_STANDING",
    "POSE_SITTING",
    "POSE_LYING",
    "POSE_DYNAMIC",
    "HAND_POSITIONS",
    "HAND_GESTURES",
    "EYES_BASE",
    "MOUTH_BASE",
    "MOOD_POOLS",
}

REJECTED_GARNISH_KEYS = {
    "VIEW_ANGLES",
    "VIEW_FRAMING",
    "EFFECTS_BASE",
    "EFFECTS_LIGHT",
    "EFFECTS_ATMOSPHERE",
}

LOGIC_ASSIGNMENTS = {"PERSONALITY_GARNISH_BIAS", "EMOTION_MODEL"}

SUBJECT_DESCRIPTOR_HINTS = {
    "arm",
    "arms",
    "body",
    "breath",
    "breathing",
    "brow",
    "cheek",
    "cheeks",
    "chest",
    "chin",
    "crying",
    "eye",
    "eyes",
    "face",
    "finger",
    "fingers",
    "fist",
    "fists",
    "frown",
    "frowning",
    "gaze",
    "gesture",
    "glance",
    "grin",
    "hand",
    "hands",
    "head",
    "jaw",
    "knee",
    "knees",
    "laugh",
    "laughing",
    "lean",
    "leaning",
    "leg",
    "legs",
    "limbs",
    "lip",
    "lips",
    "look",
    "looking",
    "mouth",
    "neck",
    "palm",
    "pose",
    "posture",
    "shoulder",
    "shoulders",
    "smile",
    "smiling",
    "stance",
    "stare",
    "tear",
    "tears",
    "teeth",
}


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _iter_strings(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_strings(item, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def _add_descriptor(
    descriptors: dict[tuple[str, str, str], dict[str, Any]],
    text: str,
    source: str,
    category: str,
    path: str,
) -> None:
    normalized = normalize_term(text)
    if not normalized:
        return
    if len(normalized) > 120:
        return
    key = (normalized, source, path)
    descriptors[key] = {
        "text": normalized,
        "display_text": str(text or "").strip(),
        "source": source,
        "category": category,
        "path": path,
    }


def _collect_garnish_base(repo_root: Path, descriptors: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    path = repo_root / "vocab" / "data" / "garnish_base_vocab.json"
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return
    for key, value in sorted(payload.items()):
        if key not in SUBJECT_GARNISH_KEYS and key not in REJECTED_GARNISH_KEYS:
            continue
        for item_path, text in _iter_strings(value, f"$.{key}"):
            _add_descriptor(descriptors, text, "vocab/data/garnish_base_vocab.json", str(key), item_path)


def _collect_personality_profiles(repo_root: Path, descriptors: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    path = repo_root / "vocab" / "data" / "personality_behavior_profiles.json"
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return
    slots = payload.get("descriptors", {})
    if not isinstance(slots, dict):
        return
    for slot, items in sorted(slots.items()):
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "")).strip()
            if text:
                _add_descriptor(
                    descriptors,
                    text,
                    "vocab/data/personality_behavior_profiles.json",
                    str(slot),
                    f"$.descriptors.{slot}[{index}].text",
                )


def _collect_micro_actions(repo_root: Path, descriptors: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    path = repo_root / "vocab" / "data" / "garnish_micro_actions.json"
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return

    def visit(value: Any, json_path: str, category: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "triggers":
                    continue
                visit(item, f"{json_path}.{key}", f"{category}.{key}" if category else str(key))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{json_path}[{index}]", category)
        elif isinstance(value, str):
            _add_descriptor(descriptors, value, "vocab/data/garnish_micro_actions.json", category, json_path)

    visit(payload, "$", "")


def _literal_assignment_value(node: ast.AST) -> tuple[str, Any] | None:
    if isinstance(node, ast.Assign):
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        value_node = node.value
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        names = [node.target.id]
        value_node = node.value
    else:
        return None
    for name in names:
        if name not in LOGIC_ASSIGNMENTS:
            continue
        try:
            return name, ast.literal_eval(value_node)
        except (TypeError, ValueError, SyntaxError):
            return None
    return None


def _collect_personality_bias(value: Any, descriptors: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        return
    for personality, payload in sorted(value.items()):
        if not isinstance(payload, dict):
            continue
        prefer = payload.get("prefer", [])
        if not isinstance(prefer, list):
            continue
        for index, text in enumerate(prefer):
            if isinstance(text, str):
                _add_descriptor(
                    descriptors,
                    text,
                    "vocab/garnish/logic.py",
                    "PERSONALITY_GARNISH_BIAS",
                    f"$.PERSONALITY_GARNISH_BIAS.{personality}.prefer[{index}]",
                )


def _collect_emotion_model(value: Any, descriptors: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    for json_path, text in _iter_strings(value, "$.EMOTION_MODEL"):
        _add_descriptor(descriptors, text, "vocab/garnish/logic.py", "EMOTION_MODEL", json_path)


def _collect_logic_constants(repo_root: Path, descriptors: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    path = repo_root / "vocab" / "garnish" / "logic.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return
    for node in tree.body:
        assignment = _literal_assignment_value(node)
        if assignment is None:
            continue
        name, value = assignment
        if name == "PERSONALITY_GARNISH_BIAS":
            _collect_personality_bias(value, descriptors)
        elif name == "EMOTION_MODEL":
            _collect_emotion_model(value, descriptors)


def collect_subject_descriptor_sources(repo_root: str | Path = ROOT) -> list[dict[str, Any]]:
    repo_path = Path(repo_root)
    descriptors: dict[tuple[str, str, str], dict[str, Any]] = {}
    _collect_garnish_base(repo_path, descriptors)
    _collect_personality_profiles(repo_path, descriptors)
    _collect_micro_actions(repo_path, descriptors)
    _collect_logic_constants(repo_path, descriptors)
    return sorted(descriptors.values(), key=lambda item: (item["text"], item["source"], item["path"]))


def _meaningful_tokens(text: str) -> list[str]:
    return [
        token
        for token in normalize_term(text).split()
        if token not in STOPWORDS and len(token) >= 3
    ]


def _token_matches(tokens: list[str], epig_records: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    subject_terms = []
    non_subject_terms = []
    for token in tokens:
        record = epig_records.get(token)
        if record is None:
            continue
        if bool(record.get("subject_centric")):
            subject_terms.append(token)
        else:
            non_subject_terms.append(token)
    return subject_terms, non_subject_terms


def _has_subject_descriptor_context(tokens: list[str], category: str) -> bool:
    if any(token in SUBJECT_DESCRIPTOR_HINTS for token in tokens):
        return True
    return category in {
        "EYES_BASE",
        "MOUTH_BASE",
        "HAND_POSITIONS",
        "HAND_GESTURES",
        "PERSONALITY_GARNISH_BIAS",
        "EMOTION_MODEL",
    }


def _classify_descriptor(descriptor: dict[str, Any], epig_records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    text = descriptor["text"]
    policy_issues = [
        {"domain": domain, "term": term}
        for domain, term in find_banned_term_matches(text, ignore_hyphenated_body_type=True)
    ]
    exact = epig_records.get(text)
    tokens = _meaningful_tokens(text)
    subject_tokens, non_subject_tokens = _token_matches(tokens, epig_records)
    matched_subject_terms = []
    matched_non_subject_terms = []
    notes = []

    if exact is not None and bool(exact.get("subject_centric")):
        matched_subject_terms.append(text)
    elif exact is not None:
        matched_non_subject_terms.append(text)

    matched_subject_terms.extend(term for term in subject_tokens if term not in matched_subject_terms)
    matched_non_subject_terms.extend(term for term in non_subject_tokens if term not in matched_non_subject_terms)

    category = descriptor.get("category", "")
    has_subject_context = _has_subject_descriptor_context(tokens, category)

    if policy_issues:
        classification = "reject"
        notes.append("semantic_policy_banned_term")
    elif category in REJECTED_GARNISH_KEYS:
        classification = "reject"
        notes.append("non_subject_garnish_category")
    elif exact is not None and bool(exact.get("subject_centric")):
        classification = "direct"
        notes.append("exact_subject_centric_match")
    elif exact is not None:
        classification = "reject"
        notes.append("exact_non_subject_centric_match")
    elif matched_subject_terms and has_subject_context:
        classification = "needs_phrase"
        coverage = len(set(matched_subject_terms)) / max(1, len(set(tokens)))
        notes.append(f"subject_token_coverage={coverage:.2f}")
        if coverage >= 0.5 and len(set(tokens)) > 1:
            notes.append("candidate_for_repo_specific_phrase_authoring")
    elif matched_subject_terms:
        classification = "unmatched"
        notes.append("weak_subject_token_ignored")
    elif matched_non_subject_terms:
        classification = "reject"
        notes.append("token_only_non_subject_centric_match")
    else:
        classification = "unmatched"
        notes.append("no_epig_subject_centric_signal")

    return {
        **descriptor,
        "classification": classification,
        "matched_subject_terms": sorted(set(matched_subject_terms)),
        "matched_non_subject_terms": sorted(set(matched_non_subject_terms)),
        "policy_issues": policy_issues,
        "meaningful_token_count": len(tokens),
        "notes": notes,
    }


def audit_subject_centric_descriptors(repo_root: str | Path = ROOT, reference_root: str | Path | None = None) -> dict[str, Any]:
    repo_path = Path(repo_root)
    ref_path = Path(reference_root) if reference_root is not None else repo_path.parent / "参考"
    epig_path = ref_path / "EPIG" / "data" / "NRC_VAD_with_subject_centric.csv"
    warnings: list[dict[str, str]] = []
    if epig_path.exists():
        try:
            epig_records = read_epig_subject_centric_csv(epig_path)
        except (OSError, ValueError) as exc:
            epig_records = {}
            warnings.append({"source": "epig_subject_centric", "path": str(epig_path), "warning": str(exc)})
    else:
        epig_records = {}
        warnings.append({"source": "epig_subject_centric", "path": str(epig_path), "warning": "missing"})

    descriptors = collect_subject_descriptor_sources(repo_path)
    records = [_classify_descriptor(descriptor, epig_records) for descriptor in descriptors]
    records = sorted(records, key=lambda item: (item["classification"], item["text"], item["source"], item["path"]))
    counts = {name: sum(1 for record in records if record["classification"] == name) for name in ("direct", "needs_phrase", "reject", "unmatched")}
    subject_record_count = sum(1 for record in epig_records.values() if bool(record.get("subject_centric")))
    non_subject_record_count = len(epig_records) - subject_record_count

    return {
        "schema_version": "1.0",
        "generated_kind": "subject_centric_descriptor_candidates",
        "tracked_policy": "generated_local_only",
        "reference_policy": {
            "source_data_not_tracked": True,
            "raw_reference_rows_not_reused_as_runtime_data": True,
            "repo_specific_derived_candidates_only": True,
        },
        "reference": {
            "path": str(epig_path),
            "record_count": len(epig_records),
            "subject_centric_record_count": subject_record_count,
            "non_subject_centric_record_count": non_subject_record_count,
        },
        "descriptor_count": len(records),
        "direct_count": counts["direct"],
        "needs_phrase_count": counts["needs_phrase"],
        "reject_count": counts["reject"],
        "unmatched_count": counts["unmatched"],
        "warning_count": len(warnings),
        "warnings": warnings,
        "classification_notes": {
            "direct": "Exact current repo descriptor match to an EPIG subject-centric term.",
            "needs_phrase": "Current repo descriptor has subject-centric token evidence but is not an exact phrase match.",
            "reject": "Descriptor is non-subject, policy-banned, or from a non-subject garnish category.",
            "unmatched": "No subject-centric EPIG evidence; keep or change only through repo-authored review.",
        },
        "records": records,
    }


def write_report(result: dict[str, Any], output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit repo-authored garnish descriptors against local EPIG subject-centric terms.")
    parser.add_argument("--reference-root", default=str(ROOT.parent / "参考"))
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--output", default=str(ROOT / "assets" / "results" / "subject_centric_descriptor_candidates.json"))
    args = parser.parse_args(argv)

    result = audit_subject_centric_descriptors(args.repo_root, args.reference_root)
    output_path = write_report(result, args.output)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "descriptor_count": result["descriptor_count"],
                "direct_count": result["direct_count"],
                "needs_phrase_count": result["needs_phrase_count"],
                "reject_count": result["reject_count"],
                "unmatched_count": result["unmatched_count"],
                "warning_count": result["warning_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
