#!/usr/bin/env python3
"""
detect_dup_translations.py — 检测 sutras-raw/*.md 中「现代语译」块里的重复翻译

用法:
  python3 scripts/detect_dup_translations.py                 # 扫描全部
  python3 scripts/detect_dup_translations.py T0026-048.md   # 单文件
  python3 scripts/detect_dup_translations.py --summary       # 文件级摘要
"""

import re, argparse
from pathlib import Path
from _dup_common import effective_orig_count, char_jaccard, has_trad_simp_mixing, is_sequential_enum

SUTRAS_DIR = Path(__file__).parent.parent / "content" / "sutras-raw"
RE_SECTION = re.compile(r'### 原文\n(.*?)\n### 现代语译\n(.*?)(?=\n### 原文|\Z)', re.DOTALL)
SIM_T = 0.25


def detect_issues(orig_text, trans_text):
    issues = []
    orig_lines = [l for l in orig_text.splitlines() if l.strip()]
    trans_nonempty = [l for l in trans_text.splitlines() if l.strip()]
    n_eff = effective_orig_count(orig_text, orig_lines)
    if n_eff == 0 or not trans_nonempty:
        return issues

    # Type A: 连续相邻精确重复
    dup_lines = [trans_nonempty[i] for i in range(1, len(trans_nonempty))
                 if trans_nonempty[i] == trans_nonempty[i - 1]]
    if dup_lines:
        issues.append({"type": "A", "detail": f"{len(dup_lines)} 行连续相邻重复",
                        "examples": dup_lines[:3]})

    # Type B: 多版本叠加
    deduped = [trans_nonempty[0]]
    for l in trans_nonempty[1:]:
        if l != deduped[-1]:
            deduped.append(l)
    n_d = len(deduped)
    ratio = n_d / n_eff

    if ratio >= 2.0:
        gs = n_eff
        k = round(ratio)
        if k >= 2 and not is_sequential_enum(deduped, gs):
            # 字符长度比：合法拆行 ≈ 1.x，真正重复 ≈ Nx
            orig_chars = len(orig_text.replace(" ", "").replace("\u3000", "").replace("\n", ""))
            trans_chars = sum(len(l.replace(" ", "")) for l in deduped)
            char_ratio = trans_chars / orig_chars if orig_chars else 0

            if char_ratio >= 2.0:
                g1 = " ".join(deduped[:gs])
                gk = " ".join(deduped[-gs:])
                j = char_jaccard(g1, gk)
                mixed = has_trad_simp_mixing("\n".join(deduped))

                if j >= SIM_T or mixed:
                    # 后置校验：建议保留（末尾 gs 行）不能比原文短
                    sug_chars = sum(len(l.replace(" ", "")) for l in deduped[-gs:])
                    if sug_chars < orig_chars:
                        pass  # 建议保留比原文短 → 是合法逐句翻译，撤销
                    else:
                        is_verse = "\u3000\u3000" in orig_text
                        detail = (f"译文{n_d}行 vs {n_eff}{'半句' if is_verse else '行'}，"
                                  f"{ratio:.1f}x，约{k}版，J={j:.2f}")
                        if mixed and j < SIM_T:
                            detail += "，繁简混排"
                        issues.append({"type": "B", "detail": detail})
    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    paths = ([SUTRAS_DIR / f if not Path(f).is_absolute() else Path(f) for f in args.files]
             if args.files else sorted(SUTRAS_DIR.glob("*.md")))

    total_files, total_issues = 0, 0
    for path in paths:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        file_results = []
        for i, m in enumerate(RE_SECTION.finditer(content), 1):
            issues = detect_issues(m.group(1).strip(), m.group(2))
            if issues:
                file_results.append({"section": i,
                    "orig": m.group(1).strip()[:60].replace("\n"," "), "issues": issues})
        if not file_results:
            continue
        total_files += 1
        total_issues += sum(len(r["issues"]) for r in file_results)
        print(f"\n{'='*70}\n文件：{path.name}  （{len(file_results)} 段）")
        if not args.summary:
            for r in file_results:
                print(f"  第 {r['section']} 段  原文：{r['orig']}…")
                for iss in r["issues"]:
                    print(f"    [{iss['type']}] {iss['detail']}")
                    for ex in iss.get("examples", []):
                        print(f"      示例：{ex[:80]}")
    print(f"\n{'='*70}\n扫描完成：{len(paths)} 文件，{total_files} 有问题，共 {total_issues} 处。")


if __name__ == "__main__":
    main()
