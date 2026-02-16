import json
import os

# Configuration
VOCAB_DIR = os.path.join(os.path.dirname(__file__), "../vocab/data")
BACKGROUND_PACKS_PATH = os.path.join(VOCAB_DIR, "background_packs.json")

# Alias Updates Map
ALIAS_UPDATES = {
    # No aliases originally
    "boardroom": ["meeting room", "conference room"],
    "poolside_resort": ["hotel pool", "resort pool"],
    "illuminated_park": ["night park", "winter illumination"],
    "cozy_bookstore": ["bookshop", "old bookstore"],
    "picnic_park": ["grassy park", "public park"],
    "clockwork_workshop": ["steampunk workshop", "inventor's lab"],

    # Few aliases enrichment
    "modern_office": ["corporate office", "open plan office"],
    "fantasy_forest": ["ancient forest", "mystical woods"],
    "rainy_bus_stop": ["bus stop", "waiting shelter"],
    "luxury_hotel_room": ["hotel room", "five star suite"],
    "steampunk_airship": ["airship deck", "flying ship"],
    "clean_modern_kitchen": ["modern kitchen", "chef's kitchen"],
    "elegant_dining_room": ["formal dining room", "banquet hall"],
    "luxury_bathroom": ["modern bathroom", "spa bathroom"],
    "cozy_living_room": ["living room", "lounge"],
    "suburban_neighborhood": ["residential area", "quiet street"],
    "mountain_resort": ["mountain lodge", "ski resort"],
    "school_library": ["library shelves", "reading room"],
    "school_gym_hall": ["assembly hall", "school gym"],
    "office_elevator": ["elevator", "lift"],
    "surveillance_room": ["security room", "monitor room"],
    "luxury_hotel_lobby": ["hotel lobby", "grand entrance"],
    "karaoke_bar": ["karaoke room", "ktv"],
    "messy_kitchen": ["dirty kitchen", "cluttered kitchen"],
    "yoga_studio": ["yoga class", "dance studio"],
    "stadium_court": ["running track", "sports field"],
    "recording_studio": ["sound studio", "music studio"],
    "opera_house": ["theater stage", "concert hall"],
    "dragon_lair": ["dragon cave", "treasure hoard"],
    "shinto_shrine": ["shrine grounds", "sacred place"],
    "bamboo_forest": ["bamboo grove", "arashiyama"],
    "wave_barrel": ["surfing tube", "inside a wave"],
    "antique_shop": ["curio shop", "vintage store"],
    "street_cafe": ["sidewalk cafe", "terrace"],
    "shopping_mall_atrium": ["shopping mall", "department store"],
    "fashion_boutique": ["clothing store", "designer shop"],
    "botanical_garden": ["greenhouse", "conservatory"],
    "spaceship_bridge": ["starship bridge", "command center"],
    "cyber_lab": ["tech lab", "research facility"],
    "airship_deck": ["sky deck", "observation deck"],
    "aquarium": ["underwater tunnel", "fish tank"],
    "school_classroom": ["classroom", "lecture hall"],
    "school_rooftop": ["school roof", "fenced rooftop"],
    "abandoned_shrine": ["ruined shrine", "haunted shrine"]
}

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def update_aliases():
    print(f"Loading data from {BACKGROUND_PACKS_PATH}...")
    try:
        bg_packs = load_json(BACKGROUND_PACKS_PATH)
    except FileNotFoundError as e:
        print(f"Error loading file: {e}")
        return

    updated_count = 0
    
    for loc_id, new_aliases in ALIAS_UPDATES.items():
        if loc_id in bg_packs:
            # Merge with existing, dedup, normalize
            current_aliases = bg_packs[loc_id].get("aliases", [])
            if not isinstance(current_aliases, list):
                current_aliases = []
            
            # Combine
            combined = current_aliases + new_aliases
            
            # Normalize and dedup
            normalized = []
            seen = set()
            for a in combined:
                norm = a.strip().lower()
                if norm and norm not in seen:
                    normalized.append(norm)
                    seen.add(norm)
            
            # Sort for stability
            normalized.sort()
            
            # Update only if changed
            if normalized != sorted(list(set([a.strip().lower() for a in current_aliases]))):
                bg_packs[loc_id]["aliases"] = normalized
                updated_count += 1
                # print(f"Updated {loc_id}: {normalized}")

    if updated_count > 0:
        save_json(BACKGROUND_PACKS_PATH, bg_packs)
        print(f"Successfully updated aliases for {updated_count} locations.")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    update_aliases()
