#!/usr/bin/env python3
"""
把 content/sutras-raw/ 里「現代語譯」块的引号统一成 CBETA 的写法：「」『』。

  python3 scripts/normalize_quotes.py            # 预览，只统计
  python3 scripts/normalize_quotes.py --write    # 写回
  python3 scripts/normalize_quotes.py T0375-028 --write   # 只处理指定文稿

只改 `### 現代語譯` 下的段落，不动原文、标题、front matter。
“→「、”→」、‘→『、’→』；直引号 " 换成「」，' 换成『』（开合判断见 normalize）。不改变原有的内外层。
读者要看简体时，网页把「」『』换成“”‘’（见 global-script-toggle.js）。
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "content" / "sutras-raw"

RE_TRANS = re.compile(
    r"(### (?:現代語譯|现代语译)\n<!-- sid:\d+ -->\n)(.*?)(?=\n#{2,3} |\Z)", re.DOTALL
)
# 弯引号直接换成对应的直角引号，不改变开合和内外层
MAP = {"“": "「", "”": "」", "‘": "『", "’": "』"}
# 直引号 " 和 ' 分别换成「」和『』。块里数量是偶数时，按出现顺序一开一合；
# 数量是奇数（引号跨段）时，下一个字符是标点或块尾的当闭引号，其余当开引号。
# 前后都是英文字母的 '（如 Maitreya's）不动。
STRAIGHT = {'"': ("「", "」"), "'": ("『", "』")}
CLOSE_BEFORE = set("，。？！；：、）)」』\n")


def _is_latin(ch):
    return ch.isascii() and ch.isalpha()


def normalize(text):
    parity = {}
    for q in STRAIGHT:
        idx = [
            i for i, ch in enumerate(text)
            if ch == q and not (
                q == "'" and i and i + 1 < len(text) and _is_latin(text[i - 1]) and _is_latin(text[i + 1])
            )
        ]
        parity[q] = (idx, len(idx) % 2 == 0)
    straight = {}
    for q, (idx, even) in parity.items():
        for n, i in enumerate(idx):
            if even:
                is_open = n % 2 == 0
            else:
                nxt = text[i + 1] if i + 1 < len(text) else "\n"
                is_open = nxt not in CLOSE_BEFORE
            straight[i] = STRAIGHT[q][0 if is_open else 1]
    out = []
    for i, ch in enumerate(text):
        if ch in MAP:
            out.append(MAP[ch])
        elif i in straight:
            out.append(straight[i])
        else:
            out.append(ch)
    return "".join(out)


def process(path, write):
    text = path.read_text(encoding="utf-8")
    changed = 0
    bad = []

    def repl(m):
        nonlocal changed
        body = m.group(2)
        new = normalize(body)
        if new != body:
            changed += 1
        return m.group(1) + new

    new_text = RE_TRANS.sub(repl, text)
    if write and new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return changed, bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    paths = [RAW / f"{s}.md" for s in args.slugs] if args.slugs else sorted(RAW.glob("*.md"))
    files = blocks = 0
    for p in paths:
        if not p.exists():
            sys.exit(f"找不到 {p}")
        n, bad = process(p, args.write)
        if n:
            files += 1
            blocks += n
    verb = "已改" if args.write else "将改"
    print(f"{verb} {files} 个文稿、{blocks} 个译文块")


if __name__ == "__main__":
    main()
