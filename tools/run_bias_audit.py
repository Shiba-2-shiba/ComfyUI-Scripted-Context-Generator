#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bias audit runner for shared location expansion / context scene-stage pipeline.

Outputs CSV files including:
  - audit_run_meta.csv
  - audit_location_distribution.csv
  - audit_object_distribution.csv
  - audit_object_rate_by_location.csv
  - audit_cooccurrence.csv
  - audit_stage_sampling.csv
  - audit_prompt_quality.csv
  - audit_quality_metrics.csv
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

from core.context_ops import patch_context  # noqa: E402
from nodes_prompt_cleaner import PromptCleaner  # noqa: E402
from pipeline.content_pipeline import build_prompt_text, expand_clothing_prompt, expand_dictionary_value, expand_location_prompt  # noqa: E402
from pipeline.context_pipeline import apply_scene_variation, sample_garnish_fields  # noqa: E402
from pipeline.source_pipeline import parse_prompt_source_fields  # noqa: E402
from vocab.garnish.logic import _has_physical_expression  # noqa: E402
from vocab.seed_utils import mix_seed  # noqa: E402
import background_vocab  # noqa: E402


KEYWORD_RULE_VERSION = "object_norm_v2_20260306"
DEFAULT_GENERATION_MODE = "scene_emotion_priority"
DAILY_LIFE_SHARE_TARGET_MIN = 0.60
DAILY_LIFE_SHARE_TARGET_MAX = 0.75
OBJECT_RULES: Dict[str, Dict[str, List[str]]] = {
    "surfboard": {
        "include": [r"\bsurfboard\b"],
        "exclude": [],
    },
    "book": {
        "include": [r"\bbook\b", r"\bbooks\b", r"\bnotebook\b", r"\bnovel\b", r"\btextbook\b"],
        "exclude": [],
    },
    "phone": {
        "include": [r"\bphone\b", r"\bsmartphone\b", r"\bmobile\b"],
        "exclude": [],
    },
    "coffee": {
        "include": [r"\bcoffee\b", r"\blatte\b", r"\bespresso\b", r"\bcappuccino\b"],
        "exclude": [],
    },
    "drink": {
        "include": [r"\bdrink\b", r"\bdrinks\b", r"\bbeverage\b", r"\bsipping\b"],
        "exclude": [],
    },
    "microphone": {
        "include": [r"\bmicrophone\b", r"\bmic\b"],
        "exclude": [],
    },
    "screen": {
        "include": [r"\bscreen\b", r"\bmonitor\b", r"\bdisplay\b"],
        "exclude": [],
    },
}

BROAD_SCENE_PRIORITY = [
    "fantasy",
    "scifi",
    "nature",
    "music",
    "sport",
    "craft",
    "steampunk",
    "luxury",
]
ABSTRACT_STYLE_PATTERNS: Dict[str, re.Pattern[str]] = {
    "anime_style": re.compile(r"\banime(?:\s+style|\s+illustration)?\b", re.IGNORECASE),
    "illustration": re.compile(r"\billustration\b", re.IGNORECASE),
    "photographic": re.compile(r"\bphotographic\b|\bphotoreal(?:istic)?\b", re.IGNORECASE),
    "cinematic": re.compile(r"\bcinematic\b", re.IGNORECASE),
    "masterpiece": re.compile(r"\bmasterpiece\b", re.IGNORECASE),
    "best_quality": re.compile(r"\bbest quality\b", re.IGNORECASE),
    "high_quality": re.compile(r"\bhigh quality\b", re.IGNORECASE),
    "ultra_detailed": re.compile(r"\bultra detailed\b", re.IGNORECASE),
    "stylized": re.compile(r"\bstylized\b", re.IGNORECASE),
    "render": re.compile(r"\brender(?:ed|ing)?\b", re.IGNORECASE),
}
UNWANTED_NOUN_PATTERNS: Dict[str, re.Pattern[str]] = {
    "imaginary": re.compile(r"\bimaginary\b", re.IGNORECASE),
    "trash": re.compile(r"\btrash\b", re.IGNORECASE),
    "debris": re.compile(r"\bdebris\b", re.IGNORECASE),
    "garbage": re.compile(r"\bgarbage\b", re.IGNORECASE),
    "rubbish": re.compile(r"\brubbish\b", re.IGNORECASE),
}
UNWANTED_NOUN_EXCEPTION_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"\bbackstreet\b", re.IGNORECASE),
    re.compile(r"\balleyway\b", re.IGNORECASE),
    re.compile(r"\bbattlefield\b", re.IGNORECASE),
    re.compile(r"\bcrashed spaceship\b", re.IGNORECASE),
    re.compile(r"\bruined\b", re.IGNORECASE),
    re.compile(r"\bwrecked\b", re.IGNORECASE),
)
UNWANTED_NOUN_EXCEPTION_LOCS = {
    "rainy_alley",
    "burning_battlefield",
    "alien_planet",
}

_object_policy_cache: Dict[str, Any] | None = None


@dataclass
class SampleRow:
    seed: int
    subj: str
    costume_key: str
    costume_prompt: str
    input_loc: str
    input_loc_tag: str
    selected_loc: str
    broad_scene: str
    is_daily_life: int
    selected_source: str
    selected_action: str
    action_pool_loc: str
    selected_pack_key: str
    props_included: int
    props_count: int
    selected_props: List[str]
    meta_mood_key: str
    meta_mood_text: str
    garnish: str
    emotion_embodied: int
    abstract_style_hits: List[str]
    unwanted_noun_hits: List[str]
    disallowed_fx_hits: List[str]
    location_prompt: str
    raw_prompt: str
    final_prompt: str
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


def load_object_concentration_policy() -> Dict[str, Any]:
    global _object_policy_cache
    if _object_policy_cache is None:
        path = ROOT / "vocab" / "data" / "object_concentration_policy.json"
        if not path.exists():
            _object_policy_cache = {}
        else:
            _object_policy_cache = json.loads(path.read_text(encoding="utf-8"))
    return _object_policy_cache


def get_policy_threshold(name: str, default: float) -> float:
    policy = load_object_concentration_policy()
    thresholds = policy.get("thresholds", {})
    try:
        return float(thresholds.get(name, default))
    except (TypeError, ValueError):
        return float(default)


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


def _normalized_exclude_phrases(norm: str) -> List[str]:
    policy = load_object_concentration_policy()
    normalization = policy.get("audit_normalization", {}).get(norm, {})
    phrases = normalization.get("exclude_phrases", [])
    return [str(phrase).lower() for phrase in phrases]


def _match_object_rule(text: str, norm: str) -> str:
    lowered = (text or "").lower()
    for phrase in _normalized_exclude_phrases(norm):
        if phrase and phrase in lowered:
            return ""

    rule = OBJECT_RULES.get(norm, {})
    for pat in rule.get("exclude", []):
        if re.search(pat, lowered):
            return ""
    for pat in rule.get("include", []):
        m = re.search(pat, lowered)
        if m:
            return m.group(0)
    return ""


def detect_objects(text: str) -> Tuple[List[str], Dict[str, str]]:
    detected: List[str] = []
    raw_map: Dict[str, str] = {}
    for norm in OBJECT_RULES:
        match_text = _match_object_rule(text, norm)
        if match_text:
            detected.append(norm)
            raw_map[norm] = match_text
    detected = sorted(set(detected))
    return detected, raw_map


def classify_object_hotspot(location_name: str, object_token: str) -> str:
    policy = load_object_concentration_policy()
    loc = str(location_name)
    token = str(object_token)
    if token in policy.get("audit_artifact", {}).get(loc, []):
        return "audit_artifact"
    if token in policy.get("true_bias_background", {}).get(loc, []):
        return "true_bias_background"
    if token in policy.get("true_bias_action", {}).get(loc, []):
        return "true_bias_action"
    if token in policy.get("thematic_anchor", {}).get(loc, {}):
        return "thematic_anchor"
    return "general"


def get_effective_object_threshold(location_name: str, object_token: str) -> float:
    policy = load_object_concentration_policy()
    classification = classify_object_hotspot(location_name, object_token)
    if classification == "thematic_anchor":
        anchor_policy = policy.get("thematic_anchor", {}).get(str(location_name), {}).get(str(object_token), {})
        try:
            return float(anchor_policy.get("threshold", get_policy_threshold("anchor_conditional_rate", 0.60)))
        except (TypeError, ValueError):
            return get_policy_threshold("anchor_conditional_rate", 0.60)
    return get_policy_threshold("default_conditional_rate", 0.40)


def detect_pattern_hits(text: str, pattern_map: Dict[str, re.Pattern[str]]) -> List[str]:
    s = text or ""
    return [name for name, pat in pattern_map.items() if pat.search(s)]


def load_scene_compatibility() -> Dict[str, Any]:
    path = ROOT / "vocab" / "data" / "scene_compatibility.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_loc_tags(loc: str, compat: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    for tag, locs in compat.get("loc_tags", {}).items():
        if loc in locs:
            tags.append(tag)
    return tags


def is_daily_life_loc(loc: str, compat: Dict[str, Any]) -> bool:
    if loc in set(compat.get("daily_life_locs", [])):
        return True
    daily_tags = set(compat.get("daily_life_tags", []))
    return bool(daily_tags.intersection(get_loc_tags(loc, compat)))


def infer_broad_scene(loc: str, compat: Dict[str, Any]) -> str:
    tags = get_loc_tags(loc, compat)
    if is_daily_life_loc(loc, compat):
        return "daily_life"
    for tag in BROAD_SCENE_PRIORITY:
        if tag in tags:
            return tag
    if tags:
        return sorted(tags)[0]
    return "other"


def detect_disallowed_fx_hits(text: str, cleaner: PromptCleaner) -> List[str]:
    s = text or ""
    hits: List[str] = []
    for pat in cleaner.fx_deny_patterns:
        match = pat.search(s)
        if match:
            hits.append(match.group(0).lower())
    return sorted(set(hits))


def detect_unwanted_noun_hits(text: str, is_daily_life: bool, selected_loc: str = "") -> List[str]:
    raw_hits = detect_pattern_hits(text, UNWANTED_NOUN_PATTERNS)
    has_exception_context = (
        selected_loc in UNWANTED_NOUN_EXCEPTION_LOCS
        or any(p.search(text or "") for p in UNWANTED_NOUN_EXCEPTION_PATTERNS)
    )
    filtered: List[str] = []
    for hit in raw_hits:
        if hit == "imaginary":
            filtered.append(hit)
            continue
        if is_daily_life and not has_exception_context:
            filtered.append(hit)
    return filtered


def has_emotion_embodiment(prompt_text: str, garnish_text: str) -> bool:
    garnish_tags = [part.strip() for part in (garnish_text or "").split(",") if part.strip()]
    if garnish_tags and _has_physical_expression(garnish_tags):
        return True
    prompt_lower = (prompt_text or "").lower()
    physical_hints = (
        "eyes",
        "gaze",
        "smile",
        "mouth",
        "jaw",
        "brow",
        "shoulders",
        "hands",
        "fingers",
        "posture",
        "stance",
        "breathing",
        "leaning",
        "glance",
        "lips",
    )
    return any(hint in prompt_lower for hint in physical_hints)


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
    cleaner = PromptCleaner()
    compat = load_scene_compatibility()

    rows: List[SampleRow] = []

    for i in range(sample_count):
        seed = seed_start + i
        subj, costume, loc, action, meta_mood_key, meta_style, scene_tags = parse_prompt_source_fields("{}", seed)

        scene_context = patch_context(
            {},
            updates={"subj": subj, "costume": costume, "loc": loc, "action": action, "seed": seed},
        )
        scene_context, debug_info = apply_scene_variation(scene_context, seed, variation_mode)
        subj2 = scene_context.subj
        costume2 = scene_context.costume
        selected_loc = scene_context.loc
        selected_action = scene_context.action
        debug_info = debug_info.to_dict()
        decision = debug_info.get("decision", {}) if isinstance(debug_info, dict) else {}
        selected_source = str(decision.get("selected_source", "original"))
        action_pool_loc = selected_loc if (selected_loc != loc and decision.get("action_updated")) else ""

        broad_scene = infer_broad_scene(selected_loc, compat)
        daily_life_flag = 1 if is_daily_life_loc(selected_loc, compat) else 0

        exp_input = choose_loc_tag_input(selected_loc, input_mode, seed)
        sim = _simulate_location_expand(exp_input, seed, location_mode, lighting_mode)
        loc_prompt = expand_location_prompt(exp_input, seed, location_mode, lighting_mode)
        sim["final_prompt"] = loc_prompt
        costume_prompt = expand_clothing_prompt(costume2, seed, "random", 0.3, "")
        meta_mood_text = expand_dictionary_value(meta_mood_key, "mood_map.json", meta_mood_key, seed)[0]
        garnish_text, garnish_debug = sample_garnish_fields(
            action_text=selected_action,
            meta_mood_key=meta_mood_key,
            seed=seed,
            max_items=3,
            include_camera=False,
            context_loc=selected_loc,
            context_costume=costume2,
            scene_tags=scene_tags,
            personality="",
        )
        raw_prompt = build_prompt_text(
            template="",
            composition_mode=True,
            seed=seed,
            subj=subj2,
            costume=costume_prompt,
            loc=loc_prompt,
            action=selected_action,
            garnish=garnish_text,
            meta_mood=meta_mood_text,
            meta_style=meta_style,
        )
        final_prompt = cleaner.clean(mode="nl", drop_empty_lines=True, text=raw_prompt)[0]

        obj_bg, _ = detect_objects(loc_prompt)
        obj_action, _ = detect_objects(selected_action)
        obj_final, raw_map = detect_objects(final_prompt)
        style_hits = detect_pattern_hits(final_prompt, ABSTRACT_STYLE_PATTERNS)
        unwanted_hits = detect_unwanted_noun_hits(final_prompt, bool(daily_life_flag), selected_loc)
        fx_hits = detect_disallowed_fx_hits(final_prompt, cleaner)
        embodied = 1 if has_emotion_embodiment(final_prompt, garnish_text) else 0

        rows.append(
            SampleRow(
                seed=seed,
                subj=subj2,
                costume_key=costume2,
                costume_prompt=costume_prompt,
                input_loc=loc,
                input_loc_tag=exp_input,
                selected_loc=selected_loc,
                broad_scene=broad_scene,
                is_daily_life=daily_life_flag,
                selected_source=selected_source,
                selected_action=selected_action,
                action_pool_loc=action_pool_loc,
                selected_pack_key=str(sim["selected_pack_key"]),
                props_included=int(sim["props_included"]),
                props_count=len(sim["selected_props"]),
                selected_props=[str(x) for x in sim["selected_props"]],
                meta_mood_key=meta_mood_key,
                meta_mood_text=meta_mood_text,
                garnish=garnish_text,
                emotion_embodied=embodied,
                abstract_style_hits=style_hits,
                unwanted_noun_hits=unwanted_hits,
                disallowed_fx_hits=fx_hits,
                location_prompt=loc_prompt,
                raw_prompt=raw_prompt,
                final_prompt=final_prompt,
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
                classification = classify_object_hotspot(loc, token)
                effective_threshold = get_effective_object_threshold(loc, token)
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
                        "classification": classification,
                        "effective_threshold": round(effective_threshold, 6),
                        "policy_source": classification if classification != "general" else "",
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
                "broad_scene": s.broad_scene,
                "is_daily_life": s.is_daily_life,
                "meta_mood_key": s.meta_mood_key,
                "garnish": s.garnish,
                "final_prompt": s.final_prompt,
            }
        )
    return rows


def build_prompt_quality_rows(run_id: str, samples: List[SampleRow]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for s in samples:
        rows.append(
            {
                "run_id": run_id,
                "seed": s.seed,
                "subj": s.subj,
                "selected_loc": s.selected_loc,
                "broad_scene": s.broad_scene,
                "is_daily_life": s.is_daily_life,
                "meta_mood_key": s.meta_mood_key,
                "emotion_embodied": s.emotion_embodied,
                "abstract_style_hits": "|".join(s.abstract_style_hits),
                "unwanted_noun_hits": "|".join(s.unwanted_noun_hits),
                "disallowed_fx_hits": "|".join(s.disallowed_fx_hits),
                "final_prompt": s.final_prompt,
            }
        )
    return rows


def _metric_row(
    run_id: str,
    metric_name: str,
    metric_value: float,
    target_min: Any = "",
    target_max: Any = "",
    status: str = "info",
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "metric_name": metric_name,
        "metric_value": round(metric_value, 6),
        "target_min": target_min,
        "target_max": target_max,
        "status": status,
        "notes": notes,
    }


def build_quality_metric_rows(
    run_id: str,
    samples: List[SampleRow],
    object_rate_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not samples:
        return rows

    sample_count = len(samples)
    daily_life_share = sum(s.is_daily_life for s in samples) / sample_count
    broad_scene_counts = Counter(s.broad_scene for s in samples)
    broad_scene_entropy = entropy_from_counts(broad_scene_counts.values())
    broad_scene_top1 = broad_scene_counts.most_common(1)[0]
    broad_scene_top1_share = broad_scene_top1[1] / sample_count
    emotion_embodiment_rate = sum(s.emotion_embodied for s in samples) / sample_count
    abstract_style_term_rate = sum(1 for s in samples if s.abstract_style_hits) / sample_count
    unwanted_noun_rate = sum(1 for s in samples if s.unwanted_noun_hits) / sample_count
    disallowed_fx_rate = sum(1 for s in samples if s.disallowed_fx_hits) / sample_count

    qualified_object_rows = [
        r for r in object_rate_rows
        if r["scope"] == "final_prompt" and int(r["count_location_samples"]) >= 5
    ]
    qualified_true_bias_rows = [
        r for r in qualified_object_rows
        if r.get("classification") in {"true_bias_background", "true_bias_action"}
    ]
    max_object_concentration = max(
        (float(r["conditional_rate"]) for r in qualified_object_rows),
        default=0.0,
    )
    max_true_bias_concentration = max(
        (float(r["conditional_rate"]) for r in qualified_true_bias_rows),
        default=0.0,
    )

    daily_status = (
        "pass"
        if DAILY_LIFE_SHARE_TARGET_MIN <= daily_life_share <= DAILY_LIFE_SHARE_TARGET_MAX
        else "fail"
    )
    emotion_status = "pass" if emotion_embodiment_rate >= 0.85 else "fail"
    unwanted_status = "pass" if unwanted_noun_rate == 0 else "fail"
    fx_status = "pass" if disallowed_fx_rate == 0 else "fail"
    style_status = "pass" if abstract_style_term_rate == 0 else "warn"
    raw_object_gate = get_policy_threshold("default_quality_gate", 0.55)
    true_bias_gate = get_policy_threshold("true_bias_quality_gate", 0.45)
    object_status = "pass" if max_object_concentration <= raw_object_gate else "warn"
    true_bias_status = "pass" if max_true_bias_concentration <= true_bias_gate else "warn"

    rows.append(
        _metric_row(
            run_id,
            "daily_life_share",
            daily_life_share,
            DAILY_LIFE_SHARE_TARGET_MIN,
            DAILY_LIFE_SHARE_TARGET_MAX,
            daily_status,
            "share of selected locations classified as daily-life",
        )
    )
    rows.append(
        _metric_row(
            run_id,
            "broad_scene_entropy",
            broad_scene_entropy,
            "",
            "",
            "info",
            f"top1={broad_scene_top1[0]}:{round(broad_scene_top1_share, 6)}",
        )
    )
    rows.append(
        _metric_row(
            run_id,
            "broad_scene_top1_share",
            broad_scene_top1_share,
            "",
            "",
            "info",
            f"top1_scene={broad_scene_top1[0]}",
        )
    )
    rows.append(
        _metric_row(
            run_id,
            "emotion_embodiment_rate",
            emotion_embodiment_rate,
            0.85,
            "",
            emotion_status,
            "rate of final prompts containing physical emotional expression",
        )
    )
    rows.append(
        _metric_row(
            run_id,
            "abstract_style_term_rate",
            abstract_style_term_rate,
            "",
            0,
            style_status,
            "rate of final prompts containing abstract style wording",
        )
    )
    rows.append(
        _metric_row(
            run_id,
            "unwanted_noun_rate",
            unwanted_noun_rate,
            "",
            0,
            unwanted_status,
            "rate of final prompts containing imaginary / trash / debris family terms",
        )
    )
    rows.append(
        _metric_row(
            run_id,
            "disallowed_fx_rate",
            disallowed_fx_rate,
            "",
            0,
            fx_status,
            "rate of final prompts containing denied FX or render-processing terms",
        )
    )
    rows.append(
        _metric_row(
            run_id,
            "max_object_concentration_final_prompt",
            max_object_concentration,
            "",
            raw_object_gate,
            object_status,
            "max conditional object rate across locations with >=5 samples",
        )
    )
    rows.append(
        _metric_row(
            run_id,
            "max_object_concentration_true_bias",
            max_true_bias_concentration,
            "",
            true_bias_gate,
            true_bias_status,
            "max conditional object rate across true-bias locations only with audit artifacts excluded",
        )
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
                    "remarks": "duplicates increase effective weight in the scene variation stage",
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
                        "remarks": "duplicates increase effective weight in the scene variation stage",
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
    quality_metric_rows: List[Dict[str, Any]],
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
        threshold = float(r.get("effective_threshold", get_policy_threshold("default_conditional_rate", 0.40)))
        classification = r.get("classification", "general")
        if float(r["conditional_rate"]) > threshold:
            if classification == "audit_artifact":
                alert_type = "audit_artifact"
            elif classification == "thematic_anchor":
                alert_type = "anchor_object_bias"
            else:
                alert_type = "high_object_bias"
            rows.append(
                {
                    "run_id": run_id,
                    "alert_type": alert_type,
                    "scope": r["scope"],
                    "input_condition_key": "location_name",
                    "input_condition_value": r["location_name"],
                    "target_name": r["object_token"],
                    "metric_name": "conditional_rate",
                    "metric_value": r["conditional_rate"],
                    "threshold": threshold,
                    "triggered": 1,
                    "severity": "high" if float(r["conditional_rate"]) > 0.60 else "medium",
                    "remarks": classification,
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

    for r in quality_metric_rows:
        if r["status"] not in {"fail", "warn"}:
            continue
        rows.append(
            {
                "run_id": run_id,
                "alert_type": "quality_gate",
                "scope": "prompt_quality",
                "input_condition_key": "metric_name",
                "input_condition_value": r["metric_name"],
                "target_name": r["metric_name"],
                "metric_name": r["metric_name"],
                "metric_value": r["metric_value"],
                "threshold": r["target_min"] if r["target_min"] != "" else r["target_max"],
                "triggered": 1,
                "severity": "high" if r["status"] == "fail" else "medium",
                "remarks": r.get("notes", ""),
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
    prompt_quality_rows = build_prompt_quality_rows(run_id, samples)
    quality_metric_rows = build_quality_metric_rows(run_id, samples, object_rate_rows)
    data_quality_rows = build_data_quality_rows(run_id)
    alert_rows = build_alert_rows(
        run_id,
        location_rows,
        object_rows,
        object_rate_rows,
        quality_metric_rows,
        data_quality_rows,
    )

    run_meta_rows = [
        {
            "run_id": run_id,
            "run_date": run_date,
            "generation_mode": DEFAULT_GENERATION_MODE,
            "sample_count": args.sample_count,
            "seed_start": args.seed_start,
            "seed_end": seed_end,
            "pipeline_scope": args.pipeline_scope,
            "variation_mode": args.variation_mode,
            "location_mode": args.location_mode,
            "lighting_mode": args.lighting_mode,
            "input_mode": args.input_mode,
            "target_scope": args.target_scope,
            "daily_life_share_target_min": DAILY_LIFE_SHARE_TARGET_MIN,
            "daily_life_share_target_max": DAILY_LIFE_SHARE_TARGET_MAX,
            "notes": args.notes,
        }
    ]

    write_csv(
        out_dir / "audit_run_meta.csv",
        run_meta_rows,
        [
            "run_id",
            "run_date",
            "generation_mode",
            "sample_count",
            "seed_start",
            "seed_end",
            "pipeline_scope",
            "variation_mode",
            "location_mode",
            "lighting_mode",
            "input_mode",
            "target_scope",
            "daily_life_share_target_min",
            "daily_life_share_target_max",
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
            "classification",
            "effective_threshold",
            "policy_source",
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
            "broad_scene",
            "is_daily_life",
            "meta_mood_key",
            "garnish",
            "final_prompt",
        ],
    )
    write_csv(
        out_dir / "audit_prompt_quality.csv",
        prompt_quality_rows,
        [
            "run_id",
            "seed",
            "subj",
            "selected_loc",
            "broad_scene",
            "is_daily_life",
            "meta_mood_key",
            "emotion_embodied",
            "abstract_style_hits",
            "unwanted_noun_hits",
            "disallowed_fx_hits",
            "final_prompt",
        ],
    )
    write_csv(
        out_dir / "audit_quality_metrics.csv",
        quality_metric_rows,
        [
            "run_id",
            "metric_name",
            "metric_value",
            "target_min",
            "target_max",
            "status",
            "notes",
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
    quality_summary = ", ".join(
        f"{row['metric_name']}={row['metric_value']}"
        for row in quality_metric_rows
        if row["metric_name"] in {
            "daily_life_share",
            "emotion_embodiment_rate",
            "abstract_style_term_rate",
            "unwanted_noun_rate",
            "disallowed_fx_rate",
            "max_object_concentration_true_bias",
        }
    )
    print(f"  alerts={len(alert_rows)} data_quality_issues={len(data_quality_rows)}")
    print(f"  quality_metrics: {quality_summary}")


if __name__ == "__main__":
    main()
