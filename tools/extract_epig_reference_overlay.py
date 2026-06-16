from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vocab.epig_reference import (  # noqa: E402
    lookup_term,
    normalize_term,
    read_emolex_csv,
    read_epig_subject_centric_csv,
    read_nrc_vad_tsv,
    read_vad_csv,
)


STOPWORDS = {
    "the",
    "and",
    "with",
    "for",
    "from",
    "into",
    "near",
    "over",
    "under",
    "while",
    "where",
    "that",
    "this",
    "her",
    "his",
    "their",
    "she",
    "he",
    "they",
    "you",
    "your",
    "a",
    "an",
    "of",
    "in",
    "on",
    "to",
    "by",
    "at",
    "as",
}


def _add_term(terms: dict[str, dict[str, Any]], text: str, source: str, path: str, kind: str) -> None:
    normalized = normalize_term(text)
    if not normalized:
        return
    words = normalized.split()
    if len(normalized) > 96 or len(words) > 10:
        return
    if len(words) == 1 and (len(normalized) < 3 or normalized in STOPWORDS):
        return
    entry = terms.setdefault(normalized, {"term": normalized, "occurrences": []})
    occurrence = {"source": source, "path": path, "kind": kind}
    if occurrence not in entry["occurrences"]:
        entry["occurrences"].append(occurrence)


def _segments(text: str) -> list[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    pieces = [raw]
    pieces.extend(part.strip() for part in re.split(r"[,;|/()\[\]{}]", raw) if part.strip())
    return pieces


def _add_text_terms(terms: dict[str, dict[str, Any]], text: str, source: str, path: str) -> None:
    for segment in _segments(text):
        _add_term(terms, segment, source, path, "phrase")
        for token in normalize_term(segment).split():
            _add_term(terms, token, source, path, "token")


def _iter_json_strings(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_json_strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_json_strings(item, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def _collect_json_terms(root: Path, terms: dict[str, dict[str, Any]]) -> None:
    patterns = [
        "vocab/data/*.json",
        "vocab/source/action_pools/*.json",
    ]
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            rel = path.relative_to(root).as_posix()
            for json_path, text in _iter_json_strings(payload):
                _add_text_terms(terms, text, rel, json_path)


def _collect_python_string_terms(root: Path, terms: dict[str, dict[str, Any]]) -> None:
    for path in sorted((root / "vocab" / "garnish").glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                _add_text_terms(terms, node.value, rel, f"line:{getattr(node, 'lineno', 0)}")


def collect_current_vocabulary(root: str | Path = ROOT) -> dict[str, dict[str, Any]]:
    root_path = Path(root)
    terms: dict[str, dict[str, Any]] = {}
    _collect_json_terms(root_path, terms)
    _collect_python_string_terms(root_path, terms)
    return dict(sorted(terms.items()))


def _load_source(name: str, path: Path, loader, warnings: list[dict[str, str]], **kwargs) -> dict[str, Any]:
    if not path.exists():
        warnings.append({"source": name, "path": str(path), "warning": "missing"})
        return {"name": name, "path": str(path), "records": {}}
    try:
        records = loader(path, source=name, **kwargs)
    except TypeError:
        try:
            records = loader(path)
        except (OSError, ValueError) as exc:
            warnings.append({"source": name, "path": str(path), "warning": str(exc)})
            records = {}
    except (OSError, ValueError) as exc:
        warnings.append({"source": name, "path": str(path), "warning": str(exc)})
        records = {}
    return {"name": name, "path": str(path), "records": records}


def load_reference_sources(reference_root: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    ref = Path(reference_root)
    warnings: list[dict[str, str]] = []
    sources: list[dict[str, Any]] = []

    sources.append(
        _load_source(
            "epig_subject_centric",
            ref / "EPIG" / "data" / "NRC_VAD_with_subject_centric.csv",
            read_epig_subject_centric_csv,
            warnings,
        )
    )
    nrc_base = ref / "NRC-VAD-Lexicon-v2.1" / "NRC-VAD-Lexicon-v2.1"
    sources.append(
        _load_source(
            "nrc_vad_v2_1",
            nrc_base / "NRC-VAD-Lexicon-v2.1.txt",
            read_nrc_vad_tsv,
            warnings,
            normalize=True,
        )
    )
    sources.append(
        _load_source(
            "nrc_vad_v2_1_mwe",
            nrc_base / "MWE" / "mwe-NRC-VAD-Lexicon-v2.1.txt",
            read_nrc_vad_tsv,
            warnings,
            normalize=True,
        )
    )
    ed_base = ref / "EmotionDynamics"
    sources.append(
        _load_source(
            "emotiondynamics_vad_combined",
            ed_base / "code" / "uedLib" / "lexicons" / "NRC-VAD-Lexicon.csv",
            read_vad_csv,
            warnings,
        )
    )
    for path in sorted((ed_base / "lexicons").glob("NRC_VAD_*.csv")):
        sources.append(_load_source(f"emotiondynamics_{path.stem.lower()}", path, read_vad_csv, warnings))
    for path in sorted((ed_base / "lexicons").glob("NRC_EmoLex_*.csv")):
        sources.append(_load_source(f"emotiondynamics_{path.stem.lower()}", path, read_emolex_csv, warnings))

    return sources, warnings


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


def build_overlay(vocabulary: dict[str, dict[str, Any]], sources: list[dict[str, Any]], warnings: list[dict[str, str]] | None = None) -> dict[str, Any]:
    matched: dict[str, dict[str, Any]] = {}
    unmatched_count = 0
    for term, payload in sorted(vocabulary.items()):
        exact_matches = _reference_matches(term, sources)
        if exact_matches:
            matched[term] = {
                "term": term,
                "match_type": "exact",
                "occurrences": payload.get("occurrences", []),
                "references": exact_matches,
            }
            continue

        token_matches = []
        if " " in term:
            for token in term.split():
                if token in STOPWORDS or len(token) < 3:
                    continue
                for match in _reference_matches(token, sources):
                    token_matches.append({"token": token, "reference": match})
        if token_matches:
            matched[term] = {
                "term": term,
                "match_type": "token_fallback",
                "occurrences": payload.get("occurrences", []),
                "token_references": token_matches,
            }
        else:
            unmatched_count += 1

    return {
        "schema_version": "1.0",
        "generated_kind": "local_reference_overlay",
        "tracked_policy": "do_not_commit_by_default",
        "extracted_term_count": len(vocabulary),
        "matched_term_count": len(matched),
        "unmatched_term_count": unmatched_count,
        "source_count": len(sources),
        "warnings": list(warnings or []),
        "matches": matched,
    }


def write_overlay(overlay: dict[str, Any], output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(overlay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract current repo vocabulary and match it to local EPIG/NRC references.")
    parser.add_argument("--reference-root", default=str(ROOT.parent / "参考"))
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--output", default=str(ROOT / "assets" / "results" / "epig_reference_overlay.local.json"))
    args = parser.parse_args(argv)

    vocabulary = collect_current_vocabulary(args.repo_root)
    sources, warnings = load_reference_sources(args.reference_root)
    overlay = build_overlay(vocabulary, sources, warnings)
    output_path = write_overlay(overlay, args.output)
    print(json.dumps({
        "output": str(output_path),
        "extracted_term_count": overlay["extracted_term_count"],
        "matched_term_count": overlay["matched_term_count"],
        "warning_count": len(overlay["warnings"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
