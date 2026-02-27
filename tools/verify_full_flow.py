import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pick_key_by_type(data, want_list=True):
    for k, v in data.items():
        if isinstance(v, list) and want_list:
            return k, v
        if isinstance(v, str) and not want_list:
            return k, v
    return None, None


def test_character_profile():
    from nodes_character_profile import CharacterProfileNode
    node = CharacterProfileNode()
    subj, hair, eye, personality, palette = node.get_profile("random", "None", 12345)
    assert_true("A solo girl" in subj, "CharacterProfileNode: subj_prompt missing base phrase")
    assert_true(isinstance(personality, str), "CharacterProfileNode: personality not string")
    assert_true(isinstance(palette, str), "CharacterProfileNode: palette not string")

    # Fixed mode (if any character exists)
    if node.profiles:
        fixed_name = list(node.profiles.keys())[0]
        subj2, _, _, _, _ = node.get_profile("fixed", fixed_name, 1)
        assert_true("A solo girl" in subj2, "CharacterProfileNode: fixed subj_prompt invalid")


def test_pack_parser():
    from nodes_pack_parser import PackParser
    node = PackParser()
    # default (prompts.jsonl)
    out = node.parse("{}", 42)
    assert_true(len(out) == 7, "PackParser: output length mismatch")
    subj, costume, loc, action, meta_mood, meta_style, scene_tags = out
    assert_true(isinstance(scene_tags, str), "PackParser: scene_tags not string")
    assert_true(subj is not None, "PackParser: subj is None")
    assert_true(loc is not None, "PackParser: loc is None")

    # explicit json input
    sample = {
        "subj": "A solo girl with short hair",
        "costume": "casual outfit",
        "loc": "classroom",
        "action": "reading a book",
        "meta": {"mood": "quiet", "style": "photo", "tags": {"time": "morning"}}
    }
    out2 = node.parse(json.dumps(sample, ensure_ascii=False), 1)
    assert_true(out2[0] == sample["subj"], "PackParser: explicit subj mismatch")
    assert_true(out2[4] == "quiet", "PackParser: explicit meta_mood mismatch")


def test_scene_variator():
    from nodes_scene_variator import SceneVariator
    node = SceneVariator()
    subj = "A solo girl with long hair"
    costume = "office_lady"
    loc = "office"
    action = "writing at a desk"

    # original
    out = node.variate(subj, costume, loc, action, 100, "original")
    assert_true(out[2] == loc, "SceneVariator: original loc changed")
    assert_true(out[3] == action, "SceneVariator: original action changed")

    # full (may or may not change)
    out2 = node.variate(subj, costume, loc, action, 101, "full")
    assert_true(isinstance(out2[4], dict), "SceneVariator: debug_info not dict")


def test_dictionary_expand():
    from nodes_dictionary_expand import DictionaryExpand
    node = DictionaryExpand()
    data = load_json(ROOT / "mood_map.json")

    key_list, _ = pick_key_by_type(data, want_list=True)
    key_str, _ = pick_key_by_type(data, want_list=False)

    if key_list:
        out = node.expand(key_list, "mood_map.json", "", 123)
        assert_true(isinstance(out[0], str) and out[0] != "", "DictionaryExpand: list key failed")
    if key_str:
        out2 = node.expand(key_str, "mood_map.json", "", 123)
        assert_true(isinstance(out2[0], str), "DictionaryExpand: string key failed")

    # default value fallback
    out3 = node.expand("nonexistent_key", "mood_map.json", "fallback", 0)
    assert_true(out3[0] == "fallback", "DictionaryExpand: default fallback failed")


def test_theme_clothing():
    from nodes_dictionary_expand import ThemeClothingExpander
    node = ThemeClothingExpander()
    out = node.expand_clothing("office_lady", 5, "random", 0.3, "")
    assert_true(isinstance(out[0], str) and out[0] != "", "ThemeClothingExpander: random failed")
    out2 = node.expand_clothing("office_lady", 6, "outerwear_only", 0.9, "")
    assert_true(isinstance(out2[0], str), "ThemeClothingExpander: outerwear_only failed")
    out3 = node.expand_clothing("office_lady", 7, "no_outerwear", 0.9, "")
    assert_true(isinstance(out3[0], str), "ThemeClothingExpander: no_outerwear failed")


def test_theme_location():
    from nodes_dictionary_expand import ThemeLocationExpander
    node = ThemeLocationExpander()
    out_simple = node.expand_location("classroom", 1, "simple")
    out_detailed = node.expand_location("classroom", 1, "detailed")
    assert_true(isinstance(out_simple[0], str), "ThemeLocationExpander: simple failed")
    assert_true(isinstance(out_detailed[0], str), "ThemeLocationExpander: detailed failed")


def test_garnish_and_merge():
    from nodes_garnish import GarnishSampler
    gnode = GarnishSampler()

    scene_tags = json.dumps({"time": "morning"})
    garnish, debug = gnode.sample(
        action_text="walking through a hallway",
        meta_mood_key="quiet",
        seed=111,
        max_items=3,
        include_camera=True,
        context_loc="school hallway",
        context_costume="school_uniform",
        scene_tags=scene_tags,
        personality="shy"
    )
    assert_true(isinstance(debug, dict), "GarnishSampler: debug_info not dict")
    assert_true(isinstance(garnish, str), "GarnishSampler: garnish_string not string")


def test_template_builder_and_cleaner():
    from nodes_simple_template import SimpleTemplateBuilder
    from nodes_prompt_cleaner import PromptCleaner

    tnode = SimpleTemplateBuilder()
    cnode = PromptCleaner()

    # legacy mode
    built = tnode.build(
        template="",
        composition_mode=False,
        seed=3,
        subj="A solo girl",
        costume="casual outfit",
        loc="park",
        action="walking",
        garnish="smiling",
        meta_mood="quiet",
        meta_style="photo"
    )[0]
    assert_true(isinstance(built, str) and built != "", "SimpleTemplateBuilder: legacy build failed")

    # composition mode
    built2 = tnode.build(
        template="",
        composition_mode=True,
        seed=4,
        subj="A solo girl",
        costume="casual outfit",
        loc="park",
        action="walking",
        garnish="smiling",
        meta_mood="quiet",
        meta_style="photo"
    )[0]
    assert_true(isinstance(built2, str) and built2 != "", "SimpleTemplateBuilder: composition build failed")

    cleaned = cnode.clean("A  apple , , in park .", mode="nl", drop_empty_lines=True)[0]
    assert_true("  " not in cleaned, "PromptCleaner: whitespace not collapsed")


def test_full_flow_smoke():
    from nodes_character_profile import CharacterProfileNode
    from nodes_pack_parser import PackParser
    from nodes_scene_variator import SceneVariator
    from nodes_dictionary_expand import ThemeClothingExpander, ThemeLocationExpander, DictionaryExpand
    from nodes_garnish import GarnishSampler
    from nodes_simple_template import SimpleTemplateBuilder
    from nodes_prompt_cleaner import PromptCleaner

    seed = 2026
    profile = CharacterProfileNode()
    pack = PackParser()
    scene = SceneVariator()
    cloth = ThemeClothingExpander()
    loc_exp = ThemeLocationExpander()
    dict_exp = DictionaryExpand()
    garnish = GarnishSampler()
    tmpl = SimpleTemplateBuilder()
    clean = PromptCleaner()

    subj, _, _, personality, palette = profile.get_profile("random", "None", seed)
    _, costume, loc, action, meta_mood, meta_style, scene_tags = pack.parse("{}", seed)
    subj, costume, loc, action, _ = scene.variate(subj, costume, loc, action, seed, "full")

    clothing = cloth.expand_clothing(costume, seed, "random", 0.3, palette)[0]
    location = loc_exp.expand_location(loc, seed, "detailed")[0]
    mood = dict_exp.expand(meta_mood, "mood_map.json", meta_mood, seed)[0]

    garnish_str, _ = garnish.sample(
        action_text=action,
        meta_mood_key=meta_mood,
        seed=seed,
        max_items=3,
        include_camera=False,
        context_loc=loc,
        context_costume=costume,
        scene_tags=scene_tags,
        personality=personality
    )
    prompt = tmpl.build(
        template="",
        composition_mode=False,
        seed=seed,
        subj=subj,
        costume=clothing,
        loc=location,
        action=action,
        garnish=garnish_str,
        meta_mood=mood,
        meta_style=meta_style
    )[0]
    final_prompt = clean.clean(prompt, mode="nl", drop_empty_lines=True)[0]
    assert_true(isinstance(final_prompt, str) and final_prompt != "", "Full flow: final prompt empty")


def main():
    test_character_profile()
    test_pack_parser()
    test_scene_variator()
    test_dictionary_expand()
    test_theme_clothing()
    test_theme_location()
    test_garnish_and_merge()
    test_template_builder_and_cleaner()
    test_full_flow_smoke()
    print("OK: verify_full_flow passed")


if __name__ == "__main__":
    main()
