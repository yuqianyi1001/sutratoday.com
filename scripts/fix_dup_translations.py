#!/usr/bin/env python3
"""
fix_dup_translations.py — 修复 sutras-raw/*.md 中「现代语译」块的重复翻译与多版本叠放

用法:
  python3 scripts/fix_dup_translations.py                       # dry-run
  python3 scripts/fix_dup_translations.py --write               # 实际写入
  python3 scripts/fix_dup_translations.py T0026-048.md --write  # 单文件
"""

import re, argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _dup_common import effective_orig_count, char_jaccard, has_trad_simp_mixing, is_sequential_enum

SUTRAS_DIR = Path(__file__).parent.parent / "content" / "sutras-raw"
RE_SECTION = re.compile(r'(### 原文\n)(.*?)(\n### (?:現代語譯|现代语译)\n)(.*?)(?=\n### 原文|\Z)', re.DOTALL)
SIM_T = 0.25


def _clean_sid(text: str) -> str:
    return re.sub(r'^\s*<!--\s*sid:\d+\s*-->\s*', '', text).strip()


def _get_sid(text: str) -> str:
    m = re.search(r'<!--\s*sid:\d+\s*-->', text)
    return m.group(0) if m else ""


def fix_block(orig_text, trans_text):
    sid = _get_sid(trans_text)
    orig_clean = _clean_sid(orig_text)
    trans_clean = _clean_sid(trans_text)

    orig_lines = [l for l in orig_clean.splitlines() if l.strip()]
    n_eff = effective_orig_count(orig_clean, orig_lines)
    if n_eff == 0:
        return trans_text, []
    trans_nonempty = [l for l in trans_clean.splitlines() if l.strip()]
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

    n_d = len(deduped)

    # Step 1.4: 针对 X1470-019 sid:020 等超量循环变体重复 (例如 7 遍叠放)
    if n_d >= 6 and n_eff in (3, 4):
        g_first = deduped[:n_eff]
        reps = 0
        for i in range(n_eff, n_d, n_eff):
            chunk = deduped[i:i+n_eff]
            if chunk and char_jaccard(" ".join(chunk), " ".join(g_first)) >= 0.5:
                reps += 1
        if reps >= 2:
            changes.append(f"步骤1.4: 清理循环变体重复，保留首套 {n_eff} 行")
            deduped = g_first
            n_d = len(deduped)

    # Step 1.5: 译文后半段误贴文言文原文 (严格要求 n_d > n_eff 且整体长度匹配，如 T1448-004)
    if n_d > n_eff and n_d >= 2:
        half = n_d // 2
        first_half = " ".join(deduped[:half])
        second_half = " ".join(deduped[half:])
        len_ratio = len(second_half) / max(1, len(orig_clean))
        if len_ratio >= 0.8 and char_jaccard(second_half, orig_clean) >= 0.85 and char_jaccard(first_half, orig_clean) < 0.6:
            changes.append("步骤1.5: 发现后半段误贴文言文原文，保留前半段现代语译")
            deduped = deduped[:half]
            n_d = len(deduped)

    # Step 1.6: 跨段错位多翻译 (如 T0120-003 sid:007, sid:008)
    if "非苦是真諦" in orig_clean and "並非『集』" in " ".join(deduped) and "並非『苦』" in " ".join(deduped):
        idx = -1
        for i, l in enumerate(deduped):
            if "並非『苦』" in l or "並非苦" in l:
                idx = i + 1
                break
        if idx > 0 and idx < len(deduped):
            changes.append(f"步骤1.6: 裁剪跨段错位多翻译的后半段 (保留前 {idx} 行)")
            deduped = deduped[:idx]
            n_d = len(deduped)

    if "第一畢竟恒" in orig_clean and "非集是真諦" in orig_clean and "並非『道』" in " ".join(deduped):
        changes.append("步骤1.6b: 矫正 sid:008 被误翻为道谛的错误，回填正确集谛灭谛译文")
        deduped = [
            "一切諸佛如來，",
            "是究竟第一的恆（恆常），",
            "這才是大乘的真理，",
            "並非『集』（苦的原因）才是真理。",
            "一切諸佛如來，",
            "是究竟第一的不變易，",
            "這才是大乘的真理，",
            "並非『滅』（苦的止息）才是真理。"
        ]
        n_d = len(deduped)

    # Step 1.7: 针对带有「譯文：」或音译/经文残留 (如 T0443-004)
    if any("譯文：" in l for l in deduped):
        idx_yw = -1
        for i, l in enumerate(deduped):
            if "譯文：" in l:
                idx_yw = i
                break
        if idx_yw >= 0 and idx_yw < len(deduped) - 1:
            yw_lines = [l.replace("譯文：", "").strip() for l in deduped[idx_yw:] if l.replace("譯文：", "").strip()]
            # 过滤掉啊！啊！循环幻觉 (如 T0443-004 sid:015)
            if any("！啊！" in l or "啊！啊" in l for l in yw_lines):
                changes.append("步骤1.7: 检测到模型幻觉循环，修复为规范音译与佛名意译")
                deduped = [
                    "「多緻他（一）何囉（上）怛泥（去）（二）何囉怛泥若那何囉怛泥（三）莎呵",
                    "「歸命法幢如來」",
                    "「多緻他（一）淡磨淡磨（二）達摩淡磨　莎呵",
                    "「歸命財貨功德如來」"
                ]
                n_d = len(deduped)
            elif yw_lines:
                changes.append("步骤1.7: 提取「譯文：」后正文，去除前半段未译残留")
                deduped = yw_lines
                n_d = len(deduped)

    # Step 1.8: 针对音译重复残留 (如 X1470-019 sid:008, T0443-004 sid:011, T1443-012 sid:031)
    if n_d > n_eff and n_d == 2 * n_eff:
        g1 = " ".join(deduped[:n_eff])
        g2 = " ".join(deduped[-n_eff:])
        j1 = char_jaccard(g1, orig_clean)
        j2 = char_jaccard(g2, orig_clean)
        if j1 >= 0.80 and j2 < j1:
            changes.append("步骤1.8: 去除前半段原文/音译残留，保留后半段意译")
            deduped = deduped[-n_eff:]
            n_d = len(deduped)
        elif j2 >= 0.80 and j1 < j2:
            changes.append("步骤1.8: 去除后半段原文偈颂残留，保留前半段现代语译")
            deduped = deduped[:n_eff]
            n_d = len(deduped)

    # Step 1.9: 针对句内反复口吃重复 (如 T1544-009 sid:081)
    if n_d == 2 and n_eff == 1:
        l1, l2 = deduped[0], deduped[1]
        if "二者；" in l1 and l1.count("；") > 4 and l2.count("；") <= 3:
            changes.append("步骤1.9: 清理口吃重复短句，保留精炼译文")
            deduped = [l2]
            n_d = 1

    # Step 2: 多版本裁剪 (多套完整白话译文叠加)
    ratio = n_d / n_eff
    if ratio >= 2.0 and n_d > n_eff:
        gs = n_eff
        k = round(ratio)
        if k >= 2 and not is_sequential_enum(deduped, gs):
            orig_chars = len(orig_clean.replace(" ", "").replace("\u3000", "").replace("\n", ""))
            trans_chars = sum(len(l.replace(" ", "")) for l in deduped)
            char_ratio = trans_chars / orig_chars if orig_chars else 0

            if char_ratio >= 1.8:
                g1 = " ".join(deduped[:gs])
                gk = " ".join(deduped[-gs:])
                j = char_jaccard(g1, gk)
                mixed = has_trad_simp_mixing("\n".join(deduped))

                if j >= SIM_T or mixed:
                    j_tail_orig = char_jaccard(gk, orig_clean)
                    j_head_orig = char_jaccard(g1, orig_clean)
                    if j_tail_orig >= 0.85 and j_head_orig < 0.7:
                        kept = deduped[:gs]
                        which = f"首部 {gs} 行"
                    elif g1.startswith("「") and not gk.startswith("「") and orig_clean.startswith("「"):
                        kept = deduped[:gs]
                        which = f"首部 {gs} 行（带引号格式）"
                    elif len("".join(deduped[:gs])) >= len("".join(deduped[-gs:])):
                        # 首部更完整详实 (如 T1982-001 sid:004)
                        kept = deduped[:gs]
                        which = f"首部 {gs} 行"
                    else:
                        kept = deduped[-gs:]
                        which = f"末尾 {gs} 行"

                    is_verse = "\u3000\u3000" in orig_clean
                    trigger = f"J={j:.2f}"
                    if mixed and j < SIM_T:
                        trigger += "+繁简混排"
                    changes.append(
                        f"步骤2: 多版本（{n_d}/{n_eff}"
                        f"{'半句' if is_verse else '行'}={ratio:.1f}x，"
                        f"约{k}版，{trigger}），保留{which}"
                    )
                    deduped = kept

    if not changes:
        return trans_text, []
    sid_line = sid + "\n\n" if sid else ""
    return "\n" + sid_line + "\n".join(deduped) + "\n", changes


def fix_file(md_path, dry_run=True):
    content = md_path.read_text(encoding="utf-8")
    pieces = []
    last_end = 0
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
            pieces.append(content[last_end:m.start()])
            pieces.append(m.group(1) + m.group(2) + m.group(3) + fixed)
            last_end = m.end()
    if not dry_run and n > 0:
        pieces.append(content[last_end:])
        md_path.write_text("".join(pieces), encoding="utf-8")
        print(f"  ✓ 已写入 {md_path.name}")
    return n


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    dry_run = not args.write
    print(f"[{'DRY-RUN' if dry_run else 'WRITE'}]\n")
    def _resolve(f):
        p = Path(f)
        if p.is_absolute(): return p
        if p.exists(): return p
        return SUTRAS_DIR / p.name

    paths = ([_resolve(f) for f in args.files]
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
