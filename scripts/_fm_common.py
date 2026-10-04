#!/usr/bin/env python3
"""文稿 front matter 与译文块的共用解析（status_report.py、check_frontmatter.py 使用）。"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SUTRAS_DIR = ROOT / "content" / "sutras-raw"

TRANSLATION_STATUS = {"untranslated", "translating", "translated"}
REVIEW_STATUS = {"unreviewed", "reviewing", "ai_reviewed", "human_reviewed"}

# 原文 / 現代語譯 成对的块；译文槽取到下一个 `### 原文`、`## ` 标题或文末
RE_PAIR = re.compile(
    r'### 原文\n(.*?)\n### (?:現代語譯|现代语译)\n(.*?)(?=\n### 原文|\n## |\Z)', re.S
)
RE_COMMENT = re.compile(r'<!--.*?-->', re.S)
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
    """現代語譯 下没有正文（只有 sid 注释或空白）的块数。"""
    return sum(1 for m in RE_PAIR.finditer(text) if not RE_COMMENT.sub("", m.group(2)).strip())
