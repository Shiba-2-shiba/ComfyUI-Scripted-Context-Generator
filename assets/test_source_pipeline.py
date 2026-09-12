import os
import sys
import unittest
import json
from pathlib import Path


sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from pipeline.source_pipeline import load_prompt_source_payload, parse_prompt_source_fields


class TestSourcePipeline(unittest.TestCase):
    def test_default_prompt_sampling_prefers_non_discouraged_daily_payloads(self):
        payload = load_prompt_source_payload("{}", 42, source_mode="auto")
        self.assertIsInstance(payload, dict)
        self.assertNotIn(payload.get("meta", {}).get("mood", ""), {
            "melancholic_sadness",
            "intense_anger",
            "creepy_fear",
        })
        self.assertNotIn(payload.get("loc", ""), {"rainy_alley", "rainy_bus_stop", "winter_street"})

    def test_explicit_json_input_is_preserved(self):
        sample = '{"subj":"girl","costume":"office_lady","loc":"modern_office","action":"reading","meta":{"mood":"quiet_focused","style":"clean lineart"}}'
        parsed = parse_prompt_source_fields(sample, 1, source_mode="auto")
        self.assertEqual(parsed[0], "girl")
        self.assertEqual(parsed[2], "modern_office")
        self.assertEqual(parsed[4], "quiet_focused")

    def test_all_prompt_subjects_have_character_compat_tags(self):
        root = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        compat = json.loads((root / "vocab" / "data" / "scene_compatibility.json").read_text(encoding="utf-8"))
        characters = set(compat.get("characters", {}))
        subjects = set()
        for line in (root / "prompts.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            subjects.add(json.loads(line)["subj"])
        self.assertEqual(sorted(subjects - characters), [])


if __name__ == "__main__":
    unittest.main()
