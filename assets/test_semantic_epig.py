import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestSemanticEpigConfig(unittest.TestCase):
    def test_known_domains_match_config_modes(self):
        from pipeline.semantic_epig import KNOWN_DOMAINS, domain_enabled, semantic_mode

        for domain in KNOWN_DOMAINS:
            with self.subTest(domain=domain):
                expected_mode = "active"
                self.assertEqual(semantic_mode(domain), expected_mode)
                self.assertTrue(domain_enabled(domain))
                self.assertTrue(domain_enabled(domain, active_only=True))

    def test_unknown_domain_is_off(self):
        from pipeline.semantic_epig import domain_enabled, semantic_mode

        self.assertEqual(semantic_mode("unknown"), "off")
        self.assertFalse(domain_enabled("unknown"))

    def test_add_semantic_debug_merges_domain_payload(self):
        from pipeline.semantic_epig import add_semantic_debug

        decision = {"existing": True}
        add_semantic_debug(decision, "action", {"mode": "passive", "selected_by_semantic": False})

        self.assertEqual(
            decision["semantic_epig"]["action"],
            {"mode": "passive", "selected_by_semantic": False},
        )
        self.assertTrue(decision["existing"])

    def test_merge_config_rejects_invalid_domain_mode(self):
        from pipeline.semantic_epig import _merge_config

        config = _merge_config({"default_mode": "active", "domains": {"action": {"mode": "bad"}}})

        self.assertEqual(config["default_mode"], "active")
        self.assertEqual(config["domains"]["action"]["mode"], "active")


if __name__ == "__main__":
    unittest.main()
