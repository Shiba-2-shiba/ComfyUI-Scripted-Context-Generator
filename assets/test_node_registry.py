import importlib
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

import __init__ as package_registry


MODULE_NAMES = [
    "nodes_prompt_cleaner",
    "nodes_context",
]

EXPECTED_SURFACE_GROUPS = {
    "primary": ("nodes_context",),
    "transition": (),
    "compat": (),
    "utility": ("nodes_prompt_cleaner",),
}


class TestNodeRegistry(unittest.TestCase):
    def test_package_registry_matches_module_exports(self):
        for module_name in MODULE_NAMES:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                for node_name, node_class in module.NODE_CLASS_MAPPINGS.items():
                    self.assertIs(package_registry.NODE_CLASS_MAPPINGS[node_name], node_class)
                for node_name, display_name in module.NODE_DISPLAY_NAME_MAPPINGS.items():
                    self.assertEqual(package_registry.NODE_DISPLAY_NAME_MAPPINGS[node_name], display_name)

    def test_surface_groups_are_explicit(self):
        self.assertEqual(package_registry.NODE_SURFACE_GROUPS, EXPECTED_SURFACE_GROUPS)

    def test_compat_surface_is_empty(self):
        self.assertEqual(EXPECTED_SURFACE_GROUPS["compat"], ())

    def test_transition_and_utility_categories_are_explicit(self):
        cleaner_module = importlib.import_module("nodes_prompt_cleaner")
        self.assertEqual(cleaner_module.PromptCleaner.CATEGORY, "prompt_builder/utility")


if __name__ == "__main__":
    unittest.main()
