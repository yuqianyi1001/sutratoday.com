#!/usr/bin/env python3
"""
init_jobs.py — 扫描 content/sutras-raw/*.md，初始化翻译任务队列

用法:
  python3 scripts/init_jobs.py            # 扫描全部，增量更新
  python3 scripts/init_jobs.py --reset    # 重置所有 pending/failed 任务（慎用）
  python3 scripts/init_jobs.py T0001      # 只扫描 T0001 系列
"""

import re
import sys
import argparse
from pathlib import Path

# 把 scripts/ 加入路径，方便导入 job_queue
sys.path.insert(0, str(Path(__file__).parent))
import job_queue

SUTRAS_DIR = Path(__file__).parent.parent / "content" / "sutras-raw"

RE_ORIG = re.compile(r'### 原文\n(.*?)(?=\n### (?:現代語譯|现代语译))', re.DOTALL)
RE_TRANS = re.compile(r'### (?:現代語譯|现代语译)\n(.*?)(?=\n### 原文|\Z)', re.DOTALL)

# 类别优先级（越高越先翻）
CATEGORY_PRIORITY = {
    "阿含部類": 10,
    "本緣部類": 9,
    "般若部類": 8,
    "法華部類": 7,
    "華嚴部類": 7,
    "寶積部類": 6,
    "涅槃部類": 6,
    "大集部類": 5,
    "經集部類": 5,
    "律部類":   4,
    "論部類":   3,
    "論集部類": 3,
}


def parse_frontmatter(text: str) -> dict:
    fm = {}
    in_fm = False
    for i, line in enumerate(text.splitlines()):
        if i == 0 and line.strip() == "---":
            in_fm = True
            continue
        if in_fm:
            if line.strip() == "---":
                break
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
    return fm


def count_segments(text: str) -> tuple[int, int]:
    """返回 (seg_total, seg_done)。判断"已翻译"时剔除 <!-- sid:NNN --> 注释。"""
    orig_blocks = RE_ORIG.findall(text)
    trans_blocks = RE_TRANS.findall(text)
    total = len(orig_blocks)
    done = 0
    for t in trans_blocks:
        # 把 sid 注释行剥掉再判空
        cleaned = re.sub(r'<!--\s*sid:\d+\s*-->', '', t).strip()
        if cleaned:
            done += 1
    return total, done


def scan_file(md_path: Path):
    try:
        content = md_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  [跳过] 读取失败: {md_path.name}: {e}")
        return None

    fm = parse_frontmatter(content)
    slug = fm.get("slug") or md_path.stem
    seg_total, seg_done = count_segments(content)
    category = fm.get("category", "")
    cbeta_id = fm.get("cbeta_id", "")
    juan_index = int(fm.get("juan_index", 0))
    priority = CATEGORY_PRIORITY.get(category, 0)

    return dict(
        slug=slug,
        file_path=str(md_path),
        seg_total=seg_total,
        seg_done=seg_done,
        category=category,
        cbeta_id=cbeta_id,
        juan_index=juan_index,
        priority=priority,
    )


def main():
    parser = argparse.ArgumentParser(description="初始化翻译任务队列")
    parser.add_argument("filter", nargs="?", default="", help="只处理匹配前缀的文件，如 T0001")
    parser.add_argument("--reset", action="store_true", help="把 pending/failed 任务重置（不影响 done/running）")
    args = parser.parse_args()

    job_queue.init_db()

    pattern = f"{args.filter}*.md" if args.filter else "*.md"
    files = sorted(SUTRAS_DIR.glob(pattern))
    print(f"扫描 {len(files)} 个文件...")

    inserted = updated = skipped = 0
    for md_path in files:
        info = scan_file(md_path)
        if not info:
            skipped += 1
            continue

        job_queue.upsert_job(**info)

        # 若 md 标记为 translated 但 seg_done < seg_total，修正状态
        if info["seg_done"] >= info["seg_total"] and info["seg_total"] > 0:
            # 已完成，upsert_job 会设 done
            pass
        updated += 1

    print(f"完成：更新 {updated} 条，跳过 {skipped} 条")
    job_queue.print_status()


if __name__ == "__main__":
    main()
