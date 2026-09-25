#!/usr/bin/env python3
"""
按段导出 / 回填一卷的现代语译，供 AI agent 直接翻译时使用。

  # 导出待译段落（含所在章节标题），给翻译者看
  python3 scripts/seg_io.py export T0220-201 [--all]

  # 回填译文，译文文件格式：
  #   @@001
  #   第 1 段译文
  #
  #   @@002
  #   第 2 段译文
  python3 scripts/seg_io.py apply T0220-201 译文文件 --model claude-opus-5.5

apply 会检查：每个待译段都有译文、没有多出的 sid、译文不含 markdown 标题、
译文长度不明显短于原文。全部通过才写回，并把 translation_status 改成
translated、写 ai_translator、更新 updated_at。
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "content" / "sutras-raw"

RE_PAIR = re.compile(
    r"### 原文\n<!-- sid:(\d{3,}) -->\n(.*?)\n### (?:现代语译|現代語譯)\n<!-- sid:\1 -->\n(.*?)(?=\n#{2,3} |\Z)",
    re.DOTALL,
)
RE_HEAD = re.compile(r"^## (.+)$", re.MULTILINE)
RE_HAN = re.compile(r"[㐀-鿿]")


def load(slug):
    path = RAW / f"{slug}.md"
    if not path.exists():
        sys.exit(f"找不到 {path}")
    return path, path.read_text(encoding="utf-8")


def pairs(text):
    """[(sid, 原文, 译文, 所在章节标题, 译文槽的起止位置)]"""
    heads = [(m.start(), m.group(1)) for m in RE_HEAD.finditer(text)]
    out = []
    for m in RE_PAIR.finditer(text):
        head = ""
        for pos, h in heads:
            if pos < m.start():
                head = h
        out.append((m.group(1), m.group(2).strip(), m.group(3).strip(), head, m.span(3)))
    return out


def cmd_export(args):
    _, text = load(args.slug)
    last_head = None
    n = 0
    for sid, orig, trans, head, _ in pairs(text):
        if trans and not args.all:
            continue
        if head != last_head:
            print(f"\n## {head}" if head else "")
            last_head = head
        print(f"\n@@{sid}\n{orig}")
        n += 1
    print(f"\n# 共 {n} 段待译", file=sys.stderr)


def parse_translations(path):
    content = Path(path).read_text(encoding="utf-8")
    chunks = re.split(r"^@@(\d{3,})\s*$", content, flags=re.MULTILINE)
    result = {}
    for i in range(1, len(chunks), 2):
        sid, body = chunks[i], chunks[i + 1].strip()
        if sid in result:
            sys.exit(f"译文文件里 @@{sid} 出现了两次")
        result[sid] = body
    return result


def cmd_apply(args):
    path, text = load(args.slug)
    trans = parse_translations(args.file)
    ps = pairs(text)
    todo = {sid: (orig, cur) for sid, orig, cur, _, _ in ps if args.overwrite or not cur}
    errors = []
    for sid in todo:
        if not trans.get(sid):
            errors.append(f"缺 @@{sid} 的译文")
    for sid in trans:
        if sid not in todo:
            errors.append(f"@@{sid} 不是待译段（不存在或已有译文）")
    for sid, body in trans.items():
        if sid not in todo:
            continue
        if re.search(r"^#{1,6} |<!--|^@@", body, re.MULTILINE):
            errors.append(f"@@{sid} 译文里有 markdown 标题、注释或 @@ 标记")
        o = len(RE_HAN.findall(todo[sid][0]))
        t = len(RE_HAN.findall(body))
        if o >= 20 and t < o * 0.8 and "意譯" not in body:
            errors.append(f"@@{sid} 译文 {t} 字，原文 {o} 字，疑似漏译")
    if errors:
        print("未写回，问题如下：", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        sys.exit(1)

    # 从后往前替换，位置不受影响
    for sid, _, _, _, (s, e) in reversed(ps):
        if sid in todo:
            text = text[:s] + "\n" + trans[sid] + "\n" + text[e:]

    fm_end = text.index("\n---\n", 4)
    fm, rest = text[:fm_end], text[fm_end:]
    fm = re.sub(r"^translation_status:.*$", "translation_status: translated", fm, flags=re.MULTILINE)
    fm = re.sub(r"^updated_at:.*$", f"updated_at: {date.today().isoformat()}", fm, flags=re.MULTILINE)
    if re.search(r"^ai_translator:", fm, re.MULTILINE):
        fm = re.sub(r"^ai_translator:.*$", f"ai_translator: {args.model}", fm, flags=re.MULTILINE)
    else:
        fm = re.sub(r"^(updated_at:.*)$", rf"\1\nai_translator: {args.model}", fm, flags=re.MULTILINE)
    path.write_text(fm + rest, encoding="utf-8")

    left = sum(1 for _, _, cur, _, _ in pairs(fm + rest) if not cur)
    print(f"{args.slug}: 写入 {len(todo)} 段，剩余空段 {left}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("slug")
    e.add_argument("--all", action="store_true", help="连已有译文的段一起导出")
    e.set_defaults(func=cmd_export)
    a = sub.add_parser("apply")
    a.add_argument("slug")
    a.add_argument("file")
    a.add_argument("--model", required=True, help="写入 ai_translator 的模型名")
    a.add_argument("--overwrite", action="store_true", help="覆盖已有译文")
    a.set_defaults(func=cmd_apply)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
