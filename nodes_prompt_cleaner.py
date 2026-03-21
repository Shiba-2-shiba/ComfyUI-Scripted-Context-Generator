import re

try:
    from .core.semantic_policy import normalize_fragment_text, remove_banned_terms
except ImportError:
    from core.semantic_policy import normalize_fragment_text, remove_banned_terms

class PromptCleaner:
    @classmethod
    def INPUT_TYPES(s):
        modes = ["safe", "nl"]  # safe: 最小修正 / nl: 英文テンプレ向けに少し整える
        return {
            "required": {
                "mode": (modes, {"default": "nl"}),  # 今回の templates.txt なら nl 推奨
                "drop_empty_lines": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "text": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        return True

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("clean_text",)
    FUNCTION = "clean"
    CATEGORY = "prompt_builder/utility"
    
    def __init__(self):
        self.article_exceptions = {
            "a": ["hour", "honest", "honor", "heir"],  # start with h but silent
            "an": ["unicorn", "university", "unit", "union", "unique", "euphoria", "one"] # start with vowel but y/w sound
        }
        self.fx_allowlist_phrases = ("sparkling eyes", "snowflakes", "snowflake")
        self.fx_deny_patterns = (
            re.compile(r"\bimaginary\b", re.IGNORECASE),
            re.compile(r"\bconfetti\b", re.IGNORECASE),
            re.compile(r"\bfloating dust particles?\b", re.IGNORECASE),
            re.compile(r"\bsparkling air\b", re.IGNORECASE),
            re.compile(r"\bsparkles?\b", re.IGNORECASE),
            re.compile(r"\bglittering air\b", re.IGNORECASE),
            re.compile(r"\bbokeh\b", re.IGNORECASE),
            re.compile(r"\bfilm grain\b", re.IGNORECASE),
            re.compile(r"\bbloom\b", re.IGNORECASE),
            re.compile(r"\bambient occlusion\b", re.IGNORECASE),
            re.compile(r"\bvolumetric lighting?\b", re.IGNORECASE),
            re.compile(r"\bprismatic light leaks?\b", re.IGNORECASE),
            re.compile(r"\blight leaks?\b", re.IGNORECASE),
            re.compile(r"\bchromatic aberration\b", re.IGNORECASE),
            re.compile(r"\blens flares?\b", re.IGNORECASE),
            re.compile(r"\bdust motes?\b", re.IGNORECASE),
            re.compile(r"\bdust particles?\b", re.IGNORECASE),
            re.compile(r"\bfloating dust\b", re.IGNORECASE),
            re.compile(r"\bsparkling(?!\s+eyes?\b)\w*\b", re.IGNORECASE),
        )

    def remove_disallowed_fx_terms(self, s: str) -> str:
        token_map = {}
        protected = s

        for phrase in self.fx_allowlist_phrases:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)

            def _repl(match):
                key = f"__ALLOW_FX_{len(token_map)}__"
                token_map[key] = match.group(0)
                return key

            protected = pattern.sub(_repl, protected)

        cleaned_segments = []
        segments = [seg.strip() for seg in protected.split(",")]
        for seg in segments:
            if not seg:
                continue

            has_deny = any(p.search(seg) for p in self.fx_deny_patterns)
            has_allow = "__ALLOW_FX_" in seg

            if has_deny and not has_allow:
                continue

            if has_deny and has_allow:
                for pat in self.fx_deny_patterns:
                    seg = pat.sub("", seg)
                seg = re.sub(r"\s{2,}", " ", seg).strip(" ,")
                if not seg:
                    continue

            cleaned_segments.append(seg)

        out = ", ".join(cleaned_segments)
        for key, value in token_map.items():
            out = out.replace(key, value)
        return out

    def normalize_newlines(self, s: str) -> str:
        return s.replace("\r\n", "\n").replace("\r", "\n")

    def remove_empty_brackets(self, s: str) -> str:
        s = re.sub(r"\(\s*\)", "", s)
        s = re.sub(r"\[\s*\]", "", s)
        return s

    def fix_punctuation_spacing(self, s: str) -> str:
        return normalize_fragment_text(s)
        
    def fix_consecutive_punctuation(self, s: str) -> str:
        return normalize_fragment_text(s)

    def remove_dangling_words(self, s: str) -> str:
        # "and .", "with ," etc.
        return re.sub(
            r"\s+\b(and|with|while|in|at|near|inside|on|to)\b(?=\s*([,.;:!?])|\s*$)",
            "",
            s,
            flags=re.IGNORECASE,
        )

    def ensure_sentence_spacing(self, s: str) -> str:
        # ".Word" -> ". Word"
        return re.sub(r"([.?!])(?=[A-Za-z(])", r"\1 ", s)

    def collapse_whitespace(self, s: str) -> str:
        s = re.sub(r"[ \t]{2,}", " ", s)
        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()

    def fix_articles(self, s: str) -> str:
        # Simple A/An fixer.
        # 1. Find "a" or "an" followed by a word.
        # 2. Check if the word starts with vowel sound.
        
        def callback(match):
            article = match.group(1).lower()
            word = match.group(2)
            word_lower = word.lower()
            
            # Check exceptions first
            if word_lower in self.article_exceptions["a"]: # should be 'an'
                return f"{'An' if article[0].isupper() else 'an'} {word}"
            if word_lower in self.article_exceptions["an"]: # should be 'a'
                return f"{'A' if article[0].isupper() else 'a'} {word}"
                
            # General rule
            is_vowel_start = word_lower[0] in "aeiou"
            
            if is_vowel_start:
                return f"{'An' if article[0].isupper() else 'an'} {word}"
            else:
                return f"{'A' if article[0].isupper() else 'a'} {word}"

        # Regex to find "a/an" + word
        # \b(a|an)\s+([a-z]+)
        return re.sub(r"\b(a|an)\s+([a-z]+)", callback, s, flags=re.IGNORECASE)

    def remove_duplicates(self, s: str) -> str:
        # Simple deduplication of comma-separated tokens
        # Split by comma, strip, dedupe preserving order
        
        # We only want to dedupe within a line/sentence context to be safe, 
        # but prompt is often just a list of tags. 
        # Let's try to handle the whole string if it looks like a list.
        
        # Strategy:
        # 1. Split by newlines.
        # 2. For each line, split by comma.
        # 3. Dedupe.
        # 4. Join back.
        
        lines = s.split('\n')
        new_lines = []
        for line in lines:
            # Check if it has commas
            if ',' in line:
                parts = [p.strip() for p in line.split(',')]
                seen = set()
                new_parts = []
                for p in parts:
                    if not p: continue # skip empty
                    p_lower = re.sub(r"[.?!]+$", "", p.lower()).strip()
                    trailing_punctuation = re.search(r"[.?!]+$", p)
                    if p_lower not in seen:
                        seen.add(p_lower)
                        new_parts.append(p)
                        continue
                    if (
                        trailing_punctuation
                        and new_parts
                        and re.sub(r"[.?!]+$", "", new_parts[-1].lower()).strip() == p_lower
                        and not re.search(r"[.?!]+$", new_parts[-1])
                    ):
                        new_parts[-1] = f"{new_parts[-1]}{trailing_punctuation.group(0)}"
                new_lines.append(", ".join(new_parts))
            else:
                new_lines.append(line)
        
        return "\n".join(new_lines)


    def _clean_nl_extras(self, s: str) -> str:
        # Previous NL extras
        s = re.sub(r"\b(is|are|was|were),\s*", r"\1 ", s, flags=re.IGNORECASE)
        s = re.sub(r",\s*", ", ", s)
        return s

    def clean(self, mode="nl", drop_empty_lines=True, text=""):
        if text is None: text = ""
        s = str(text)
        if mode not in ["safe", "nl"]:
            mode = "nl"
        drop_empty_lines = bool(drop_empty_lines)

        # Pipeline
        s = self.normalize_newlines(s)
        
        # Early empty line check (optional, but we do it at the end usually)
        
        # Line-based processing implies splitting first, but some regexes work better on full text.
        # The previous implementation split lines first.
        # Let's stick to line-based for safety on "drop_empty_lines".
        
        lines = s.splitlines()
        out_lines = []
        
        for line in lines:
            # Apply pipeline to each line
            # print(f"DEBUG 0: '{line}'")
            
            # 1. Basic Structure
            line = self.remove_empty_brackets(line)
            line = self.remove_disallowed_fx_terms(line)
            line = remove_banned_terms(line)
            # print(f"DEBUG 1 brackets: '{line}'")
            
            # 2. Articles
            line = self.fix_articles(line)
            # print(f"DEBUG 3 articles: '{line}'")
            
            # 3. Deduplication
            line = self.remove_duplicates(line)
            # print(f"DEBUG 4 dedupe: '{line}'")
            
            # 4. Cleanup
            line = self.remove_dangling_words(line)
            # print(f"DEBUG 6 dangling: '{line}'")
            
            line = normalize_fragment_text(line)
            
            line = self.ensure_sentence_spacing(line)
            # print(f"DEBUG 7 spacing: '{line}'")
            
            if mode == "nl":
                line = self._clean_nl_extras(line)
                # print(f"DEBUG 8 nl: '{line}'")
            
            line = self.collapse_whitespace(line)
            # print(f"DEBUG 9 collapse: '{line}'")
            
            if drop_empty_lines and not line:
                continue
                
            out_lines.append(line)
            
        return ("\n".join(out_lines).strip(),)


NODE_CLASS_MAPPINGS = {
    "PromptCleaner": PromptCleaner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptCleaner": "Prompt Cleaner",
}

