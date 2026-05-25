#!/usr/bin/env python3
"""
fetch_cbeta.py — 从 CBETA 拉取经文原文（TEI XML），按卷切分为纯文本

用法:
  python3 scripts/fetch_cbeta.py T0001               # 按 cbeta_id 拉
  python3 scripts/fetch_cbeta.py 長阿含經            # 按经名拉
  python3 scripts/fetch_cbeta.py 长阿含经            # 简体也行
  python3 scripts/fetch_cbeta.py T0001 --force       # 覆盖已下载文件
  python3 scripts/fetch_cbeta.py T0001 --xml-only    # 只下载 XML 不切卷

产物:
  sources/cbeta/T01n0001.xml             # 完整 TEI XML 底本
  content/cbeta-raw/T/T0001/T0001_001.txt …  # 按卷拆分的 bookcase 风格 TXT

数据源：
  https://raw.githubusercontent.com/cbeta-org/xml-p5/master/T/T01/T01n0001.xml
"""

import os
import re
import sys
import argparse
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TSV_PATH     = PROJECT_ROOT / "target_sutra_list.tsv"
XML_DIR      = PROJECT_ROOT / "sources" / "cbeta"
TXT_DIR      = PROJECT_ROOT / "content" / "cbeta-raw"

XML_BASE = "https://raw.githubusercontent.com/cbeta-org/xml-p5/master"

_CN_DIGITS = "〇一二三四五六七八九"

def _cn_num(n: int) -> str:
    """整数 → 简单中文数字（1~99 即可，超过 99 退化为阿拉伯数字）。"""
    if n < 10:
        return _CN_DIGITS[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + _CN_DIGITS[n - 10]
    if n < 100:
        tens, units = divmod(n, 10)
        return _CN_DIGITS[tens] + "十" + (_CN_DIGITS[units] if units else "")
    return str(n)


# ── TSV 查询 ──────────────────────────────────────────────────────────────────

def load_tsv():
    rows = []
    with open(TSV_PATH, "r", encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) == len(header):
                rows.append(dict(zip(header, cols)))
    return rows


def find_entry(key: str):
    """按 cbeta_id（T0001）或经名（含简繁）匹配。"""
    rows = load_tsv()

    # 1) cbeta_id 精确匹配（去掉 collection 字母 + sutra_no）
    norm = key.strip()
    for r in rows:
        if r["collection"] + r["sutra_no"] == norm:
            return r
        if r.get("cbeta_id") == norm:
            return r

    # 2) 按 title 模糊匹配（简繁都试）
    try:
        from opencc import OpenCC
        t2s = OpenCC("t2s").convert
        s2t = OpenCC("s2t").convert
    except ImportError:
        t2s = s2t = lambda x: x

    candidates = {key, t2s(key), s2t(key)}
    for r in rows:
        t = r.get("title", "")
        if t in candidates or any(c == t for c in candidates):
            return r
    # 包含匹配（防止用户漏字）
    for r in rows:
        t = r.get("title", "")
        if t and any(c and (c in t or t in c) for c in candidates):
            return r
    return None


# ── 下载 XML ──────────────────────────────────────────────────────────────────

def xml_url(entry: dict) -> str:
    coll = entry["collection"]
    vol  = entry["volume"]
    no   = entry["sutra_no"]
    return f"{XML_BASE}/{coll}/{coll}{vol}/{coll}{vol}n{no}.xml"


def xml_path(entry: dict) -> Path:
    return XML_DIR / f"{entry['collection']}{entry['volume']}n{entry['sutra_no']}.xml"


def download_xml(entry: dict, force: bool = False) -> Path:
    target = xml_path(entry)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        print(f"  XML 已存在: {target.relative_to(PROJECT_ROOT)}")
        return target

    url = xml_url(entry)
    print(f"  下载 {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "sutratoday-fetch/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"下载失败 HTTP {e.code}: {url}")

    target.write_bytes(data)
    print(f"  → {target.relative_to(PROJECT_ROOT)} ({len(data)} 字节)")
    return target


# ── XML → TXT ─────────────────────────────────────────────────────────────────

RE_CB_JUAN_OPEN = re.compile(r'<cb:juan\s+n="(\d+)"\s+fun="open"[^>]*>', re.DOTALL)
RE_BODY         = re.compile(r'<body[^>]*>(.*?)</body>', re.DOTALL)
RE_DOC_NUMBER   = re.compile(r'<cb:docNumber>(.*?)</cb:docNumber>', re.DOTALL)
RE_JHEAD        = re.compile(r'<cb:jhead>(.*?)</cb:jhead>', re.DOTALL)
RE_BYLINE_TR    = re.compile(r'<byline[^>]*cb:type="Translator"[^>]*>(.*?)</byline>', re.DOTALL)


def _strip_tags(s: str) -> str:
    """剥去所有 XML 标签，只留文字内容。"""
    return re.sub(r'<[^>]+>', '', s)


def _normalize_text(s: str) -> str:
    """处理 XML 转义、空白、合并行内换行。"""
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    s = s.replace("&apos;", "'").replace("&quot;", '"')
    # 去除每行首尾空白后重新拼接
    lines = [ln.strip() for ln in s.split("\n")]
    return "\n".join(lines)


def _xml_to_plain(xml_chunk: str) -> str:
    """
    把一段 TEI XML 转成 bookcase 风格纯文本：
    - <lb .../> → 换行
    - <pb .../> → 换行（页边界）
    - <caesura/> → 全角空格 `　`
    - <l>...</l> → 该行末尾补 \n
    - </p> → 段末空行
    - <lg> 偈颂块前后加空行
    - 其他标签剥光
    """
    s = xml_chunk

    # cb:mulu 是 CBETA 内部目录树，对正文无用，整块剥掉
    s = re.sub(r'<cb:mulu[^>]*>.*?</cb:mulu>', '', s, flags=re.DOTALL)
    s = re.sub(r'<cb:mulu[^/]*/>', '', s)
    # <note> 是 CBETA 给读者的小注（多为校勘、读音），与正文混排会污染，剥掉
    s = re.sub(r'<note[^>]*>.*?</note>', '', s, flags=re.DOTALL)

    # 段落/标题/标签块边界 → 空行（保证不同结构块之间一定分段）
    for closing in ('p', 'lg', 'head', 'byline', 'title',
                    'cb:jhead', 'cb:juan', 'cb:div'):
        s = re.sub(rf'</{re.escape(closing)}>', '\n\n', s)
    s = re.sub(r'<lg[^>]*>', '\n', s)

    # 偈颂单行结束 → 换行（在标签处理前先标记）
    s = re.sub(r'</l>', '\n', s)
    s = re.sub(r'<l[^>]*>', '　　', s)   # 偈颂行首加全角空格对齐

    # caesura 全角空格
    s = re.sub(r'<caesura\s*/>', '　　', s)

    # 行/页边界 → 换行（保留 CBETA 原版式参考）
    s = re.sub(r'<lb\s+[^>]*/>', '\n', s)
    s = re.sub(r'<pb\s+[^>]*/>', '\n', s)

    # 剥掉其余标签
    s = _strip_tags(s)
    s = _normalize_text(s)

    # 合并被 <lb> 拆开的同一句：行尾不是中文标点就把换行接回去
    out_lines = []
    buf = ""
    PUNC_END = "。！？；：、，」』）】〕》〉…—"
    for ln in s.split("\n"):
        ln = ln.strip()
        if not ln:
            if buf:
                out_lines.append(buf)
                buf = ""
            out_lines.append("")
            continue
        # 偈颂行（以全角空格开头）独立成行
        if ln.startswith("　　"):
            if buf:
                out_lines.append(buf)
                buf = ""
            out_lines.append(ln)
            continue
        if buf and buf[-1] in PUNC_END:
            out_lines.append(buf)
            buf = ln
        elif buf:
            buf += ln
        else:
            buf = ln
    if buf:
        out_lines.append(buf)

    # 压缩多余空行
    result = "\n".join(out_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


def split_juans(body_xml: str):
    """
    按 <cb:juan n="NNN" fun="open"> 切分。
    返回 [(juan_no:int, juan_xml:str, preface_xml:str_or_None), ...]
    preface_xml 仅在第一卷出现（第一个 cb:juan 标签之前的内容）。
    """
    matches = list(RE_CB_JUAN_OPEN.finditer(body_xml))
    if not matches:
        # 没有 cb:juan 标签 → 整篇视为一卷
        return [(1, body_xml, None)]

    juans = []
    preface = body_xml[: matches[0].start()].strip() or None
    for i, m in enumerate(matches):
        no = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body_xml)
        juans.append((no, body_xml[start:end], preface if i == 0 else None))
    return juans


def build_juan_txt(entry: dict, juan_no: int, juan_xml: str, preface_xml: str) -> str:
    """生成一卷 bookcase 风格 TXT：
       # 头注释 / No.X / 序文 / 卷标题 / 译者 / 正文
    """
    cbeta_id = f"{entry['collection']}{entry['volume']}n{entry['sutra_no']}"
    title    = entry["title"]
    tsv_translator = entry.get("translator", "")

    lines = []
    lines.append(f"# 来源: CBETA xml-p5 {cbeta_id} 卷 {juan_no:03d}")
    lines.append(f"# 经名: {title}")
    lines.append("")

    # No.X（取 XML 第一个 cb:docNumber，若无则按 sutra_no 生成）
    doc_match = RE_DOC_NUMBER.search(juan_xml) or (
        RE_DOC_NUMBER.search(preface_xml) if preface_xml else None
    )
    if doc_match:
        lines.append(_strip_tags(doc_match.group(1)).strip())
    else:
        lines.append(f"No. {int(entry['sutra_no'])}")
    lines.append("")

    # 序文（仅第一卷）：剥掉 docNumber 后再转纯文本，避免与上面的 No.X 行重复
    if preface_xml:
        preface_clean = RE_DOC_NUMBER.sub('', preface_xml)
        preface_txt   = _xml_to_plain(preface_clean)
        if preface_txt:
            lines.append(preface_txt)
            lines.append("")

    # 卷标题：从 <cb:jhead> 提取，否则用 title + 卷N。
    # 必须含 "卷第X"，否则 cbeta_txt_to_md.py 的 RE_VOLUME_TITLE 识别不到。
    CN_NUMS = "〇一二三四五六七八九十百千廿卅"
    jhead = RE_JHEAD.search(juan_xml)
    if jhead:
        jh_raw = jhead.group(1)
        # 先剥 note（小注 + 该卷国家数等），再剥所有标签
        jh_raw = re.sub(r'<note[^>]*>.*?</note>', '', jh_raw, flags=re.DOTALL)
        jh = re.sub(r'\s+', '', _strip_tags(jh_raw))
    else:
        jh = title
    if not re.search(rf'卷第?[{CN_NUMS}]+', jh):
        # 单卷经 / jhead 不含卷号 → 补上
        jh = f"{jh}卷第{_cn_num(juan_no)}"
    lines.append(jh)
    lines.append("")

    # 译者：优先 byline cb:type=Translator，否则用 TSV。
    # byline 常被 <lb/> 拆成多行，要合并成单行，否则 cbeta_txt_to_md.py 的
    # RE_TRANSLATOR (^.{3,25}譯$) 识别不到。
    byline = RE_BYLINE_TR.search(juan_xml)
    if byline:
        tr = _strip_tags(byline.group(1))
        tr = re.sub(r'\s+', '', tr).strip()
    else:
        tr = tsv_translator.replace(" ", "") or "失譯"
    if not tr.endswith("譯"):
        tr += "譯"
    lines.append(tr)
    lines.append("")

    # 正文：把卷头 + 译者 byline 之外的内容转纯文本
    # 简单做法：把 <cb:juan>...</cb:juan> 标签和 jhead/byline 这几个 XML 块从 juan_xml 中去掉，
    # 剩下的扔给 _xml_to_plain
    body = juan_xml
    body = RE_CB_JUAN_OPEN.sub('', body)
    body = re.sub(r'<cb:juan\s+n="\d+"\s+fun="close"\s*/>', '', body)
    body = re.sub(r'<cb:jhead>.*?</cb:jhead>',  '', body, flags=re.DOTALL)
    # 卷正文里的所有 byline（Translator/author/Scribe）已在头部处理过，全剥
    body = re.sub(r'<byline[^>]*>.*?</byline>', '', body, flags=re.DOTALL)
    body = RE_DOC_NUMBER.sub('', body)

    body_txt = _xml_to_plain(body)
    lines.append(body_txt)
    lines.append("")

    return "\n".join(lines)


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="拉取 CBETA TEI XML 并切分为 bookcase 风格 TXT")
    parser.add_argument("key", help="cbeta_id（如 T0001）或经名（如 長阿含經/长阿含经）")
    parser.add_argument("--force", action="store_true", help="覆盖已下载/已生成的文件")
    parser.add_argument("--xml-only", action="store_true", help="只下载 XML，不切分 TXT")
    args = parser.parse_args()

    entry = find_entry(args.key)
    if not entry:
        print(f"错误：在 {TSV_PATH.name} 中找不到 {args.key}")
        sys.exit(1)

    sutra_id   = entry["collection"] + entry["sutra_no"]   # 如 T0001
    juan_total = int(entry["juan_count"])
    print(f"匹配到：{sutra_id} {entry['title']}（共 {juan_total} 卷，{entry['category']}）")

    # 1. 下载 XML
    xml_file = download_xml(entry, force=args.force)
    if args.xml_only:
        return

    # 2. 解析切卷
    xml_text = xml_file.read_text(encoding="utf-8")
    body_match = RE_BODY.search(xml_text)
    if not body_match:
        raise SystemExit("XML 中找不到 <body> 标签")
    juans = split_juans(body_match.group(1))

    if len(juans) != juan_total:
        print(f"  注意：XML 切出 {len(juans)} 卷，TSV 记 {juan_total} 卷。以实际为准。")

    # 3. 写出每卷 TXT
    out_dir = TXT_DIR / entry["collection"] / sutra_id
    out_dir.mkdir(parents=True, exist_ok=True)

    written = skipped = 0
    for juan_no, juan_xml, preface_xml in juans:
        out_path = out_dir / f"{sutra_id}_{juan_no:03d}.txt"
        if out_path.exists() and not args.force:
            skipped += 1
            continue
        txt = build_juan_txt(entry, juan_no, juan_xml, preface_xml)
        out_path.write_text(txt, encoding="utf-8")
        written += 1

    print(f"写入 {written} 卷，跳过 {skipped} 卷 → {out_dir.relative_to(PROJECT_ROOT)}/")
    print(f"下一步：python3 scripts/cbeta_txt_to_md.py {sutra_id}")


if __name__ == "__main__":
    main()
