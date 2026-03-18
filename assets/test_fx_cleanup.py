import json
import os
import re
import sys
import unittest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import background_vocab
from pipeline.content_pipeline import expand_location_prompt


def _disallowed_hits(text):
    s = (text or "").lower()
    s = s.replace("sparkling eyes", "")
    s = s.replace("snowflakes", "")
    s = s.replace("snowflake", "")

    patterns = {
        "confetti": re.compile(r"\bconfetti\b"),
        "floating_dust_particles": re.compile(r"\bfloating dust particles?\b"),
        "sparkling_air": re.compile(r"\bsparkling air\b"),
        "sparkles_family": re.compile(r"\bsparkles?\b|\bglittering air\b"),
        "bokeh_family": re.compile(r"\bbokeh\b"),
        "film_grain": re.compile(r"\bfilm grain\b"),
        "bloom": re.compile(r"\bbloom\b"),
        "ambient_occlusion": re.compile(r"\bambient occlusion\b"),
        "volumetric_lighting": re.compile(r"\bvolumetric lighting?\b"),
        "light_leaks": re.compile(r"\bprismatic light leaks?\b|\blight leaks?\b"),
        "chromatic_aberration": re.compile(r"\bchromatic aberration\b"),
        "lens_flare_family": re.compile(r"\blens flares?\b"),
        "dust_family": re.compile(r"\bdust motes?\b|\bdust particles?\b|\bfloating dust\b"),
        "sparkling_family": re.compile(r"\bsparkling\w*\b"),
    }
    return [name for name, pat in patterns.items() if pat.search(s)]


class TestFxCleanup(unittest.TestCase):
    def test_mood_map_descriptions_have_no_disallowed_fx(self):
        with open("mood_map.json", "r", encoding="utf-8") as f:
            mood_map = json.load(f)

        for mood_key, payload in mood_map.items():
            for desc in payload.get("description", []):
                hits = _disallowed_hits(desc)
                self.assertEqual(
                    hits,
                    [],
                    msg=f"mood={mood_key} desc={desc} hits={hits}",
                )

    def test_background_fx_vocab_has_no_disallowed_fx(self):
        with open(os.path.join("vocab", "data", "background_defaults.json"), "r", encoding="utf-8") as f:
            defaults = json.load(f)
        for item in defaults.get("fx", []):
            hits = _disallowed_hits(item)
            self.assertEqual(hits, [], msg=f"default fx={item} hits={hits}")

        with open(os.path.join("vocab", "data", "background_packs.json"), "r", encoding="utf-8") as f:
            packs = json.load(f)
        for pack_name, pack_data in packs.items():
            for item in pack_data.get("fx", []):
                hits = _disallowed_hits(item)
                self.assertEqual(hits, [], msg=f"pack={pack_name} fx={item} hits={hits}")

    def test_location_expander_output_has_no_disallowed_fx(self):
        tags = sorted(background_vocab.LOC_TAG_MAP.keys())

        for i, tag in enumerate(tags):
            for offset in range(3):
                seed = 5000 + i * 11 + offset
                out = expand_location_prompt(tag, seed, "detailed", "auto")
                hits = _disallowed_hits(out)
                self.assertEqual(
                    hits,
                    [],
                    msg=f"tag={tag} seed={seed} out={out} hits={hits}",
                )

    def test_allowlist_terms_remain_generatable(self):
        with open(os.path.join("vocab", "data", "background_packs.json"), "r", encoding="utf-8") as f:
            packs = json.load(f)

        snowflake_terms = [
            item
            for pack_data in packs.values()
            for item in pack_data.get("fx", [])
            if "snowflake" in item.lower()
        ]
        self.assertTrue(snowflake_terms)

        cleaner = __import__("nodes_prompt_cleaner").PromptCleaner()
        cleaned = cleaner.clean(mode="nl", drop_empty_lines=True, text="sparkling eyes, sparkles, bokeh")[0].lower()
        self.assertIn("sparkling eyes", cleaned)
        self.assertNotIn("sparkles", cleaned)
        self.assertNotIn("bokeh", cleaned)


if __name__ == "__main__":
    unittest.main()
