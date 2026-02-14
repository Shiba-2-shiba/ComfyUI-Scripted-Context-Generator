import json
import os
import glob

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB_DIR = os.path.join(BASE_DIR, "vocab")
DATA_DIR = os.path.join(VOCAB_DIR, "data")
MOOD_MAP_PATH = os.path.join(BASE_DIR, "mood_map.json")

OUTPUT_FILE = "current_resources.md"

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    print(f"Warning: File not found: {path}")
    return {}

def generate_markdown():
    content = []
    content.append("# Current Resources Overview\n")
    content.append("This document is automatically generated from the current vocabulary JSON files.\n")

    # 1. Characters (from scene_compatibility.json)
    content.append("## 1. Characters\n")
    content.append("Defined in `vocab/data/scene_compatibility.json`. Currently links names to tags and default costumes.\n")
    
    compat_data = load_json(os.path.join(DATA_DIR, "scene_compatibility.json"))
    characters = compat_data.get("characters", {})
    
    content.append("| Character Name | Tags | Default Costume |")
    content.append("|---|---|---|")
    
    for name, data in sorted(characters.items()):
        tags = ", ".join(data.get("tags", []))
        costume = data.get("default_costume", "")
        content.append(f"| {name} | {tags} | {costume} |")
    content.append("\n")

    # 1.5. Character Profiles (New - Phase 1)
    content.append("## 1.5. Character Profiles (Phase 1)\n")
    content.append("Defined in `vocab/data/character_profiles.json`. Contains detailed visual traits and personality.\n")
    
    profiles_path = os.path.join(DATA_DIR, "character_profiles.json")
    if os.path.exists(profiles_path):
        profiles_data = load_json(profiles_path)
        characters_p1 = profiles_data.get("characters", {})
        
        content.append("| Name | Hair | Eyes | Personality | Palette |")
        content.append("|---|---|---|---|---|")
        
        for name, data in sorted(characters_p1.items()):
            visuals = data.get("visual_traits", {})
            hair = f"{visuals.get('hair_color', '')} / {visuals.get('hair_style', '')}"
            eyes = visuals.get("eye_color", "")
            pers = data.get("personality", "")
            palette = ", ".join(data.get("color_palette", []))
            content.append(f"| {name} | {hair} | {eyes} | {pers} | {palette} |")
        content.append("\n")
    else:
        content.append("*No character_profiles.json found.*\n")

    # 2. Clothing Themes (from clothing_theme_map.json)
    content.append("## 2. Clothing Themes\n")
    content.append("Defined in `vocab/data/clothing_theme_map.json`. Maps themes to specific outfit types.\n")
    
    clothing_map = load_json(os.path.join(DATA_DIR, "clothing_theme_map.json"))
    
    content.append("| Theme Key | Dresses | Separates | Outerwear |")
    content.append("|---|---|---|---|")
    
    for theme, data in sorted(clothing_map.items()):
        dresses = "<br>".join(data.get("dresses", []))
        separates = "<br>".join(data.get("separates", []))
        outerwear = "<br>".join(data.get("outerwear", []))
        content.append(f"| {theme} | {dresses} | {separates} | {outerwear} |")
    content.append("\n")

    # 3. Locations (from scene_compatibility.json loc_tags)
    content.append("## 3. Locations\n")
    content.append("Defined in `vocab/data/scene_compatibility.json` (Category Mapping) and `vocab/data/background_packs.json` (Details).\n")
    
    loc_tags = compat_data.get("loc_tags", {})
    
    content.append("| Category (Tag) | Location Keys |")
    content.append("|---|---|")
    
    for tag, locs in sorted(loc_tags.items()):
        loc_str = "<br>".join(locs)
        content.append(f"| {tag} | {loc_str} |")
    content.append("\n")

    # 4. Moods (from mood_map.json)
    content.append("## 4. Moods\n")
    content.append("Defined in `mood_map.json`. Affects lighting and atmosphere.\n")
    
    mood_data = load_json(MOOD_MAP_PATH)
    
    content.append("| Mood Key | Example Description (1st entry) | Total Variations |")
    content.append("|---|---|---|")
    
    for key, variations in sorted(mood_data.items()):
        example = variations[0] if variations else ""
        # Truncate example for table readability
        if len(example) > 100:
            example = example[:97] + "..."
        count = len(variations)
        content.append(f"| {key} | {example} | {count} |")
    content.append("\n")

    # Write to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(content))
    
    print(f"Documentation generated at: {os.path.abspath(OUTPUT_FILE)}")

if __name__ == "__main__":
    generate_markdown()
