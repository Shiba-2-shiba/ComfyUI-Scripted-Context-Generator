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
    from pipeline.character_profile_pipeline import build_character_profile, load_character_profiles

    profiles = load_character_profiles()
    result = build_character_profile(12345, "random", "None", profiles)
    subj = result["subj_prompt"]
    personality = result["personality"]
    palette = result["color_palette_str"]

    assert_true("A solo girl" in subj, "character profile: subj_prompt missing base phrase")
    assert_true(isinstance(personality, str), "character profile: personality not string")
    assert_true(isinstance(palette, str), "character profile: palette not string")

    # Fixed mode (if any character exists)
    if profiles:
        fixed_name = list(profiles.keys())[0]
        subj2 = build_character_profile(1, "fixed", fixed_name, profiles)["subj_prompt"]
        assert_true("A solo girl" in subj2, "character profile: fixed subj_prompt invalid")


def test_pack_parser():
    from pipeline.source_pipeline import parse_prompt_source_fields
    # default (prompts.jsonl)
    out = parse_prompt_source_fields("{}", 42)
    assert_true(len(out) == 7, "prompt source fields: output length mismatch")
    subj, costume, loc, action, meta_mood, meta_style, scene_tags = out
    assert_true(isinstance(scene_tags, str), "prompt source fields: scene_tags not string")
    assert_true(subj is not None, "prompt source fields: subj is None")
    assert_true(loc is not None, "prompt source fields: loc is None")

    # explicit json input
    sample = {
        "subj": "A solo girl with short hair",
        "costume": "casual outfit",
        "loc": "classroom",
        "action": "reading a book",
        "meta": {"mood": "quiet", "style": "photo", "tags": {"time": "morning"}}
    }
    out2 = parse_prompt_source_fields(json.dumps(sample, ensure_ascii=False), 1)
    assert_true(out2[0] == sample["subj"], "prompt source fields: explicit subj mismatch")
    assert_true(out2[4] == "quiet", "prompt source fields: explicit meta_mood mismatch")


def test_context_scene_stage():
    from core.context_codec import context_from_json
    from nodes_context import ContextSceneVariator

    node = ContextSceneVariator()
    subj = "A solo girl with long hair"
    costume = "office_lady"
    loc = "office"
    action = "writing at a desk"
    base_context = json.dumps({
        "subj": subj,
        "costume": costume,
        "loc": loc,
        "action": action,
        "seed": 100,
    }, ensure_ascii=False)

    # original
    context_json = node.variate_context(base_context, 100, "original")[0]
    ctx = context_from_json(context_json, default_seed=100)
    assert_true(ctx.loc == loc, "context scene stage: original loc changed")
    assert_true(ctx.action == action, "context scene stage: original action changed")

    # full (may or may not change)
    out2 = node.variate_context(base_context, 101, "full")[0]
    ctx2 = context_from_json(out2, default_seed=101)
    assert_true(isinstance(ctx2.loc, str), "context scene stage: loc not string")
    assert_true(isinstance(ctx2.action, str), "context scene stage: action not string")


def test_dictionary_expand():
    from pipeline.content_pipeline import expand_dictionary_value
    data = load_json(ROOT / "mood_map.json")

    key_list, _ = pick_key_by_type(data, want_list=True)
    key_str, _ = pick_key_by_type(data, want_list=False)

    if key_list:
        out = expand_dictionary_value(key_list, "mood_map.json", "", 123)
        assert_true(isinstance(out[0], str) and out[0] != "", "mood expansion: list key failed")
    if key_str:
        out2 = expand_dictionary_value(key_str, "mood_map.json", "", 123)
        assert_true(isinstance(out2[0], str), "mood expansion: string key failed")

    # default value fallback
    out3 = expand_dictionary_value("nonexistent_key", "mood_map.json", "fallback", 0)
    assert_true(out3[0] == "fallback", "mood expansion: default fallback failed")


def test_theme_clothing():
    from pipeline.content_pipeline import expand_clothing_prompt

    out = expand_clothing_prompt("office_lady", 5, "random", 0.3, "")
    assert_true(isinstance(out, str) and out != "", "clothing expansion: random failed")
    out2 = expand_clothing_prompt("office_lady", 6, "outerwear_only", 0.9, "")
    assert_true(isinstance(out2, str), "clothing expansion: outerwear_only failed")
    out3 = expand_clothing_prompt("office_lady", 7, "no_outerwear", 0.9, "")
    assert_true(isinstance(out3, str), "clothing expansion: no_outerwear failed")


def test_theme_location():
    from pipeline.content_pipeline import expand_location_prompt

    out_simple = expand_location_prompt("classroom", 1, "simple")
    out_detailed = expand_location_prompt("classroom", 1, "detailed")
    assert_true(isinstance(out_simple, str), "location expansion: simple failed")
    assert_true(isinstance(out_detailed, str), "location expansion: detailed failed")


def test_garnish_and_merge():
    from pipeline.context_pipeline import sample_garnish_fields

    scene_tags = json.dumps({"time": "morning"})
    garnish, debug = sample_garnish_fields(
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
    assert_true(isinstance(debug, dict), "context garnish stage: debug_info not dict")
    assert_true(isinstance(garnish, str), "context garnish stage: garnish string not string")


def test_template_builder_and_cleaner():
    from nodes_prompt_cleaner import PromptCleaner
    from pipeline.content_pipeline import build_prompt_text

    cnode = PromptCleaner()

    built = build_prompt_text(
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
    )
    assert_true(isinstance(built, str) and built != "", "prompt assembly: default build failed")

    built2 = build_prompt_text(
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
    )
    assert_true(isinstance(built2, str) and built2 != "", "prompt assembly: composition build failed")

    cleaned = cnode.clean("A  apple , , in park .", mode="nl", drop_empty_lines=True)[0]
    assert_true("  " not in cleaned, "PromptCleaner: whitespace not collapsed")


def test_full_flow_smoke():
    from pipeline.character_profile_pipeline import build_character_profile, load_character_profiles
    from pipeline.content_pipeline import build_prompt_text, expand_clothing_prompt, expand_dictionary_value, expand_location_prompt
    from pipeline.source_pipeline import parse_prompt_source_fields
    from core.context_ops import patch_context
    from pipeline.context_pipeline import apply_scene_variation, sample_garnish_fields
    from nodes_prompt_cleaner import PromptCleaner

    seed = 2026
    profiles = load_character_profiles()
    clean = PromptCleaner()

    profile_result = build_character_profile(seed, "random", "None", profiles)
    subj = profile_result["subj_prompt"]
    personality = profile_result["personality"]
    palette = profile_result["color_palette_str"]
    _, costume, loc, action, meta_mood, meta_style, scene_tags = parse_prompt_source_fields("{}", seed)
    scene_ctx = patch_context(
        {},
        updates={"subj": subj, "costume": costume, "loc": loc, "action": action, "seed": seed},
    )
    scene_ctx, _scene_debug = apply_scene_variation(scene_ctx, seed, "full")
    subj = scene_ctx.subj
    costume = scene_ctx.costume
    loc = scene_ctx.loc
    action = scene_ctx.action

    clothing = expand_clothing_prompt(costume, seed, "random", 0.3, palette)
    location = expand_location_prompt(loc, seed, "detailed")
    mood = expand_dictionary_value(meta_mood, "mood_map.json", meta_mood, seed)[0]

    garnish_str, _ = sample_garnish_fields(
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
    prompt = build_prompt_text(
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
    )
    final_prompt = clean.clean(prompt, mode="nl", drop_empty_lines=True)[0]
    assert_true(isinstance(final_prompt, str) and final_prompt != "", "Full flow: final prompt empty")


def main():
    test_character_profile()
    test_pack_parser()
    test_context_scene_stage()
    test_dictionary_expand()
    test_theme_clothing()
    test_theme_location()
    test_garnish_and_merge()
    test_template_builder_and_cleaner()
    test_full_flow_smoke()
    print("OK: verify_full_flow passed")


if __name__ == "__main__":
    main()
