import importlib
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

import __init__ as package_registry
from cutover_plan import gate_map, load_cutover_plan, node_map
from workflow_samples import load_workflow_samples


class TestCutoverPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = load_cutover_plan()
        cls.gates = gate_map()
        cls.nodes = node_map()
        cls.workflow_samples = {sample.id: sample for sample in load_workflow_samples()}

    def test_every_cutover_entry_uses_known_gate_ids(self):
        for node in self.plan["nodes"]:
            with self.subTest(node=node.node_name):
                self.assertGreaterEqual(node.retirement_wave, 1)
                self.assertGreater(node.retirement_order, 0)
                self.assertTrue(node.successor.strip())
                self.assertTrue(node.gate_ids)
                for gate_id in node.gate_ids:
                    self.assertIn(gate_id, self.gates)

    def test_cutover_plan_covers_all_compat_and_transition_nodes(self):
        expected_nodes = set()
        for surface_name in ("compat", "transition"):
            for module_name in package_registry.NODE_SURFACE_GROUPS[surface_name]:
                module = importlib.import_module(module_name)
                expected_nodes.update(module.NODE_CLASS_MAPPINGS.keys())

        self.assertEqual(set(self.nodes.keys()), expected_nodes)

    def test_cutover_entries_match_registry_surface_groups(self):
        for node in self.plan["nodes"]:
            with self.subTest(node=node.node_name):
                self.assertIn(node.surface, ("compat", "transition"))
                self.assertIn(node.module, package_registry.NODE_SURFACE_GROUPS[node.surface])

    def test_workflow_ids_in_cutover_plan_reference_known_samples(self):
        known_workflow_ids = set(self.workflow_samples.keys())
        for node in self.plan["nodes"]:
            with self.subTest(node=node.node_name):
                for workflow_id in node.workflow_ids:
                    self.assertIn(workflow_id, known_workflow_ids)

    def test_compat_entries_require_compat_sample_gate(self):
        for node in self.plan["nodes"]:
            with self.subTest(node=node.node_name):
                if node.surface == "compat":
                    self.assertIn("compat_sample_not_required", node.gate_ids)
                else:
                    self.assertNotIn("compat_sample_not_required", node.gate_ids)

    def test_transition_nodes_retire_before_compat_nodes(self):
        transition_waves = {
            node.retirement_wave
            for node in self.plan["nodes"]
            if node.surface == "transition"
        }
        compat_waves = {
            node.retirement_wave
            for node in self.plan["nodes"]
            if node.surface == "compat"
        }
        if compat_waves:
            self.assertLess(max(transition_waves), min(compat_waves))

    def test_retirement_order_is_unique_within_each_wave(self):
        by_wave = {}
        for node in self.plan["nodes"]:
            by_wave.setdefault(node.retirement_wave, []).append(node.retirement_order)

        for wave, orders in by_wave.items():
            with self.subTest(wave=wave):
                self.assertEqual(len(orders), len(set(orders)))

    def test_cutover_inventory_is_empty_after_all_wave_retirements(self):
        self.assertEqual(self.plan["nodes"], ())


if __name__ == "__main__":
    unittest.main()
