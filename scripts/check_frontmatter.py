#!/usr/bin/env python3
"""
check_frontmatter.py — 检查 content/sutras-raw/ 文稿是否符合 AGENTS.md 的 front matter 规范

检查项：
  - 必填字段：title、slug、cbeta_id、translation_status、review_status、updated_at
  - translation_status、review_status 只能取规范里的值
  - slug 与文件名一致
  - 旧字段 translated_by（应改为 ai_translator）
  - translated 的文稿必须有 ai_translator，且没有空的 現代語譯 块

用法:
  python3 scripts/check_frontmatter.py              # 汇总各类问题的数量
  python3 scripts/check_frontmatter.py -v           # 另列出每个有问题的文稿
  python3 scripts/check_frontmatter.py T0220        # 只查某部经
  有问题时退出码为 1
"""

import sys
import argparse
from collections import defaultdict

sys.path.insert(0, __import__("os").path.dirname(__file__))
from _fm_common import load_all, empty_blocks, TRANSLATION_STATUS, REVIEW_STATUS

REQUIRED = ["title", "slug", "cbeta_id", "translation_status", "review_status", "updated_at"]


def check(path, fm, text):
    issues = []
    if not fm:
        return ["没有 front matter"]
    for k in REQUIRED:
        if not fm.get(k):
            issues.append(f"缺字段 {k}")
    ts, rs = fm.get("translation_status"), fm.get("review_status")
    if ts and ts not in TRANSLATION_STATUS:
        issues.append(f"translation_status 非法值 {ts}")
    if rs and rs not in REVIEW_STATUS:
        issues.append(f"review_status 非法值 {rs}")
    if fm.get("slug") and fm["slug"] != path.stem:
        issues.append(f"slug {fm['slug']} 与文件名不一致")
    if "translated_by" in fm:
        issues.append("使用旧字段 translated_by")
    if ts == "translated":
        if not fm.get("ai_translator"):
            issues.append("translated 但没有 ai_translator")
        n = empty_blocks(text)
        if n:
            issues.append(f"translated 但有 {n} 个空译文块")
    return issues


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sutra", nargs="?", help="只查某部经，如 T0220")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    kinds = defaultdict(int)
    bad = []
    total = 0
    for path, fm, text in load_all():
        if args.sutra and fm.get("cbeta_id") != args.sutra and not path.stem.startswith(args.sutra + "-"):
            continue
        total += 1
        issues = check(path, fm, text)
        if issues:
            bad.append((path.name, issues))
            for i in issues:
                key = "translated 但有空译文块" if "个空译文块" in i else i
                kinds[key] += 1

    print(f"检查 {total} 个文稿，{len(bad)} 个有问题")
    for k, n in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f"  {n:6d}  {k}")
    if args.verbose:
        for name, issues in bad:
            print(f"{name}: {'；'.join(issues)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
