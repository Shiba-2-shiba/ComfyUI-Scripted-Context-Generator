"""Candidate05 action trace contracts, bound to archived real workflow intake."""

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline import action_renderer as CANDIDATE  # noqa: E402


CASES = json.loads((ROOT / "assets" / "fixtures" / "n27_r4_action_trace_cases.json").read_text(encoding="utf-8"))["cases"]


class ActionTraceTests(unittest.TestCase):
    def test_all_real_workflow_bytes_match_frozen_text_and_both_baseline_modes(self):
        self.assertEqual(len(CASES), 512)
        for case in CASES:
            slots = case["slots"]
            with self.subTest(seed=case["run_seed"]):
                for mode in (False, True):
                    actual = CANDIDATE.render_action_slots(slots, mode)
                    expected = case["activity_first_text" if mode else "normal_text"]
                    self.assertEqual(actual.encode(), expected.encode())

    def test_real_workflow_trace_preserves_emitted_slot_sources(self):
        emitted = set()
        for case in CASES:
            slots = case["slots"]
            for mode in (False, True):
                with self.subTest(seed=case["run_seed"], activity_first=mode):
                    parts = CANDIDATE.trace_action_slots(slots, mode)
                    self.assertIsInstance(parts, tuple)
                    self.assertEqual(", ".join(part.text for part in parts), case["activity_first_text" if mode else "normal_text"])
                    for part in parts:
                        self.assertIsInstance(part, CANDIDATE.RenderedActionPart)
                        emitted.add(part.slot_key)
                        if "+" not in part.slot_key and part.slot_key != "default_purpose":
                            self.assertEqual(part.text, str(slots[part.slot_key]).strip())
                    with self.assertRaises(FrozenInstanceError):
                        parts[0].text = "changed"
        self.assertTrue({"primary_action", "posture", "gaze_target", "purpose_clause",
                         "progress_clause", "obstacle_clause", "time_or_weather"} <= emitted)

    def test_primary_choice_and_support_precedence(self):
        slots = {"hand_action": "holding a cup", "posture": "standing quietly",
                 "obstacle_clause": "after hearing a sound", "progress_clause": "while waiting",
                 "optional_micro_action": "checking the door"}
        parts = CANDIDATE.trace_action_slots(slots, True)
        self.assertEqual([(part.slot_key, part.text) for part in parts], [
            ("hand_action", "holding a cup"), ("posture", "standing quietly"),
            ("obstacle_clause", "after hearing a sound"),
        ])
        for first in ("obstacle_clause", "progress_clause", "optional_micro_action"):
            self.assertEqual(CANDIDATE.trace_action_slots(slots, True)[-1].slot_key, first)
            slots.pop(first)

    def test_composite_and_default_primary_are_not_mislabeled_as_one_source(self):
        slots = {"purpose_clause": " waiting quietly ", "anchor": "near the door"}
        part, = CANDIDATE.trace_action_slots(slots)
        self.assertEqual((part.slot_key, part.text), ("purpose_clause+anchor", "waiting quietly near the door"))
        default, = CANDIDATE.trace_action_slots({})
        self.assertEqual((default.slot_key, default.text), ("default_purpose", "holding onto the moment in front of her"))
        anchored, = CANDIDATE.trace_action_slots({"anchor": "near the door"})
        self.assertEqual(anchored.slot_key, "default_purpose+anchor")
        self.assertEqual(anchored.text, "holding onto the moment in front of her near the door")

    def test_deduplication_retains_first_source_and_weather_bigram_rule(self):
        slots = {"primary_action": "holding a cup", "posture": "Standing quietly",
                 "gaze_target": "standing quietly", "purpose_clause": "holding a cup carefully",
                 "social_clause": "standing quietly near the door", "time_or_weather": "standing quietly in rain"}
        parts = CANDIDATE.trace_action_slots(slots, True)
        self.assertEqual([(part.slot_key, part.text) for part in parts], [
            ("primary_action", "holding a cup"), ("posture", "Standing quietly"),
        ])
        self.assertEqual(CANDIDATE.render_action_slots(slots, True), "holding a cup, Standing quietly")


if __name__ == "__main__":
    unittest.main()
