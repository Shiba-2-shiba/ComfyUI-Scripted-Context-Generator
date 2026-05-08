import unittest

from tools.build_action_pools import build_check_report, read_runtime_action_pools, read_source_action_pools, runtime_location_order


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


if __name__ == "__main__":
    unittest.main()
