
import json
import os
import sys

# New Schema (9 Categories x 3 Intensities)
# joy, playful, anger, sadness, relax, focus, care, impatience, moved

def migrate_vocab():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_file = os.path.join(base_dir, "vocab", "data", "garnish_base_vocab.json")
    
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    old_moods = data.get("MOOD_POOLS", {})
    
    # Define new structure with manual mappings/expansions
    new_moods = {
        "joy": {
            "mild": ["soft smile", "gentle look", "content expression", "faint smile"],
            "medium": ["cheerful", "smile", "radiant", "visible happiness", "beaming"],
            "strong": ["laughing", "big smile", "ecstatic", "grinning widely", "tears of joy"]
        },
        "playful": {
            "mild": ["smirk", "curious look", "mischievous glint", "playful glance"],
            "medium": ["winking", "mischievous smile", "finger on lips", "peace sign"],
            "strong": ["tongue out", "laughing playfully", "yelling happily", "excited gesture"]
        },
        "anger": {
            "mild": ["furrowed brow", "serious look", "annoyed expression", "stern face"],
            "medium": ["scowl", "glaring", "angry eyes", "clenched jaw", "frowning"],
            "strong": ["shouting", "rage", "clenched teeth", "veins popping", "furious scream"]
        },
        "sadness": {
            "mild": ["downcast eyes", "pout", "wistful look", "melancholic gaze"],
            "medium": ["teary eyes", "sad face", "quivering lips", "looking down"],
            "strong": ["crying", "sobbing", "despair", "streaming tears", "covering face"]
        },
        "relax": {
            "mild": ["soft gaze", "calm expression", "posture relaxed", "relaxed lips"],
            "medium": ["eyes closed", "sighing happily", "leaning back", "loose shoulders"],
            "strong": ["dozing off", "slouching", "drooling slightly", "deep sleep", "totally limp"]
        },
        "focus": {
            "mild": ["looking straight ahead", "serious expression", "steady gaze", "alert look"],
            "medium": ["narrowed eyes", "intense stare", "concentrating", "brows knit"],
            "strong": ["tunnel vision", "trance-like focus", "unblinking stare", "ignoring everything else"]
        },
        "care": {
            "mild": ["soft smile", "gentle eyes", "kind expression", "warm gaze"],
            "medium": ["affectionate gaze", "doting look", "patting head", "soothing expression"],
            "strong": ["hugging tightly", "protective embrace", "loving gaze", "filled with love"]
        },
        "impatience": {
            "mild": ["glancing at watch", "tapping foot", "restless gaze", "fidgeting"],
            "medium": ["frowning impatiently", "restless pose", "sighing heavily", "checking phone rapidly"],
            "strong": ["panic", "frantic expression", "sweating", "yelling to hurry", "hair disheveled"]
        },
        "moved": {
            "mild": ["soft eyes", "hand on chest", "touched expression", "gentle awe"],
            "medium": ["teary smile", "touched deeply", "misty eyes", "emotional gaze"],
            "strong": ["weeping with joy", "speechless", "bawling happy tears", "overwhelmed"]
        }
    }

    # Harvest existing tags to populate/enrich new buckets (Best Effort)
    # Joy
    if "joy" in old_moods:
        for tag in old_moods["joy"]:
            if "laugh" in tag or "big" in tag: new_moods["joy"]["strong"].append(tag)
            elif "smile" in tag: new_moods["joy"]["medium"].append(tag)
            else: new_moods["joy"]["medium"].append(tag)
            
    # Sadness
    if "sadness" in old_moods:
        for tag in old_moods["sadness"]:
            if "cry" in tag or "tear" in tag: new_moods["sadness"]["strong"].append(tag)
            elif "frown" in tag: new_moods["sadness"]["medium"].append(tag)
            else: new_moods["sadness"]["mild"].append(tag)

    # Anger
    if "anger" in old_moods:
        for tag in old_moods["anger"]:
            if "shout" in tag or "scom" in tag or "rage" in tag: new_moods["anger"]["strong"].append(tag)
            elif "glare" in tag: new_moods["anger"]["medium"].append(tag)
            else: new_moods["anger"]["mild"].append(tag)

    # Playful
    if "playful" in old_moods:
        for tag in old_moods["playful"]:
            if "tongue" in tag: new_moods["playful"]["strong"].append(tag)
            elif "wink" in tag: new_moods["playful"]["medium"].append(tag)
            else: new_moods["playful"]["mild"].append(tag)
            
    # Map old "focused" to "focus"
    if "focused" in old_moods:
        for tag in old_moods["focused"]:
            new_moods["focus"]["medium"].append(tag)

    # Map "relaxed" to "relax"
    if "relaxed" in old_moods:
        for tag in old_moods["relaxed"]:
            new_moods["relax"]["medium"].append(tag)
            
    # Universal/Neutral -> Relax Mild / Focus Mild
    if "universal" in old_moods:
        for tag in old_moods["universal"]:
            if "calm" in tag or "relax" in tag or "soft" in tag:
                new_moods["relax"]["mild"].append(tag)
            else:
                new_moods["focus"]["mild"].append(tag)

    # Dedupe lists
    for cat in new_moods:
        for intensity in new_moods[cat]:
            new_moods[cat][intensity] = sorted(list(set(new_moods[cat][intensity])))

    data["MOOD_POOLS"] = new_moods
    
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Migrated garnish_base_vocab.json to new schema (9 cats). Saved to {target_file}")

if __name__ == "__main__":
    migrate_vocab()
