#!/usr/bin/env python3
"""
status_report.py — 扫描 content/sutras-raw/，生成各经的进度汇总 docs/STATUS.md

内容：总体计数、translation_status / review_status 分布、ai_translator 分布，
以及有空 現代語譯 块的经（按空块数从多到少）。

用法:
  python3 scripts/status_report.py            # 写 docs/STATUS.md
  python3 scripts/status_report.py --stdout   # 只打印，不写文件
"""

import sys
import argparse
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, __import__("os").path.dirname(__file__))
from _fm_common import load_all, empty_blocks, ROOT


def build():
    ts, rs, tr = Counter(), Counter(), Counter()
    sutras = defaultdict(lambda: {"title": "", "juan": 0, "empty": 0, "empty_juan": 0, "models": set(), "review": Counter()})
    files = 0
    for path, fm, text in load_all():
        files += 1
        ts[fm.get("translation_status", "（无）")] += 1
        rs[fm.get("review_status", "（无）")] += 1
        tr[fm.get("ai_translator") or "（无）"] += 1
        sid = fm.get("cbeta_id") or path.stem.rsplit("-", 1)[0]
        s = sutras[sid]
        if not s["title"]:
            s["title"] = fm.get("title", "").rsplit(" 卷", 1)[0]
        s["juan"] += 1
        n = empty_blocks(text)
        s["empty"] += n
        s["empty_juan"] += 1 if n else 0
        s["models"].add(fm.get("ai_translator") or "（无）")
        s["review"][fm.get("review_status", "（无）")] += 1
    return files, ts, rs, tr, sutras


def table(counter, head):
    rows = [f"| {head} | 卷数 |", "| --- | ---: |"]
    rows += [f"| {k} | {v} |" for k, v in counter.most_common()]
    return "\n".join(rows)


def render():
    files, ts, rs, tr, sutras = build()
    empty_total = sum(s["empty"] for s in sutras.values())
    empty_files = sum(s["empty_juan"] for s in sutras.values())
    with_empty = sorted((s for s in sutras.items() if s[1]["empty"]), key=lambda x: -x[1]["empty"])
    out = [
        "# 经文进度汇总",
        "",
        "由 `scripts/status_report.py` 生成，不要手改。",
        "",
        f"- 经数：{len(sutras)}",
        f"- 卷文稿数：{files}",
        f"- 有空译文块的卷：{empty_files}，空译文块共 {empty_total} 个",
        "",
        "## translation_status",
        "",
        table(ts, "状态"),
        "",
        "## review_status",
        "",
        table(rs, "状态"),
        "",
        "## ai_translator",
        "",
        table(tr, "模型"),
        "",
        "## 有空译文块的经",
        "",
        "| 经号 | 经名 | 总卷数 | 有空块的卷 | 空块数 | 译者模型 |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for sid, s in with_empty:
        out.append(f"| {sid} | {s['title']} | {s['juan']} | {s['empty_juan']} | {s['empty']} | {'、'.join(sorted(s['models']))} |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    text = render()
    if args.stdout:
        print(text)
    else:
        out = ROOT / "docs" / "STATUS.md"
        out.parent.mkdir(exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"已写入 {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
