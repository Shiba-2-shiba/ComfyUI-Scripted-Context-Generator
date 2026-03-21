from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Sequence


ROOT_DIR = Path(__file__).resolve().parents[1]
POLICY_TERMS_PATH = ROOT_DIR / "vocab" / "data" / "policy_terms.json"
REQUIRED_POLICY_DOMAINS = (
    "style",
    "quality",
    "camera",
    "render",
    "body_type",
)


def load_policy_terms_payload() -> dict:
    payload = json.loads(POLICY_TERMS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("policy_terms.json must be a JSON object")

    domains = payload.get("domains")
    if not isinstance(domains, dict):
        raise ValueError("policy_terms.json must contain a 'domains' object")

    normalized_domains: Dict[str, tuple[str, ...]] = {}
    for domain in REQUIRED_POLICY_DOMAINS:
        terms = domains.get(domain)
        if not isinstance(terms, list):
            raise ValueError(f"policy_terms.json domain '{domain}' must be a list")
        normalized_terms = tuple(
            term_text
            for term_text in (str(term).strip() for term in terms)
            if term_text
        )
        if not normalized_terms:
            raise ValueError(f"policy_terms.json domain '{domain}' must not be empty")
        normalized_domains[domain] = normalized_terms

    return {
        "version": int(payload.get("version", 1) or 1),
        "domains": normalized_domains,
    }


POLICY_TERMS_PAYLOAD = load_policy_terms_payload()
POLICY_SCHEMA_VERSION = POLICY_TERMS_PAYLOAD["version"]
BANNED_DOMAIN_TERMS: Dict[str, Sequence[str]] = POLICY_TERMS_PAYLOAD["domains"]

_COMPILED_PATTERNS = {
    domain: [
        (
            term,
            re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE),
        )
        for term in sorted(terms, key=len, reverse=True)
    ]
    for domain, terms in BANNED_DOMAIN_TERMS.items()
}


def normalize_fragment_text(text: str, *, strip_chars: str = "") -> str:
    if not text:
        return ""

    cleaned = str(text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"\.\s*\.+", ".", cleaned)
    cleaned = re.sub(r",\s*\.", ".", cleaned)
    cleaned = ", ".join(part.strip() for part in cleaned.split(",") if part.strip(" ,"))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if strip_chars:
        cleaned = cleaned.strip(strip_chars)
    return cleaned


def remove_dangling_fragment_terms(
    text: str,
    *,
    terms: Sequence[str] = ("with", "and", "plus"),
    strip_chars: str = " ,.;:",
) -> str:
    if not text:
        return ""

    pattern = "|".join(re.escape(str(term)) for term in terms if str(term).strip())
    if not pattern:
        return normalize_fragment_text(text, strip_chars=strip_chars)

    cleaned = re.sub(
        rf"(?:^|,\s*)(?:{pattern})\s*(?=,|$)",
        "",
        str(text),
        flags=re.IGNORECASE,
    )
    return normalize_fragment_text(cleaned, strip_chars=strip_chars)


def find_banned_term_matches(
    text: str,
    *,
    ignore_hyphenated_body_type: bool = False,
) -> List[tuple[str, str]]:
    if not text:
        return []

    source = str(text)
    hits: List[tuple[str, str]] = []
    seen = set()

    for domain, compiled_patterns in _COMPILED_PATTERNS.items():
        for term, pattern in compiled_patterns:
            for match in pattern.finditer(source):
                before = source[match.start() - 1] if match.start() > 0 else ""
                after = source[match.end()] if match.end() < len(source) else ""
                if ignore_hyphenated_body_type and term in {"slim", "petite"} and (before == "-" or after == "-"):
                    continue
                key = (domain, term)
                if key in seen:
                    continue
                seen.add(key)
                hits.append(key)

    return hits


def find_banned_terms(text: str) -> Dict[str, List[str]]:
    if not text:
        return {}
    hits: Dict[str, List[str]] = {}
    for domain, term in find_banned_term_matches(text):
        hits.setdefault(domain, []).append(term)
    return hits


def contains_banned_terms(text: str) -> bool:
    return bool(find_banned_terms(text))


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = remove_banned_terms(text)
    return remove_dangling_fragment_terms(cleaned)


def remove_banned_terms(text: str) -> str:
    if not text:
        return ""
    cleaned = str(text)
    for patterns in _COMPILED_PATTERNS.values():
        for _term, pattern in patterns:
            cleaned = pattern.sub("", cleaned)
    return normalize_fragment_text(cleaned)


def filter_candidate_strings(values: Iterable[str]) -> List[str]:
    filtered: List[str] = []
    for value in values:
        text = sanitize_text(value)
        if not text or contains_banned_terms(text):
            continue
        filtered.append(text)
    return filtered


def sanitize_sequence(values: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        text = sanitize_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
