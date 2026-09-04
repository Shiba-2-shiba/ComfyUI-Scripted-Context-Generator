import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PromptTemplateNaturalnessTests(unittest.TestCase):
    def test_action_garnish_templates_do_not_use_broken_as_connector(self):
        catalog = json.loads((ROOT / "vocab/data/template_catalog.json").read_text(encoding="utf-8"))
        body_templates = catalog.get("body", catalog.get("body_templates", []))
        texts = [str(item.get("text", "")) for item in body_templates if isinstance(item, dict)]
        self.assertFalse(any("{action} as {garnish}" in text for text in texts))


if __name__ == "__main__":
    unittest.main()
