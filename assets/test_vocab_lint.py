import json
import os
import re
import sys
import unittest


ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
if ASSETS_DIR not in sys.path:
    sys.path.insert(0, ASSETS_DIR)
ROOT = os.path.dirname(ASSETS_DIR)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import test_bootstrap  # noqa: F401,E402

import background_vocab  # noqa: E402
import improved_pose_emotion_vocab  # noqa: E402
from registry import resolve_clothing_theme, resolve_location_key  # noqa: E402

try:
    from vocab.garnish.logic import LEGACY_MAP  # noqa: E402
except ImportError:
    LEGACY_MAP = {}


def _load_prompt_rows():
    prompts_path = os.path.join(ROOT, "prompts.jsonl")
    rows = []
    with open(prompts_path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _collect_string_violations(obj, path=""):
    banned_patterns = {
        "meta_style": re.compile(r"\bmeta_style\b"),
        "art style": re.compile(r"\bart style\b"),
        "illustration": re.compile(r"\billustration\b"),
        "oil painting": re.compile(r"\boil painting\b"),
        "digital art": re.compile(r"\bdigital art\b"),
        "film grain": re.compile(r"\bfilm grain\b"),
        "ambient occlusion": re.compile(r"\bambient occlusion\b"),
        "volumetric lighting": re.compile(r"\bvolumetric lighting\b"),
        "bloom": re.compile(r"\bbloom\b"),
        "light leaks": re.compile(r"\blight leaks\b"),
        "prismatic light leaks": re.compile(r"\bprismatic light leaks\b"),
        "chromatic aberration": re.compile(r"\bchromatic aberration\b"),
    }
    violations = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            violations.extend(_collect_string_violations(value, f"{path}.{key}" if path else str(key)))
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            item_path = f"{path}[{index}]"
            if isinstance(item, str):
                if not item.strip():
                    violations.append(f"{item_path} is empty/whitespace")
                item_lower = item.lower()
                for label, pattern in banned_patterns.items():
                    if pattern.search(item_lower):
                        if "art" in label and ("museum" in item_lower or "gallery" in item_lower):
                            continue
                        violations.append(f"{item_path} contains banned '{label}': '{item}'")
            else:
                violations.extend(_collect_string_violations(item, item_path))
    return violations


def _normalize_emotion_token(mood_key):
    key = mood_key.lower().strip()
    if key in LEGACY_MAP:
        return LEGACY_MAP[key][0]
    parts = [part for part in key.split("_") if part]
    if parts and parts[0] in getattr(improved_pose_emotion_vocab, "MOOD_POOLS", {}):
        return parts[0]
    return key


class TestVocabLint(unittest.TestCase):
    def test_prompt_references_resolve(self):
        missing_locs = set()
        missing_costumes = set()

        for payload in _load_prompt_rows():
            loc = payload.get("loc_tag", "") or payload.get("loc", "")
            costume = payload.get("costume_key", "") or payload.get("costume", "")
            if loc and not resolve_location_key(loc.lower().strip()):
                missing_locs.add(loc.lower().strip())
            if costume and not resolve_clothing_theme(costume.lower().strip()):
                missing_costumes.add(costume.lower().strip())

        self.assertEqual(missing_locs, set())
        self.assertEqual(missing_costumes, set())

    def test_vocab_strings_are_clean(self):
        violations = []
        violations.extend(_collect_string_violations(background_vocab.CONCEPT_PACKS, "background_vocab.CONCEPT_PACKS"))
        violations.extend(_collect_string_violations(improved_pose_emotion_vocab.MICRO_ACTION_CONCEPTS, "MICRO_ACTION_CONCEPTS"))
        violations.extend(_collect_string_violations(improved_pose_emotion_vocab.MOOD_POOLS, "MOOD_POOLS"))

        allow_dirty_packs = {
            "rainy_alley",
            "cyberpunk_street",
            "burning_battlefield",
            "alien_planet",
            "dragon_lair",
            "abandoned_shrine",
        }
        for pack_name, pack_data in background_vocab.CONCEPT_PACKS.items():
            if pack_name in allow_dirty_packs:
                continue
            for field in ("core", "props", "fx"):
                for item in pack_data.get(field, []):
                    lowered = str(item).lower()
                    if "trash" in lowered or "debris" in lowered:
                        violations.append(
                            f"background_vocab.CONCEPT_PACKS.{pack_name}.{field} contains unwanted noun: '{item}'"
                        )

        action_pools_path = os.path.join(ROOT, "vocab", "data", "action_pools.json")
        with open(action_pools_path, "r", encoding="utf-8") as handle:
            action_pools = json.load(handle)
        for loc, items in action_pools.items():
            if loc.startswith("_") or loc == "schema_version":
                continue
            for index, item in enumerate(items):
                text = item.get("text", "") if isinstance(item, dict) else str(item)
                lowered = text.lower()
                if "imaginary" in lowered:
                    violations.append(f"action_pools.{loc}[{index}] contains banned 'imaginary': '{text}'")
                if loc not in allow_dirty_packs and ("trash" in lowered or "debris" in lowered):
                    violations.append(f"action_pools.{loc}[{index}] contains unwanted noun: '{text}'")

        self.assertEqual(violations, [])

    def test_mood_references_resolve(self):
        mood_map_path = os.path.join(ROOT, "mood_map.json")
        with open(mood_map_path, "r", encoding="utf-8") as handle:
            mood_map = json.load(handle)

        moods = sorted({payload.get("meta", {}).get("mood", "") for payload in _load_prompt_rows() if payload.get("meta")})
        missing_moods = [mood for mood in moods if mood and mood not in mood_map]
        emotion_tokens = sorted({_normalize_emotion_token(mood) for mood in moods if mood})
        missing_emotion_pool = [
            token
            for token in emotion_tokens
            if token not in getattr(improved_pose_emotion_vocab, "MOOD_POOLS", {})
        ]

        self.assertEqual(missing_moods, [])
        self.assertEqual(missing_emotion_pool, [])

    def test_prompt_actions_keep_basic_anchor_verbs(self):
        anchor_words = {
            "browsing",
            "checking",
            "comparing",
            "dancing",
            "gripping",
            "holding",
            "kneeling",
            "leaning",
            "lying",
            "moving",
            "organizing",
            "pausing",
            "pinning",
            "resting",
            "reviewing",
            "running",
            "settling",
            "singing",
            "sitting",
            "slipping",
            "sorting",
            "staying",
            "standing",
            "stretching",
            "walking",
            "watching",
            "working",
        }
        missing = []
        for payload in _load_prompt_rows():
            action = payload.get("action", "")
            words = re.findall(r"[A-Za-z']+", action.lower())
            if action and (not words or words[0] not in anchor_words):
                missing.append(action)

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
