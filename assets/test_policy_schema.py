import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(str(ROOT))

from asset_validator import find_banned_asset_terms
from core.semantic_policy import (
    BANNED_DOMAIN_TERMS,
    POLICY_SCHEMA_VERSION,
    POLICY_TERMS_PATH,
    find_banned_terms,
    load_policy_terms_payload,
)


class TestPolicySchema(unittest.TestCase):
    def test_policy_terms_json_schema_is_valid(self):
        payload = json.loads(POLICY_TERMS_PATH.read_text(encoding="utf-8"))

        self.assertEqual(payload["version"], POLICY_SCHEMA_VERSION)
        self.assertEqual(tuple(payload["domains"].keys()), tuple(BANNED_DOMAIN_TERMS.keys()))
        self.assertEqual(load_policy_terms_payload()["domains"], BANNED_DOMAIN_TERMS)

    def test_runtime_and_validator_detect_identical_shared_terms(self):
        for domain, terms in BANNED_DOMAIN_TERMS.items():
            for term in terms:
                with self.subTest(domain=domain, term=term):
                    sample = f"prefix {term} suffix"
                    self.assertIn(term, find_banned_terms(sample).get(domain, []))
                    self.assertIn((domain, term), find_banned_asset_terms(sample))


if __name__ == "__main__":
    unittest.main()
