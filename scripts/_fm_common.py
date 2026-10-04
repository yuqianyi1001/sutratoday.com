#!/usr/bin/env python3
"""文稿 front matter 与译文块的共用解析（status_report.py、check_frontmatter.py 使用）。"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SUTRAS_DIR = ROOT / "content" / "sutras-raw"

TRANSLATION_STATUS = {"untranslated", "translating", "translated"}
REVIEW_STATUS = {"unreviewed", "reviewing", "ai_reviewed", "human_reviewed"}

# 現代語譯 标题下没有正文（只有 sid 注释或空白）的块
RE_EMPTY_BLOCK = re.compile(
    r'### (?:現代語譯|现代语译)\n(?:<!--[^\n]*-->\n)?\s*(?=\n### |\n## |\n# |\Z)'
)
RE_FM = re.compile(r'\A---\n(.*?)\n---', re.S)


def parse_front_matter(text: str) -> dict:
    m = RE_FM.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split("\n"):
        if ": " in line:
            k, v = line.split(": ", 1)
            fm[k.strip()] = v.strip()
        elif line.endswith(":"):
            fm[line[:-1].strip()] = ""
    return fm


def load_all():
    """逐个返回 (路径, front matter, 全文)。"""
    for p in sorted(SUTRAS_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        yield p, parse_front_matter(text), text


def empty_blocks(text: str) -> int:
    return len(RE_EMPTY_BLOCK.findall(text))
