import unittest

from tools.build_action_pools import (
    build_check_report,
    expand_source_payload,
    read_runtime_action_pools,
    read_source_action_pools,
    read_shared_families,
    runtime_location_order,
)


class TestBuildActionPools(unittest.TestCase):
    def test_source_files_rebuild_runtime_action_pools_exactly(self):
        report = build_check_report()

        self.assertEqual(report["ERROR"], [])
        self.assertEqual(report["WARNING"], [])

        summary = [item for item in report["INFO"] if item["code"] == "action_pool_source_summary"][0]
        self.assertEqual(summary["runtime_location_count"], summary["source_location_count"])

    def test_source_location_order_matches_runtime_location_order(self):
        report = {"ERROR": [], "WARNING": [], "INFO": []}
        runtime_payload = read_runtime_action_pools()
        source_payload = read_source_action_pools(report)

        self.assertEqual(report["ERROR"], [])
        self.assertEqual(runtime_location_order(source_payload), runtime_location_order(runtime_payload))

    def test_shared_family_refs_expand_after_location_actions(self):
        report = {"ERROR": [], "WARNING": [], "INFO": []}
        payload = {
            "location": "example_location",
            "actions": [{"text": "standing and checking the first detail", "load": "calm"}],
            "families": [{"name": "shared", "take": 2}],
        }
        families = {
            "shared": [
                {"text": "walking while keeping track of the route", "load": "active"},
                {"text": "pausing to reassess the next step", "load": "calm"},
                {"text": "leaning in with quiet attention", "load": "calm"},
            ]
        }

        expanded = expand_source_payload("example_location", payload, families, report)

        self.assertEqual(report["ERROR"], [])
        self.assertEqual([item["text"] for item in expanded], [
            "standing and checking the first detail",
            "walking while keeping track of the route",
            "pausing to reassess the next step",
        ])

    def test_shared_family_source_is_available_for_action_authoring(self):
        report = {"ERROR": [], "WARNING": [], "INFO": []}
        families = read_shared_families(report)

        self.assertEqual(report["ERROR"], [])
        self.assertIn("public_presence", families)
        self.assertGreaterEqual(len(families["public_presence"]), 4)


if __name__ == "__main__":
    unittest.main()
