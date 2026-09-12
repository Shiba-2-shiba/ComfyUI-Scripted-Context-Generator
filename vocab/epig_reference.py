"""Local reference readers for EPIG/NRC VAD audit artifacts.

These helpers intentionally do not load reference data at runtime. They are used
by audit tools that read local files under ``参考/`` and write generated reports
under ignored result directories.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Iterable

VAD_AXES = ("valence", "arousal", "dominance")


def normalize_term(value: str) -> str:
    text = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_nrc_score(value: float | str) -> float:
    numeric = float(value)
    if -1.0 <= numeric <= 1.0:
        return max(0.0, min(1.0, (numeric + 1.0) / 2.0))
    raise ValueError(f"NRC score out of -1..1 range: {value!r}")


def _clamp01(value: float | str) -> float:
    numeric = float(value)
    return max(0.0, min(1.0, numeric))


def _parse_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _clean_record(term: str, record: dict[str, Any]) -> dict[str, Any] | None:
    normalized = normalize_term(term)
    if not normalized:
        return None
    payload = dict(record)
    payload["term"] = normalized
    payload.setdefault("display_term", str(term or "").strip())
    return payload


def read_epig_subject_centric_csv(path: str | Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            term = row.get("Word", "")
            try:
                record = _clean_record(
                    term,
                    {
                        "valence": _clamp01(row.get("Valence", 0.5)),
                        "arousal": _clamp01(row.get("Arousal", 0.5)),
                        "dominance": _clamp01(row.get("Dominance", 0.5)),
                        "subject_centric": _parse_bool(row.get("subject_centric")),
                        "source": "epig_subject_centric",
                        "scale": "0..1",
                    },
                )
            except (TypeError, ValueError):
                continue
            if record is not None:
                records[record["term"]] = record
    return records


def read_nrc_vad_tsv(path: str | Path, *, normalize: bool = True, source: str = "nrc_vad") -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            term = row.get("term") or row.get("word") or ""
            try:
                values = {}
                for axis in VAD_AXES:
                    raw_value = row.get(axis)
                    if raw_value in (None, ""):
                        continue
                    values[axis] = normalize_nrc_score(raw_value) if normalize else _clamp01(raw_value)
                if not values:
                    continue
                record = _clean_record(
                    term,
                    {
                        **values,
                        "source": source,
                        "scale": "-1..1 normalized to 0..1" if normalize else "0..1",
                    },
                )
            except (TypeError, ValueError):
                continue
            if record is not None:
                records[record["term"]] = record
    return records


def read_vad_csv(path: str | Path, *, source: str = "vad_csv") -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = {str(name or "").strip().lower() for name in (reader.fieldnames or [])}
        single_axis = None
        if "val" in fieldnames:
            name = Path(path).stem.lower()
            for axis in VAD_AXES:
                if axis in name:
                    single_axis = axis
                    break
        for row in reader:
            term = row.get("word") or row.get("term") or ""
            try:
                values = {}
                if single_axis:
                    values[single_axis] = _clamp01(row.get("val", 0.5))
                else:
                    for axis in VAD_AXES:
                        raw_value = row.get(axis)
                        if raw_value in (None, ""):
                            continue
                        values[axis] = _clamp01(raw_value)
                if not values:
                    continue
                record = _clean_record(term, {**values, "source": source, "scale": "0..1"})
            except (TypeError, ValueError):
                continue
            if record is not None:
                records[record["term"]] = record
    return records


def read_emolex_csv(path: str | Path, *, source: str = "emolex") -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        emotion = Path(path).stem.lower().replace("nrc_emolex_", "")
        for row in reader:
            term = row.get("word") or row.get("term") or ""
            try:
                association = int(float(row.get("val", 0)))
            except (TypeError, ValueError):
                continue
            record = _clean_record(
                term,
                {
                    "emotion": emotion,
                    "association": association,
                    "source": source,
                    "scale": "binary",
                },
            )
            if record is not None:
                records[record["term"]] = record
    return records


def lookup_term(term: str, *sources: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    normalized = normalize_term(term)
    if not normalized:
        return None
    for source in sources:
        if not isinstance(source, dict):
            continue
        match = source.get(normalized)
        if match is not None:
            return dict(match)
    return None


def merge_reference_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        for key, value in record.items():
            if key in {"term", "display_term"}:
                merged.setdefault(key, value)
            elif key == "source":
                sources = merged.setdefault("sources", [])
                if value not in sources:
                    sources.append(value)
            elif key not in merged:
                merged[key] = value
    return merged
