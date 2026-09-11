#!/usr/bin/env python3
"""
把杂阿含等「独立经号」从段落里抬成二级标题。

CBETA 中 `（一八）` 是 <cb:div type="jing"><head>，即一经的开头，
不应留在上一段正文或译文的段落内部。

用法:
  python3 scripts/lift_sutra_numbers.py content/sutras-raw/T0099-001.md
  python3 scripts/lift_sutra_numbers.py content/sutras-raw/T0099-*.md
  python3 scripts/lift_sutra_numbers.py --dry-run content/sutras-raw/T0099-*.md
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

RE_ORIG_HEAD = re.compile(r"^### 原文\s*$")
RE_TRANS_HEAD = re.compile(r"^### (現代語譯|现代语译)\s*$")
RE_H2 = re.compile(r"^## (.+)$")
RE_SID = re.compile(r"^<!-- sid:\d+ -->\s*$")
RE_FRONTMATTER_END = re.compile(r"^---\s*$")
RE_UPDATED = re.compile(r"^(updated_at:\s*).+$", re.MULTILINE)

# 原文经号：整行只有 （一八） / （六〇五） / （一四〇、一四一） / （七五五～七）
RE_CN_NUM = r"[一二三四五六七八九十〇零兩两百千]+"
RE_ORIG_NUM = re.compile(
    r"^（[一二三四五六七八九十〇百千]+(?:[、～][一二三四五六七八九十〇百千]+)*）$"
)
RE_TRANS_MARK_INNER = (
    rf"(?:"
    rf"這是第{RE_CN_NUM}部?經"
    rf"|經文編號[：:]?{RE_CN_NUM}(?:[至～、]{RE_CN_NUM})?"
    rf"|第{RE_CN_NUM}(?:(?:至|～|、|[經经]至){RE_CN_NUM})*部?[經经則则]?"
    rf")"
)
RE_TRANS_NUM = re.compile(
    rf"^（(?:{RE_TRANS_MARK_INNER}|"
    rf"[一二三四五六七八九十〇百千]+(?:[、～][一二三四五六七八九十〇百千]+)*)）$"
)
RE_INLINE_TRANS_NUM = re.compile(rf"（{RE_TRANS_MARK_INNER}）")
RE_TRANS_OPENING = re.compile(
    r"^(我是這樣聽說的|我是这样听说的|這是我親耳聽聞的|这是我亲耳听闻的|"
    r"我是這樣聽佛說的|我是这样听佛说的|我是這樣聽聞的|我是这样听闻的|"
    r"如是我聞)[：:]"
)


def normalize_inline_trans_numbers(text: str) -> str:
    """把夹在句中的译文经号拆成独立行，便于按行切段。"""
    def repl(m: re.Match[str]) -> str:
        return "\n" + m.group(0) + "\n"

    text = RE_INLINE_TRANS_NUM.sub(repl, text)
    text = re.sub(
        r"(?<=。)（([一二三四五六七八九十〇百千]+)）(?=(?:我是|如是我聞|這是我))",
        r"\n（\1）\n",
        text,
    )
    return re.sub(r"\n{3,}", "\n\n", text)


def split_by_sutra_numbers(text: str, num_re: re.Pattern[str]) -> list[dict]:
    """按独立经号行切开。返回 [{'num': None|'（一八）', 'text': str}, ...]。"""
    chunks: list[dict] = [{"num": None, "lines": []}]
    for line in text.split("\n"):
        if num_re.match(line.strip()):
            chunks.append({"num": line.strip(), "lines": []})
        else:
            chunks[-1]["lines"].append(line)
    for chunk in chunks:
        chunk["text"] = "\n".join(chunk["lines"]).strip()
        del chunk["lines"]
    return chunks


def parse_markdown(content: str) -> tuple[str, str, list[dict]]:
    """拆成 frontmatter、一级标题后的前置文本、以及正文块列表。"""
    if not content.startswith("---"):
        raise ValueError("缺少 front matter")
    end = content.find("\n---", 3)
    if end < 0:
        raise ValueError("front matter 未闭合")
    fm = content[: end + 4]
    body = content[end + 4 :].lstrip("\n")

    lines = body.split("\n")
    preamble: list[str] = []
    blocks: list[dict] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if RE_H2.match(line):
            blocks.append({"type": "h2", "text": line})
            i += 1
            continue
        if RE_ORIG_HEAD.match(line):
            orig_head = line
            i += 1
            orig_sid = ""
            if i < len(lines) and RE_SID.match(lines[i]):
                orig_sid = lines[i]
                i += 1
            orig_buf: list[str] = []
            while i < len(lines) and not (
                RE_TRANS_HEAD.match(lines[i])
                or RE_ORIG_HEAD.match(lines[i])
                or RE_H2.match(lines[i])
            ):
                orig_buf.append(lines[i])
                i += 1
            trans_head = ""
            trans_sid = ""
            trans_buf: list[str] = []
            if i < len(lines) and RE_TRANS_HEAD.match(lines[i]):
                trans_head = lines[i]
                i += 1
                if i < len(lines) and RE_SID.match(lines[i]):
                    trans_sid = lines[i]
                    i += 1
                while i < len(lines) and not (
                    RE_ORIG_HEAD.match(lines[i]) or RE_H2.match(lines[i])
                ):
                    trans_buf.append(lines[i])
                    i += 1
            blocks.append(
                {
                    "type": "pair",
                    "orig_head": orig_head,
                    "orig_sid": orig_sid,
                    "orig": "\n".join(orig_buf).strip("\n"),
                    "trans_head": trans_head or "### 現代語譯",
                    "trans_sid": trans_sid,
                    "trans": "\n".join(trans_buf).strip("\n"),
                }
            )
            continue
        if not blocks:
            preamble.append(line)
            i += 1
            continue
        # 正文开始后的游离空行忽略
        i += 1

    while preamble and preamble[-1] == "":
        preamble.pop()
    return fm, "\n".join(preamble).strip("\n"), blocks


def _split_trans_by_openings(trans: str, orig_chunks: list[dict]) -> list[dict] | None:
    """译文漏写经号时，按「我是这样听说的」与原文「如是我聞」对齐。"""
    trans_lines = trans.split("\n")
    opening_idxs = [i for i, ln in enumerate(trans_lines) if RE_TRANS_OPENING.match(ln.strip())]
    orig_openings = [
        i for i, c in enumerate(orig_chunks)
        if c["num"] and c["text"].lstrip().startswith("如是我聞")
    ]
    if not orig_openings or len(opening_idxs) != len(orig_openings):
        return None
    first_empty = orig_chunks[0]["num"] is None and not orig_chunks[0]["text"].strip()
    expected_prefix = 0 if first_empty else 1
    if orig_openings[0] != expected_prefix:
        # 原文以经号开头、译文整段都是「我是这样听说的」
        if first_empty and orig_openings == [1] and opening_idxs == [0]:
            aligned = [{"num": None, "text": ""}]
            for i, oc in enumerate(orig_chunks[1:]):
                aligned.append(
                    {
                        "num": oc["num"],
                        "text": trans if i == 0 else "",
                    }
                )
            return aligned
        return None

    chunks = [{"num": orig_chunks[0]["num"], "text": ""}]
    cursor = 0
    for orig_i, line_i in zip(orig_openings, opening_idxs):
        prefix = "\n".join(trans_lines[cursor:line_i]).strip()
        if orig_i == 0:
            chunks[0]["text"] = prefix
        else:
            chunks[-1]["text"] = prefix
            chunks.append({"num": orig_chunks[orig_i]["num"], "text": ""})
        cursor = line_i
    chunks[-1]["text"] = "\n".join(trans_lines[cursor:]).strip()
    while len(chunks) < len(orig_chunks):
        chunks.append({"num": orig_chunks[len(chunks)]["num"], "text": ""})
    return chunks[: len(orig_chunks)]


def lift_pair(orig: str, trans: str) -> tuple[list[dict], str | None]:
    """
    把一对原文/译文按经号切开。
    返回 (emits, warning)。
    emit 为 {'heading': str|None, 'orig': str, 'trans': str}；
    heading 非空时表示先写 ## 再写 pair（pair 可空）。
    """
    orig_chunks = split_by_sutra_numbers(orig.strip("\n"), RE_ORIG_NUM)
    trans_chunks = split_by_sutra_numbers(
        normalize_inline_trans_numbers(trans.strip("\n")), RE_TRANS_NUM
    )

    if len(orig_chunks) == 1 and orig_chunks[0]["num"] is None:
        return ([{"heading": None, "orig": orig.strip("\n"), "trans": trans.strip("\n")}], None)

    warning = None
    if len(orig_chunks) != len(trans_chunks):
        aligned = _split_trans_by_openings(trans.strip("\n"), orig_chunks)
        if aligned:
            trans_chunks = aligned
        else:
            warning = (
                f"原文 {sum(1 for c in orig_chunks if c['num'])} 个经号，"
                f"译文 {sum(1 for c in trans_chunks if c['num'])} 个经号"
            )
            while len(trans_chunks) < len(orig_chunks):
                trans_chunks.append({"num": orig_chunks[len(trans_chunks)]["num"], "text": ""})
            if len(trans_chunks) > len(orig_chunks):
                extra = "\n".join(
                    c["text"] for c in trans_chunks[len(orig_chunks) :] if c["text"]
                )
                if extra:
                    if trans_chunks[len(orig_chunks) - 1]["text"]:
                        trans_chunks[len(orig_chunks) - 1]["text"] += "\n" + extra
                    else:
                        trans_chunks[len(orig_chunks) - 1]["text"] = extra
                trans_chunks = trans_chunks[: len(orig_chunks)]

    emits: list[dict] = []
    for oc, tc in zip(orig_chunks, trans_chunks):
        heading = oc["num"]
        o_text = oc["text"]
        t_text = tc["text"]
        if heading is None:
            if o_text.strip() or t_text.strip():
                emits.append({"heading": None, "orig": o_text, "trans": t_text})
            continue
        emits.append({"heading": heading, "orig": o_text, "trans": t_text})
    return emits, warning


def rebuild(fm: str, preamble: str, blocks: list[dict], today: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    out: list[str] = []
    fm = RE_UPDATED.sub(rf"\g<1>{today}", fm, count=1)
    out.append(fm.rstrip("\n"))
    out.append("")
    if preamble.strip():
        out.append(preamble.rstrip("\n"))
        out.append("")

    sid = 0

    def emit_pair(orig: str, trans: str, trans_head: str) -> None:
        nonlocal sid
        sid += 1
        sid_str = f"{sid:03d}"
        out.append("### 原文")
        out.append(f"<!-- sid:{sid_str} -->")
        out.append("")
        out.append(orig.strip("\n"))
        out.append("")
        out.append(trans_head)
        out.append(f"<!-- sid:{sid_str} -->")
        out.append("")
        out.append(trans.strip("\n"))
        out.append("")

    for block in blocks:
        if block["type"] == "h2":
            out.append(block["text"].rstrip())
            out.append("")
            continue
        emits, warning = lift_pair(block["orig"], block["trans"])
        if warning:
            warnings.append(warning)
        trans_head = block["trans_head"]
        for emit in emits:
            if emit["heading"]:
                out.append(f"## {emit['heading']}")
                out.append("")
            if emit["orig"].strip() or emit["trans"].strip():
                emit_pair(emit["orig"], emit["trans"], trans_head)

    while out and out[-1] == "":
        out.pop()
    out.append("")
    return "\n".join(out), warnings


def process_file(path: Path, dry_run: bool, today: str) -> dict:
    original = path.read_text(encoding="utf-8")
    fm, preamble, blocks = parse_markdown(original)
    new_text, warnings = rebuild(fm, preamble, blocks, today)
    changed = new_text != original
    headings = len(re.findall(r"^## （.+）$", new_text, re.M))
    if changed and not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return {
        "path": str(path),
        "changed": changed,
        "headings": headings,
        "warnings": warnings,
        "pairs": len(re.findall(r"^### 原文\s*$", new_text, re.M)),
    }


def _self_check() -> None:
    sample_orig = "心得解脫。\n（一八）\n如是我聞：\n一時，佛住舍衛國祇樹給孤獨園。"
    sample_trans = "内心获得了解脱。\n（第十八經）\n我是这样听说的：\n有一个时期，佛陀住在舍卫国的祇树给孤独园。"
    emits, warning = lift_pair(sample_orig, sample_trans)
    assert warning is None, warning
    assert emits[0]["heading"] is None
    assert "（一八）" not in emits[0]["orig"]
    assert "如是我聞" not in emits[0]["orig"]
    assert emits[1]["heading"] == "（一八）"
    assert emits[1]["orig"].startswith("如是我聞")
    assert "（第十八經）" not in emits[1]["trans"]
    assert emits[1]["trans"].startswith("我是这样听说的")

    start_orig = "（八）\n如是我聞：\n一時，佛住舍衛國祇樹給孤獨園。"
    start_trans = "（八）\n我是这样听说的：\n有一个时期，佛陀住在舍卫国的祇树给孤独园。"
    emits, warning = lift_pair(start_orig, start_trans)
    assert warning is None
    assert emits[0]["heading"] == "（八）"
    assert not emits[0]["orig"].startswith("（八）")

    multi_orig = "成阿羅漢。\n（二〇）\n染經亦如是說。\n（二一）\n如是我聞："
    multi_trans = "成为了阿罗汉。\n（第二十經）\n关于染着的经也是像这样说的。\n（第二十一經）\n我是这样听说的："
    emits, warning = lift_pair(multi_orig, multi_trans)
    assert warning is None
    assert [e["heading"] for e in emits] == [None, "（二〇）", "（二一）"]
    assert emits[1]["orig"] == "染經亦如是說。"
    assert emits[2]["orig"].startswith("如是我聞")

    end_orig = "作禮而去。\n（三一）"
    end_trans = "行礼后离去。\n（第三十一經）"
    emits, warning = lift_pair(end_orig, end_trans)
    assert warning is None
    assert emits[0]["orig"] == "作禮而去。"
    assert emits[1]["heading"] == "（三一）"
    assert emits[1]["orig"] == ""

    range_orig = "歡喜奉行。\n（七五五～七）\n如上三經。\n（七五八）\n如是我聞："
    range_trans = "欢喜奉行。\n（經文編號七五五至七五七）\n以上三部经。\n（經文編號七五八）\n我是这样听说的："
    emits, warning = lift_pair(range_orig, range_trans)
    assert warning is None, warning
    assert [e["heading"] for e in emits] == [None, "（七五五～七）", "（七五八）"]

    combo_orig = "（一四〇、一四一）\n如是我聞："
    combo_trans = "（一四〇、一四一）\n我是这样听说的："
    emits, warning = lift_pair(combo_orig, combo_trans)
    assert warning is None
    assert emits[0]["heading"] == "（一四〇、一四一）"

    inline_orig = "歡喜奉行。\n（四六五）\n如是我聞：\n一時，佛住王舍城。"
    inline_trans = "欢喜地遵照实行。（四六五）我是这样听说的：有一个时期，佛陀住在王舍城。"
    emits, warning = lift_pair(inline_orig, inline_trans)
    assert warning is None, warning
    assert emits[1]["heading"] == "（四六五）"
    assert "如是我聞" not in emits[0]["orig"]

    omitted_orig = "（一〇三）\n如是我聞：\n一時，有眾多上座比丘。"
    omitted_trans = "我是這樣聽說的：\n有一個時期，許多上座比丘。"
    emits, warning = lift_pair(omitted_orig, omitted_trans)
    assert warning is None, warning
    assert emits[0]["heading"] == "（一〇三）"
    assert emits[0]["trans"].startswith("我是這樣聽說的")

    this_is_orig = "歡喜奉行。\n（五一一）\n如是我聞："
    this_is_trans = "歡喜地信受奉行。\n（這是第五百一十一部經）\n我是這樣聽說的："
    emits, warning = lift_pair(this_is_orig, this_is_trans)
    assert warning is None, warning
    assert emits[1]["heading"] == "（五一一）"
    assert "這是第五百一十一部經" not in emits[1]["trans"]

    verse_trans = "（五）蘊與（六）根二者相互關聯（二陰共相關）"
    verse_orig = "陰、根、陰即受　　二陰共相關"
    emits, warning = lift_pair(verse_orig, verse_trans)
    assert warning is None
    assert len(emits) == 1
    assert "（五）蘊與（六）根" in emits[0]["trans"]
    print("self-check ok")


def main() -> int:
    parser = argparse.ArgumentParser(description="把独立经号抬成 ## 标题")
    parser.add_argument("files", nargs="*", help="要处理的 md 文件")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        _self_check()
        if not args.files:
            return 0

    if not args.files:
        parser.error("请提供 md 文件路径")

    today = date.today().isoformat()
    any_warn = False
    for raw in args.files:
        path = Path(raw)
        info = process_file(path, args.dry_run, today)
        flag = "DRY" if args.dry_run and info["changed"] else ("OK" if info["changed"] else "—")
        print(
            f"{flag:4} {path.name:14} headings={info['headings']:4} pairs={info['pairs']:4}"
            + (f"  WARN {'; '.join(info['warnings'])}" if info["warnings"] else "")
        )
        if info["warnings"]:
            any_warn = True
    return 1 if any_warn else 0


if __name__ == "__main__":
    sys.exit(main())
