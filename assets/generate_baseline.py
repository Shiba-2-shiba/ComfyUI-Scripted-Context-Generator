
import sys
import os
import json
import time
from datetime import datetime

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from core.context_ops import patch_context
from pipeline.content_pipeline import build_prompt_text
from pipeline.context_pipeline import apply_scene_variation, sample_garnish_fields
from pipeline.source_pipeline import parse_prompt_source_fields

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
    
    results = []
    
    for i, data in enumerate(inputs):
        # Use a fixed seed strategy for reproducibility (e.g., input index + constant)
        seed = 1000 + i
        
        # 1. Source parsing
        # Input: json_string (re-dump data), seed
        json_str = json.dumps(data)
        # Returns: (subj, costume, loc, action, meta_mood, meta_style, scene_tags)
        p_res = parse_prompt_source_fields(json_str, seed)
        subj, costume, loc, action, meta_mood, meta_style, scene_tags = p_res
        
        # 2. Context scene stage
        scene_context = patch_context(
            {},
            updates={"subj": subj, "costume": costume, "loc": loc, "action": action, "seed": seed},
        )
        scene_context, debug_info = apply_scene_variation(scene_context, seed, "full")
        subj_v = scene_context.subj
        costume_v = scene_context.costume
        loc_v = scene_context.loc
        action_v = scene_context.action
        debug_info = debug_info.to_dict()
        
        # 3. Context garnish stage
        garnish_res = sample_garnish_fields(
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
        
        raw_prompt = build_prompt_text(
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
        
        # 5. PromptCleaner (Simulated)
        # Assuming user adds PromptCleaner node after simple template
        from nodes_prompt_cleaner import PromptCleaner
        cleaner = PromptCleaner()
        cleaned_res = cleaner.clean(mode="nl", text=raw_prompt) # Use 'nl' mode as per default
        final_prompt = cleaned_res[0]
        
        # Record Result
        # Aggregate debug info
        all_debug = []
        if debug_info:
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
