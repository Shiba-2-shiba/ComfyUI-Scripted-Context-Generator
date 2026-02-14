import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nodes_simple_template import SimpleTemplateBuilder
import unittest

class TestComposition(unittest.TestCase):
    def test_composition_mode(self):
        builder = SimpleTemplateBuilder()
        # Mock inputs
        res = builder.build(
            template="", 
            composition_mode=True, 
            seed=42, 
            subj="girl", 
            costume="dress", 
            loc="park", 
            action="walking", 
            garnish="smiling", 
            meta_mood="sunny", 
            meta_style="photo"
        )[0]
        
        print(f"Result: {res}")
        
        # Check if result contains parts from intro, body, end
        # Intro templates have "{subj} wearing {costume}" etc.
        # Body templates have "{action}. {garnish}." etc.
        # End templates have "The location is {loc}" etc.
        
        self.assertIn("girl", res)
        self.assertIn("dress", res)
        self.assertIn("park", res)
        self.assertIn("walking", res)
        
        # Simple check for structure (approximate)
        # Expected: "Intro Body End"
        # Since we use random choice, we can't be 100% sure of exact string without mocking random,
        # but we can check basic validity.
        self.assertTrue(len(res) > 20)

if __name__ == "__main__":
    unittest.main()
