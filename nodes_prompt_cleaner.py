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

    def _clean_core(self, s: str) -> str:
        if s is None:
            return ""

        # 改行正規化
        s = str(s).replace("\r\n", "\n").replace("\r", "\n")

        # 空括弧だけ除去（重み付け括弧 "((...))" は触らない）
        s = re.sub(r"\(\s*\)", "", s)
        s = re.sub(r"\[\s*\]", "", s)

        # 句読点の前に付いた空白を除去: "word ." -> "word."
        s = re.sub(r"[ \t]+([,.;:!?])", r"\1", s)

        # 文章で起きがちな衝突を解消: "., " や ".,"
        s = re.sub(r"([.?!])\s*,\s*", r"\1 ", s)

        # ", ." ", ?" など：カンマが句点直前に残った場合は削除
        s = re.sub(r",(?=\s*[.?!])", "", s)

        # ", , ," など連続カンマ
        s = re.sub(r",\s*,+", ", ", s)

        # ". ." ".." "..."（過剰な句点）
        s = re.sub(r"\.\s*\.+", ".", s)

        # 接続詞/前置詞だけが残ったケースを除去（空変数由来のゴミ）
        # 例: "and ." / "with ," / "in ." / "at ," など
        s = re.sub(
            r"\s+\b(and|with|while|in|at|near|inside|on|to)\b(?=\s*([,.;:!?])|\s*$)",
            "",
            s,
            flags=re.IGNORECASE,
        )

        # 文末記号の直後に単語が続くなら最低1スペースを入れる（"elements.high" 防止）
        s = re.sub(r"([.?!])(?=[A-Za-z(])", r"\1 ", s)

        # 余分なスペース整理
        s = re.sub(r"[ \t]{2,}", " ", s)
        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)

        return s.strip()

    def _clean_nl_extras(self, s: str) -> str:
        # NLテンプレ向けの追加整形（タグ列を壊しにくい範囲に限定）

        # "is, filled" のような不自然さを緩和（今回のテンプレで発生しやすい）
        # ※ "is, however" みたいな英文は通常プロンプトに来ない前提
        s = re.sub(r"\b(is|are|was|were),\s*", r"\1 ", s, flags=re.IGNORECASE)

        # カンマ後スペースを1個に統一（タグの区切りにも使える）
        s = re.sub(r",\s*", ", ", s)

        # 仕上げのスペース整理
        s = re.sub(r"[ \t]{2,}", " ", s).strip()
        return s

    def clean(self, text, mode="nl", drop_empty_lines=True):
        raw = "" if text is None else str(text)

        # 行ごとに処理（ネガプロンプト等で改行が意味を持つ場合もあるため）
        lines = raw.splitlines()
        out_lines = []

        for line in lines:
            s = self._clean_core(line)
            if mode == "nl":
                s = self._clean_nl_extras(s)

            if drop_empty_lines:
                if s:
                    out_lines.append(s)
            else:
                out_lines.append(s)

        return ("\n".join(out_lines).strip(),)

