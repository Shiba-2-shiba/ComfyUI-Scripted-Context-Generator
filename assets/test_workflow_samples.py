import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from nodes_context import (
    ContextCharacterProfile,
    ContextClothingExpander,
    ContextGarnish,
    ContextInspector,
    ContextLocationExpander,
    ContextMoodExpander,
    ContextPromptBuilder,
    ContextSceneVariator,
    ContextSource,
)
from nodes_prompt_cleaner import PromptCleaner
from workflow_samples import (
    get_recommended_workflow_sample,
    load_workflow_samples,
)
from workflow_widget_validation import load_workflow, validate_workflow_roundtrip, validate_workflow_widgets


class TestWorkflowSamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow_samples = load_workflow_samples()
        cls.recommended_sample = get_recommended_workflow_sample()
        cls.class_map = {
            "PromptCleaner": PromptCleaner,
            "ContextSource": ContextSource,
            "ContextCharacterProfile": ContextCharacterProfile,
            "ContextSceneVariator": ContextSceneVariator,
            "ContextClothingExpander": ContextClothingExpander,
            "ContextLocationExpander": ContextLocationExpander,
            "ContextMoodExpander": ContextMoodExpander,
            "ContextGarnish": ContextGarnish,
            "ContextPromptBuilder": ContextPromptBuilder,
            "ContextInspector": ContextInspector,
        }

    def test_workflow_samples_widgets_match_current_node_specs(self):
        for sample in self.workflow_samples:
            with self.subTest(sample=sample.id):
                workflow = load_workflow(sample.path)
                problems = validate_workflow_widgets(workflow, self.class_map)
                self.assertEqual(problems, [])

    def test_workflow_samples_widget_roundtrip_match_current_specs(self):
        for sample in self.workflow_samples:
            with self.subTest(sample=sample.id):
                workflow = load_workflow(sample.path)
                problems = validate_workflow_roundtrip(workflow, self.class_map)
                self.assertEqual(problems, [])

    def test_recommended_workflow_sample_is_context_first(self):
        self.assertEqual(self.recommended_sample.id, "context")
        self.assertEqual(self.recommended_sample.surface, "primary")

        workflow = load_workflow(self.recommended_sample.path)
        node_types = {node.get("type") for node in workflow.get("nodes", [])}
        self.assertTrue(set(self.recommended_sample.expected_node_types).issubset(node_types))

    def test_context_workflow_is_the_only_active_sample(self):
        self.assertEqual([sample.id for sample in self.workflow_samples], ["context"])
        self.assertTrue(all(sample.surface == "primary" for sample in self.workflow_samples))


if __name__ == "__main__":
    unittest.main()
