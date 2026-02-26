import traceback

def log_import_error(name, error):
    print(f"\033[91m[ComfyUI-Nodes] Error importing {name}:\033[0m")
    traceback.print_exc()

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# PackParser
try:
    from .nodes_pack_parser import PackParser
    NODE_CLASS_MAPPINGS["PackParser"] = PackParser
    NODE_DISPLAY_NAME_MAPPINGS["PackParser"] = "Pack Parser (JSONL)"
except ImportError as e:
    log_import_error("PackParser", e)

# SimpleTemplateBuilder
try:
    from .nodes_simple_template import SimpleTemplateBuilder
    NODE_CLASS_MAPPINGS["SimpleTemplateBuilder"] = SimpleTemplateBuilder
    NODE_DISPLAY_NAME_MAPPINGS["SimpleTemplateBuilder"] = "Simple Template Builder"
except ImportError as e:
    log_import_error("SimpleTemplateBuilder", e)

# DictionaryExpand, etc.
try:
    from .nodes_dictionary_expand import DictionaryExpand, ThemeClothingExpander, ThemeLocationExpander
    NODE_CLASS_MAPPINGS["DictionaryExpand"] = DictionaryExpand
    NODE_CLASS_MAPPINGS["ThemeClothingExpander"] = ThemeClothingExpander
    NODE_CLASS_MAPPINGS["ThemeLocationExpander"] = ThemeLocationExpander
    NODE_DISPLAY_NAME_MAPPINGS["DictionaryExpand"] = "Dictionary Expand (JSON)"
    NODE_DISPLAY_NAME_MAPPINGS["ThemeClothingExpander"] = "Theme Clothing Expander"
    NODE_DISPLAY_NAME_MAPPINGS["ThemeLocationExpander"] = "Theme Location Expander"
except ImportError as e:
    log_import_error("DictionaryExpand/ThemeExpanders", e)

# SceneVariator
try:
    from .nodes_scene_variator import SceneVariator
    NODE_CLASS_MAPPINGS["SceneVariator"] = SceneVariator
    NODE_DISPLAY_NAME_MAPPINGS["SceneVariator"] = "Scene Variator (Compatibility Matrix)"
except ImportError as e:
    log_import_error("SceneVariator", e)
    print("\033[93m[ComfyUI-Nodes] Warning: nodes_scene_variator.py import failed.\033[0m")

# GarnishNodes
try:
    from .nodes_garnish import GarnishSampler
    NODE_CLASS_MAPPINGS["GarnishSampler"] = GarnishSampler
    NODE_DISPLAY_NAME_MAPPINGS["GarnishSampler"] = "Garnish Sampler (Mood & Pose)"
except ImportError as e:
    log_import_error("GarnishNodes", e)
    print("\033[93m[ComfyUI-Nodes] Warning: nodes_garnish.py import failed.\033[0m")

# PromptCleaner
try:
    from .nodes_prompt_cleaner import PromptCleaner
    NODE_CLASS_MAPPINGS["PromptCleaner"] = PromptCleaner
    NODE_DISPLAY_NAME_MAPPINGS["PromptCleaner"] = "Prompt Cleaner"
except ImportError as e:
    log_import_error("PromptCleaner", e)
    print("\033[93m[ComfyUI-Nodes] Warning: nodes_prompt_cleaner.py import failed.\033[0m")

# CharacterProfileNode
try:
    from .nodes_character_profile import CharacterProfileNode
    NODE_CLASS_MAPPINGS["CharacterProfileNode"] = CharacterProfileNode
    NODE_DISPLAY_NAME_MAPPINGS["CharacterProfileNode"] = "Character Profile Generator"
except ImportError as e:
    log_import_error("CharacterProfileNode", e)
    print("\033[93m[ComfyUI-Nodes] Warning: nodes_character_profile.py import failed.\033[0m")

WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
