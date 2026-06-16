from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.semantic_policy import REQUIRED_POLICY_DOMAINS, find_banned_term_matches  # noqa: E402


def _empty_domain_counts() -> dict[str, int]:
    return {domain: 0 for domain in REQUIRED_POLICY_DOMAINS}


def _compact_hits(hits: list[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"domain": domain, "term": term} for domain, term in hits]


def scan_llm_expanded_prompts(reference_root: str | Path) -> dict[str, Any]:
    ref_path = Path(reference_root)
    path = ref_path / "EPIG" / "data" / "llm_expanded_prompts.csv"
    domain_counts = _empty_domain_counts()
    term_counts: dict[str, dict[str, int]] = {domain: {} for domain in REQUIRED_POLICY_DOMAINS}
    examples = []
    row_count = 0
    rows_with_policy_issues = 0
    policy_issue_count = 0

    if not path.exists():
        return {
            "schema_version": "1.0",
            "generated_kind": "llm_expanded_prompt_policy_audit",
            "tracked_policy": "generated_local_only",
            "available": False,
            "path": str(path),
            "row_count": 0,
            "rows_with_policy_issues": 0,
            "policy_issue_count": 0,
            "domain_counts": domain_counts,
            "term_counts": term_counts,
            "examples": [],
            "policy": {
                "negative_corpus_only": True,
                "runtime_prompt_source": False,
                "raw_reference_rows_not_tracked": True,
            },
        }

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_count += 1
                prompt = str(row.get("expanded_prompt", "") or "")
                hits = find_banned_term_matches(prompt, ignore_hyphenated_body_type=True)
                if not hits:
                    continue
                rows_with_policy_issues += 1
                policy_issue_count += len(hits)
                for domain, term in hits:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
                    domain_terms = term_counts.setdefault(domain, {})
                    domain_terms[term] = domain_terms.get(term, 0) + 1
                if len(examples) < 20:
                    examples.append(
                        {
                            "row": row_count,
                            "base_prompt": row.get("base_prompt", ""),
                            "emotion": row.get("emotion", ""),
                            "hits": _compact_hits(hits),
                        }
                    )
    except (OSError, csv.Error) as exc:
        return {
            "schema_version": "1.0",
            "generated_kind": "llm_expanded_prompt_policy_audit",
            "tracked_policy": "generated_local_only",
            "available": True,
            "path": str(path),
            "error": str(exc),
            "row_count": row_count,
            "rows_with_policy_issues": rows_with_policy_issues,
            "policy_issue_count": policy_issue_count,
            "domain_counts": dict(sorted(domain_counts.items())),
            "term_counts": {domain: dict(sorted(terms.items())) for domain, terms in sorted(term_counts.items())},
            "examples": examples,
            "policy": {
                "negative_corpus_only": True,
                "runtime_prompt_source": False,
                "raw_reference_rows_not_tracked": True,
            },
        }

    return {
        "schema_version": "1.0",
        "generated_kind": "llm_expanded_prompt_policy_audit",
        "tracked_policy": "generated_local_only",
        "available": True,
        "path": str(path),
        "row_count": row_count,
        "rows_with_policy_issues": rows_with_policy_issues,
        "policy_issue_count": policy_issue_count,
        "domain_counts": dict(sorted(domain_counts.items())),
        "term_counts": {domain: dict(sorted(terms.items())) for domain, terms in sorted(term_counts.items())},
        "examples": examples,
        "policy": {
            "negative_corpus_only": True,
            "runtime_prompt_source": False,
            "raw_reference_rows_not_tracked": True,
        },
    }


def write_audit(result: dict[str, Any], output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan EPIG LLM expanded prompts as a semantic-only negative corpus.")
    parser.add_argument("--reference-root", default=str(ROOT.parent / "参考"))
    parser.add_argument("--output", default=str(ROOT / "assets" / "results" / "llm_expanded_prompt_policy_audit.json"))
    args = parser.parse_args(argv)

    result = scan_llm_expanded_prompts(args.reference_root)
    output_path = write_audit(result, args.output)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "available": result["available"],
                "row_count": result["row_count"],
                "rows_with_policy_issues": result["rows_with_policy_issues"],
                "policy_issue_count": result["policy_issue_count"],
                "domain_counts": result["domain_counts"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
