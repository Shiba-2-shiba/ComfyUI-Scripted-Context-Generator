from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.semantic_families import SEMANTIC_FAMILY_KEYWORDS, semantic_families_for_text  # noqa: E402
from pipeline.context_pipeline import sample_garnish_fields  # noqa: E402
from pipeline.mood_builder import DEFAULT_STAGING_TAG_LIMIT, expand_dictionary_value  # noqa: E402
from prompt_renderer import build_prompt_text  # noqa: E402


ARTIFACT_VERSION = 1
PROMPT_SOURCE_DEFAULT = "prompts.jsonl"
SAMPLES_PER_ROW_DEFAULT = 8
TOP_LIMIT = 12
SAMPLE_PREVIEW_LIMIT = 8

def _load_prompt_rows(path: Path, row_limit: int = 0) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        payload = json.loads(line)
        payload["_row_index"] = index
        rows.append(payload)
        if row_limit and len(rows) >= row_limit:
            break
    return rows


def _seed_for_sample(row_index: int, sample_index: int) -> int:
    return int(row_index) + (int(sample_index) * 1000)


def _split_tags(text: str) -> List[str]:
    return [part.strip() for part in str(text or "").split(",") if part.strip()]


def _signature_from_tags(tags: Sequence[str]) -> str:
    return " | ".join(str(tag).strip() for tag in tags if str(tag).strip())


def _tag_families(tag: str) -> Set[str]:
    return semantic_families_for_text(tag)


def _text_families(text: str) -> Set[str]:
    return semantic_families_for_text(text)


def _rows_from_counter(counter: Counter[str], key_name: str, total: int, limit: int = TOP_LIMIT) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    total = int(total)
    ordered = sorted(counter.items(), key=lambda item: (-int(item[1]), str(item[0])))
    for key, count in ordered[:limit]:
        rows.append(
            {
                key_name: key,
                "count": int(count),
                "rate": round((float(count) / float(total)) if total else 0.0, 4),
            }
        )
    return rows


def _family_rows(counter: Counter[str], total: int) -> Dict[str, Dict[str, Any]]:
    total = int(total)
    result: Dict[str, Dict[str, Any]] = {}
    for family in SEMANTIC_FAMILY_KEYWORDS:
        count = int(counter.get(family, 0))
        result[family] = {
            "count": count,
            "rate": round((float(count) / float(total)) if total else 0.0, 4),
        }
    return result


def _forced_tag_rows(counter: Counter[str], total: int) -> List[Dict[str, Any]]:
    if total <= 0:
        return []
    forced = [(tag, count) for tag, count in counter.items() if int(count) == int(total)]
    forced.sort(key=lambda item: item[0])
    return [
        {
            "tag": tag,
            "count": int(count),
            "rate": 1.0,
        }
        for tag, count in forced
    ]


def build_prompt_repetition_report(
    prompt_source_path: str = PROMPT_SOURCE_DEFAULT,
    samples_per_row: int = SAMPLES_PER_ROW_DEFAULT,
    row_limit: int = 0,
) -> Dict[str, Any]:
    prompt_source = Path(prompt_source_path)
    if not prompt_source.is_absolute():
        prompt_source = ROOT / prompt_source

    rows = _load_prompt_rows(prompt_source, row_limit=row_limit)

    staging_counter: Counter[str] = Counter()
    garnish_counter: Counter[str] = Counter()
    final_tag_counter: Counter[str] = Counter()
    description_counter: Counter[str] = Counter()
    mood_row_counter: Counter[str] = Counter()
    staging_family_counter: Counter[str] = Counter()
    garnish_family_counter: Counter[str] = Counter()
    final_family_counter: Counter[str] = Counter()
    mood_reports: Dict[str, Dict[str, Any]] = {}
    samples: List[Dict[str, Any]] = []

    for row in rows:
        mood_key = str(row.get("meta", {}).get("mood", "")).strip()
        mood_row_counter[mood_key] += 1
        mood_report = mood_reports.setdefault(
            mood_key,
            {
                "mood_key": mood_key,
                "row_count": 0,
                "sample_count": 0,
                "description_counter": Counter(),
                "staging_tag_counter": Counter(),
                "garnish_tag_counter": Counter(),
                "final_tag_counter": Counter(),
                "staging_signature_counter": Counter(),
                "garnish_signature_counter": Counter(),
                "staging_family_counter": Counter(),
                "garnish_family_counter": Counter(),
                "final_family_counter": Counter(),
            },
        )
        mood_report["row_count"] += 1

        scene_tags = row.get("meta", {}).get("tags", {}) or {}
        emotion_nuance = str(scene_tags.get("emotion_nuance", "random"))

        for sample_index in range(samples_per_row):
            seed = _seed_for_sample(int(row.get("_row_index", 0)), sample_index)
            mood_text, staging_text = expand_dictionary_value(
                mood_key,
                "mood_map.json",
                mood_key,
                seed,
                staging_tag_limit=DEFAULT_STAGING_TAG_LIMIT,
            )
            garnish_text, _debug = sample_garnish_fields(
                action_text=str(row.get("action", "")),
                meta_mood_key=mood_key,
                seed=seed,
                max_items=3,
                include_camera=False,
                emotion_nuance=emotion_nuance,
                context_loc=str(row.get("loc", "")),
                context_costume=str(row.get("costume", "")),
                scene_tags=scene_tags,
                personality="",
            )
            prompt = build_prompt_text(
                template="",
                composition_mode=True,
                seed=seed,
                subj=str(row.get("subj", "")),
                costume=str(row.get("costume", "")),
                loc=str(row.get("loc", "")),
                action=str(row.get("action", "")),
                garnish=garnish_text,
                meta_mood=mood_text,
                staging_tags=staging_text,
            )

            staging_tags = _split_tags(staging_text)
            garnish_tags = _split_tags(garnish_text)
            description_counter[mood_text] += 1
            mood_report["description_counter"][mood_text] += 1
            mood_report["sample_count"] += 1

            staging_signature = _signature_from_tags(staging_tags)
            garnish_signature = _signature_from_tags(garnish_tags)
            if staging_signature:
                mood_report["staging_signature_counter"][staging_signature] += 1
            if garnish_signature:
                mood_report["garnish_signature_counter"][garnish_signature] += 1

            staging_families_present: Set[str] = set()
            garnish_families_present: Set[str] = set()

            for tag in staging_tags:
                staging_counter[tag] += 1
                mood_report["staging_tag_counter"][tag] += 1
                staging_families_present.update(_tag_families(tag))

            for tag in garnish_tags:
                garnish_counter[tag] += 1
                mood_report["garnish_tag_counter"][tag] += 1
                garnish_families_present.update(_tag_families(tag))

            for family in staging_families_present:
                staging_family_counter[family] += 1
                mood_report["staging_family_counter"][family] += 1

            for family in garnish_families_present:
                garnish_family_counter[family] += 1
                mood_report["garnish_family_counter"][family] += 1

            prompt_lower = prompt.lower()
            current_surface_tags = {tag for tag in [*staging_tags, *garnish_tags] if tag}
            for tag in current_surface_tags:
                if tag and tag.lower() in prompt_lower:
                    final_tag_counter[tag] += 1
                    mood_report["final_tag_counter"][tag] += 1
            for family in _text_families(prompt):
                final_family_counter[family] += 1
                mood_report["final_family_counter"][family] += 1

            if len(samples) < SAMPLE_PREVIEW_LIMIT:
                samples.append(
                    {
                        "row_index": int(row.get("_row_index", 0)),
                        "sample_index": int(sample_index),
                        "seed": int(seed),
                        "mood_key": mood_key,
                        "description": mood_text,
                        "staging_tags": staging_tags,
                        "garnish_tags": garnish_tags,
                        "prompt": prompt,
                    }
                )

    total_rows = len(rows)
    total_samples = total_rows * int(samples_per_row)
    mood_entries: List[Dict[str, Any]] = []
    moods_with_single_staging_signature: List[str] = []
    moods_with_forced_staging_tags: List[str] = []

    for mood_key, data in sorted(mood_reports.items(), key=lambda item: item[0]):
        sample_count = int(data["sample_count"])
        unique_staging_signatures = len(data["staging_signature_counter"])
        forced_staging_tags = _forced_tag_rows(data["staging_tag_counter"], sample_count)
        if unique_staging_signatures == 1 and sample_count > 0:
            moods_with_single_staging_signature.append(mood_key)
        if forced_staging_tags:
            moods_with_forced_staging_tags.append(mood_key)
        mood_entries.append(
            {
                "mood_key": mood_key,
                "row_count": int(data["row_count"]),
                "sample_count": sample_count,
                "unique_description_count": len(data["description_counter"]),
                "unique_staging_signature_count": unique_staging_signatures,
                "unique_garnish_signature_count": len(data["garnish_signature_counter"]),
                "top_descriptions": _rows_from_counter(data["description_counter"], "description", sample_count, limit=5),
                "top_staging_tags": _rows_from_counter(data["staging_tag_counter"], "tag", sample_count, limit=8),
                "top_garnish_tags": _rows_from_counter(data["garnish_tag_counter"], "tag", sample_count, limit=8),
                "top_final_tags": _rows_from_counter(data["final_tag_counter"], "tag", sample_count, limit=8),
                "top_staging_signatures": _rows_from_counter(data["staging_signature_counter"], "signature", sample_count, limit=3),
                "top_garnish_signatures": _rows_from_counter(data["garnish_signature_counter"], "signature", sample_count, limit=3),
                "forced_staging_tags": forced_staging_tags,
                "staging_family_counts": _family_rows(data["staging_family_counter"], sample_count),
                "garnish_family_counts": _family_rows(data["garnish_family_counter"], sample_count),
                "final_family_counts": _family_rows(data["final_family_counter"], sample_count),
            }
        )

    summary = {
        "artifact_version": ARTIFACT_VERSION,
        "prompt_source_path": str(prompt_source),
        "runtime_staging_tag_limit": int(DEFAULT_STAGING_TAG_LIMIT),
        "row_count": total_rows,
        "samples_per_row": int(samples_per_row),
        "total_samples": total_samples,
        "unique_mood_count": len(mood_entries),
        "mood_row_counts": dict(mood_row_counter),
        "top_staging_tags": _rows_from_counter(staging_counter, "tag", total_samples),
        "top_garnish_tags": _rows_from_counter(garnish_counter, "tag", total_samples),
        "top_final_tags": _rows_from_counter(final_tag_counter, "tag", total_samples),
        "top_mood_descriptions": _rows_from_counter(description_counter, "description", total_samples),
        "staging_family_counts": _family_rows(staging_family_counter, total_samples),
        "garnish_family_counts": _family_rows(garnish_family_counter, total_samples),
        "final_family_counts": _family_rows(final_family_counter, total_samples),
        "moods_with_single_staging_signature": moods_with_single_staging_signature,
        "moods_with_forced_staging_tags": moods_with_forced_staging_tags,
    }
    return {
        "summary": summary,
        "moods": mood_entries,
        "samples": samples,
    }


def evaluate_prompt_repetition_thresholds(report: Dict[str, Any]) -> Dict[str, Any]:
    summary = report.get("summary", {}) or {}
    failures: List[Dict[str, Any]] = []

    row_count = int(summary.get("row_count", 0))
    samples_per_row = int(summary.get("samples_per_row", 0))
    total_samples = int(summary.get("total_samples", 0))
    if row_count <= 0:
        failures.append({"code": "row_count_missing", "expected_gte": 1, "actual": row_count})
    if samples_per_row <= 0:
        failures.append({"code": "samples_per_row_missing", "expected_gte": 1, "actual": samples_per_row})
    if total_samples != row_count * samples_per_row:
        failures.append(
            {
                "code": "total_samples_mismatch",
                "expected": row_count * samples_per_row,
                "actual": total_samples,
            }
        )
    if int(summary.get("unique_mood_count", 0)) <= 0:
        failures.append({"code": "unique_mood_count_missing", "expected_gte": 1, "actual": int(summary.get("unique_mood_count", 0))})
    for key in ("top_staging_tags", "top_garnish_tags", "top_final_tags"):
        if not (summary.get(key) or []):
            failures.append({"code": f"{key}_missing"})
    final_family_counts = summary.get("final_family_counts", {}) or {}
    if not any(int((payload or {}).get("count", 0)) > 0 for payload in final_family_counts.values()):
        failures.append({"code": "final_family_counts_empty"})
    if not (report.get("moods") or []):
        failures.append({"code": "mood_reports_missing"})
    if not (report.get("samples") or []):
        failures.append({"code": "sample_previews_missing"})

    return {
        "passed": not failures,
        "thresholds": {
            "min_row_count": 1,
            "min_samples_per_row": 1,
            "min_unique_mood_count": 1,
            "requires_surface_toplists": True,
            "requires_final_family_counts": True,
        },
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit repeated tags and semantic families on the active prompt source")
    parser.add_argument("--prompt-source", default=PROMPT_SOURCE_DEFAULT)
    parser.add_argument("--samples-per-row", type=int, default=SAMPLES_PER_ROW_DEFAULT)
    parser.add_argument("--row-limit", type=int, default=0)
    parser.add_argument("--output", default="")
    parser.add_argument("--enforce-thresholds", action="store_true")
    args = parser.parse_args()

    report = build_prompt_repetition_report(
        prompt_source_path=args.prompt_source,
        samples_per_row=args.samples_per_row,
        row_limit=args.row_limit,
    )
    report["threshold_evaluation"] = evaluate_prompt_repetition_thresholds(report)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    print(text)
    if args.enforce_thresholds and not report["threshold_evaluation"]["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
