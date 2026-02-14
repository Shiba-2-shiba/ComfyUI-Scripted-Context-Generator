"""Garnish vocabulary - Utility functions."""

from __future__ import annotations
from typing import List
import re

def normalize(tag: str) -> str:
    """タグの正規化（前後の空白・末尾句読点除去、二重スペース圧縮）"""
    if not tag:
        return ""
    s = tag.strip()
    while s and s[-1] in ".,;!?":
        s = s[:-1].strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _dedupe(seq: List[str]) -> List[str]:
    """順序保持の重複除去"""
    seen = set()
    out: List[str] = []
    for s in seq:
        norm = normalize(s)
        key = norm.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(norm)
    return out

def _merge_unique(*lists: List[str]) -> List[str]:
    buf: List[str] = []
    for lst in lists:
        buf.extend(lst or [])
    return _dedupe(buf)

