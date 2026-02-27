#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bias audit runner for ThemeLocationExpander / SceneVariator pipeline.

Outputs 8 CSV files:
  - audit_run_meta.csv
  - audit_location_distribution.csv
  - audit_object_distribution.csv
  - audit_object_rate_by_location.csv
  - audit_cooccurrence.csv
  - audit_stage_sampling.csv
  - audit_data_quality.csv
  - audit_alerts.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nodes_dictionary_expand import ThemeLocationExpander  # noqa: E402
from nodes_pack_parser import PackParser  # noqa: E402
from nodes_scene_variator import SceneVariator  # noqa: E402
from vocab.seed_utils import mix_seed  # noqa: E402
import background_vocab  # noqa: E402


KEYWORD_RULE_VERSION = "object_norm_v1_20260227"
OBJECT_RULES: Dict[str, List[str]] = {
    "surfboard": [r"\bsurfboard\b", r"\bboard\b"],
    "book": [r"\bbook\b", r"\bbooks\b", r"\bnotebook\b", r"\bnovel\b", r"\btextbook\b"],
    "phone": [r"\bphone\b", r"\bsmartphone\b", r"\bmobile\b"],
    "coffee": [r"\bcoffee\b", r"\blatte\b", r"\bespresso\b", r"\bcappuccino\b"],
    "drink": [r"\bdrink\b", r"\bdrinks\b", r"\bbeverage\b", r"\bsipping\b"],
    "microphone": [r"\bmicrophone\b", r"\bmic\b"],
    "screen": [r"\bscreen\b", r"\bmonitor\b", r"\bdisplay\b"],
}


@dataclass
class SampleRow:
    seed: int
    subj: str
    input_loc: str
    input_loc_tag: str
    selected_loc: str
    selected_source: str
    selected_action: str
    action_pool_loc: str
    selected_pack_key: str
    props_included: int
    props_count: int
    selected_props: List[str]
    location_prompt: str
    objects_bg_norm: List[str]
    objects_action_norm: List[str]
    objects_final_norm: List[str]
    objects_final_raw: Dict[str, str]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: List[Dict[str, Any]], headers: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(headers), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def entropy_from_counts(counts: Iterable[int]) -> float:
    values = [c for c in counts if c > 0]
    total = sum(values)
    if total == 0:
        return 0.0
    ent = 0.0
    for c in values:
        p = c / total
        ent -= p * math.log2(p)
    return ent


def detect_objects(text: str) -> Tuple[List[str], Dict[str, str]]:
    s = (text or "").lower()
    detected: List[str] = []
    raw_map: Dict[str, str] = {}
    for norm, patterns in OBJECT_RULES.items():
        for pat in patterns:
            m = re.search(pat, s)
            if m:
                detected.append(norm)
                raw_map[norm] = m.group(0)
                break
    detected = sorted(set(detected))
    return detected, raw_map


def _simulate_location_expand(
    loc_tag: str,
    seed: int,
    mode: str,
    lighting_mode: str,
) -> Dict[str, Any]:
    rng = random.Random(mix_seed(seed, "loc"))
    cleaned_tag = (loc_tag or "").lower().strip()

    pack_candidates = background_vocab.LOC_TAG_MAP.get(cleaned_tag)
    if not pack_candidates:
        return {
            "pack_candidates": [],
            "selected_pack_key": cleaned_tag,
            "props_included": 0,
            "selected_props": [],
            "final_prompt": loc_tag,
        }

    selected_pack_key = rng.choice(pack_candidates)
    pack_data = background_vocab.CONCEPT_PACKS.get(selected_pack_key)
    if not pack_data:
        return {
            "pack_candidates": pack_candidates,
            "selected_pack_key": selected_pack_key,
            "props_included": 0,
            "selected_props": [],
            "final_prompt": loc_tag,
        }

    env_options = pack_data.get("environment", [])
    env_part = rng.choice(env_options) if env_options else cleaned_tag

    if mode == "simple":
        return {
            "pack_candidates": pack_candidates,
            "selected_pack_key": selected_pack_key,
            "props_included": 0,
            "selected_props": [],
            "final_prompt": env_part,
        }

    segments: List[str] = []
    selected_props: List[str] = []
    props_included = 0

    core_opts = pack_data.get("core", [])
    if core_opts and rng.random() < 0.95:
        num_core = 2 if len(core_opts) > 1 and rng.random() < 0.50 else 1
        chosen_core = rng.sample(core_opts, k=min(num_core, len(core_opts)))
        if len(chosen_core) == 1:
            segments.append(f"featuring {chosen_core[0]}")
        else:
            connector = rng.choice(["and", "plus", "featuring"])
            segments.append(f"featuring {chosen_core[0]} {connector} {chosen_core[1]}")

    props_opts = pack_data.get("props", [])
    if props_opts and rng.random() < 0.8:
        props_included = 1
        num_props = 2 if len(props_opts) > 1 and rng.random() < 0.45 else 1
        selected_props = rng.sample(props_opts, k=min(num_props, len(props_opts)))
        connector_word = rng.choice(["with", "scattered with", "filled with", "adorned with"])
        if len(selected_props) == 1:
            segments.append(f"{connector_word} {selected_props[0]}")
        else:
            joiner = rng.choice(["and", "plus", "as well as"])
            segments.append(f"{connector_word} {selected_props[0]} {joiner} {selected_props[1]}")

    texture_opts = pack_data.get("texture", []) or []
    texture_candidates = list(texture_opts)
    general_defaults = getattr(background_vocab, "GENERAL_DEFAULTS", {})
    texture_candidates.extend(general_defaults.get("texture", []))
    if texture_candidates and rng.random() < 0.7:
        segments.append(rng.choice(texture_candidates))

    if rng.random() < 0.50:
        details_defaults = general_defaults.get("details", [])
        if details_defaults:
            segments.append(rng.choice(details_defaults))

    time_opts = pack_data.get("time", [])
    if time_opts and rng.random() < 0.5:
        segments.append(f"during {rng.choice(time_opts)}")

    fx_opts = pack_data.get("fx", []) or []
    fx_candidates = list(fx_opts)
    fx_candidates.extend(general_defaults.get("fx", []))
    if fx_candidates and rng.random() < 0.7:
        segments.append(rng.choice(fx_candidates))

    rng.shuffle(segments)

    if lighting_mode == "auto":
        lighting_opts = pack_data.get("lighting", [])
        if lighting_opts:
            segments.append(rng.choice(lighting_opts))

    final_prompt = ", ".join([env_part] + segments) if segments else env_part
    return {
        "pack_candidates": pack_candidates,
        "selected_pack_key": selected_pack_key,
        "props_included": props_included,
        "selected_props": selected_props,
        "final_prompt": final_prompt,
    }


def choose_loc_tag_input(loc_key: str, input_mode: str, seed: int) -> str:
    if input_mode == "canonical":
        return loc_key
    aliases = background_vocab.CONCEPT_PACKS.get(loc_key, {}).get("aliases", [])
    if input_mode == "alias":
        if aliases:
            rng = random.Random(mix_seed(seed, "audit_alias"))
            return rng.choice(aliases)
        return loc_key
    rng = random.Random(mix_seed(seed, "audit_mixed"))
    if aliases and rng.random() < 0.5:
        return rng.choice(aliases)
    return loc_key


def generate_samples(
    sample_count: int,
    seed_start: int,
    variation_mode: str,
    location_mode: str,
    lighting_mode: str,
    input_mode: str,
) -> List[SampleRow]:
    parser = PackParser()
    scene = SceneVariator()
    loc_exp = ThemeLocationExpander()

    rows: List[SampleRow] = []

    for i in range(sample_count):
        seed = seed_start + i
        subj, costume, loc, action, _, _, _ = parser.parse("{}", seed)

        subj2, _, selected_loc, selected_action, debug_info = scene.variate(
            subj, costume, loc, action, seed, variation_mode
        )
        decision = debug_info.get("decision", {}) if isinstance(debug_info, dict) else {}
        selected_source = str(decision.get("selected_source", "original"))
        action_pool_loc = selected_loc if (selected_loc != loc and decision.get("action_updated")) else ""

        exp_input = choose_loc_tag_input(selected_loc, input_mode, seed)
        sim = _simulate_location_expand(exp_input, seed, location_mode, lighting_mode)
        loc_prompt = loc_exp.expand_location(exp_input, seed, location_mode, lighting_mode)[0]
        sim["final_prompt"] = loc_prompt

        obj_bg, _ = detect_objects(loc_prompt)
        obj_action, _ = detect_objects(selected_action)
        obj_final, raw_map = detect_objects(f"{loc_prompt}, {selected_action}")

        rows.append(
            SampleRow(
                seed=seed,
                subj=subj2,
                input_loc=loc,
                input_loc_tag=exp_input,
                selected_loc=selected_loc,
                selected_source=selected_source,
                selected_action=selected_action,
                action_pool_loc=action_pool_loc,
                selected_pack_key=str(sim["selected_pack_key"]),
                props_included=int(sim["props_included"]),
                props_count=len(sim["selected_props"]),
                selected_props=[str(x) for x in sim["selected_props"]],
                location_prompt=loc_prompt,
                objects_bg_norm=obj_bg,
                objects_action_norm=obj_action,
                objects_final_norm=obj_final,
                objects_final_raw=raw_map,
            )
        )
    return rows


def build_location_distribution_rows(run_id: str, samples: List[SampleRow]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    group = defaultdict(list)
    for s in samples:
        group[s.input_loc_tag].append(s)
    for cond, items in sorted(group.items()):
        cnt = Counter(x.selected_pack_key for x in items)
        n = len(items)
        ent = entropy_from_counts(cnt.values())
        ranked = cnt.most_common()
        for rank, (name, c) in enumerate(ranked, start=1):
            rows.append(
                {
                    "run_id": run_id,
                    "scope": "theme_location",
                    "input_condition_key": "loc_tag",
                    "input_condition_value": cond,
                    "entity_type": "location",
                    "entity_name": name,
                    "count": c,
                    "rate": round(c / n, 6),
                    "rank": rank,
                    "top1_flag": 1 if rank == 1 else 0,
                    "source_breakdown": "",
                    "entropy_group": round(ent, 6),
                    "remarks": "",
                }
            )

    group = defaultdict(list)
    for s in samples:
        group[s.subj].append(s)
    for cond, items in sorted(group.items()):
        cnt = Counter(x.selected_loc for x in items)
        src = Counter(
            "tag" if x.selected_source.startswith("tag:") else x.selected_source for x in items
        )
        n = len(items)
        ent = entropy_from_counts(cnt.values())
        ranked = cnt.most_common()
        src_text = f"existing={src.get('existing',0)};tag={src.get('tag',0)};universal={src.get('universal',0)}"
        for rank, (name, c) in enumerate(ranked, start=1):
            rows.append(
                {
                    "run_id": run_id,
                    "scope": "scene_variator",
                    "input_condition_key": "subj",
                    "input_condition_value": cond,
                    "entity_type": "location",
                    "entity_name": name,
                    "count": c,
                    "rate": round(c / n, 6),
                    "rank": rank,
                    "top1_flag": 1 if rank == 1 else 0,
                    "source_breakdown": src_text,
                    "entropy_group": round(ent, 6),
                    "remarks": "",
                }
            )

    cnt = Counter(s.selected_loc for s in samples)
    n = len(samples)
    ent = entropy_from_counts(cnt.values())
    for rank, (name, c) in enumerate(cnt.most_common(), start=1):
        rows.append(
            {
                "run_id": run_id,
                "scope": "final_prompt",
                "input_condition_key": "all",
                "input_condition_value": "all",
                "entity_type": "location",
                "entity_name": name,
                "count": c,
                "rate": round(c / n, 6),
                "rank": rank,
                "top1_flag": 1 if rank == 1 else 0,
                "source_breakdown": "",
                "entropy_group": round(ent, 6),
                "remarks": "",
            }
        )
    return rows


def _aggregate_object_rows(
    run_id: str,
    scope: str,
    stage: str,
    samples: List[SampleRow],
    token_getter,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    conditions: List[Tuple[str, str, List[SampleRow]]] = [("all", "all", samples)]

    by_loc = defaultdict(list)
    by_subj = defaultdict(list)
    for s in samples:
        by_loc[s.selected_loc].append(s)
        by_subj[s.subj].append(s)
    for key, items in by_loc.items():
        conditions.append(("loc", key, items))
    for key, items in by_subj.items():
        conditions.append(("subj", key, items))

    for cond_key, cond_val, items in conditions:
        n = len(items)
        if n == 0:
            continue
        count_by_norm: Counter = Counter()
        raw_by_norm: Dict[str, Counter] = defaultdict(Counter)
        locs_by_norm: Dict[str, set] = defaultdict(set)
        for s in items:
            norms, raw_map = token_getter(s)
            for norm in norms:
                count_by_norm[norm] += 1
                raw_by_norm[norm][raw_map.get(norm, norm)] += 1
                locs_by_norm[norm].add(s.selected_loc)

        for rank, (norm, c) in enumerate(count_by_norm.most_common(), start=1):
            raw_token = raw_by_norm[norm].most_common(1)[0][0]
            rows.append(
                {
                    "run_id": run_id,
                    "scope": scope,
                    "stage": stage,
                    "input_condition_key": cond_key,
                    "input_condition_value": cond_val,
                    "entity_type": "object",
                    "raw_token": raw_token,
                    "normalized_token": norm,
                    "count": c,
                    "rate": round(c / n, 6),
                    "unique_locs": len(locs_by_norm[norm]),
                    "rank": rank,
                    "keyword_rule_version": KEYWORD_RULE_VERSION,
                    "remarks": "",
                }
            )
    return rows


def build_object_distribution_rows(run_id: str, samples: List[SampleRow]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    rows.extend(
        _aggregate_object_rows(
            run_id,
            "background",
            "props",
            samples,
            lambda s: (s.objects_bg_norm, {k: v for k, v in s.objects_final_raw.items() if k in s.objects_bg_norm}),
        )
    )
    rows.extend(
        _aggregate_object_rows(
            run_id,
            "action",
            "action_text",
            samples,
            lambda s: (
                s.objects_action_norm,
                {k: v for k, v in s.objects_final_raw.items() if k in s.objects_action_norm},
            ),
        )
    )
    rows.extend(
        _aggregate_object_rows(
            run_id,
            "final_prompt",
            "combined",
            samples,
            lambda s: (s.objects_final_norm, s.objects_final_raw),
        )
    )
    return rows


def build_object_rate_by_location_rows(run_id: str, samples: List[SampleRow]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    by_loc = defaultdict(list)
    for s in samples:
        by_loc[s.selected_loc].append(s)

    scopes = [
        ("background", lambda s: s.objects_bg_norm),
        ("action", lambda s: s.objects_action_norm),
        ("final_prompt", lambda s: s.objects_final_norm),
    ]
    for scope, getter in scopes:
        for loc, items in sorted(by_loc.items()):
            n = len(items)
            cnt: Counter = Counter()
            top_action_for_token: Dict[str, Counter] = defaultdict(Counter)
            for s in items:
                for token in getter(s):
                    cnt[token] += 1
                    top_action_for_token[token][s.selected_action] += 1
            for rank, (token, hits) in enumerate(cnt.most_common(), start=1):
                top_action = top_action_for_token[token].most_common(1)[0][0]
                rows.append(
                    {
                        "run_id": run_id,
                        "scope": scope,
                        "location_name": loc,
                        "object_token": token,
                        "count_location_samples": n,
                        "count_object_hits": hits,
                        "conditional_rate": round(hits / n, 6),
                        "rank_in_location": rank,
                        "top_cooccurring_action": top_action,
                        "remarks": "",
                    }
                )
    return rows


def build_cooccurrence_rows(run_id: str, samples: List[SampleRow]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    n = len(samples)
    if n == 0:
        return rows

    loc_count = Counter(s.selected_loc for s in samples)
    obj_count = Counter()
    pair_count = Counter()
    for s in samples:
        uniq_tokens = set(s.objects_final_norm)
        for token in uniq_tokens:
            obj_count[token] += 1
            pair_count[(s.selected_loc, token)] += 1

    for (loc, token), c in pair_count.most_common():
        p_xy = c / n
        p_x = loc_count[loc] / n
        p_y = obj_count[token] / n
        denom = p_x + p_y - p_xy
        jaccard = (p_xy / denom) if denom > 0 else 0.0
        pmi_like = math.log2((p_xy / (p_x * p_y))) if p_x > 0 and p_y > 0 and p_xy > 0 else 0.0
        rows.append(
            {
                "run_id": run_id,
                "scope": "final_prompt",
                "left_type": "location",
                "left_name": loc,
                "right_type": "object",
                "right_name": token,
                "count": c,
                "rate": round(p_xy, 6),
                "jaccard": round(jaccard, 6),
                "pmi_like": round(pmi_like, 6),
                "input_condition_key": "all",
                "input_condition_value": "all",
                "remarks": "",
            }
        )
    return rows


def build_stage_sampling_rows(run_id: str, samples: List[SampleRow]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for s in samples:
        rows.append(
            {
                "run_id": run_id,
                "seed": s.seed,
                "subj": s.subj,
                "input_loc": s.input_loc,
                "input_loc_tag": s.input_loc_tag,
                "selected_pack_key": s.selected_pack_key,
                "selected_loc": s.selected_loc,
                "selected_source": s.selected_source,
                "props_included": s.props_included,
                "props_count": s.props_count,
                "selected_props": "|".join(s.selected_props),
                "action_pool_loc": s.action_pool_loc,
                "selected_action": s.selected_action,
                "objects_detected_final": "|".join(sorted(set(s.objects_final_norm))),
            }
        )
    return rows


def build_data_quality_rows(run_id: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    data_dir = ROOT / "vocab" / "data"
    sc = json.loads((data_dir / "scene_compatibility.json").read_text(encoding="utf-8"))
    bg = json.loads((data_dir / "background_packs.json").read_text(encoding="utf-8"))
    ap = json.loads((data_dir / "action_pools.json").read_text(encoding="utf-8"))

    ctr = Counter(sc.get("universal_locs", []))
    for item, c in ctr.items():
        if c > 1:
            rows.append(
                {
                    "run_id": run_id,
                    "file_name": "scene_compatibility.json",
                    "entity_scope": "universal_locs",
                    "parent_key": "universal_locs",
                    "field_name": "universal_locs",
                    "item_value": item,
                    "issue_type": "duplicate_in_list",
                    "duplicate_count": c,
                    "severity": "high",
                    "remarks": "duplicates increase effective weight in SceneVariator",
                }
            )

    for tag, arr in sc.get("loc_tags", {}).items():
        ctr = Counter(arr)
        for item, c in ctr.items():
            if c > 1:
                rows.append(
                    {
                        "run_id": run_id,
                        "file_name": "scene_compatibility.json",
                        "entity_scope": "loc_tags",
                        "parent_key": tag,
                        "field_name": "loc_tags",
                        "item_value": item,
                        "issue_type": "duplicate_in_list",
                        "duplicate_count": c,
                        "severity": "high",
                        "remarks": "duplicates increase effective weight in SceneVariator",
                    }
                )

    for loc, info in bg.items():
        props = [x for x in info.get("props", []) if isinstance(x, str)]
        if 0 < len(props) <= 3:
            rows.append(
                {
                    "run_id": run_id,
                    "file_name": "background_packs.json",
                    "entity_scope": "background_props",
                    "parent_key": loc,
                    "field_name": "props",
                    "item_value": f"size={len(props)}",
                    "issue_type": "small_pool",
                    "duplicate_count": "",
                    "severity": "high" if len(props) <= 2 else "medium",
                    "remarks": "small props pool can amplify object repetition",
                }
            )

    for loc, items in ap.items():
        if loc.startswith("_") or loc == "schema_version":
            continue
        texts = []
        for it in items:
            t = it.get("text", "") if isinstance(it, dict) else str(it)
            if isinstance(t, str) and not t.startswith("_"):
                texts.append(t)
        if 0 < len(texts) <= 4:
            rows.append(
                {
                    "run_id": run_id,
                    "file_name": "action_pools.json",
                    "entity_scope": "action_pools",
                    "parent_key": loc,
                    "field_name": "actions",
                    "item_value": f"size={len(texts)}",
                    "issue_type": "small_pool",
                    "duplicate_count": "",
                    "severity": "high" if len(texts) <= 3 else "medium",
                    "remarks": "small action pool can amplify wording/object repetition",
                }
            )
        if len(texts) >= 4:
            hit_counter = Counter()
            for t in texts:
                norms, _ = detect_objects(t)
                for n in norms:
                    hit_counter[n] += 1
            for token, c in hit_counter.items():
                share = c / len(texts)
                if share >= 0.5:
                    rows.append(
                        {
                            "run_id": run_id,
                            "file_name": "action_pools.json",
                            "entity_scope": "action_pools",
                            "parent_key": loc,
                            "field_name": "actions",
                            "item_value": token,
                            "issue_type": "high_object_concentration",
                            "duplicate_count": "",
                            "severity": "high" if share >= 0.66 else "medium",
                            "remarks": f"object appears in {c}/{len(texts)} action lines",
                        }
                    )
    return rows


def build_alert_rows(
    run_id: str,
    location_rows: List[Dict[str, Any]],
    object_rows: List[Dict[str, Any]],
    object_rate_rows: List[Dict[str, Any]],
    data_quality_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    by_group = defaultdict(list)
    for r in location_rows:
        by_group[(r["scope"], r["input_condition_key"], r["input_condition_value"])].append(r)
        if float(r["rate"]) > 0.30:
            rows.append(
                {
                    "run_id": run_id,
                    "alert_type": "high_location_bias",
                    "scope": r["scope"],
                    "input_condition_key": r["input_condition_key"],
                    "input_condition_value": r["input_condition_value"],
                    "target_name": r["entity_name"],
                    "metric_name": "rate",
                    "metric_value": r["rate"],
                    "threshold": 0.30,
                    "triggered": 1,
                    "severity": "high" if float(r["rate"]) > 0.40 else "medium",
                    "remarks": "",
                }
            )
    for (scope, key, value), grp in by_group.items():
        top3 = sum(float(x["rate"]) for x in sorted(grp, key=lambda x: float(x["rate"]), reverse=True)[:3])
        if top3 > 0.60:
            rows.append(
                {
                    "run_id": run_id,
                    "alert_type": "high_location_bias",
                    "scope": scope,
                    "input_condition_key": key,
                    "input_condition_value": value,
                    "target_name": "top3",
                    "metric_name": "top3_share",
                    "metric_value": round(top3, 6),
                    "threshold": 0.60,
                    "triggered": 1,
                    "severity": "medium",
                    "remarks": "",
                }
            )

    for r in object_rows:
        if (
            r["scope"] == "final_prompt"
            and r["input_condition_key"] == "all"
            and float(r["rate"]) > 0.20
        ):
            rows.append(
                {
                    "run_id": run_id,
                    "alert_type": "high_object_bias",
                    "scope": "final_prompt",
                    "input_condition_key": "all",
                    "input_condition_value": "all",
                    "target_name": r["normalized_token"],
                    "metric_name": "rate",
                    "metric_value": r["rate"],
                    "threshold": 0.20,
                    "triggered": 1,
                    "severity": "high" if float(r["rate"]) > 0.30 else "medium",
                    "remarks": "",
                }
            )

    for r in object_rate_rows:
        if float(r["conditional_rate"]) > 0.40:
            rows.append(
                {
                    "run_id": run_id,
                    "alert_type": "high_object_bias",
                    "scope": r["scope"],
                    "input_condition_key": "location_name",
                    "input_condition_value": r["location_name"],
                    "target_name": r["object_token"],
                    "metric_name": "conditional_rate",
                    "metric_value": r["conditional_rate"],
                    "threshold": 0.40,
                    "triggered": 1,
                    "severity": "high" if float(r["conditional_rate"]) > 0.60 else "medium",
                    "remarks": "",
                }
            )

    for r in data_quality_rows:
        if r["issue_type"] == "duplicate_in_list":
            rows.append(
                {
                    "run_id": run_id,
                    "alert_type": "duplicate_weighting",
                    "scope": "data_quality",
                    "input_condition_key": r["entity_scope"],
                    "input_condition_value": r["parent_key"],
                    "target_name": r["item_value"],
                    "metric_name": "dup_count",
                    "metric_value": r.get("duplicate_count", 2),
                    "threshold": 1,
                    "triggered": 1,
                    "severity": r.get("severity", "high"),
                    "remarks": r.get("remarks", ""),
                }
            )
    return rows


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run bias audit and emit CSV suite")
    ap.add_argument("--sample-count", type=int, default=1000)
    ap.add_argument("--seed-start", type=int, default=0)
    ap.add_argument("--variation-mode", default="full", choices=["original", "genre_only", "full"])
    ap.add_argument("--location-mode", default="detailed", choices=["detailed", "simple"])
    ap.add_argument("--lighting-mode", default="auto", choices=["auto", "off"])
    ap.add_argument("--input-mode", default="canonical", choices=["canonical", "alias", "mixed"])
    ap.add_argument("--pipeline-scope", default="final_prompt")
    ap.add_argument("--target-scope", default="full_audit")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--output-dir", default="assets/results/audit")
    ap.add_argument("--notes", default="")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_date = datetime.now().strftime("%Y-%m-%d")
    seed_end = args.seed_start + args.sample_count - 1

    out_dir = Path(args.output_dir) / run_id
    ensure_dir(out_dir)

    samples = generate_samples(
        sample_count=args.sample_count,
        seed_start=args.seed_start,
        variation_mode=args.variation_mode,
        location_mode=args.location_mode,
        lighting_mode=args.lighting_mode,
        input_mode=args.input_mode,
    )

    location_rows = build_location_distribution_rows(run_id, samples)
    object_rows = build_object_distribution_rows(run_id, samples)
    object_rate_rows = build_object_rate_by_location_rows(run_id, samples)
    cooccur_rows = build_cooccurrence_rows(run_id, samples)
    stage_rows = build_stage_sampling_rows(run_id, samples)
    data_quality_rows = build_data_quality_rows(run_id)
    alert_rows = build_alert_rows(run_id, location_rows, object_rows, object_rate_rows, data_quality_rows)

    run_meta_rows = [
        {
            "run_id": run_id,
            "run_date": run_date,
            "sample_count": args.sample_count,
            "seed_start": args.seed_start,
            "seed_end": seed_end,
            "pipeline_scope": args.pipeline_scope,
            "variation_mode": args.variation_mode,
            "location_mode": args.location_mode,
            "lighting_mode": args.lighting_mode,
            "input_mode": args.input_mode,
            "target_scope": args.target_scope,
            "notes": args.notes,
        }
    ]

    write_csv(
        out_dir / "audit_run_meta.csv",
        run_meta_rows,
        [
            "run_id",
            "run_date",
            "sample_count",
            "seed_start",
            "seed_end",
            "pipeline_scope",
            "variation_mode",
            "location_mode",
            "lighting_mode",
            "input_mode",
            "target_scope",
            "notes",
        ],
    )
    write_csv(
        out_dir / "audit_location_distribution.csv",
        location_rows,
        [
            "run_id",
            "scope",
            "input_condition_key",
            "input_condition_value",
            "entity_type",
            "entity_name",
            "count",
            "rate",
            "rank",
            "top1_flag",
            "source_breakdown",
            "entropy_group",
            "remarks",
        ],
    )
    write_csv(
        out_dir / "audit_object_distribution.csv",
        object_rows,
        [
            "run_id",
            "scope",
            "stage",
            "input_condition_key",
            "input_condition_value",
            "entity_type",
            "raw_token",
            "normalized_token",
            "count",
            "rate",
            "unique_locs",
            "rank",
            "keyword_rule_version",
            "remarks",
        ],
    )
    write_csv(
        out_dir / "audit_object_rate_by_location.csv",
        object_rate_rows,
        [
            "run_id",
            "scope",
            "location_name",
            "object_token",
            "count_location_samples",
            "count_object_hits",
            "conditional_rate",
            "rank_in_location",
            "top_cooccurring_action",
            "remarks",
        ],
    )
    write_csv(
        out_dir / "audit_cooccurrence.csv",
        cooccur_rows,
        [
            "run_id",
            "scope",
            "left_type",
            "left_name",
            "right_type",
            "right_name",
            "count",
            "rate",
            "jaccard",
            "pmi_like",
            "input_condition_key",
            "input_condition_value",
            "remarks",
        ],
    )
    write_csv(
        out_dir / "audit_stage_sampling.csv",
        stage_rows,
        [
            "run_id",
            "seed",
            "subj",
            "input_loc",
            "input_loc_tag",
            "selected_pack_key",
            "selected_loc",
            "selected_source",
            "props_included",
            "props_count",
            "selected_props",
            "action_pool_loc",
            "selected_action",
            "objects_detected_final",
        ],
    )
    write_csv(
        out_dir / "audit_data_quality.csv",
        data_quality_rows,
        [
            "run_id",
            "file_name",
            "entity_scope",
            "parent_key",
            "field_name",
            "item_value",
            "issue_type",
            "duplicate_count",
            "severity",
            "remarks",
        ],
    )
    write_csv(
        out_dir / "audit_alerts.csv",
        alert_rows,
        [
            "run_id",
            "alert_type",
            "scope",
            "input_condition_key",
            "input_condition_value",
            "target_name",
            "metric_name",
            "metric_value",
            "threshold",
            "triggered",
            "severity",
            "remarks",
        ],
    )

    print(f"[OK] audit complete: {out_dir}")
    print(f"  samples={len(samples)} variation_mode={args.variation_mode} location_mode={args.location_mode}")
    print(f"  alerts={len(alert_rows)} data_quality_issues={len(data_quality_rows)}")


if __name__ == "__main__":
    main()
