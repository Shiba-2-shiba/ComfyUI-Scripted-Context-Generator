"""Pure calculations for effective-diversity-audit/v1 (spec sections 6.3–6.6).

Signatures and categories are already canonical projections supplied by the
caller. None denotes an invalid signature or unknown category, not a novel value.
Sequence-sensitive metrics consume caller order; workflow/seed validation and
sorting belong to the audit runner. No generation or source-data reads occur here.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import math
import re
from typing import Any
import unicodedata

from pipeline.prompt_realizer import normalize_subject_to_girl
from tools.workflow_prompt_runner import canonical_json_bytes


Signature = Mapping[str, Any] | None
AxisValue = str | Sequence[str] | None
_PUNCTUATION_TRANSLATION = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-",
})


def metric_prefixes(sample_count: int) -> list[int]:
    """Include only available standard prefixes plus the actual sample count."""
    if type(sample_count) is not int or sample_count < 0:
        raise ValueError("sample_count must be a non-negative integer")
    return sorted({n for n in (128, 512, 2048, 8192) if n <= sample_count} | {sample_count})


def normalize_prompt(prompt: str) -> str:
    """Apply effective-diversity-normalization/v1 without removing repeated words."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("cleaned_prompt must be a non-blank string")
    text = unicodedata.normalize("NFC", prompt).lower().translate(_PUNCTUATION_TRANSLATION)
    # The runtime helper also collapses "girl girl". Applying it token by token
    # reuses its aliases while preserving token multiplicity in this audit.
    text = re.sub(r"\b\w+\b", lambda match: normalize_subject_to_girl(match.group()), text)
    text = re.sub(r"[.,;:!?]+", " ", text)
    return " ".join(text.split())


def semantic_uniqueness(signatures: Sequence[Signature]) -> dict[str, Any]:
    """Count prevalidated signatures; the caller supplies None for invalid ones."""
    unique = set()
    valid_count = 0
    for signature in signatures:
        if signature is None:
            continue
        if not isinstance(signature, Mapping):
            raise ValueError("signature must be a canonical mapping or None")
        unique.add(canonical_json_bytes(dict(signature)))
        valid_count += 1
    count = len(signatures)
    return {
        "sample_count": count,
        "valid_count": valid_count,
        "missing_count": count - valid_count,
        "unique_count": len(unique),
        "rate": round(len(unique) / count, 6) if count else 0.0,
    }


def _category(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("category must be a non-blank canonical string")
    return value


def axis_coverage(values: Sequence[AxisValue], reference_values: Sequence[str]) -> dict[str, Any]:
    """Measure reference intersection, preserving unknown versus known-empty."""
    reference = {_category(value) for value in reference_values}
    observed: set[str] = set()
    missing_count = 0
    for value in values:
        if value is None:
            missing_count += 1
        elif isinstance(value, str):
            observed.add(_category(value))
        elif isinstance(value, Sequence):
            observed.update(_category(item) for item in value)
        else:
            raise ValueError("axis value must be a category, category sequence, or None")
    covered_count = len(observed & reference)
    return {
        "observed_unique_count": len(observed),
        "covered_unique_count": covered_count,
        "reference_count": len(reference),
        "missing_count": missing_count,
        "out_of_reference_values": sorted(observed - reference),
        "rate": round(covered_count / len(reference), 6) if reference else None,
    }


def max_consecutive_run(families: Sequence[str | None]) -> int:
    """Return the longest run in supplied order; unknown values break runs."""
    longest = current = 0
    previous = None
    for family in families:
        if family is None:
            current = 0
        else:
            _category(family)
            current = current + 1 if family == previous else 1
            longest = max(longest, current)
        previous = family
    return longest


def syntax_entropy(families: Sequence[str | None], active_families: Sequence[str]) -> dict[str, Any]:
    """Shannon entropy over observations, normalized by declared active families."""
    counts = dict.fromkeys(sorted({_category(family) for family in active_families}), 0)
    observed = Counter(_category(family) for family in families if family is not None)
    if observed.keys() - counts.keys():
        raise ValueError("observed syntax family is not declared active")
    counts.update(observed)
    valid_count = sum(counts.values())
    active_count = len(counts)
    entropy = 0.0
    for count in counts.values():
        if count:
            probability = count / valid_count
            entropy -= probability * math.log2(probability)
    return {
        "sample_count": len(families),
        "valid_count": valid_count,
        "missing_count": len(families) - valid_count,
        "active_family_count": active_count,
        "family_counts": counts,
        "raw_entropy": round(entropy, 6),
        "normalized_entropy": round(entropy / math.log2(active_count), 6) if active_count > 1 else 0.0,
        "dominant_family_share": round(max(counts.values()) / valid_count, 6) if valid_count else 0.0,
    }


def repetition_metrics(
    cleaned_prompts: Sequence[str],
    core_signatures: Sequence[Signature],
    frame_signatures: Sequence[Signature],
    action_families: Sequence[str | None],
    syntax_families: Sequence[str | None],
) -> dict[str, Any]:
    """Count occurrences after the first, retaining missing semantic samples in N."""
    count = len(cleaned_prompts)
    if any(len(values) != count for values in (core_signatures, frame_signatures, action_families, syntax_families)):
        raise ValueError("all metric sequences must have the same sample count")
    normalized_prompts = {normalize_prompt(prompt) for prompt in cleaned_prompts}
    core = semantic_uniqueness(core_signatures)
    frame = semantic_uniqueness(frame_signatures)
    return {
        "sample_count": count,
        "exact_prompt_duplicate_rate": round((count - len(set(cleaned_prompts))) / count, 6) if count else 0.0,
        "normalized_prompt_duplicate_rate": round((count - len(normalized_prompts)) / count, 6) if count else 0.0,
        "semantic_core_duplicate_rate": round((core["valid_count"] - core["unique_count"]) / count, 6) if count else 0.0,
        "semantic_frame_duplicate_rate": round((frame["valid_count"] - frame["unique_count"]) / count, 6) if count else 0.0,
        "max_consecutive_same_action_family": max_consecutive_run(action_families),
        "max_consecutive_same_syntax_family": max_consecutive_run(syntax_families),
    }
