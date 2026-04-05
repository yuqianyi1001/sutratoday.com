#!/usr/bin/env python3
"""
review_dup_translations.py — 生成人工审阅报告（Markdown 格式）

复用 review_page.py 的检测逻辑，避免重复维护。

用法:
  python3 scripts/review_dup_translations.py > review_all_issues.md
  python3 scripts/review_dup_translations.py T0026-048.md
"""

import re, argparse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from review_page import _analyze_section, RE_SECTION

SUTRAS_DIR = Path(__file__).parent.parent / "content" / "sutras-raw"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    parser.add_argument("--max-files", type=int, default=0)
    args = parser.parse_args()
    paths = ([SUTRAS_DIR / f if not Path(f).is_absolute() else Path(f) for f in args.files]
             if args.files else sorted(SUTRAS_DIR.glob("*.md")))
    if args.max_files:
        paths = paths[:args.max_files]

    total_sections, total_files = 0, 0
    print("# 译文重复问题审阅报告\n")

    for path in paths:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")

        # 无指定文件时只看 translated
        if not args.files:
            m = re.search(r'^translation_status:\s*(.+)$', content, re.MULTILINE)
            if m and m.group(1).strip() != 'translated':
                continue

        issues_list = []
        for i, sm in enumerate(RE_SECTION.finditer(content), 1):
            orig = sm.group(1 if len(sm.groups()) == 2 else 2).strip()
            trans = sm.group(2 if len(sm.groups()) == 2 else 4)
            iss, suggested, rc = _analyze_section(orig, trans)
            if not iss:
                continue
            trans_lines = [l for l in trans.splitlines() if l.strip()]
            fixed_lines = [l for l in ("\n".join(suggested) if suggested else trans).splitlines() if l.strip()]
            issues_list.append({
                "section": i, "orig": orig, "repeat_count": rc,
                "trans": trans_lines, "fixed": fixed_lines,
                "changes": [f"{x['type']}: {x['detail']}" for x in iss],
            })

        if not issues_list:
            continue
        total_files += 1
        total_sections += len(issues_list)
        print(f"\n---\n\n## {path.name}  （{len(issues_list)} 段）\n")
        for r in issues_list:
            orig_s = r["orig"][:80].replace("\n", " ")
            print(f"### 第 {r['section']} 段\n")
            print(f"**原文：** `{orig_s}`{'…' if len(r['orig']) > 80 else ''}\n")
            print(f"**修复说明：** {' | '.join(r['changes'])}\n")
            print("**当前译文：**\n")
            for line in r["trans"]:
                print(f"> {line}")
            print(f"\n**建议保留：**\n")
            for line in r["fixed"]:
                print(f"✅ {line}")
            print()

    print(f"\n---\n\n## 汇总\n\n- 有问题的文件：**{total_files}**\n- 有问题的段落：**{total_sections}**")


if __name__ == "__main__":
    main()
