#!/usr/bin/env python3
"""
scan_review_index.py — 離線掃描所有譯文，生成 review 索引

掃描所有 translated + 未 reviewed 的卷，檢測重複翻譯問題，
結果寫入 data/review_index.json，供 review 網頁讀取。

用法:
  python3 scripts/scan_review_index.py          # 掃描並生成索引
  python3 scripts/scan_review_index.py --all     # 包含已 reviewed 的（重掃全部）
"""

import sys
import re
import json
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _dup_common import effective_orig_count, char_jaccard, has_trad_simp_mixing, is_sequential_enum
from review_page import _analyze_section, _load_allowlist, _allowlist_key

ROOT = Path(__file__).parent.parent
SUTRAS_DIR = ROOT / "content" / "sutras-raw"
INDEX_FILE = ROOT / "data" / "review_index.json"

RE_SECTION = re.compile(
    r'(### 原文\n)(.*?)(\n### (?:現代語譯|现代语译)\n)(.*?)(?=\n### 原文|\Z)',
    re.DOTALL
)


def scan():
    parser = argparse.ArgumentParser(description="掃描生成 review 索引")
    parser.add_argument("--all", action="store_true", help="包含已 reviewed 的（重掃全部）")
    args = parser.parse_args()

    allowlist = _load_allowlist()
    result = {}
    scanned = 0
    skipped_status = 0
    skipped_reviewed = 0
    t0 = time.time()

    paths = sorted(SUTRAS_DIR.glob("*.md"))
    total = len(paths)

    for pi, path in enumerate(paths):
        content = path.read_text(encoding="utf-8")

        # 讀 frontmatter
        fm = {}
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                for line in content[3:end].splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        fm[k.strip()] = v.strip()

        ts = fm.get("translation_status", "untranslated")
        if ts != "translated":
            skipped_status += 1
            continue

        rs = fm.get("review_status", "unreviewed")
        if not args.all and rs.startswith("reviewed"):
            skipped_reviewed += 1
            continue

        slug = fm.get("slug", path.stem)
        cbeta_id = fm.get("cbeta_id", slug.rsplit("-", 1)[0])
        title = fm.get("title", slug)
        juan_index = int(fm.get("juan_index", 0))
        scanned += 1

        issue_count = 0
        max_repeat = 1
        total_sections = 0

        for idx, m in enumerate(RE_SECTION.finditer(content), 1):
            total_sections += 1
            if _allowlist_key(slug, idx) in allowlist:
                continue
            issues, _, rc = _analyze_section(m.group(2).strip(), m.group(4))
            if issues:
                issue_count += 1
                if rc > max_repeat:
                    max_repeat = rc

        result.setdefault(cbeta_id, []).append({
            "slug": slug,
            "title": title,
            "juan_index": juan_index,
            "issue_count": issue_count,
            "max_repeat": max_repeat,
            "total_sections": total_sections,
        })

        # 進度
        if scanned % 500 == 0:
            elapsed = time.time() - t0
            print(f"  [{scanned}/{total}] {elapsed:.0f}s ...", flush=True)

    # 排序
    for cid in result:
        result[cid].sort(key=lambda x: x["juan_index"])

    # 組裝
    filtered = {}
    for cid, juans in result.items():
        if any(j["issue_count"] > 0 for j in juans):
            filtered[cid] = {
                "juans": juans,
                "total_issues": sum(j["issue_count"] for j in juans),
            }
    sorted_items = sorted(filtered.items(), key=lambda x: -x[1]["total_issues"])
    total_issues = sum(v["total_issues"] for _, v in sorted_items)

    output = {
        "sutras": [{"cbeta_id": k, **v} for k, v in sorted_items],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stats": {
            "scanned": scanned,
            "skipped_not_translated": skipped_status,
            "skipped_reviewed": skipped_reviewed,
            "files_with_issues": len(filtered),
            "total_issues": total_issues,
        },
    }

    INDEX_FILE.parent.mkdir(exist_ok=True)
    INDEX_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.time() - t0
    print(f"\n{'='*50}")
    print(f"掃描完成（{elapsed:.1f}s）")
    print(f"  掃描文件: {scanned}")
    print(f"  跳過（未翻譯）: {skipped_status}")
    print(f"  跳過（已審閱）: {skipped_reviewed}")
    print(f"  有問題的經: {len(filtered)}")
    print(f"  問題段落: {total_issues}")
    print(f"  索引已寫入: {INDEX_FILE}")


if __name__ == "__main__":
    scan()
