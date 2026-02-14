#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prompt Builder Evaluation Script Final (The Robust Benchmark)
----------------------------------------------------------
Features:
1. Correct Pipeline: Uses 'action_merged' for final prompt generation.
2. Robust Normalization: Core Unique logic to strip stopwords/symbols.
3. Semantic Checks: Separates Tech Anachronism from Semantic Mood Conflicts.
4. Deep Stats (v2 revived): Top-N Share, Entropy, N-gram Repetition.
5. Auto-Detect: Automatically reports top frequent words per field.
6. Multi-Run Stability: Runs generations multiple times to calculate stability (CV, Jaccard).
7. Context-Aware Style Check: Flags "illustration/art style" but allows "art museum".
8. Watch Attribution: Detailed breakdown of which field introduces specific terms.
"""

from __future__ import annotations
import argparse, csv, json, os, re, math, statistics
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any, Set

# --- Import Nodes ---
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from nodes_pack_parser import PackParser
    from nodes_dictionary_expand import DictionaryExpand, ThemeClothingExpander, ThemeLocationExpander
    from nodes_simple_template import SimpleTemplateBuilder
    from nodes_garnish import GarnishSampler, ActionMerge
except ImportError as e:
    print(f"[Fatal Error] Failed to import nodes: {e}")
    exit(1)

# --- Import Vocab Checks ---
try:
    import improved_pose_emotion_vocab
    _is_tech_violation = getattr(improved_pose_emotion_vocab, "_is_out_of_context", None)
except ImportError:
    _is_tech_violation = None


# --- Configuration ---

DEFAULT_WATCH_MAP = {
    # "common_verbs" separated to avoid noise in bias detection
    "action_merged": ["phone", "smartphone", "book", "reading", "guitar", "microphone"],
    "garnish": ["phone", "book", "smile", "particle", "light", "camera"],
    "loc": ["classroom", "ruins", "forest"],
    "final": ["phone", "gun", "sword"]
}

# --- GoalScore (v4) defaults ---
# Evaluation-side heuristics for the refactor goals:
#  ① action_raw should be abstract (intent), not concrete props
#  ② intent should be materialized into coherent concrete actions/props
#  ③ role/prop mismatches (e.g., knight + bow) should be suppressed

# Concrete props that should NOT live in action_raw after the “intent -> concrete” refactor.
RAW_CONCRETE_TERMS_DEFAULT = [
    # devices
    "phone", "smartphone", "tablet", "laptop", "camera",
    # reading
    "book", "novel", "magazine", "newspaper", "scroll",
    # weapons
    "sword", "katana", "dagger", "knife", "spear", "lance", "axe", "mace", "hammer",
    "bow", "crossbow", "arrow", "arrows", "quiver",
    "gun", "pistol", "rifle", "shotgun",
    # instruments
    "guitar", "violin", "cello", "piano", "microphone",
]

# Category lexicons used for intent-completion / mismatch checks.
PROP_CATEGORIES_DEFAULT: Dict[str, List[str]] = {
    "device": ["phone", "smartphone", "tablet", "laptop", "camera"],
    "reading": ["book", "novel", "magazine", "newspaper", "scroll"],
    "weapon_melee": ["sword", "katana", "dagger", "knife", "spear", "lance", "axe", "mace", "hammer"],
    "weapon_ranged": ["bow", "crossbow", "arrow", "arrows", "quiver", "gun", "pistol", "rifle", "shotgun"],
    "weapon_defense": ["shield", "buckler"],
    "magic": ["magic", "spell", "spells", "wand", "staff", "incantation"],
    "instrument": ["guitar", "violin", "cello", "piano", "microphone"],
}

# Disambiguate “bow” (weapon) vs “bow” (greeting). Token-based to avoid “elbow”.
BOW_WEAPON_CONTEXT = {"archer", "archery", "arrow", "arrows", "quiver", "aim", "aiming", "shoot", "shooting", "draw", "string", "nock"}
BOW_COURTESY_CONTEXT = {"greet", "greeting", "apology", "apologizing", "polite", "respect", "respectful", "head", "slight", "deep"}

# Intent detection from action_raw (after refactor, action_raw should carry intent words)
INTENT_KEYWORDS_DEFAULT: Dict[str, List[str]] = {
    "combat": ["battle", "combat", "fight", "duel", "war", "skirmish", "stance", "ready", "warrior", "knight", "soldier"],
    "relax": ["relax", "rest", "nap", "sleep", "calm", "quiet", "peaceful", "tea", "chill", "break", "home", "room"],
    "study": ["study", "learn", "practice", "training", "class", "school", "homework", "notes", "reading", "library"],
    "work": ["work", "office", "meeting", "business", "typing", "presentation", "report", "job", "career"],
    "travel": ["travel", "journey", "walk", "walking", "ride", "riding", "explore", "commute", "urban", "street", "city", "shop", "shopping"],
    "perform": ["sing", "singing", "dance", "dancing", "perform", "playing", "concert", "stage", "music", "idol", "band"],
    "surveillance": ["surveillance", "investigate", "investigation", "spy", "search", "looking", "detective", "clue", "mission"],
}

# Role detection from subj + costume_key (simple heuristic)
ROLE_KEYWORDS_DEFAULT: Dict[str, List[str]] = {
    "knight": ["knight", "paladin", "armored", "armor", "plate"],
    "ranger": ["ranger", "archer", "huntress", "scout"],
    "mage": ["mage", "wizard", "sorcerer", "sorceress", "witch"],
    "modern": ["school", "student", "office", "casual", "street", "detective", "agent"],
}

# Mismatch rules: role -> forbidden prop categories
ROLE_FORBID_CATS_DEFAULT: Dict[str, List[str]] = {
    # The main target: “knight with bow”
    "knight": ["weapon_ranged"],
    # Modern everyday roles generally shouldn’t carry fantasy weapons by default
    "modern": ["weapon_melee", "weapon_ranged", "weapon_defense"],
}

# Intent completion terms: if combat intent, at least weapon/magic OR these verbs should appear.
COMBAT_COMPLETION_TERMS = [
    "attack", "attacking", "strike", "striking", "parry", "parrying", "block", "blocking",
    "charge", "charging", "cast", "casting",
    "aiming", "drawing", "gripping", "clenched", "guarding", "ready", "chanting",
    "stance", "nocking", "reloading", "gathering", "glaring", "defensive"
]


# Intent completion rules: detect “under-materialized intent” per pack.
# Rule format: intent -> {cats_any: [...], terms_any: [...], cats_forbid: [...]}
INTENT_COMPLETION_RULES_DEFAULT: Dict[str, Dict[str, List[str]]] = {
    "combat": {"cats_any": ["weapon_melee", "weapon_ranged", "weapon_defense", "magic"], "terms_any": COMBAT_COMPLETION_TERMS},
    "study": {"cats_any": ["reading", "device"], "terms_any": ["write", "writing", "type", "typing", "note", "notes", "study", "studying"]},
    "work": {"cats_any": ["device"], "terms_any": ["type", "typing", "present", "presenting", "meeting", "report"]},
    "perform": {"cats_any": ["instrument"], "terms_any": ["sing", "singing", "dance", "dancing", "perform", "performing", "play", "playing"]},
    "travel": {"cats_any": [], "terms_any": ["walk", "walking", "run", "running", "ride", "riding", "travel", "journey", "explore", "exploring"]},
    "surveillance": {"cats_any": ["device"], "terms_any": ["look", "looking", "search", "searching", "watch", "watching", "note", "notes", "camera", "binocular"]},
    "relax": {"cats_any": ["reading"], "terms_any": ["relax", "rest", "sleep", "nap", "sit", "sitting", "lie", "lying", "drink", "drinking", "tea", "coffee"]},
}

# Minimum completion rates (global target / pack-level warning thresholds)
INTENT_COMPLETION_MINS_DEFAULT: Dict[str, float] = {
    "combat": 0.85,
    "study": 0.60,
    "work": 0.60,
    "perform": 0.60,
    "travel": 0.60,
    "surveillance": 0.60,
    "relax": 0.60,
}

# Bias caps (global). These are score penalties (not hard failures).
BIAS_CAPS_DEFAULT = {
    "device": 0.05,  # Relaxed from 0.02 because modern roles use phones naturally
    "reading": 0.05, # Relaxed from 0.03
}

# Verbs that are too common and not indicative of bias
COMMON_VERBS = {"holding", "looking", "standing", "sitting", "walking"}

# Connector words to exclude from Location token metrics (to measure "Noun Core" diversity)
LOCATION_CONNECTORS = {"with", "featuring", "during", "plus", "and", "as", "well", "scattered", "filled", "adorned"}

STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "by", "of", "is", "are", 
    "wearing", "background", "she", "he", "it", "view", "from", "up",
    "to"
} | LOCATION_CONNECTORS

SEMANTIC_CONFLICT_RULES = {
    "peaceful": ["gun", "sword", "weapon", "battle", "fight", "blood", "kill", "war", "soldier"],
    "relax": ["run", "sprint", "fight", "battle", "urgent", "danger", "explosion"],
    "happy": ["crying", "tears", "sad", "depressed", "grief", "mourning"],
    "quiet": ["scream", "shout", "explosion", "loud", "noise", "concert"]
}

# Style words that should NOT appear in the final prompt (unless contextually valid like "art gallery")
STYLE_BANNED_WORDS = {"illustration", "art style", "oil painting", "meta_style", "sketch", "digital art", "watercolor"}
# Contexts where "art" words are allowed
STYLE_ALLOWLIST = {"art gallery", "art museum", "street art", "martial arts", "sword art"}

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")

# --- Utilities ---

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def norm_text(s: str) -> str:
    """Basic normalization: lower, remove symbols, collapse spaces."""
    s = (s or "").strip().lower()
    s = s.replace("_", " ")
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s

def get_tokens(s: str) -> List[str]:
    """Get simple tokens from normalized text."""
    return norm_text(s).split()

def get_core_tokens(s: str) -> str:
    """Core Unique Logic: remove stopwords, sort tokens."""
    tokens = [t for t in get_tokens(s) if t not in STOPWORDS and len(t) > 1]
    tokens.sort()
    return " ".join(tokens)

# --- Metrics Functions (v2 Revived + Phase 1 Enhanced) ---

def unique_rate(xs: List[str]) -> float:
    n = len(xs)
    if n == 0: return 0.0
    return len(set(xs)) / n

def shannon_entropy(tokens: List[str]) -> float:
    """Calculate Shannon Entropy for token distribution."""
    if not tokens: return 0.0
    cnt = Counter(tokens)
    total = sum(cnt.values())
    ent = 0.0
    for v in cnt.values():
        p = v / total
        ent -= p * math.log(p, 2)
    return ent

def topk_share(tokens: List[str], k: int = 5) -> float:
    """Calculate the percentage of total tokens covered by the top K most frequent words."""
    if not tokens: return 0.0
    cnt = Counter(tokens)
    total = sum(cnt.values())
    if total == 0: return 0.0
    top_sum = sum(v for _, v in cnt.most_common(k))
    return top_sum / total

def ngram_repetition_rate(tokens: List[str], n: int = 3) -> float:
    """Detect repetitive phrases (stuttering) within a single string."""
    if len(tokens) < n: return 0.0
    grams = [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]
    if not grams: return 0.0
    
    # Count duplicates
    c = Counter(grams)
    dup_count = sum(v-1 for v in c.values() if v > 1)
    
    # Normalize by total possible grams
    return dup_count / len(grams)

def calculate_cv(values: List[float]) -> float:
    """Calculate Coefficient of Variation (CV) = StdDev / Mean."""
    if len(values) < 2: return 0.0
    mean = statistics.mean(values)
    if mean == 0: return 0.0
    stdev = statistics.stdev(values)
    return stdev / mean

def jaccard_similarity(list1: List[str], list2: List[str]) -> float:
    """Calculate Jaccard Similarity between two lists of tokens."""
    s1 = set(list1)
    s2 = set(list2)
    if not s1 and not s2: return 1.0
    return len(s1 & s2) / len(s1 | s2)

# --- Semantic Checks ---

def detect_mood_category(text: str) -> str:
    t = norm_text(text)
    if any(w in t for w in ["peaceful", "calm", "quiet", "relax", "serene", "soft", "rest", "sleep"]):
        return "peaceful"
    if any(w in t for w in ["energetic", "joy", "happy", "excited", "dynamic", "jump", "sport"]):
        return "happy"
    if any(w in t for w in ["intense", "anger", "battle", "fight", "war", "dangerous"]):
        return "intense"
    return "neutral"

def check_semantic_violation(merged_text: str, mood_key: str, mood_expanded: str) -> bool:
    text = norm_text(merged_text)
    cat = detect_mood_category(mood_expanded)
    if cat == "neutral":
        cat = detect_mood_category(mood_key)
        
    if cat in SEMANTIC_CONFLICT_RULES:
        forbidden_words = SEMANTIC_CONFLICT_RULES[cat]
        tokens = set(text.split())
        for bad in forbidden_words:
            if bad in tokens:
                return True
    return False

def check_style_violation(text: str) -> bool:
    """
    Context-Aware Style Violation Check.
    Returns True if 'text' contains banned style words, UNLESS they are part of allowed phrases.
    """
    t_norm = norm_text(text)
    
    # 1. Check if ANY banned word is present
    found_banned = False
    for bad in STYLE_BANNED_WORDS:
        # Simple substring check (normalized)
        if bad in t_norm:
            found_banned = True
            break
            
    if not found_banned:
        return False
        
    # 2. If present, check if it's ONLY in allowed context
    # Create a temporary string with allowed phrases removed
    t_cleaned = t_norm
    for allowed in STYLE_ALLOWLIST:
        t_cleaned = t_cleaned.replace(allowed, "")
        
    # 3. Re-check banned words in the cleaned string
    for bad in STYLE_BANNED_WORDS:
        # Use word boundary check for safety (e.g. "smart" vs "art")
        # but norm_text already stripped symbols, so simple " word " check or regex is robust
        if re.search(rf"\b{re.escape(bad)}\b", t_cleaned):
            return True
            
    return False

def _contains_ngram(tokens: List[str], pat: List[str]) -> bool:
    """Return True if tokens contains pat as a contiguous n-gram (exact token match)."""
    if not pat:
        return False
    if len(pat) == 1:
        return pat[0] in tokens
    n = len(pat)
    # sliding window
    for i in range(len(tokens) - n + 1):
        if tokens[i:i+n] == pat:
            return True
    return False

def watch_hit_count(text: str, terms: List[str]) -> Counter:
    """
    Token-based watch:
      - Single-word term: exact token match only (NO partial match like "elbow"->"bow", "narrow"->"arrow")
      - Multi-word term (e.g. "art style"): contiguous n-gram match
    Presence-based count: if a term appears >=1 time in text, count as 1.
    """
    c = Counter()
    tokens = get_tokens(text)  # norm_text + split
    if not tokens or not terms:
        return c
    for term in terms:
        pat = get_tokens(term)
        if _contains_ngram(tokens, pat):
            c[term] += 1
    return c

def build_watch_terms_by_pack_rows(
    samples_by_pack_run: Dict[int, Dict[int, List["Sample"]]],
    watch_map: Dict[str, List[str]]
) -> List[Dict[str, Any]]:
    """
    Emit rows: pack_idx, subj, loc_tag, field, term, hit_count, hit_rate, n_samples
    Aggregated over ALL runs (flattened).
    """
    rows: List[Dict[str, Any]] = []
    for pack_idx in sorted(samples_by_pack_run.keys()):
        # flatten all runs for this pack
        flat: List[Sample] = []
        for run_id in sorted(samples_by_pack_run[pack_idx].keys()):
            flat.extend(samples_by_pack_run[pack_idx][run_id])
        if not flat:
            continue
        ref = flat[0]
        n = len(flat)
        for field, terms in watch_map.items():
            if not hasattr(ref, field):
                continue
            if not terms:
                continue

            term_hits = Counter()
            any_hits = 0

            for s in flat:
                txt = getattr(s, field, "")
                hc = watch_hit_count(txt, terms)
                # presence-based (hc[term] is 0/1)
                term_hits.update(hc)
                
                # "__any__" hit: this sample contains ANY watch term in this field
                if sum(hc.values()) > 0:
                    any_hits += 1

            # Add field-level "any" row first (same CSV, term="__any__")
            rows.append({
                "pack_idx": pack_idx,
                "subj": getattr(ref, "subj", ""),
                "loc_tag": getattr(ref, "loc_tag", ""),
                "field": field,
                "term": "__any__",
                "hit_count": int(any_hits),
                "hit_rate": round(any_hits / n, 6),
                "n_samples": n,
            })

            for term in terms:
                hit_count = int(term_hits.get(term, 0))
                rows.append({
                    "pack_idx": pack_idx,
                    "subj": getattr(ref, "subj", ""),
                    "loc_tag": getattr(ref, "loc_tag", ""),
                    "field": field,
                    "term": term,
                    "hit_count": hit_count,
                    "hit_rate": round(hit_count / n, 6),
                    "n_samples": n,
                })
    return rows

def compute_watch_summary(samples: List[Sample], fields: List[str], watch_map: Dict[str, List[str]]) -> Dict[str, Any]:
    """Summarize watch hits per field (rate + per-term sample hit counts).

    - rate: fraction of samples that contain ANY watch term in that field
    - term_counts: number of samples containing each term (presence-based, not frequency)
    - term_rates: term_counts normalized by sample count
    """
    n = len(samples)
    if n == 0:
        return {}

    out: Dict[str, Any] = {}
    for f, terms in watch_map.items():
        # Only summarize for fields that exist in Sample and are being evaluated
        if f not in fields:
            continue
        if not hasattr(samples[0], f):
            continue

        any_hit = 0
        term_counts = Counter()
        for s in samples:
            txt = getattr(s, f, "")
            c = watch_hit_count(txt, terms)
            if sum(c.values()) > 0:
                any_hit += 1
            term_counts.update(c)

        out[f] = {
            "rate": round(any_hit / n, 6),
            "term_counts": dict(term_counts),
            "term_rates": {t: round(term_counts.get(t, 0) / n, 6) for t in terms},
        }

    return out


# --- GoalScore (v4) ---

def _clamp01(x: float) -> float:
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)

def _safe_div(a: float, b: float) -> float:
    return 0.0 if b == 0 else (a / b)

def _load_goal_cfg(path: str | None) -> Dict[str, Any]:
    """Optional JSON override for lexicons/rules used by GoalScore."""
    if not path:
        return {}
    if not os.path.exists(path):
        print(f"[Warn] --goal_cfg not found: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception as e:
        print(f"[Warn] failed to read --goal_cfg: {e}")
        return {}

def _merge_cfg_list(base: List[str], override: Any) -> List[str]:
    if not override:
        return sorted(set((t or "").strip().lower() for t in base if t))
    if not isinstance(override, list):
        return sorted(set((t or "").strip().lower() for t in base if t))
    merged = list(base) + [str(t) for t in override]
    return sorted(set((t or "").strip().lower() for t in merged if t))

def _merge_cfg_dict_list(base: Dict[str, List[str]], override: Any) -> Dict[str, List[str]]:
    out = {k: _merge_cfg_list(v, None) for k, v in base.items()}
    if not override or not isinstance(override, dict):
        return out
    for k, v in override.items():
        key = str(k).strip().lower()
        if key not in out:
            out[key] = []
        out[key] = _merge_cfg_list(out[key], v)
    return out

def _merge_cfg_nested_dict_list(default: Dict[str, Dict[str, List[str]]], override: Any) -> Dict[str, Dict[str, List[str]]]:
    """Deep-merge: intent -> key -> list[str]. Deterministic unique union."""
    out: Dict[str, Dict[str, List[str]]] = {k: {kk: list(vv) for kk, vv in dv.items()} for k, dv in (default or {}).items()}
    if not override:
        return out
    if not isinstance(override, dict):
        return out
    for intent, d in override.items():
        if not isinstance(d, dict):
            continue
        if intent not in out:
            out[intent] = {}
        for kk, vv in d.items():
            if not isinstance(vv, list):
                continue
            cur = out[intent].get(kk, [])
            merged = list(dict.fromkeys(cur + vv))
            out[intent][kk] = merged
    return out


def _detect_intent(action_raw: str, costume_key: str, subj: str, loc_tag: str, intent_keywords: Dict[str, List[str]]) -> str:
    """Detect intent with deterministic priority.
    First try action_raw (post-refactor it should contain intent words), then fallback to costume/subj/loc.
    """
    toks_raw = set(get_tokens(action_raw))
    toks_fallback = set(get_tokens(f"{costume_key} {subj} {loc_tag}"))
    for intent in ("combat", "relax", "study", "work", "travel", "perform"):
        keys = set(intent_keywords.get(intent, []))
        if keys and (toks_raw & keys):
            return intent
    for intent in ("combat", "relax", "study", "work", "travel", "perform"):
        keys = set(intent_keywords.get(intent, []))
        if keys and (toks_fallback & keys):
            return intent
    return "other"

def _detect_role_info(subj: str, costume_key: str, role_keywords: Dict[str, List[str]]) -> Tuple[str, List[str]]:
    """Return (primary_role, matched_roles). matched_roles can be empty (unknown) or >1 (ambiguous)."""
    toks = set(get_tokens(f"{subj} {costume_key}"))
    matched: List[str] = []
    for role in ("knight", "ranger", "mage", "modern"):
        keys = set(role_keywords.get(role, []))
        if keys and (toks & keys):
            matched.append(role)
    if not matched:
        return "unknown", []
    return matched[0], matched

def _bow_kind(tokens: Set[str], bow_weapon_ctx: Set[str], bow_courtesy_ctx: Set[str]) -> str:
    if "bow" not in tokens:
        return "none"
    if tokens & bow_weapon_ctx:
        return "weapon"
    if tokens & bow_courtesy_ctx:
        return "courtesy"
    return "unknown"

def _present_categories(text: str, prop_categories: Dict[str, List[str]], bow_weapon_ctx: Set[str], bow_courtesy_ctx: Set[str]) -> Set[str]:
    toks = set(get_tokens(text))
    present: Set[str] = set()
    for cat, terms in prop_categories.items():
        if not terms:
            continue
        if sum(watch_hit_count(text, terms).values()) > 0:
            present.add(cat)

    # refine bow ambiguity
    if "weapon_ranged" in present and "bow" in toks:
        kind = _bow_kind(toks, bow_weapon_ctx, bow_courtesy_ctx)
        if kind == "courtesy":
            # courtesy bow should not count as ranged weapon
            present.discard("weapon_ranged")
    return present

def _intent_completed(intent: str, text: str, present_cats: Set[str], rules: Dict[str, Dict[str, List[str]]]) -> bool:
    """Check whether an intent is materialized into concrete description in action_merged/final."""
    rule = rules.get(intent)
    if not rule:
        return True  # no rule => not evaluated
    cats_any = set(rule.get("cats_any", []) or [])
    terms_any = list(rule.get("terms_any", []) or [])
    if cats_any and (present_cats & cats_any):
        return True
    if terms_any and sum(watch_hit_count(text, terms_any).values()) > 0:
        return True
    return False


def _compute_goal_metrics(
    samples: List["Sample"],
    samples_by_pack_run: Dict[int, Dict[int, List["Sample"]]],
    raw_concrete_terms: List[str],
    prop_categories: Dict[str, List[str]],
    bow_weapon_ctx: Set[str],
    bow_courtesy_ctx: Set[str],
    intent_keywords: Dict[str, List[str]],
    role_keywords: Dict[str, List[str]],
    role_forbid: Dict[str, List[str]],
    combat_completion_terms: List[str],
    intent_completion_rules: Dict[str, Dict[str, List[str]]],
    intent_completion_mins: Dict[str, float],
    bias_caps: Dict[str, float],
    goals: Dict[str, float],
    mismatch_examples_max: int = 30,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str], Dict[int, Dict[str, Any]]]:
    """Compute GoalScore (0-100) and per-pack breakdown."""

    n = len(samples)
    if n == 0:
        return {"score_total": 0.0, "note": "no samples"}, [], [], {}

    # global tallies
    raw_concrete_any = 0
    mismatch = 0
    combat_n = 0
    combat_ok = 0
    relax_n = 0
    relax_weapon = 0

    # role/intent debug (global)
    role_unknown = 0
    role_ambig = 0
    intent_counts = Counter()
    intent_ok = Counter()

    # per-pack debug for priority list
    pack_debug: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
        "intent_counts": Counter(),
        "intent_ok": Counter(),
        "role_counts": Counter(),
        "role_unknown": 0,
        "role_ambig": 0,
    })

    bias_hit = {k: 0 for k in bias_caps.keys()}
    mismatch_examples: List[str] = []

    # fixed-pack detection: if a concrete term appears in action_raw for ALL samples of a pack
    fixed_packs: List[Dict[str, Any]] = []
    fixed_terms_by_pack: Dict[int, List[str]] = defaultdict(list)
    for pack_idx in sorted(samples_by_pack_run.keys()):
        flat: List[Sample] = []
        for rid in sorted(samples_by_pack_run[pack_idx].keys()):
            flat.extend(samples_by_pack_run[pack_idx][rid])
        if not flat:
            continue
        term_hits = Counter()
        for s in flat:
            term_hits.update(watch_hit_count(s.action_raw, raw_concrete_terms))
        for term, cnt in term_hits.items():
            if cnt == len(flat):
                fixed_packs.append({
                    "pack_idx": pack_idx,
                    "term": term,
                    "n_samples": len(flat),
                    "subj": flat[0].subj,
                    "costume_key": flat[0].costume_key,
                    "loc_tag": flat[0].loc_tag,
                })

    for fp in fixed_packs:
        fixed_terms_by_pack[fp["pack_idx"]].append(fp["term"])

    for s in samples:
        # raw concrete leak
        if sum(watch_hit_count(s.action_raw, raw_concrete_terms).values()) > 0:
            raw_concrete_any += 1

        intent = _detect_intent(s.action_raw, s.costume_key, s.subj, s.loc_tag, intent_keywords)
        role, role_matches = _detect_role_info(s.subj, s.costume_key, role_keywords)
        if role == "unknown":
            role_unknown += 1
        if len(role_matches) > 1:
            role_ambig += 1

        intent_counts[intent] += 1

        present = _present_categories(
            f"{s.action_merged} {s.final}",
            prop_categories,
            bow_weapon_ctx,
            bow_courtesy_ctx,
        )

        # per-pack debug updates
        pd = pack_debug[s.pack_idx]
        pd["intent_counts"][intent] += 1
        pd["role_counts"][role] += 1
        if role == "unknown":
            pd["role_unknown"] += 1
        if len(role_matches) > 1:
            pd["role_ambig"] += 1

        # role/prop mismatch
        forbid = set(role_forbid.get(role, []))
        if forbid and (present & forbid):
            mismatch += 1
            if len(mismatch_examples) < mismatch_examples_max:
                mismatch_examples.append(
                    f"pack={s.pack_idx} run={s.run_id} seed={s.seed} role={role} forbid={sorted(forbid)} present={sorted(present)}\n"
                    f"  subj={s.subj} costume_key={s.costume_key}\n"
                    f"  action_raw={s.action_raw}\n"
                    f"  action_merged={s.action_merged}\n"
                    f"  final={s.final}\n"
                )

        # intent completion (under-materialized intent detection)
        text_cm = f"{s.action_merged} {s.final}"
        ok_intent = _intent_completed(intent, text_cm, present, intent_completion_rules)
        if ok_intent:
            intent_ok[intent] += 1
            pack_debug[s.pack_idx]["intent_ok"][intent] += 1

        # relax: weapon leakage (hard negative)
        if intent == "relax":
            relax_n += 1
            if present & {"weapon_melee", "weapon_ranged", "weapon_defense"}:
                relax_weapon += 1

        # combat: keep legacy counters for headline rate
        if intent == "combat":
            combat_n += 1
            if ok_intent:
                combat_ok += 1


        # bias caps (final only)
        for cat in bias_caps.keys():
            terms = prop_categories.get(cat, [])
            if terms and sum(watch_hit_count(s.final, terms).values()) > 0:
                bias_hit[cat] += 1

    raw_rate = _safe_div(raw_concrete_any, n)
    mismatch_rate = _safe_div(mismatch, n)
    combat_completion_rate = _safe_div(combat_ok, combat_n) if combat_n > 0 else 1.0
    relax_weapon_rate = _safe_div(relax_weapon, relax_n) if relax_n > 0 else 0.0

    role_unknown_rate = _safe_div(role_unknown, n)
    role_ambiguous_rate = _safe_div(role_ambig, n)
    intent_completion_rates = {k: (_safe_div(intent_ok[k], intent_counts[k]) if intent_counts[k] > 0 else 1.0) for k in intent_counts.keys()}

    bias_rates = {f"{k}_rate": _safe_div(v, n) for k, v in bias_hit.items()}

    # scoring
    score_raw = 25.0 * _clamp01(1.0 - _safe_div(raw_rate, goals.get("raw_concrete_max", 0.005)))
    score_mismatch = 30.0 * _clamp01(1.0 - _safe_div(mismatch_rate, goals.get("mismatch_max", 0.005)))
    score_completion = 25.0 * _clamp01(_safe_div(combat_completion_rate, goals.get("combat_completion_min", 0.85)))
    # relax-weapon penalty is folded into completion (keeps score simple)
    relax_pen = _clamp01(1.0 - _safe_div(relax_weapon_rate, goals.get("relax_weapon_max", 0.01)))
    score_completion *= relax_pen

    # bias score: average over caps
    if bias_caps:
        bias_scores = []
        for cat, cap in bias_caps.items():
            rate = bias_rates.get(f"{cat}_rate", 0.0)
            bias_scores.append(_clamp01(1.0 - _safe_div(rate, cap)))
        score_bias = 20.0 * (sum(bias_scores) / len(bias_scores))
    else:
        score_bias = 20.0

    score_total = round(score_raw + score_completion + score_mismatch + score_bias, 3)

    global_goal = {
        "score_total": score_total,
        "score_components": {
            "raw_abstractness": round(score_raw, 3),
            "intent_completion": round(score_completion, 3),
            "role_coherence": round(score_mismatch, 3),
            "bias_caps": round(score_bias, 3),
        },
        "rates": {
            "raw_concrete_rate": round(raw_rate, 6),
            "combat_completion_rate": round(combat_completion_rate, 6),
            "relax_weapon_rate": round(relax_weapon_rate, 6),
            "mismatch_rate": round(mismatch_rate, 6),
            "role_unknown_rate": round(role_unknown_rate, 6),
            "role_ambiguous_rate": round(role_ambiguous_rate, 6),
            **{k: round(v, 6) for k, v in bias_rates.items()},
        },
        "targets": goals,
        "intent_completion": {
            "rates": {k: round(v, 6) for k, v in sorted(intent_completion_rates.items())},
            "mins": intent_completion_mins,
            "counts": {k: int(v) for k, v in sorted(intent_counts.items())},
        },
        "fixed_pack": {
            "count": len(fixed_packs),
            "examples": fixed_packs[:10],
        },
    }

    # per-pack breakdown (rates only)
    per_pack_rows: List[Dict[str, Any]] = []
    for pack_idx in sorted(samples_by_pack_run.keys()):
        flat: List[Sample] = []
        for rid in sorted(samples_by_pack_run[pack_idx].keys()):
            flat.extend(samples_by_pack_run[pack_idx][rid])
        if not flat:
            continue

        pn = len(flat)
        pr_raw = sum(1 for s in flat if sum(watch_hit_count(s.action_raw, raw_concrete_terms).values()) > 0)
        pr_mismatch = 0
        pr_c_n = 0
        pr_c_ok = 0
        pr_r_n = 0
        pr_r_weapon = 0
        pr_bias = {k: 0 for k in bias_caps.keys()}

        for s in flat:
            intent = _detect_intent(s.action_raw, s.costume_key, s.subj, s.loc_tag, intent_keywords)
            role, role_matches = _detect_role_info(s.subj, s.costume_key, role_keywords)
            present = _present_categories(f"{s.action_merged} {s.final}", prop_categories, bow_weapon_ctx, bow_courtesy_ctx)
            forbid = set(role_forbid.get(role, []))
            if forbid and (present & forbid):
                pr_mismatch += 1

            if intent == "combat":
                pr_c_n += 1
                ok = False
                if present & {"weapon_melee", "weapon_ranged", "weapon_defense", "magic"}:
                    ok = True
                elif sum(watch_hit_count(f"{s.action_merged} {s.final}", combat_completion_terms).values()) > 0:
                    ok = True
                if ok:
                    pr_c_ok += 1
            elif intent == "relax":
                pr_r_n += 1
                if present & {"weapon_melee", "weapon_ranged", "weapon_defense"}:
                    pr_r_weapon += 1

            for cat in bias_caps.keys():
                terms = prop_categories.get(cat, [])
                if terms and sum(watch_hit_count(s.final, terms).values()) > 0:
                    pr_bias[cat] += 1

        row = {
            "pack_idx": pack_idx,
            "n_samples": pn,
            "subj": flat[0].subj,
            "costume_key": flat[0].costume_key,
            "loc_tag": flat[0].loc_tag,
            "raw_concrete_rate": round(_safe_div(pr_raw, pn), 6),
            "combat_completion_rate": round(_safe_div(pr_c_ok, pr_c_n) if pr_c_n > 0 else 1.0, 6),
            "relax_weapon_rate": round(_safe_div(pr_r_weapon, pr_r_n) if pr_r_n > 0 else 0.0, 6),
            "mismatch_rate": round(_safe_div(pr_mismatch, pn), 6),
        }
        for cat in bias_caps.keys():
            row[f"{cat}_rate"] = round(_safe_div(pr_bias[cat], pn), 6)
        per_pack_rows.append(row)

        # enrich per-pack rows with intent/role debug for priority list
    for row in per_pack_rows:
        pack_idx = int(row.get("pack_idx", -1))
        pn = int(row.get("n_samples", 0))
        pd = pack_debug.get(pack_idx)
        if not pd or pn <= 0:
            continue
        ic = pd.get("intent_counts", Counter())
        iok = pd.get("intent_ok", Counter())
        rc = pd.get("role_counts", Counter())
        row["fixed_terms"] = ";".join(sorted(set(fixed_terms_by_pack.get(pack_idx, []))))
        row["role_unknown_rate"] = round(_safe_div(pd.get("role_unknown", 0), pn), 6)
        row["role_ambiguous_rate"] = round(_safe_div(pd.get("role_ambig", 0), pn), 6)
        row["dominant_intent"] = sorted(ic.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if ic else "other"
        row["dominant_role"] = sorted(rc.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if rc else "unknown"
        dom_int = row["dominant_intent"]
        dom_n = int(ic.get(dom_int, 0))
        dom_ok = int(iok.get(dom_int, 0))
        row["dominant_intent_completion_rate"] = round(_safe_div(dom_ok, dom_n) if dom_n > 0 else 1.0, 6)
        # compact counts for debugging (json, stable key order)
        row["intent_counts_json"] = json.dumps({k: int(v) for k, v in sorted(ic.items())}, ensure_ascii=False)
        row["role_counts_json"] = json.dumps({k: int(v) for k, v in sorted(rc.items())}, ensure_ascii=False)

    mismatch_lines = ["# mismatch examples (role/prop coherence)"] + mismatch_examples
    return global_goal, per_pack_rows, mismatch_lines, pack_debug


def _role_entropy(role_counts: Dict[str, int]) -> float:
    tot = sum(role_counts.values())
    if tot <= 0:
        return 0.0
    import math
    ent = 0.0
    for v in role_counts.values():
        if v <= 0:
            continue
        p = v / tot
        ent -= p * math.log(p + 1e-12, 2)
    return float(ent)

def _build_pack_priority_rows(
    goal_by_pack_rows: List[Dict[str, Any]],
    goals: Dict[str, float],
    bias_caps: Dict[str, float],
    intent_completion_mins: Dict[str, float],
) -> List[Dict[str, Any]]:
    """Rank packs by how urgently they should be fixed.
    Uses fixed-pack detection, raw concrete leak, bias over-caps, intent under-materialization,
    and role inference instability (unknown/ambiguous).
    """
    out: List[Dict[str, Any]] = []
    raw_max = float(goals.get("raw_concrete_max", 0.005))
    mismatch_max = float(goals.get("mismatch_max", 0.02))

    for row in goal_by_pack_rows:
        pack_idx = int(row.get("pack_idx", -1))
        pn = int(row.get("n_samples", 0))
        fixed_terms = (row.get("fixed_terms") or "").strip()
        raw_rate = float(row.get("raw_concrete_rate", 0.0))
        mismatch_rate = float(row.get("mismatch_rate", 0.0))
        dom_intent = (row.get("dominant_intent") or "other")
        dom_comp = float(row.get("dominant_intent_completion_rate", 1.0))
        role_unknown_rate = float(row.get("role_unknown_rate", 0.0))
        role_ambig_rate = float(row.get("role_ambiguous_rate", 0.0))

        # parse compact counts
        try:
            ic = json.loads(row.get("intent_counts_json") or "{}")
        except Exception:
            ic = {}
        try:
            rc = json.loads(row.get("role_counts_json") or "{}")
        except Exception:
            rc = {}

        other_rate = 0.0
        if pn > 0:
            other_rate = float(ic.get("other", 0)) / pn

        reasons: List[str] = []
        score = 0.0

        if fixed_terms:
            reasons.append(f"fixed_pack_raw:{fixed_terms}")
            score += 60.0

        if raw_rate > raw_max:
            reasons.append("raw_concrete_leak")
            score += 50.0 * _clamp01((raw_rate - raw_max) / max(1e-9, 1.0 - raw_max))

        if mismatch_rate > mismatch_max:
            reasons.append("role_prop_mismatch")
            score += 70.0 * _clamp01((mismatch_rate - mismatch_max) / max(1e-9, mismatch_max))

        if other_rate > 0.50:
            reasons.append("intent_unknown")
            score += 35.0 * other_rate

        min_rate = float(intent_completion_mins.get(dom_intent, 0.0) or 0.0)
        if min_rate > 0.0 and dom_comp < min_rate:
            reasons.append(f"intent_under:{dom_intent}")
            score += 45.0 * _clamp01((min_rate - dom_comp) / max(1e-9, min_rate))

        if role_unknown_rate > 0.25:
            reasons.append("role_unknown")
        score += 25.0 * role_unknown_rate

        if role_ambig_rate > 0.05:
            reasons.append("role_ambiguous")
        score += 10.0 * role_ambig_rate

        for cat, cap in bias_caps.items():
            rate = float(row.get(f"{cat}_rate", 0.0))
            if cap > 0 and rate > cap:
                reasons.append(f"bias_over:{cat}")
                score += 25.0 * _clamp01((rate - cap) / max(1e-9, cap))

        out.append({
            "pack_idx": pack_idx,
            "n_samples": pn,
            "subj": row.get("subj", ""),
            "costume_key": row.get("costume_key", ""),
            "loc_tag": row.get("loc_tag", ""),
            "priority_score": round(score, 4),
            "reasons": ";".join(reasons),
            "fixed_terms": fixed_terms,
            "raw_concrete_rate": raw_rate,
            "dominant_intent": dom_intent,
            "dominant_intent_completion_rate": dom_comp,
            "other_intent_rate": round(other_rate, 6),
            "dominant_role": row.get("dominant_role", "unknown"),
            "role_unknown_rate": role_unknown_rate,
            "role_ambiguous_rate": role_ambig_rate,
            "role_entropy": round(_role_entropy({k: int(v) for k, v in rc.items()}), 6),
            "mismatch_rate": mismatch_rate,
            **{f"{cat}_rate": float(row.get(f"{cat}_rate", 0.0)) for cat in bias_caps.keys()},
        })

    out.sort(key=lambda r: (-r["priority_score"], r["pack_idx"]))
    for i, r in enumerate(out, 1):
        r["priority_rank"] = i
    return out

# --- Data Structures ---

@dataclass
class Sample:
    pack_idx: int
    seed: int
    run_id: int # Phase 1: Added run_id
    subj: str
    costume_key: str
    loc_tag: str
    meta_mood_key: str
    
    costume: str
    loc: str
    garnish: str
    action_raw: str
    action_merged: str
    meta_mood: str
    final: str
    
    violation_tech: int
    violation_sem: int
    violation_style: int # Phase 1: Added style violation

def read_jsonl(path: str) -> List[dict]:
    if not os.path.exists(path):
        print(f"[Warning] {path} not found.")
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: rows.append(json.loads(line))
            except: pass
    return rows

def write_csv(path: str, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in rows: w.writerow(r)

# --- Main Execution ---

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default="prompts.jsonl")
    ap.add_argument("--mood_map", default="mood_map.json")
    ap.add_argument("--n", type=int, default=200, help="Samples per pack per run")
    ap.add_argument("--runs", type=int, default=3, help="Number of stability runs")
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--out_dir", default="_eval_out_final")
    
    # Evaluate fields (comma-separated). Include garnish/action_raw for bias attribution.
    ap.add_argument("--eval_fields", default="loc,costume,action_raw,garnish,action_merged,final",
                    help="Comma-separated Sample fields to evaluate (unique/entropy/watch).")
    
    # Phase 2 Goal: Remove {meta_style} from default. Done here in Phase 1 for checking.
    # Updated default to REMOVE {meta_style} as requested
    ap.add_argument("--template", default="A of {subj} wearing {costume}. She is {action}. The background is {loc}, with {meta_mood}.")
    ap.add_argument("--garnish_max", type=int, default=3)
    ap.add_argument("--include_camera", action="store_true")
    ap.add_argument("--watch", action="append", default=[], help='Additional watch terms "field:term,term"')
    ap.add_argument("--watch_any", action="append", default=[],
                    help='Watch terms applied to ALL eval_fields: "term,term" (or use --watch "*:term,term")')
    ap.add_argument("--force_no_style", action="store_true", default=True, help="Force meta_style to empty string to test 0-violation goal")

    # GoalScore (v4)
    ap.add_argument("--goal_cfg", default=None, help="Optional JSON file to override GoalScore lexicons/rules")
    ap.add_argument("--goal_raw_concrete_max", type=float, default=0.005, help="Target max rate for concrete terms in action_raw")
    ap.add_argument("--goal_mismatch_max", type=float, default=0.005, help="Target max role/prop mismatch rate")
    ap.add_argument("--goal_combat_completion_min", type=float, default=0.85, help="Target min completion rate for combat intent")
    ap.add_argument("--goal_relax_weapon_max", type=float, default=0.01, help="Target max weapon rate for relax intent")
    ap.add_argument("--goal_mismatch_examples", type=int, default=30, help="Max mismatch examples to output")
    ap.add_argument("--no_goal_emit", action="store_true", help="Disable GoalScore output files")

    args = ap.parse_args()
    ensure_dir(args.out_dir)

    # Parse eval fields once (used for watch attribution + metrics)
    eval_fields = [x.strip() for x in args.eval_fields.split(',') if x.strip()]

    # 1. Template Cleaning (Simulating Phase 2 Node Default)
    # If user didn't specify a custom template, use the clean one (without {meta_style} if we are serious)
    # But for now, let's just strip it if force_no_style is ON and template is default-ish
    current_template = args.template
    if args.force_no_style and "{meta_style}" in current_template:
        print("[Info] --force_no_style is ON. Removing {meta_style} from template.")
        current_template = current_template.replace("A {meta_style} of ", "A ").replace("{meta_style}", "")

    packs = read_jsonl(args.jsonl)
    if not packs:
        print("No data found.")
        return

    # Watch Setup
    watch_map = defaultdict(list)
    for f, terms in DEFAULT_WATCH_MAP.items():
        watch_map[f].extend(terms)
    
    # --watch "field:term,term" (supports field='*' or 'all' to apply to all eval_fields)
    for w in args.watch:
        if ":" not in w:
            continue
        f, ts = w.split(":", 1)
        f = f.strip()
        terms = [t.strip() for t in ts.split(",") if t.strip()]
        if not terms:
            continue
        if f in {"*", "all"}:
            for ef in eval_fields:
                watch_map[ef].extend(terms)
        else:
            watch_map[f].extend(terms)

    # --watch_any "term,term" applies to ALL eval_fields (handy for "where did it come from?" debugging)
    for w in args.watch_any:
        terms = [t.strip() for t in w.split(",") if t.strip()]
        if not terms:
            continue
        for ef in eval_fields:
            watch_map[ef].extend(terms)

    # Dedup + sort
    for f in list(watch_map.keys()):
        watch_map[f] = sorted(set(t.lower() for t in watch_map[f] if t))

    # Inform if user set a watch field not in eval_fields (it won't be reported unless included)
    for f in sorted(watch_map.keys()):
        if f not in eval_fields:
            print(f"[Warn] watch field '{f}' is not in --eval_fields, so it won't appear in per-field watch_rate.")

    # Node Init
    parser = PackParser()
    cloth  = ThemeClothingExpander()
    locexp = ThemeLocationExpander()
    gar    = GarnishSampler()
    merge  = ActionMerge()
    dictex = DictionaryExpand()
    tmpl   = SimpleTemplateBuilder()

    all_run_samples: Dict[int, List[Sample]] = {}

    print(f"Generating {len(packs) * args.n * args.runs} samples ({args.runs} runs)...")

    # --- Generation Loop (Multi-Run) ---
    for run_id in range(args.runs):
        print(f"  Run {run_id+1}/{args.runs}...")
        run_samples = []
        
        for pack_idx, pack in enumerate(packs):
            js = json.dumps(pack, ensure_ascii=False)
            subj, costume_key, loc_tag, action_raw, meta_mood_key, raw_meta_style = parser.parse(js)

            # Force Clear Meta Style if requested
            meta_style = "" if args.force_no_style else raw_meta_style

            for i in range(args.n):
                # Deterministic Seed Strategy for Multi-Run
                # scheme: seed0 + i + (pack * 10000) + (run * 1000000)
                seed = args.seed0 + i + (pack_idx * 10000) + (run_id * 1000000)

                # Expansion
                costume = cloth.expand_clothing(theme_key=costume_key, seed=seed, outfit_mode="random", outerwear_chance=0.3)[0]
                loc = locexp.expand_location(loc_tag=loc_tag, seed=seed, mode="detailed")[0]
                meta_mood = dictex.expand(key=meta_mood_key, json_path=args.mood_map, default_value=meta_mood_key, seed=seed)[0]

                # Garnish & Merge
                garnish = gar.sample(
                    action_text=action_raw,
                    meta_mood_key=meta_mood_key,
                    seed=seed,
                    max_items=args.garnish_max,
                    include_camera=args.include_camera,
                    context_loc=loc_tag,
                    context_costume=costume_key,
                )[0]
                action_merged = merge.merge(original_action=action_raw, garnish=garnish)[0]

                # Final Build
                final = tmpl.build(
                    template=current_template,
                    subj=subj,
                    costume=costume,
                    loc=loc,
                    action=action_merged,
                    garnish="", # Garnish is already merged into action_merged
                    meta_mood=meta_mood,
                    meta_style=meta_style
                )[0]

                # Violation Checks
                v_tech = 0
                if _is_tech_violation:
                    words = get_tokens(action_merged)
                    if any(_is_tech_violation(w, loc_tag, costume_key) for w in words):
                        v_tech = 1
                
                v_sem = 1 if check_semantic_violation(action_merged, meta_mood_key, meta_mood) else 0
                v_style = 1 if check_style_violation(final) else 0

                run_samples.append(Sample(
                    pack_idx=pack_idx, seed=seed, run_id=run_id,
                    subj=subj, costume_key=costume_key, loc_tag=loc_tag, meta_mood_key=meta_mood_key,
                    costume=costume, loc=loc, garnish=garnish,
                    action_raw=action_raw, action_merged=action_merged, meta_mood=meta_mood, final=final,
                    violation_tech=v_tech, violation_sem=v_sem, violation_style=v_style
                ))
        
        all_run_samples[run_id] = run_samples

    # --- Analysis & Stats (Aggregated) ---
    
    # Fields to evaluate (unique/entropy/watch)
    fields = eval_fields
    
    # 1. Per-Pack Stability Analysis (averaged across runs)
    by_pack_rows = []
    
    # We need to map pack_idx -> [Sample_run0, Sample_run1...]
    samples_by_pack_run = defaultdict(lambda: defaultdict(list))
    for run_id, samples in all_run_samples.items():
        for s in samples:
            samples_by_pack_run[s.pack_idx][run_id].append(s)

    for pack_idx in sorted(samples_by_pack_run.keys()):
        # Just grab metadata from first sample of run 0
        ref_s = samples_by_pack_run[pack_idx][0][0]
        
        row = {
            "pack_idx": pack_idx, "subj": ref_s.subj, "loc_tag": ref_s.loc_tag
        }
        
        # Calculate stats for EACH run, then average
        run_stats = defaultdict(list)
        
        for run_id in range(args.runs):
            ss = samples_by_pack_run[pack_idx][run_id]
            run_stats["n"].append(len(ss))
            run_stats["tech_viol"].append(sum(x.violation_tech for x in ss) / len(ss))
            run_stats["sem_viol"].append(sum(x.violation_sem for x in ss) / len(ss))
            run_stats["style_viol"].append(sum(x.violation_style for x in ss) / len(ss))
            
            for f in fields:
                if not hasattr(ss[0], f): continue
                raw_vals = [getattr(x, f) for x in ss]
                norm_vals = [norm_text(v) for v in raw_vals]
                # Filter stopwords for unique rate etc
                core_vals = [get_core_tokens(v) for v in raw_vals]
                
                run_stats[f"{f}_uniq"].append(unique_rate(norm_vals))
                run_stats[f"{f}_core_uniq"].append(unique_rate(core_vals))
                
                # Distribution
                all_tokens = []
                for v in norm_vals:
                    all_tokens.extend(get_tokens(v))
                
                run_stats[f"{f}_entropy"].append(shannon_entropy(all_tokens))
                run_stats[f"{f}_top1_share"].append(topk_share(all_tokens, 1))
                
                # Watch Rate
                if f in watch_map:
                    terms = watch_map[f]
                    hit_count = sum(1 for v in raw_vals if sum(watch_hit_count(v, terms).values()) > 0)
                    run_stats[f"{f}_watch_rate"].append(hit_count / len(ss))

        # Store Mean and CV (std/mean) in the row
        row["n"] = int(statistics.mean(run_stats["n"]))
        
        for key, vals in run_stats.items():
            if key == "n": continue
            mean_val = statistics.mean(vals)
            row[key] = round(mean_val, 3)
            # Add CV for key metrics to check stability
            if "uniq" in key or "entropy" in key or "watch_rate" in key:
                 row[f"{key}_cv"] = round(calculate_cv(vals), 3)

        by_pack_rows.append(row)

    # 2. Global Analysis & Stability Check
    # Collect top tokens per run to compute Jaccard
    global_top_tokens_by_run = {run_id: {} for run_id in range(args.runs)}
    global_viol_counts = {run_id: Counter() for run_id in range(args.runs)}
    
    for run_id, samples in all_run_samples.items():
        # Aggregated tokens for this run
        field_tokens = {f: Counter() for f in fields}
        
        for s in samples:
            global_viol_counts[run_id]["tech"] += s.violation_tech
            global_viol_counts[run_id]["sem"] += s.violation_sem
            global_viol_counts[run_id]["style"] += s.violation_style
            
            for f in fields:
                if not hasattr(s, f): continue
                tks = get_tokens(getattr(s, f))
                # Filter stopwords for auto-detect logic
                cleaned = [t for t in tks if t not in STOPWORDS and len(t) > 1]
                field_tokens[f].update(cleaned)
        
        # Store top 50 words per field for Jaccard comp
        for f, cnt in field_tokens.items():
            global_top_tokens_by_run[run_id][f] = [w for w, _ in cnt.most_common(50)]

    # Calculate Jaccard Stability (Run 0 vs Run 1, Run 0 vs Run 2...)
    jaccard_scores = {f: [] for f in fields}
    if args.runs > 1:
        base_tokens = global_top_tokens_by_run[0]
        for run_id in range(1, args.runs):
            for f in fields:
                score = jaccard_similarity(base_tokens[f], global_top_tokens_by_run[run_id][f])
                jaccard_scores[f].append(score)
    else:
        for f in fields: jaccard_scores[f] = [1.0]

    # Global Stats
    global_stats = {
        "n_total": len(packs) * args.n * args.runs,
        "runs": args.runs,
        "seed_scheme": "v2_deterministic_offset",
        "jaccard_stability_top50": {f: round(statistics.mean(scores), 3) for f, scores in jaccard_scores.items()},
        "violations_total": {
            "tech": sum(global_viol_counts[r]["tech"] for r in range(args.runs)),
            "sem": sum(global_viol_counts[r]["sem"] for r in range(args.runs)),
            "style": sum(global_viol_counts[r]["style"] for r in range(args.runs))
        }
    }

    # Watch Summary (ALL runs aggregated)
    all_samples_flat = []
    for _rid, _ss in all_run_samples.items():
        all_samples_flat.extend(_ss)
    global_stats["watch_summary"] = compute_watch_summary(all_samples_flat, fields, watch_map)

    # --- GoalScore (v4) ---
    goal_cfg = _load_goal_cfg(args.goal_cfg)
    raw_concrete_terms = _merge_cfg_list(RAW_CONCRETE_TERMS_DEFAULT, goal_cfg.get("raw_concrete_terms"))
    prop_categories = _merge_cfg_dict_list(PROP_CATEGORIES_DEFAULT, goal_cfg.get("prop_categories"))
    bow_weapon_ctx = set(_merge_cfg_list(sorted(BOW_WEAPON_CONTEXT), goal_cfg.get("bow_weapon_context")))
    bow_courtesy_ctx = set(_merge_cfg_list(sorted(BOW_COURTESY_CONTEXT), goal_cfg.get("bow_courtesy_context")))
    intent_keywords = _merge_cfg_dict_list(INTENT_KEYWORDS_DEFAULT, goal_cfg.get("intent_keywords"))
    role_keywords = _merge_cfg_dict_list(ROLE_KEYWORDS_DEFAULT, goal_cfg.get("role_keywords"))
    role_forbid = _merge_cfg_dict_list(ROLE_FORBID_CATS_DEFAULT, goal_cfg.get("role_forbid_categories"))
    combat_terms = _merge_cfg_list(COMBAT_COMPLETION_TERMS, goal_cfg.get("combat_completion_terms"))

    intent_completion_rules = _merge_cfg_nested_dict_list(INTENT_COMPLETION_RULES_DEFAULT, goal_cfg.get("intent_completion_rules"))
    intent_completion_mins = dict(INTENT_COMPLETION_MINS_DEFAULT)
    intent_completion_mins.update(goal_cfg.get("intent_completion_mins") or {})

    bias_caps = dict(BIAS_CAPS_DEFAULT)
    if isinstance(goal_cfg.get("bias_caps"), dict):
        for k, v in goal_cfg["bias_caps"].items():
            try:
                bias_caps[str(k).strip().lower()] = float(v)
            except Exception:
                pass

    goals = {
        "raw_concrete_max": float(args.goal_raw_concrete_max),
        "mismatch_max": float(args.goal_mismatch_max),
        "combat_completion_min": float(args.goal_combat_completion_min),
        "relax_weapon_max": float(args.goal_relax_weapon_max),
    }

    goal_global, goal_by_pack_rows, mismatch_lines, pack_debug = _compute_goal_metrics(
        samples=all_samples_flat,
        samples_by_pack_run=samples_by_pack_run,
        raw_concrete_terms=raw_concrete_terms,
        prop_categories=prop_categories,
        bow_weapon_ctx=bow_weapon_ctx,
        bow_courtesy_ctx=bow_courtesy_ctx,
        intent_keywords=intent_keywords,
        role_keywords=role_keywords,
        role_forbid=role_forbid,
        combat_completion_terms=combat_terms,
        intent_completion_rules=intent_completion_rules,
        intent_completion_mins=intent_completion_mins,
        bias_caps=bias_caps,
        goals=goals,
        mismatch_examples_max=int(args.goal_mismatch_examples),
    )
    global_stats["goal_score"] = goal_global

    if not args.no_goal_emit:
        with open(os.path.join(args.out_dir, "score_global.json"), "w", encoding="utf-8") as f:
            json.dump(goal_global, f, ensure_ascii=False, indent=2)

        if goal_by_pack_rows:
            cat_cols = [f"{c}_rate" for c in bias_caps.keys()]
            header_goal = [
                "pack_idx", "n_samples", "subj", "costume_key", "loc_tag",
                "raw_concrete_rate", "combat_completion_rate", "relax_weapon_rate", "mismatch_rate",
                *cat_cols,
            ]
            write_csv(os.path.join(args.out_dir, "score_by_pack.csv"), goal_by_pack_rows, header_goal)

        if mismatch_lines:
            with open(os.path.join(args.out_dir, "mismatch_examples.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(mismatch_lines))

        # 2.5 Pack Priority List (CSV)
        priority_rows = _build_pack_priority_rows(goal_by_pack_rows, goals, bias_caps, intent_completion_mins)
        if priority_rows:
            header_pri = [
                "priority_rank","pack_idx","priority_score","reasons","n_samples","subj","costume_key","loc_tag",
                "fixed_terms","raw_concrete_rate","dominant_intent","dominant_intent_completion_rate","other_intent_rate",
                "dominant_role","role_unknown_rate","role_ambiguous_rate","role_entropy","mismatch_rate",
            ] + [f"{c}_rate" for c in bias_caps.keys()]
            write_csv(os.path.join(args.out_dir, "pack_priority.csv"), priority_rows, header_pri)

            # also emit a compact “intent gaps” view (dominant intent only)
            gaps = []
            for r in priority_rows:
                if "intent_under:" in (r.get("reasons") or "") or "intent_unknown" in (r.get("reasons") or ""):
                    gaps.append({
                        "pack_idx": r["pack_idx"],
                        "subj": r.get("subj",""),
                        "dominant_intent": r.get("dominant_intent","other"),
                        "dominant_intent_completion_rate": r.get("dominant_intent_completion_rate", 1.0),
                        "other_intent_rate": r.get("other_intent_rate", 0.0),
                        "reasons": r.get("reasons",""),
                    })
            if gaps:
                write_csv(os.path.join(args.out_dir, "intent_gaps_by_pack.csv"), gaps,
                          ["pack_idx","subj","dominant_intent","dominant_intent_completion_rate","other_intent_rate","reasons"])
    
    # Auto-detect top words (merged across all runs for final report)
    # Using Run 0 for representative "Top Words" display
    auto_watch_stats = {}
    tokens_run0 = Counter()
    for s in all_run_samples[0]:
        for f in fields:
             if not hasattr(s, f): continue
             if f not in auto_watch_stats: auto_watch_stats[f] = Counter()
             tks = get_tokens(getattr(s, f))
             cleaned = [t for t in tks if t not in STOPWORDS and len(t) > 1]
             auto_watch_stats[f].update(cleaned)
    
    global_stats["top_words_run0"] = {f: dict(c.most_common(20)) for f, c in auto_watch_stats.items()}

    # --- Watch attribution: which FIELD is causing spikes? ---
    all_samples_flat: List[Sample] = []
    for _rid, _ss in all_run_samples.items():
        all_samples_flat.extend(_ss)

    watch_stats = {}
    n_all = len(all_samples_flat)
    if n_all > 0:
        for f, terms in watch_map.items():
            if f not in fields:
                continue
            hits_any = 0
            term_counts = Counter()
            for s0 in all_samples_flat:
                txt = getattr(s0, f, "")
                c0 = watch_hit_count(txt, terms)
                if sum(c0.values()) > 0:
                    hits_any += 1
                term_counts.update(c0)

            term_rates = {t: (term_counts.get(t, 0) / n_all) for t in terms}
            term_rates_sorted = dict(sorted(((k, round(v, 4)) for k, v in term_rates.items()),
                                            key=lambda kv: (-kv[1], kv[0])))

            watch_stats[f] = {
                "watch_rate": round(hits_any / n_all, 4),
                "term_rates": term_rates_sorted,
            }

    global_stats["watch_stats"] = watch_stats

    # Compact CSV (field-level) for quick eyeballing
    watch_rows = []
    for f, st in watch_stats.items():
        tr = list(st.get("term_rates", {}).items())
        top_terms = ";".join([f"{k}:{v}" for k, v in tr[:10]])
        watch_rows.append({
            "field": f,
            "watch_rate": st.get("watch_rate", 0.0),
            "top_terms": top_terms,
        })
    if watch_rows:
        write_csv(os.path.join(args.out_dir, "watch_summary_global.csv"), watch_rows, ["field", "watch_rate", "top_terms"])

    # --- Output ---
    
    # 1. Pack Summary (CSV)
    header = ["pack_idx", "n", "subj", "loc_tag", "tech_viol", "sem_viol", "style_viol"]
    for f in fields:
        header.extend([f"{f}_uniq", f"{f}_uniq_cv", f"{f}_core_uniq", f"{f}_entropy", f"{f}_top1_share"])
        if f in watch_map:
            header.extend([f"{f}_watch_rate", f"{f}_watch_rate_cv"])
            
    write_csv(os.path.join(args.out_dir, "summary_by_pack.csv"), by_pack_rows, header)

    # 1.5. Term-by-pack watch table (CSV)
    # This shows WHICH term is spiking in WHICH pack & field, aggregated over ALL runs.
    watch_rows = build_watch_terms_by_pack_rows(samples_by_pack_run, watch_map)
    if watch_rows:
        write_csv(
            os.path.join(args.out_dir, "watch_terms_by_pack.csv"),
            watch_rows,
            ["pack_idx","subj","loc_tag","field","term","hit_count","hit_rate","n_samples"]
        )

    # 2. Global Analysis (JSON)
    with open(os.path.join(args.out_dir, "summary_global.json"), "w", encoding="utf-8") as f:
        json.dump(global_stats, f, ensure_ascii=False, indent=2)

    print(f"[OK] Analysis complete (Multi-Run v2). Check {args.out_dir}")
    print(f"  - Runs: {args.runs}")
    print(f"  - Style Violations: {global_stats['violations_total']['style']} (Goal: 0)")
    print(f"  - Jaccard Stability: {global_stats['jaccard_stability_top50']}")
    if "goal_score" in global_stats:
        gs = global_stats["goal_score"]
        print(f"  - GoalScore: {gs.get('score_total', 0.0)} / 100")
        fp = gs.get("fixed_pack", {}).get("count", 0)
        if fp:
            print(f"    - Fixed-Pack hits (raw concrete locked): {fp}")

if __name__ == "__main__":
    main()