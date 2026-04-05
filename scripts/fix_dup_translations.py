#!/usr/bin/env python3
"""
fix_dup_translations.py — 修复 sutras-raw/*.md 中「现代语译」块的重复翻译

用法:
  python3 scripts/fix_dup_translations.py                       # dry-run
  python3 scripts/fix_dup_translations.py --write               # 实际写入
  python3 scripts/fix_dup_translations.py T0026-048.md --write  # 单文件
"""

import re, argparse
from pathlib import Path
from _dup_common import effective_orig_count, char_jaccard, has_trad_simp_mixing, is_sequential_enum

SUTRAS_DIR = Path(__file__).parent.parent / "content" / "sutras-raw"
RE_SECTION = re.compile(r'(### 原文\n)(.*?)(\n### 现代语译\n)(.*?)(?=\n### 原文|\Z)', re.DOTALL)
SIM_T = 0.25


def fix_block(orig_text, trans_text):
    orig_lines = [l for l in orig_text.splitlines() if l.strip()]
    n_eff = effective_orig_count(orig_text, orig_lines)
    if n_eff == 0:
        return trans_text, []
    trans_nonempty = [l for l in trans_text.splitlines() if l.strip()]
    if not trans_nonempty:
        return trans_text, []

    changes = []

    # Step 1: 连续相邻精确去重
    deduped = [trans_nonempty[0]]
    removed = 0
    for l in trans_nonempty[1:]:
        if l == deduped[-1]:
            removed += 1
        else:
            deduped.append(l)
    if removed:
        changes.append(f"步骤1: 删除 {removed} 行连续相邻重复")

    # Step 2: 多版本裁剪
    n_d = len(deduped)
    ratio = n_d / n_eff
    if ratio >= 2.0:
        gs = n_eff
        k = round(ratio)
        if k >= 2 and not is_sequential_enum(deduped, gs):
            orig_chars = len(orig_text.replace(" ", "").replace("\u3000", "").replace("\n", ""))
            trans_chars = sum(len(l.replace(" ", "")) for l in deduped)
            char_ratio = trans_chars / orig_chars if orig_chars else 0

            if char_ratio >= 2.0:
                g1 = " ".join(deduped[:gs])
                gk = " ".join(deduped[-gs:])
                j = char_jaccard(g1, gk)
                mixed = has_trad_simp_mixing("\n".join(deduped))

                if j >= SIM_T or mixed:
                    # 后置校验：建议保留不能比原文短
                    sug_chars = sum(len(l.replace(" ", "")) for l in deduped[-gs:])
                    if sug_chars >= orig_chars:
                        is_verse = "\u3000\u3000" in orig_text
                        kept = deduped[-gs:]
                        trigger = f"J={j:.2f}"
                        if mixed and j < SIM_T:
                            trigger += "+繁简混排"
                        changes.append(
                            f"步骤2: 多版本（{n_d}/{n_eff}"
                            f"{'半句' if is_verse else '行'}={ratio:.1f}x，"
                            f"约{k}版，{trigger}），保留末尾 {gs} 行"
                        )
                        deduped = kept

    if not changes:
        return trans_text, []
    leading = "\n" if trans_text.startswith("\n") else ""
    trailing = "\n" if trans_text.endswith("\n") else ""
    return leading + "\n".join(deduped) + trailing, changes


def fix_file(md_path, dry_run=True):
    content = md_path.read_text(encoding="utf-8")
    new_content = content
    n = 0
    for m in RE_SECTION.finditer(content):
        orig_text = m.group(2).strip()
        fixed, changes = fix_block(orig_text, m.group(4))
        if not changes:
            continue
        n += 1
        preview = orig_text[:50].replace("\n"," ") + ("…" if len(orig_text) > 50 else "")
        print(f"  [{n}] {preview}")
        for c in changes:
            print(f"      {c}")
        if dry_run:
            before = [l for l in m.group(4).splitlines() if l.strip()]
            after = [l for l in fixed.splitlines() if l.strip()]
            print(f"      前({len(before)}行) → 后({len(after)}行)")
        else:
            new_content = new_content.replace(m.group(0),
                m.group(1) + m.group(2) + m.group(3) + fixed, 1)
    if not dry_run and n > 0:
        md_path.write_text(new_content, encoding="utf-8")
        print(f"  ✓ 已写入 {md_path.name}")
    return n


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    dry_run = not args.write
    print(f"[{'DRY-RUN' if dry_run else 'WRITE'}]\n")
    paths = ([SUTRAS_DIR / f if not Path(f).is_absolute() else Path(f) for f in args.files]
             if args.files else sorted(SUTRAS_DIR.glob("*.md")))
    tf, ts = 0, 0
    for path in paths:
        if not path.exists():
            continue
        n = fix_file(path, dry_run)
        if n:
            tf += 1; ts += n
            print(f"  → {n} 段")
    print(f"\n{'='*60}\n完成{'（未写入）' if dry_run else '（已写入）'}：{tf} 文件 {ts} 段")


if __name__ == "__main__":
    main()
