from __future__ import annotations

import re
from typing import Optional

_EMPTY_THINK_RE = re.compile(r"<think>\s*</think>", flags=re.I | re.S)
_ANY_THINK_RE = re.compile(r"<think>.*?</think>", flags=re.I | re.S)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def strip_empty_think_tags(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = _EMPTY_THINK_RE.sub("", text)
    cleaned = _MULTI_BLANK_RE.sub("\n\n", cleaned).strip()
    return cleaned


def strip_all_think_tags(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = _ANY_THINK_RE.sub("", text)
    cleaned = _MULTI_BLANK_RE.sub("\n\n", cleaned).strip()
    return cleaned


def make_preview(text: Optional[str], limit: int = 120, *, remove_think: bool = True) -> str:
    if not text:
        return ""
    visible = strip_empty_think_tags(text) if remove_think else text
    visible = visible.replace("\r\n", "\n").replace("\r", "\n")
    if len(visible) <= limit:
        return visible
    return visible[:limit]
