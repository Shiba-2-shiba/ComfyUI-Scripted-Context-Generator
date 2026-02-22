import json
import os
import random
try:
    from .vocab.seed_utils import mix_seed
except ImportError:
    from vocab.seed_utils import mix_seed

# --------------------------------------------------------------------------------
# Data Loading
# --------------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "vocab", "data")

_compat_cache = None
_action_pools_cache = None


def _load_compatibility():
    global _compat_cache
    if _compat_cache is None:
        path = os.path.join(DATA_DIR, "scene_compatibility.json")
        with open(path, "r", encoding="utf-8") as f:
            _compat_cache = json.load(f)
    return _compat_cache


def _load_action_pools():
    global _action_pools_cache
    if _action_pools_cache is None:
        path = os.path.join(DATA_DIR, "action_pools.json")
        with open(path, "r", encoding="utf-8") as f:
            _action_pools_cache = json.load(f)
    return _action_pools_cache


def _build_exclusion_set(compat):
    """(character, loc) の除外ペア set を構築"""
    excluded = set()
    for rule in compat.get("exclusions", []):
        for char in rule["characters"]:
            for loc in rule["denied_locs"]:
                excluded.add((char, loc))
    return excluded


def _get_compatible_locs(subj, compat, excluded, mode="full"):
    """
    subj に対する互換ロケーション一覧を返す。
    mode:
      "genre_only" → タグマッチのみ
      "full"       → タグマッチ + 汎用loc
    Returns: list of (loc, source) tuples
    """
    char_info = compat.get("characters", {}).get(subj)
    if not char_info:
        return []

    result = []
    char_tags = char_info.get("tags", [])

    # 1. タグマッチ
    for tag in char_tags:
        for loc in compat.get("loc_tags", {}).get(tag, []):
            if (subj, loc) not in excluded:
                result.append((loc, f"tag:{tag}"))

    # 2. 汎用loc (full モードのみ)
    if mode == "full":
        for loc in compat.get("universal_locs", []):
            if (subj, loc) not in excluded:
                # タグマッチで既に含まれている場合はスキップ
                if not any(l == loc for l, _ in result):
                    result.append((loc, "universal"))

    return result


# --------------------------------------------------------------------------------
# Node
# --------------------------------------------------------------------------------
class SceneVariator:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "subj":  ("STRING", {"forceInput": True}),
                "costume": ("STRING", {"forceInput": True}),
                "loc":   ("STRING", {"forceInput": True}),
                "action": ("STRING", {"forceInput": True}),
                "seed":  ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "variation_mode": (["original", "genre_only", "full"],),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "DICT")
    RETURN_NAMES = ("subj", "costume", "loc", "action", "debug_info")
    FUNCTION = "variate"
    CATEGORY = "prompt_builder"

    def variate(self, subj, costume, loc, action, seed, variation_mode):
        # Import Schema
        try:
            from .core.schema import PromptContext, DebugInfo
        except ImportError:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
            from core.schema import PromptContext, DebugInfo

        # Wrap inputs in Context
        ctx = PromptContext(
            subj=subj,
            costume=costume,
            loc=loc,
            action=action
        )

        decision_log = {
            "mode": variation_mode,
            "candidates_count": 0,
            "selected_source": "original",
            "selected_loc": loc
        }

        # original モードでは何も変更しない
        if variation_mode == "original":
            debug_info = DebugInfo(
                node="SceneVariator",
                seed=seed,
                decision=decision_log
            )
            return (ctx.subj, ctx.costume, ctx.loc, ctx.action, debug_info.to_dict())

        compat = _load_compatibility()
        action_pools = _load_action_pools()
        excluded = _build_exclusion_set(compat)

        rng = random.Random(mix_seed(seed, "scene_var"))

        # 互換ロケーション一覧を取得
        compatible = _get_compatible_locs(ctx.subj, compat, excluded, mode=variation_mode)

        if not compatible:
            decision_log["warnings"] = ["No compatible locations found"]
            debug_info = DebugInfo(
                node="SceneVariator",
                seed=seed,
                decision=decision_log
            )
            return (ctx.subj, ctx.costume, ctx.loc, ctx.action, debug_info.to_dict())

        # 既存の loc も候補に含める（重み付き選択のため）
        weights = compat.get("priority_weights", {})
        existing_weight = weights.get("existing", 50)
        genre_weight = weights.get("genre_gated", 35)
        universal_weight = weights.get("universal", 15)

        candidates = []
        candidate_weights = []

        # 既存 (original) の組み合わせ
        candidates.append(("existing", ctx.loc))
        candidate_weights.append(existing_weight)

        # 互換ロケーション
        for compat_loc, source in compatible:
            if compat_loc == ctx.loc:
                continue  # 既存と同じlocは除外
            candidates.append((source, compat_loc))
            if source.startswith("tag:"):
                candidate_weights.append(genre_weight)
            else:
                candidate_weights.append(universal_weight)

        decision_log["candidates_count"] = len(candidates)
        # Capture candidates for debug (limit size if needed, but 10-20 is fine)
        decision_log["candidates_preview"] = [f"{c[1]} ({c[0]})" for c in candidates]

        # 重み付きランダム選択
        chosen_source, chosen_loc = rng.choices(
            candidates, weights=candidate_weights, k=1
        )[0]
        
        decision_log["selected_source"] = chosen_source
        decision_log["selected_loc"] = chosen_loc

        # actionの差し替え
        new_action = ctx.action
        if chosen_loc != ctx.loc:
            # action_pools から新しいlocに対応するアクションを選択
            pool_key = chosen_loc
            pool = action_pools.get(pool_key, [])
            # _comment キーを除外
            pool = [a for a in pool if not isinstance(a, str) or not a.startswith("_")]
            if pool:
                new_action_item = rng.choice(pool)
                # Parse dict if new schema (Phase 3+), else string
                if isinstance(new_action_item, dict):
                    new_action = new_action_item.get("text", "")
                    decision_log["action_load"] = new_action_item.get("load")
                else:
                    new_action = str(new_action_item)
                
                decision_log["action_updated"] = True
                decision_log["new_action"] = new_action
        
        debug_info = DebugInfo(
            node="SceneVariator",
            seed=seed,
            decision=decision_log
        )

        return (ctx.subj, ctx.costume, chosen_loc, new_action, debug_info.to_dict())


# --------------------------------------------------------------------------------
# Node Mappings
# --------------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "SceneVariator": SceneVariator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SceneVariator": "Scene Variator (Compatibility Matrix)"
}
