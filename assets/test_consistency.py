import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nodes_simple_template import SimpleTemplateBuilder

class TestConsistency(unittest.TestCase):
    def test_winter_conflict(self):
        builder = SimpleTemplateBuilder()
        # Input "winter" should conflict with "warm sun" in templates_body.txt
        # We run multiple times to ensure the random selection avoids the conflict.
        
        conflict_found = False
        for i in range(20):
            res = builder.build(
                template="", 
                composition_mode=True, 
                seed=i, 
                subj="girl", 
                loc="winter street"
            )[0]
            
            if "warm sun" in res:
                conflict_found = True
                print(f"FAILURE at seed {i}: {res}")
                break
        
        self.assertFalse(conflict_found, "Generated prompt contained 'warm sun' despite 'winter' input.")

    def test_night_conflict(self):
        builder = SimpleTemplateBuilder()
        # Input "night" should conflict with "sunny" and "blue sky"
        
        conflict_found = False
        for i in range(20):
            res = builder.build(
                template="", 
                composition_mode=True, 
                seed=i+100, 
                subj="girl", 
                loc="night city"
            )[0]
            
            if "sunny" in res or "blue sky" in res:
                conflict_found = True
                print(f"FAILURE at seed {i+100}: {res}")
                break
        
        self.assertFalse(conflict_found, "Generated prompt contained 'sunny'/'blue sky' despite 'night' input.")

if __name__ == "__main__":
    unittest.main()
