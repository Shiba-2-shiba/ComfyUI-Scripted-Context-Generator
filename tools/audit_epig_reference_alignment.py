from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.semantic_policy import find_banned_term_matches  # noqa: E402
from tools.extract_epig_reference_overlay import collect_current_vocabulary, load_reference_sources  # noqa: E402
from vocab.epig_reference import lookup_term, normalize_term  # noqa: E402


def _distance(left: dict[str, Any], right: dict[str, Any], axes: tuple[str, ...] = ("valence", "arousal")) -> float | None:
    deltas = []
    for axis in axes:
        if axis not in left or axis not in right:
            continue
        try:
            deltas.append(float(left[axis]) - float(right[axis]))
        except (TypeError, ValueError):
            continue
    if not deltas:
        return None
    return math.sqrt(sum(delta * delta for delta in deltas) / len(deltas))


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


def _load_emotion_profiles(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "vocab" / "data" / "emotion_vad_profiles.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_json(repo_root: Path, relative_path: str) -> dict[str, Any]:
    path = repo_root / relative_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _align_emotion_profiles(profiles: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
    categories = profiles.get("categories", {}) if isinstance(profiles, dict) else {}
    nuances = profiles.get("nuances", {}) if isinstance(profiles, dict) else {}
    records = []
    for group_name, group in (("category", categories), ("nuance", nuances)):
        if not isinstance(group, dict):
            continue
        for name, payload in sorted(group.items()):
            if isinstance(payload, dict):
                vad = payload.get("vad", [])
                aliases = payload.get("aliases", [])
            else:
                vad = payload
                aliases = []
            current = {}
            if isinstance(vad, list) and len(vad) >= 2:
                current = {"valence": vad[0], "arousal": vad[1]}
            terms = [str(name)]
            if isinstance(aliases, list):
                terms.extend(str(alias) for alias in aliases)
            matches = []
            seen = set()
            for term in terms:
                for match in _reference_matches(term, sources):
                    key = (normalize_term(term), match.get("source"))
                    if key in seen:
                        continue
                    seen.add(key)
                    entry = {
                        "lookup_term": normalize_term(term),
                        "source": match.get("source", ""),
                        "valence": match.get("valence"),
                        "arousal": match.get("arousal"),
                        "dominance": match.get("dominance"),
                        "emotion": match.get("emotion"),
                        "association": match.get("association"),
                    }
                    dist = _distance(current, match)
                    if dist is not None:
                        entry["distance"] = round(dist, 4)
                    matches.append(entry)
            records.append(
                {
                    "type": group_name,
                    "name": str(name),
                    "current_vad": current,
                    "match_count": len(matches),
                    "matches": matches[:8],
                }
            )
    return {
        "record_count": len(records),
        "matched_count": sum(1 for record in records if record["match_count"] > 0),
        "records": records,
    }


def _match_descriptor(text: str, sources: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    exact = _reference_matches(text, sources)
    if exact:
        return "exact", exact
    token_matches = []
    for token in normalize_term(text).split():
        if len(token) < 3:
            continue
        for match in _reference_matches(token, sources):
            token_matches.append({"token": token, "reference": match})
    if token_matches:
        return "token_fallback", token_matches
    return "none", []


def _personality_descriptor_coverage(repo_root: Path, sources: list[dict[str, Any]]) -> dict[str, Any]:
    payload = _load_json(repo_root, "vocab/data/personality_behavior_profiles.json")
    descriptors = payload.get("descriptors", {}) if isinstance(payload, dict) else {}
    records = []
    if isinstance(descriptors, dict):
        for slot, items in sorted(descriptors.items()):
            if not isinstance(items, list):
                continue
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                match_type, matches = _match_descriptor(text, sources)
                records.append(
                    {
                        "slot": str(slot),
                        "index": index,
                        "text": text,
                        "match_type": match_type,
                        "match_count": len(matches),
                        "matches": matches[:6],
                    }
                )
    return {
        "descriptor_count": len(records),
        "exact_match_count": sum(1 for record in records if record["match_type"] == "exact"),
        "token_fallback_count": sum(1 for record in records if record["match_type"] == "token_fallback"),
        "unmatched_count": sum(1 for record in records if record["match_type"] == "none"),
        "records": records,
    }


def _subject_centric_counts(vocabulary: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
    epig_records = {}
    for source in sources:
        if source.get("name") == "epig_subject_centric":
            epig_records = source.get("records", {})
            break
    subject_terms = [term for term, record in epig_records.items() if bool(record.get("subject_centric"))]
    non_subject_terms = [term for term, record in epig_records.items() if not bool(record.get("subject_centric"))]
    exact_subject_matches = []
    exact_non_subject_matches = []
    for term, payload in vocabulary.items():
        record = epig_records.get(term)
        if record is None:
            continue
        item = {"term": term, "occurrences": payload.get("occurrences", [])[:4]}
        if bool(record.get("subject_centric")):
            exact_subject_matches.append(item)
        else:
            exact_non_subject_matches.append(item)
    return {
        "epig_record_count": len(epig_records),
        "subject_centric_record_count": len(subject_terms),
        "non_subject_centric_record_count": len(non_subject_terms),
        "current_vocab_exact_subject_match_count": len(exact_subject_matches),
        "current_vocab_exact_non_subject_match_count": len(exact_non_subject_matches),
        "subject_match_preview": exact_subject_matches[:20],
        "non_subject_match_preview": exact_non_subject_matches[:20],
    }


def _llm_prompt_policy_scan(reference_root: Path) -> dict[str, Any]:
    path = reference_root / "EPIG" / "data" / "llm_expanded_prompts.csv"
    if not path.exists():
        return {"available": False, "row_count": 0, "policy_issue_count": 0, "domain_counts": {}, "examples": []}
    row_count = 0
    domain_counts: dict[str, int] = {}
    examples = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_count += 1
                prompt = str(row.get("expanded_prompt", "") or "")
                hits = find_banned_term_matches(prompt, ignore_hyphenated_body_type=True)
                if not hits:
                    continue
                compact_hits = [{"domain": domain, "term": term} for domain, term in hits]
                for domain, _term in hits:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
                if len(examples) < 12:
                    examples.append(
                        {
                            "base_prompt": row.get("base_prompt", ""),
                            "emotion": row.get("emotion", ""),
                            "hits": compact_hits,
                        }
                    )
    except (OSError, csv.Error) as exc:
        return {"available": True, "error": str(exc), "row_count": row_count, "policy_issue_count": sum(domain_counts.values()), "domain_counts": domain_counts, "examples": examples}
    return {
        "available": True,
        "row_count": row_count,
        "policy_issue_count": sum(domain_counts.values()),
        "domain_counts": dict(sorted(domain_counts.items())),
        "examples": examples,
    }


def _availability(reference_root: Path, sources: list[dict[str, Any]], warnings: list[dict[str, str]]) -> dict[str, Any]:
    lexicons_html = reference_root / "lexicons.html"
    emotion_dynamics = reference_root / "EmotionDynamics"
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
        "lexicons_html": lexicons_html.exists(),
        "optional_lexicons": {
            "worrywords_available": any(path.exists() for path in worry_candidates),
            "words_of_warmth_available": any(path.exists() for path in warmth_candidates),
        },
        "emotiondynamics": {
            "root": emotion_dynamics.exists(),
            "readme": (emotion_dynamics / "README.md").exists(),
            "ued": (emotion_dynamics / "code" / "uedLib" / "lib" / "ued.py").exists(),
            "combined_vad": (emotion_dynamics / "code" / "uedLib" / "lexicons" / "NRC-VAD-Lexicon.csv").exists(),
            "emolex_file_count": len(list((emotion_dynamics / "lexicons").glob("NRC_EmoLex_*.csv"))),
            "vad_file_count": len(list((emotion_dynamics / "lexicons").glob("NRC_VAD_*.csv"))),
        },
        "source_count": len(sources),
        "loaded_record_count": sum(len(source.get("records", {})) for source in sources),
        "warning_count": len(warnings),
        "warnings": warnings,
    }


def audit_reference_alignment(repo_root: str | Path = ROOT, reference_root: str | Path | None = None) -> dict[str, Any]:
    repo_path = Path(repo_root)
    ref_path = Path(reference_root) if reference_root is not None else repo_path.parent / "参考"
    sources, warnings = load_reference_sources(ref_path)
    vocabulary = collect_current_vocabulary(repo_path)
    profiles = _load_emotion_profiles(repo_path)
    alignment = _align_emotion_profiles(profiles, sources)
    matched_terms = sum(1 for term in vocabulary if _reference_matches(term, sources))
    return {
        "schema_version": "1.0",
        "generated_kind": "reference_alignment_audit",
        "availability": _availability(ref_path, sources, warnings),
        "current_vocabulary": {
            "extracted_term_count": len(vocabulary),
            "exact_reference_match_count": matched_terms,
        },
        "emotion_profile_alignment": alignment,
        "personality_descriptor_coverage": _personality_descriptor_coverage(repo_path, sources),
        "subject_centric_summary": _subject_centric_counts(vocabulary, sources),
        "llm_expanded_prompt_policy_scan": _llm_prompt_policy_scan(ref_path),
        "policy": {
            "reference_scores_are_local_only": True,
            "do_not_commit_generated_score_overlays_by_default": True,
        },
    }


def write_audit(result: dict[str, Any], output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit current EPIG/VAD configuration against local reference sources.")
    parser.add_argument("--reference-root", default=str(ROOT.parent / "参考"))
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--output", default=str(ROOT / "assets" / "results" / "epig_reference_alignment.json"))
    args = parser.parse_args(argv)

    result = audit_reference_alignment(args.repo_root, args.reference_root)
    output_path = write_audit(result, args.output)
    print(json.dumps({
        "output": str(output_path),
        "source_count": result["availability"]["source_count"],
        "emotion_profile_matched_count": result["emotion_profile_alignment"]["matched_count"],
        "exact_reference_match_count": result["current_vocabulary"]["exact_reference_match_count"],
        "warning_count": result["availability"]["warning_count"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
