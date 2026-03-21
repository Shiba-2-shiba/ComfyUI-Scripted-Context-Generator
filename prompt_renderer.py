from __future__ import annotations

import json
import logging
import os
import random
import re
from typing import Callable

if __package__:
    from .core.semantic_families import (
        filter_semantic_family_tags,
        semantic_families_for_text,
        split_semantic_tags,
    )
    from .core.semantic_policy import filter_candidate_strings, sanitize_text
    from .location_service import load_background_packs, resolve_location_key
    from .pipeline.action_generator import action_verb as normalize_action_verb
else:
    from core.semantic_families import (
        filter_semantic_family_tags,
        semantic_families_for_text,
        split_semantic_tags,
    )
    from core.semantic_policy import filter_candidate_strings, sanitize_text
    from location_service import load_background_packs, resolve_location_key
    from pipeline.action_generator import action_verb as normalize_action_verb


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "vocab", "data")

_PROMPT_DEBUG_ENV = "PROMPT_RENDERER_DEBUG_LOG"
_PROMPT_DEBUG_PATH_ENV = "PROMPT_RENDERER_LOG_PATH"
_PROMPT_DEBUG_LEVEL_ENV = "PROMPT_RENDERER_LOG_LEVEL"


def _env_flag(name):
    return str(os.getenv(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _configure_logger():
    logger_instance = logging.getLogger("PromptAssembly")
    if getattr(logger_instance, "_prompt_renderer_configured", False):
        return logger_instance

    logger_instance.propagate = False
    if _env_flag(_PROMPT_DEBUG_ENV):
        level_name = str(os.getenv(_PROMPT_DEBUG_LEVEL_ENV, "DEBUG")).strip().upper() or "DEBUG"
        log_level = getattr(logging, level_name, logging.DEBUG)
        log_path = os.getenv(_PROMPT_DEBUG_PATH_ENV, os.path.join(ROOT_DIR, "simple_template_debug.log"))
        handler = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger_instance.setLevel(log_level)
        logger_instance.addHandler(handler)
    else:
        logger_instance.setLevel(logging.WARNING)
        logger_instance.addHandler(logging.NullHandler())

    logger_instance._prompt_renderer_configured = True
    return logger_instance


logger = _configure_logger()

DEFAULT_GENERATION_MODE = "scene_emotion_priority"
DEFAULT_TEMPLATE = "{subject_clause}, {action_clause}, {scene_clause}."
DEFAULT_END_TEMPLATE = "{scene_clause}"

_template_catalog_cache = None

_ACTION_FOCUSED_HINTS = (
    "read", "reading", "write", "writing", "study", "studying", "check", "checking",
    "sort", "sorting", "organizing", "arranging", "inspect", "inspecting", "examining",
    "working", "review", "reviewing", "comparing", "measuring", "tracking",
)
_ACTION_TRANSITION_HINTS = (
    "walk", "walking", "heading", "commut", "arriv", "leav", "moving", "crossing",
    "travel", "boarding", "stepping", "on the way", "before ", "after ", "between ",
)
_ACTION_SOCIAL_HINTS = (
    "talk", "talking", "chat", "chatting", "meeting", "meet", "waving", "greet",
    "greeting", "answer", "answering", "conversation", "friend", "companion",
    "serving", "offering", "discuss", "discussing",
)
_ACTION_QUIET_HINTS = (
    "quiet", "soft", "gentle", "pause", "lingering", "resting", "still", "calm",
    "peaceful", "breath", "looking", "watching",
)
_FRAGMENT_ACTION_STARTS = {
    "hands", "fingers", "one", "deep", "peaceful", "quiet", "gentle", "soft",
}
_NON_GERUND_BODY_KEYS = {
    "body_carrying_action",
    "body_room_for_action",
}
_TEMPLATE_ROLE_PRIORITY = ("focused", "transition", "social", "quiet")
_TEMPLATE_ROLE_HINTS = {
    "focused": _ACTION_FOCUSED_HINTS,
    "transition": _ACTION_TRANSITION_HINTS,
    "social": _ACTION_SOCIAL_HINTS,
    "quiet": _ACTION_QUIET_HINTS,
}
_TEMPLATE_ROLE_SOURCE_WEIGHTS = {
    "action": 2.2,
    "meta_mood": 1.5,
    "garnish": 0.7,
    "loc": 0.4,
}


def _load_template_catalog():
    global _template_catalog_cache
    if _template_catalog_cache is None:
        path = os.path.join(DATA_DIR, "template_catalog.json")
        catalog = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        _template_catalog_cache = catalog if isinstance(catalog, dict) else {}
    return _template_catalog_cache


def _load_lines(filename):
    path = os.path.join(ROOT_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                return lines
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            print(f"\033[93m[PromptAssembly] Error loading {filename}: {e}\033[0m")
    return []


def _load_rules():
    rule_path = os.path.join(ROOT_DIR, "rules", "consistency_rules.json")
    if os.path.exists(rule_path):
        try:
            with open(rule_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                rules = data.get("conflicts", [])
                logger.debug(f"Loaded {len(rules)} consistency rules.")
                return rules
        except Exception as e:
            logger.error(f"Error loading consistency_rules.json: {e}")
            print(f"\033[93m[PromptAssembly] Error loading consistency_rules.json: {e}\033[0m")
    else:
        logger.warning("consistency_rules.json not found.")
    return []


def _join_nonempty(parts, sep=", "):
    cleaned = []
    for part in parts:
        if part is None:
            continue
        text = str(part).strip().strip(",")
        if text:
            cleaned.append(text)
    return sep.join(cleaned)


def _strip_clause_punctuation(text):
    if text is None:
        return ""
    return re.sub(r"[\s,.;:]+$", "", str(text).strip())


def _compose_visual_sentence(*parts):
    clauses = []
    for part in parts:
        clean = _strip_clause_punctuation(part)
        if clean:
            clauses.append(clean)
    if not clauses:
        return ""
    return ", ".join(clauses) + "."


def _count_role_hits(text, hints):
    lowered = str(text or "").lower()
    return sum(1 for hint in hints if hint in lowered)


def _derive_template_roles(action, garnish, meta_mood, loc):
    role_scores = {role: 0.0 for role in _TEMPLATE_ROLE_PRIORITY}
    source_texts = {
        "action": action,
        "meta_mood": meta_mood,
        "garnish": garnish,
        "loc": loc,
    }
    for source_name, source_text in source_texts.items():
        weight = float(_TEMPLATE_ROLE_SOURCE_WEIGHTS.get(source_name, 1.0))
        for role_name, hints in _TEMPLATE_ROLE_HINTS.items():
            hits = _count_role_hits(source_text, hints)
            if hits:
                role_scores[role_name] += hits * weight

    ordered_roles = [
        role_name
        for role_name, score in sorted(
            role_scores.items(),
            key=lambda item: (-item[1], _TEMPLATE_ROLE_PRIORITY.index(item[0])),
        )
        if score > 0
    ]
    if not ordered_roles:
        ordered_roles = ["neutral"]
    elif "neutral" not in ordered_roles:
        ordered_roles.append("neutral")

    return {
        "intro_roles": list(ordered_roles),
        "body_roles": list(ordered_roles),
        "end_roles": list(ordered_roles),
    }


def _derive_action_surface(action):
    first_clause = str(action or "").split(",", 1)[0].strip().lower()
    if not first_clause:
        return {"surface": "clause", "verb": "", "first_token": "", "word_count": 0}

    tokens = re.findall(r"[a-z']+", first_clause)
    first_token = tokens[0] if tokens else ""
    verb = normalize_action_verb(first_clause)
    surface = "clause"
    if first_token.endswith("ing"):
        surface = "gerund"
    if first_token in _FRAGMENT_ACTION_STARTS:
        surface = "fragment"
    if verb and verb in _FRAGMENT_ACTION_STARTS:
        surface = "fragment"
    return {
        "surface": surface,
        "verb": verb,
        "first_token": first_token,
        "word_count": len(tokens),
    }


def _render_action_clause(action, garnish, action_surface, body_entry):
    action_text = sanitize_text(str(action or "").strip())
    garnish_text = sanitize_text(str(garnish or "").strip())
    rendered_clause = sanitize_text(_join_nonempty([action_text, garnish_text]))
    normalized_surface = dict(action_surface or {})
    input_surface = str(normalized_surface.get("surface", "")).strip() or "clause"
    normalized_surface["input_surface"] = input_surface
    normalized_surface["rendered_clause"] = rendered_clause

    body_key = str((body_entry or {}).get("key", "")).strip()
    if action_text and input_surface == "gerund" and body_key in _NON_GERUND_BODY_KEYS:
        framed_action = sanitize_text(f"in the middle of {action_text}")
        rendered_clause = sanitize_text(_join_nonempty([framed_action, garnish_text]))
        normalized_surface["surface"] = "framed"
        normalized_surface["rendered_clause"] = rendered_clause

    return rendered_clause, normalized_surface


def _fallback_template_entries(filename, prefix):
    entries = []
    for index, line in enumerate(_load_lines(filename)):
        entries.append(
            {
                "key": f"{prefix}_{index}",
                "text": line,
                "roles": ["neutral"],
            }
        )
    return entries


def _template_entries(section_name):
    catalog = _load_template_catalog()
    entries = catalog.get(section_name, []) if isinstance(catalog, dict) else []
    normalized = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        text = str(entry.get("text", "")).strip()
        if not text:
            continue
        key = str(entry.get("key", f"{section_name}_{index}")).strip() or f"{section_name}_{index}"
        roles = [str(item).strip() for item in entry.get("roles", []) if str(item).strip()]
        normalized.append(
            {
                "key": key,
                "text": text,
                "roles": roles or ["neutral"],
                "needs_garnish": bool(entry.get("needs_garnish", False)),
                "needs_mood": bool(entry.get("needs_mood", False)),
                "needs_loc": bool(entry.get("needs_loc", False)),
                "preferred_surfaces": [str(item).strip() for item in entry.get("preferred_surfaces", []) if str(item).strip()],
                "avoid_surfaces": [str(item).strip() for item in entry.get("avoid_surfaces", []) if str(item).strip()],
                "min_action_words": int(entry.get("min_action_words", 0) or 0),
                "max_action_words": int(entry.get("max_action_words", 0) or 0),
            }
        )
    if normalized:
        return normalized
    fallback_map = {
        "intro": _fallback_template_entries("vocab/templates_intro.txt", "intro"),
        "body": _fallback_template_entries("vocab/templates_body.txt", "body"),
        "end": _fallback_template_entries("vocab/templates_end.txt", "end"),
    }
    return fallback_map.get(section_name, [])


def _select_template_entry(
    entries,
    default_text,
    default_key,
    preferred_roles,
    recent_part_keys,
    recent_templates,
    rng,
    is_consistent,
    has_garnish,
    has_loc,
    has_mood,
    action_surface=None,
):
    if not entries:
        return {"key": default_key, "text": default_text, "roles": ["neutral"]}

    recent_part_keys = {str(item) for item in (recent_part_keys or []) if item}
    recent_templates = {str(item) for item in (recent_templates or []) if item}
    preferred_roles = [str(item) for item in (preferred_roles or []) if item]

    candidates = []
    for entry in entries:
        if entry.get("needs_garnish") and not has_garnish:
            continue
        if entry.get("needs_loc") and not has_loc:
            continue
        if entry.get("needs_mood") and not has_mood:
            continue
        if not is_consistent(entry["text"]):
            continue
        action_word_count = int((action_surface or {}).get("word_count", 0) or 0)
        min_action_words = int(entry.get("min_action_words", 0) or 0)
        max_action_words = int(entry.get("max_action_words", 0) or 0)
        if min_action_words and action_word_count < min_action_words:
            continue
        if max_action_words and action_word_count > max_action_words:
            continue

        score = 1.0
        roles = entry.get("roles", [])
        for index, role in enumerate(preferred_roles):
            if role in roles:
                score += max(0.4, 2.0 - (index * 0.3))
        surface_name = str((action_surface or {}).get("surface", "")).strip()
        if surface_name:
            if surface_name in entry.get("preferred_surfaces", []):
                score += 1.1
            if surface_name in entry.get("avoid_surfaces", []):
                score *= 0.25
        if entry["key"] in recent_part_keys and len(entries) > 1:
            score *= 0.15
        if entry["key"] in recent_templates and len(entries) > 1:
            score *= 0.25
        candidates.append((entry, max(score, 0.01)))

    if not candidates:
        return {"key": default_key, "text": default_text, "roles": ["neutral"]}

    candidate_entries = [item[0] for item in candidates]
    weights = [item[1] for item in candidates]
    return rng.choices(candidate_entries, weights=weights, k=1)[0]


def _normalize_prompt(text):
    if text is None:
        return ""
    return sanitize_text(str(text))


def _apply_semantic_family_budget(action, garnish, meta_mood, staging_tags):
    action_text = sanitize_text(str(action or "").strip())
    garnish_tags = split_semantic_tags(garnish)
    meta_mood_text = sanitize_text(str(meta_mood or "").strip())
    staging_tag_items = split_semantic_tags(staging_tags)

    base_families = semantic_families_for_text(action_text) | semantic_families_for_text(meta_mood_text)
    filtered_garnish_tags, dropped_garnish_tags, garnish_families = filter_semantic_family_tags(
        garnish_tags,
        blocked_families=base_families,
        per_family_limit=1,
    )
    filtered_staging_tags, dropped_staging_tags, staging_families = filter_semantic_family_tags(
        staging_tag_items,
        blocked_families=base_families | garnish_families,
        per_family_limit=1,
    )

    return {
        "action": action_text,
        "garnish": sanitize_text(", ".join(filtered_garnish_tags)),
        "meta_mood": meta_mood_text,
        "staging_tags": sanitize_text(", ".join(filtered_staging_tags)),
        "debug": {
            "base_families": sorted(base_families),
            "garnish_input_tags": garnish_tags,
            "garnish_kept_tags": filtered_garnish_tags,
            "garnish_dropped_tags": dropped_garnish_tags,
            "garnish_kept_families": sorted(garnish_families),
            "staging_input_tags": staging_tag_items,
            "staging_kept_tags": filtered_staging_tags,
            "staging_dropped_tags": dropped_staging_tags,
            "staging_kept_families": sorted(staging_families),
            "final_families": sorted(base_families | garnish_families | staging_families),
        },
    }


def _make_consistency_checker(rules, context_values):
    def is_consistent(template_part):
        for rule in rules:
            input_term = rule.get("input_term", "").lower()
            template_term = rule.get("template_term", "").lower()
            if not input_term or not template_term:
                continue
            triggered = False
            for val in context_values:
                if val and input_term in str(val).lower():
                    triggered = True
                    break
            if triggered and template_term in str(template_part).lower():
                logger.debug(
                    f"Conflict detected: input '{input_term}' conflicts with template '{template_term}' in part '{template_part}'"
                )
                return False
        return True

    return is_consistent


def _expand_location_key_for_builder(loc, rng, context_values, is_consistent):
    if not loc or not isinstance(loc, str):
        return loc
    try:
        bg_packs = load_background_packs()
        resolved_loc = resolve_location_key(loc) or loc
        if resolved_loc not in bg_packs:
            return loc
        logger.info(f"Expanding location: {resolved_loc}")
        pack = bg_packs[resolved_loc]
        parts = []

        def pick_consistent(candidates):
            safe_candidates = filter_candidate_strings(candidates)
            if not safe_candidates:
                return None
            for _ in range(10):
                candidate = rng.choice(safe_candidates)
                if is_consistent(str(candidate)):
                    return candidate
            logger.debug("Failed to find consistent candidate after 10 attempts.")
            return None

        envs = pack.get("environment", [])
        if envs:
            e = pick_consistent(envs)
            parts.append(e if e else pack.get("label", resolved_loc))
        else:
            parts.append(pack.get("label", resolved_loc))

        times = pack.get("time", [])
        if times:
            t = pick_consistent(times)
            if t:
                parts.append(f"during {t}")
        weathers = pack.get("weather", [])
        if weathers:
            w = pick_consistent(weathers)
            if w:
                parts.append(w)
        crowds = pack.get("crowd", [])
        if crowds:
            c = pick_consistent(crowds)
            if c:
                parts.append(c)
        new_loc = ", ".join(parts)
        logger.debug(f"Expanded loc '{resolved_loc}' to '{new_loc}'")
        return sanitize_text(new_loc)
    except Exception as e:
        logger.error(f"Error expanding location: {e}")
        print(f"[PromptAssembly] Error expanding location: {e}")
        return loc


def build_prompt_text(
    template,
    composition_mode,
    seed,
    subj="",
    costume="",
    loc="",
    action="",
    garnish="",
    meta_mood="",
    meta_style="",
    staging_tags="",
    recent_templates=None,
    recent_intro_keys=None,
    recent_body_keys=None,
    recent_end_keys=None,
    return_debug=False,
    template_entries_fn: Callable[[str], list[dict]] | None = None,
):
    logger.info(f"--- PromptAssembly Build Start (Seed: {seed}) ---")
    logger.debug(f"Generation Mode: {DEFAULT_GENERATION_MODE}")
    logger.debug(
        f"Inputs - Subj: {subj}, Costume: {costume}, Loc: {loc}, Action: {action}, "
        f"Garnish: {garnish}, Mood: {meta_mood}, DeprecatedStyle: {meta_style}, Staging: {staging_tags}"
    )
    logger.debug(f"Composition Mode: {composition_mode}")

    template_entries_fn = template_entries_fn or _template_entries
    rng = random.Random(seed)
    semantic_layers = _apply_semantic_family_budget(action, garnish, meta_mood, staging_tags)
    action = semantic_layers["action"]
    garnish = semantic_layers["garnish"]
    meta_mood = semantic_layers["meta_mood"]
    staging_tags = semantic_layers["staging_tags"]
    subject_clause = sanitize_text(_join_nonempty([subj, f"in {costume}" if costume else ""], " "))
    action_clause = sanitize_text(_join_nonempty([action, garnish]))
    scene_clause = sanitize_text(_join_nonempty([f"in {loc}" if loc else "", meta_mood]))
    rules = _load_rules()
    context_vals = [subj, costume, loc, action, garnish, meta_mood, staging_tags]
    is_consistent = _make_consistency_checker(rules, context_vals)
    recent_templates = {str(item) for item in (recent_templates or []) if item}
    selected_template_key = ""

    loc = _expand_location_key_for_builder(loc, rng, context_vals, is_consistent)
    context_vals = [subj, costume, loc, action, garnish, meta_mood, staging_tags]
    is_consistent = _make_consistency_checker(rules, context_vals)
    scene_clause = sanitize_text(_join_nonempty([f"in {loc}" if loc else "", meta_mood]))
    scene_anchor_clause = scene_clause[3:] if scene_clause.lower().startswith("in ") else scene_clause

    if composition_mode:
        logger.info("Using Composition Mode")
        template_roles = _derive_template_roles(action, garnish, meta_mood, loc)
        action_surface = _derive_action_surface(action)
        intro_entry = _select_template_entry(
            template_entries_fn("intro"),
            "{subject_clause}",
            "intro_default",
            template_roles["intro_roles"],
            recent_intro_keys,
            recent_templates,
            rng,
            is_consistent,
            has_garnish=bool(str(garnish).strip()),
            has_loc=bool(str(loc).strip()),
            has_mood=bool(str(meta_mood).strip()),
            action_surface=action_surface,
        )
        body_entry = _select_template_entry(
            template_entries_fn("body"),
            "{action_clause}",
            "body_default",
            template_roles["body_roles"],
            recent_body_keys,
            recent_templates,
            rng,
            is_consistent,
            has_garnish=bool(str(garnish).strip()),
            has_loc=bool(str(loc).strip()),
            has_mood=bool(str(meta_mood).strip()),
            action_surface=action_surface,
        )
        end_entry = _select_template_entry(
            template_entries_fn("end"),
            DEFAULT_END_TEMPLATE,
            "end_default",
            template_roles["end_roles"],
            recent_end_keys,
            recent_templates,
            rng,
            is_consistent,
            has_garnish=bool(str(garnish).strip()),
            has_loc=bool(str(loc).strip()),
            has_mood=bool(str(meta_mood).strip()),
            action_surface=action_surface,
        )

        p_intro = intro_entry["text"]
        p_body = body_entry["text"]
        p_end = end_entry["text"]
        action_clause, action_surface = _render_action_clause(action, garnish, action_surface, body_entry)
        template = _compose_visual_sentence(p_intro, p_body, p_end)
        selected_template_key = f"{intro_entry['key']}||{body_entry['key']}||{end_entry['key']}"
        logger.debug(f"Composed Template: {template}")
    else:
        logger.info("Using Legacy/Single Template Mode")
        if not template or str(template).strip() == "" or template == DEFAULT_TEMPLATE:
            lines = _load_lines("templates.txt")
            if lines:
                non_recent = [line for line in lines if line not in recent_templates]
                template = rng.choice(non_recent or lines)
        selected_template_key = str(template)

    result = template
    result = result.replace("{subject_clause}", subject_clause)
    result = result.replace("{action_clause}", action_clause)
    result = result.replace("{scene_clause}", scene_clause)
    result = result.replace("{scene_anchor_clause}", scene_anchor_clause)
    result = result.replace("{subj}", str(subj) if subj is not None else "")
    result = result.replace("{costume}", str(costume) if costume is not None else "")
    result = result.replace("{loc}", str(loc) if loc is not None else "")
    result = result.replace("{action}", str(action) if action is not None else "")
    result = result.replace("{garnish}", str(garnish) if garnish is not None else "")
    result = result.replace("{meta_mood}", str(meta_mood) if meta_mood is not None else "")
    result = result.replace("{meta_style}", "")

    if staging_tags and isinstance(staging_tags, str) and staging_tags.strip():
        if "{staging_tags}" in result:
            result = result.replace("{staging_tags}", staging_tags)
        else:
            result = f"{result}, {sanitize_text(staging_tags)}"
    else:
        result = result.replace("{staging_tags}", "")

    result = _normalize_prompt(result)
    logger.info(f"Final Prompt: {result}")
    if return_debug:
        debug_payload = {
            "template_key": selected_template_key or str(template),
            "composition_mode": bool(composition_mode),
            "semantic_family_budget": semantic_layers["debug"],
        }
        if composition_mode:
            debug_payload.update(
                {
                    "intro_key": intro_entry["key"],
                    "body_key": body_entry["key"],
                    "end_key": end_entry["key"],
                    "template_roles": template_roles,
                    "action_surface": action_surface,
                }
            )
        return result, debug_payload
    return result
