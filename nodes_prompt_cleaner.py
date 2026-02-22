import re

class PromptCleaner:
    @classmethod
    def INPUT_TYPES(s):
        modes = ["safe", "nl"]  # safe: 最小修正 / nl: 英文テンプレ向けに少し整える
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "mode": (modes, {"default": "nl"}),  # 今回の templates.txt なら nl 推奨
                "drop_empty_lines": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("clean_text",)
    FUNCTION = "clean"
    CATEGORY = "prompt_builder"
    
    def __init__(self):
        self.article_exceptions = {
            "a": ["hour", "honest", "honor", "heir"],  # start with h but silent
            "an": ["unicorn", "university", "unit", "union", "unique", "euphoria", "one"] # start with vowel but y/w sound
        }

    def normalize_newlines(self, s: str) -> str:
        return s.replace("\r\n", "\n").replace("\r", "\n")

    def remove_empty_brackets(self, s: str) -> str:
        s = re.sub(r"\(\s*\)", "", s)
        s = re.sub(r"\[\s*\]", "", s)
        return s

    def fix_punctuation_spacing(self, s: str) -> str:
        # "word ." -> "word."
        s = re.sub(r"[ \t]+([,.;:!?])", r"\1", s)
        # "., " -> ". "
        s = re.sub(r"([.?!])\s*,\s*", r"\1 ", s)
        return s
        
    def fix_consecutive_punctuation(self, s: str) -> str:
        # ", ." -> ""
        s = re.sub(r",(?=\s*[.?!])", "", s)
        # ", , ," -> ", "
        s = re.sub(r",\s*,+", ", ", s)
        # ". ." -> "." (but keep "...")
        # To strictly follow previous logic: re.sub(r"\.\s*\.+", ".", s)
        # But maybe we want to keep ellipsis? The previous logic collapsed them.
        # Let's keep previous behavior for consistency, or improve it.
        # Plan says "overlap removal", but maybe ellipsis is fine in creative writing.
        # Let's collapse for now to be safe as per previous code.
        s = re.sub(r"\.\s*\.+", ".", s)
        return s

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
                    p_lower = p.lower()
                    if p_lower not in seen:
                        seen.add(p_lower)
                        new_parts.append(p)
                new_lines.append(", ".join(new_parts))
            else:
                new_lines.append(line)
        
        return "\n".join(new_lines)


    def _clean_nl_extras(self, s: str) -> str:
        # Previous NL extras
        s = re.sub(r"\b(is|are|was|were),\s*", r"\1 ", s, flags=re.IGNORECASE)
        s = re.sub(r",\s*", ", ", s)
        return s

    def clean(self, text, mode="nl", drop_empty_lines=True):
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
            # print(f"DEBUG 1 brackets: '{line}'")
            
            # 2. Words & Articles
            line = self.fix_punctuation_spacing(line)
            # print(f"DEBUG 2 punct: '{line}'")
            
            # 3. Articles
            line = self.fix_articles(line)
            # print(f"DEBUG 3 articles: '{line}'")
            
            # 4. Deduplication
            line = self.remove_duplicates(line)
            # print(f"DEBUG 4 dedupe: '{line}'")
            
            # 5. Cleanup
            line = self.fix_consecutive_punctuation(line)
            # print(f"DEBUG 5 consec: '{line}'")
            line = self.remove_dangling_words(line)
            # print(f"DEBUG 6 dangling: '{line}'")
            
            # Re-run punctuation spacing to fix artifacts (e.g. "word .")
            line = self.fix_punctuation_spacing(line)
            
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

