
import sys
import os
import json
import time
from datetime import datetime

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Import Nodes
from nodes_pack_parser import PackParser
from nodes_scene_variator import SceneVariator
from nodes_garnish import GarnishSampler
from nodes_simple_template import SimpleTemplateBuilder

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def generate_baseline():
    print("=== Starting Baseline Generation ===")
    
    # Paths
    fixtures_path = os.path.join(current_dir, "fixtures", "benchmark_inputs.jsonl")
    results_dir = os.path.join(current_dir, "results")
    ensure_dir(results_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(results_dir, f"baseline_{timestamp}.json")
    
    # Load Fixtures
    inputs = []
    with open(fixtures_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                inputs.append(json.loads(line))
    
    print(f"Loaded {len(inputs)} inputs.")
    
    # Instantiate Nodes
    parser_node = PackParser()
    scene_node = SceneVariator()
    garnish_node = GarnishSampler()
    template_node = SimpleTemplateBuilder()
    
    results = []
    
    for i, data in enumerate(inputs):
        # Use a fixed seed strategy for reproducibility (e.g., input index + constant)
        seed = 1000 + i
        
        # 1. PackParser
        # Input: json_string (re-dump data), seed
        json_str = json.dumps(data)
        # Returns: (subj, costume, loc, action, meta_mood, meta_style, scene_tags)
        p_res = parser_node.parse(json_str, seed)
        subj, costume, loc, action, meta_mood, meta_style, scene_tags = p_res
        
        # 2. SceneVariator
        # Input: subj, costume, loc, action, seed, variation_mode
        # Using "full" to test the logic fully
        sv_res = scene_node.variate(subj, costume, loc, action, seed, "full")
        # Handle 5-tuple return (added debug_info in Phase 2)
        if len(sv_res) == 5:
            subj_v, costume_v, loc_v, action_v, debug_info = sv_res
        else:
            # Fallback for backward compatibility if needed, though we just updated the node
            subj_v, costume_v, loc_v, action_v = sv_res[:4]
            debug_info = {}
        
        # 3. GarnishSampler
        # Input: action_text, meta_mood_key, seed, max_items, include_camera, context_loc, context_costume, scene_tags, personality
        garnish_res = garnish_node.sample(
            action_text=action_v,
            meta_mood_key=meta_mood,
            seed=seed,
            max_items=3,
            include_camera=False,
            context_loc=loc_v,
            context_costume=costume_v,
            scene_tags=scene_tags,
            personality="" # Not in benchmark input explicitly, leaving empty
        )
        
        garnish_debug = {}
        if len(garnish_res) == 2:
            garnish, garnish_debug = garnish_res
        else:
            garnish = garnish_res[0]
        
        # 4. SimpleTemplateBuilder
        # Input: template, seed, subj, costume, loc, action, garnish, meta_mood, meta_style
        # Using default template (passed as empty string to trigger default logic?? 
        # Actually SimpleTemplateBuilder code checks for empty string or default string.
        # Let's pass the default string explicitly or just use the node's method default if possible.
        # The node method signature is: build(self, template, seed, ...)
        # We will parse a specific template string to be sure, or rely on auto-load.
        # Let's assume auto-load from templates.txt is desired.
        tb_res = template_node.build(
            template="", # Trigger auto-load
            composition_mode=True,
            seed=seed,
            subj=subj_v,
            costume=costume_v,
            loc=loc_v,
            action=action_v,
            garnish=garnish,
            meta_mood=meta_mood,
            meta_style=meta_style
        )
        raw_prompt = tb_res[0]
        
        # 5. PromptCleaner (Simulated)
        # Assuming user adds PromptCleaner node after simple template
        from nodes_prompt_cleaner import PromptCleaner
        cleaner = PromptCleaner()
        cleaned_res = cleaner.clean(raw_prompt, mode="nl") # Use 'nl' mode as per default
        final_prompt = cleaned_res[0]
        
        # Record Result
        # Aggregate debug info
        all_debug = []
        if debug_info: # SceneVariator debug
            all_debug.append(debug_info)
        if garnish_debug:
            all_debug.append(garnish_debug)

        record = {
            "index": i,
            "seed": seed,
            "input": data,
            "output": {
                "subj": subj_v,
                "costume": costume_v,
                "loc": loc_v,
                "action": action_v,
                "garnish": garnish,
                "final_prompt": final_prompt,
                "debug_info": all_debug
            }
        }
        results.append(record)
        
    # Save Results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"Baseline generated at: {output_path}")
    return output_path

if __name__ == "__main__":
    generate_baseline()
