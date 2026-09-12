import json
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from core.semantic_families import semantic_families_for_text
from pipeline.context_pipeline import sample_garnish_fields
from pipeline.source_pipeline import _source_payload_score, _load_daily_life_locations


FACE_FORWARD_FAMILIES = {"gaze", "expression", "smile_mouth"}


class TestCalmBiasControls(unittest.TestCase):
    def test_source_payload_scoring_no_longer_bonuses_quiet_or_peaceful_moods(self):
        daily_life_locs = _load_daily_life_locations(ROOT)
        base = {
            "loc": "modern_office",
            "action": "sorting papers",
            "meta": {"tags": {"purpose": "work"}},
        }
        energetic = dict(base, meta={"mood": "energetic_joy", "tags": {"purpose": "work"}})
        quiet = dict(base, meta={"mood": "quiet_focused", "tags": {"purpose": "work"}})
        peaceful = dict(base, meta={"mood": "peaceful_relaxed", "tags": {"purpose": "work"}})
        fear = dict(base, meta={"mood": "creepy_fear", "tags": {"purpose": "work"}})

        self.assertGreater(_source_payload_score(energetic, daily_life_locs), _source_payload_score(quiet, daily_life_locs))
        self.assertEqual(_source_payload_score(quiet, daily_life_locs), _source_payload_score(peaceful, daily_life_locs))
        self.assertGreater(_source_payload_score(quiet, daily_life_locs), _source_payload_score(fear, daily_life_locs))

    def test_calm_garnish_caps_face_forward_tags_for_high_frequency_moods(self):
        for mood_key, emotion_nuance in (("quiet_focused", "absorbed"), ("peaceful_relaxed", "content")):
            for seed in range(12):
                garnish, debug = sample_garnish_fields(
                    action_text="sorting papers at a desk",
                    meta_mood_key=mood_key,
                    seed=seed,
                    max_items=3,
                    include_camera=False,
                    emotion_nuance=emotion_nuance,
                    context_loc="modern_office",
                    context_costume="office_lady",
                    scene_tags={"purpose": "work", "emotion_nuance": emotion_nuance},
                    personality="serious" if mood_key == "quiet_focused" else "gentle",
                )
                tags = [tag.strip() for tag in garnish.split(",") if tag.strip()]
                face_forward_count = sum(
                    1
                    for tag in tags
                    if semantic_families_for_text(tag) & FACE_FORWARD_FAMILIES
                )
                self.assertLessEqual(
                    face_forward_count,
                    1,
                    msg=f"mood={mood_key} seed={seed} tags={tags} debug={debug}",
                )

    def test_targeted_calm_action_pool_entries_avoid_breath_family_language(self):
        with open(os.path.join(ROOT, "vocab", "data", "action_pools.json"), "r", encoding="utf-8") as handle:
            pools = json.load(handle)

        targeted_entries = {
            "school_classroom": "sitting at a desk with notes spread in front of her",
            "surveillance_room": "standing in front of the monitor wall",
            "winter_street": "standing in winter with cold hands tucked close",
        }
        for loc, expected_text in targeted_entries.items():
            items = [item.get("text", "") for item in pools[loc]]
            self.assertIn(expected_text, items)
            self.assertNotIn("breath", semantic_families_for_text(expected_text))


if __name__ == "__main__":
    unittest.main()
