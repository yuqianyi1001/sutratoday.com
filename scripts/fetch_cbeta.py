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
RE_MILESTONE_JUAN = re.compile(r'<milestone\b[^>]*\bunit="juan"[^>]*/>')
RE_BODY         = re.compile(r'<body[^>]*>(.*?)</body>', re.DOTALL)
RE_DOC_NUMBER   = re.compile(r'<cb:docNumber>(.*?)</cb:docNumber>', re.DOTALL)
RE_JHEAD        = re.compile(r'<cb:jhead>(.*?)</cb:jhead>', re.DOTALL)
RE_BYLINE_TR    = re.compile(
    r'<byline[^>]*cb:type="(?:Translator|author|Author)"[^>]*>(.*?)</byline>',
    re.DOTALL,
)
_AUTHORSHIP_END = ("譯", "撰", "述", "集", "編", "錄", "註", "注", "說", "製", "記", "箋")

# 僧传等史传：cb:mulu 有人名、后面直接接 <p>、没有 <head> 时，补一条标题。
# 目录内容不得跨过 </cb:mulu>，否则会把「1 譯經」一直吃到第一位传主的 </cb:mulu><p>。
RE_MULU_THEN_P = re.compile(
    r'(<cb:mulu[^>]*>)((?:(?!</cb:mulu>).)*?)(</cb:mulu>)'
    r'((?:\s|<lb[^>]*/?>)*)'
    r'(<p\b)',
    re.DOTALL,
)
_MULU_SKIP_NAMES = {
    "", "上", "中", "下", "一", "二", "三", "四", "五",
    "譯經", "義解", "神異", "習禪", "明律", "亡身",
    "誦經", "興福", "經師", "唱導", "序錄", "序",
}
RE_GAIJI_MAP = re.compile(
    r'<char xml:id="(CB\d+)">.*?'
    r'<mapping[^>]*type="(?:normal_unicode|unicode)"[^>]*>U\+([0-9A-Fa-f]+)</mapping>',
    re.DOTALL,
)
RE_G_TAG = re.compile(r'<g[^>]*ref="#(CB\d+)"[^>]*>(.*?)</g>', re.DOTALL)

# 高僧傳各卷科名（XML 有的卷只有 mulu「二」「三」而无 <head>）
T2059_JUAN_CATEGORY = {
    1: "譯經上",
    2: "譯經中",
    3: "譯經下",
    4: "義解一",
    5: "義解二",
    6: "義解三",
    7: "義解四",
    8: "義解五",
    9: "神異上",
    10: "神異下",
    11: "習禪",
    12: "亡身",
    13: "興福",
    14: "序錄",
}


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


def _load_gaiji_map(xml_text: str) -> dict:
    """从 teiHeader 的 charDecl 取出 CBETA 缺字 → Unicode。"""
    mapping = {}
    for m in RE_GAIJI_MAP.finditer(xml_text):
        mapping[m.group(1)] = chr(int(m.group(2), 16))
    return mapping


def _replace_gaiji(s: str, gaiji_map: dict) -> str:
    def repl(m):
        return gaiji_map.get(m.group(1), m.group(2))
    return RE_G_TAG.sub(repl, s)


def _inject_heads_from_mulu(xml_chunk: str) -> str:
    """僧传常见：传主只有 <cb:mulu>1 攝摩騰</cb:mulu> 后直接 <p>，没有 <head>。补上。"""
    def repl(m):
        raw = re.sub(r'\s+', '', _strip_tags(m.group(2))).strip()
        # mulu 形如 "1 攝摩騰" / "8 釋僧肇"
        name = re.sub(r'^\d+', '', raw).strip()
        if name in _MULU_SKIP_NAMES or not (2 <= len(name) <= 20):
            return m.group(0)
        # 保留原编号，便于 md 转成「一、攝摩騰」
        numbered = re.sub(r'^(\d+)(?=\S)', r'\1 ', raw)
        return (
            f"{m.group(1)}{m.group(2)}{m.group(3)}"
            f"{m.group(4)}<head>{numbered}</head>\n{m.group(5)}"
        )
    return RE_MULU_THEN_P.sub(repl, xml_chunk)


def _xml_to_plain(xml_chunk: str, gaiji_map: dict | None = None) -> str:
    """
    把一段 TEI XML 转成 bookcase 风格纯文本：
    - <lb .../> → 换行
    - <pb .../> → 删除（分页不是段界，避免把一句从中切断）
    - <caesura/> → 全角空格 `　`
    - <l>...</l> → 该行末尾补 \n
    - </p> → 段末空行
    - <lg> 偈颂块前后加空行
    - 其他标签剥光
    """
    s = xml_chunk
    if gaiji_map:
        s = _replace_gaiji(s, gaiji_map)
    s = _inject_heads_from_mulu(s)
    # 悉昙字是 CBETA 私用区字形，markdown 里无法显示；咒语保留对照的汉字音译
    s = re.sub(r'<cb:t xml:lang="sa-Sidd"[^>]*>.*?</cb:t>', '', s, flags=re.DOTALL)

    # cb:mulu 是 CBETA 内部目录树，对正文无用，整块剥掉
    s = re.sub(r'<cb:mulu[^>]*>.*?</cb:mulu>', '', s, flags=re.DOTALL)
    s = re.sub(r'<cb:mulu[^/]*/>', '', s)
    # 行内小注（人数、附见人名）保留为括号；校勘注剥掉
    s = re.sub(
        r'<note[^>]*place="inline"[^>]*>(.*?)</note>',
        lambda m: "（" + _strip_tags(m.group(1)) + "）",
        s,
        flags=re.DOTALL,
    )
    s = re.sub(r'<note[^>]*>.*?</note>', '', s, flags=re.DOTALL)

    # 段落/标题/标签块边界 → 空行（保证不同结构块之间一定分段）
    for closing in ('p', 'lg', 'head', 'byline', 'title',
                    'cb:jhead', 'cb:juan', 'cb:div', 'list'):
        s = re.sub(rf'</{re.escape(closing)}>', '\n\n', s)
    # <head> 是块级标题，前面也要断开（咒文 <p> 后紧接咒名 <head> 时不在同一行）
    s = re.sub(r'<head\b', '\n\n<head', s)
    s = re.sub(r'</item>', '、', s)
    s = re.sub(r'<lg[^>]*>', '\n', s)

    # 偈颂单行结束 → 换行（在标签处理前先标记）
    s = re.sub(r'</l>', '\n', s)
    s = re.sub(r'<l[^>]*>', '　　', s)   # 偈颂行首加全角空格对齐

    # caesura 全角空格
    s = re.sub(r'<caesura\s*/>', '　　', s)

    # 行界换行；分页不是段界，去掉以免「而奉戒 / 精峻」被空行切开
    s = re.sub(r'<lb\s+[^>]*/>', '\n', s)
    s = re.sub(r'<pb\s+[^>]*/>', '', s)

    # 剥掉其余标签
    s = _strip_tags(s)
    s = _normalize_text(s)

    # 合并被 <lb> 拆开的同一句：行尾不是中文标点就把换行接回去
    out_lines = []
    buf = ""
    PUNC_END = "。！？；：、，」』）】〕》〉…—"
    SENTENCE_END = "。！？；」』"

    def _is_complete_catalog_item(text: str) -> bool:
        """高僧传目录人名行虽不以句号收尾，仍是完整条目，不可与下一条黏在一起。"""
        if not text or "。" in text:
            return False
        if text[0] not in "漢魏晉宋齊梁秦":
            return False
        return len(text) >= 6

    def _is_heading_line(text: str) -> bool:
        """传主、篇名、游记篇题：不以句号收尾，但不能跟下一段黏在一起。"""
        if not text or any(ch in text for ch in "。！？"):
            return False
        if len(text) > 40:
            return False
        if text in ("序", "并序", "序文"):
            return True
        if text.endswith("序") and 2 <= len(text) <= 20:
            return True
        if re.match(r"^\d+\s+\S{2,20}$", text):
            return True
        if re.search(
            r"(法師|禪師|律師|論師|尊者|和尚|尼傳[一二三四五六七八九十]*|"
            r"篇第[一二三四五六七八九十百]+.*)$",
            text,
        ):
            return True
        if re.match(r"^[一二三四五六七八九十百]+[\u4e00-\u9fff]{2,8}$", text) and len(text) <= 14:
            return True
        if re.search(r"(傳考|記逸文|銘并序|行程|傳|記|考|碑)$", text) and 4 <= len(text) <= 40:
            return True
        if re.match(r"^（[一二三四五六七八九十]+）.+", text):
            return True
        # 大般若经：初分難信解品第三十四之二十 / 第九能斷金剛分 / 大般若經第六會施波羅蜜多分
        if re.search(r"品第[一二三四五六七八九十百]+(之[一二三四五六七八九十百]+)?$", text):
            return True
        if re.match(r"^第[一二三四五六七八九十百]+.{2,12}分(之[一二三四五六七八九十百]+)?$", text):
            return True
        if re.match(r"^大般若.{0,12}第[一二三四五六七八九十百]+會.{0,14}$", text):
            return True
        # 咒名：般若佛姆心呪
        if re.fullmatch(r"般若佛姆.{0,2}心[呪咒]", text):
            return True
        # 会序作者：沙門玄則撰 / 西明寺沙門玄則製
        if re.match(r"^.{0,4}沙門.{1,6}[撰製]$", text):
            return True
        if text.endswith("師") and 4 <= len(text) <= 16:
            return True
        return False

    for ln in s.split("\n"):
        ln = ln.strip()
        if not ln:
            # 空行而上一句未结束：多半是分页残留，不能当成段界
            if buf and buf[-1] not in SENTENCE_END and not _is_complete_catalog_item(buf) and not _is_heading_line(buf):
                continue
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
        # 咒名（<head>）前面是没有标点的咒文，要另起一段
        if buf and re.fullmatch(r"般若佛姆.{0,2}心[呪咒]", ln):
            out_lines.append(buf)
            out_lines.append("")
            buf = ln
            continue
        if buf and (buf[-1] in PUNC_END or _is_heading_line(buf)):
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
    # 有的 XML 开卷标签写作 fun="open" n="1"（属性顺序不同），或卷号带子卷后缀
    # （n="001a"），上面的正则切不出来。这时按每卷开头的 <milestone unit="juan"> 切分。
    milestones = list(RE_MILESTONE_JUAN.finditer(body_xml))
    if len(milestones) > len(matches):
        juans = []
        preface = body_xml[: milestones[0].start()].strip() or None
        for i, m in enumerate(milestones):
            no = int(re.search(r'\bn="(\d+)"', m.group(0)).group(1))
            end = milestones[i + 1].start() if i + 1 < len(milestones) else len(body_xml)
            juans.append((no, body_xml[m.start():end], preface if i == 0 else None))
        return juans
    if not matches:
        # 没有 cb:juan 标签 → 整篇视为一卷
        return [(1, body_xml, None)]

    juans = []
    preface = body_xml[: matches[0].start()].strip() or None
    # 大般若经 T05 卷一只有收卷标签、没有开卷标签：卷一正文落在第一个开卷标签之前，
    # 要单独切成卷一，不能当作序文并进卷二
    first_no = int(matches[0].group(1))
    if preface and first_no > 1 and re.search(
            rf'<cb:juan\s+n="0*{first_no - 1}"\s+fun="close"', preface):
        juans.append((first_no - 1, preface, None))
        preface = None
    for i, m in enumerate(matches):
        no = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body_xml)
        juans.append((no, body_xml[start:end], preface if i == 0 else None))
    return juans


def build_juan_txt(entry: dict, juan_no: int, juan_xml: str, preface_xml: str,
                   gaiji_map: dict | None = None) -> str:
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

    # 大般若经 T06/T07 两册开头是会序（第二会序），属正文，放到卷标题之后
    body_preface = ""
    if preface_xml and entry.get("sutra_no") == "0220":
        body_preface = _xml_to_plain(RE_DOC_NUMBER.sub('', preface_xml), gaiji_map)
        preface_xml = None

    # 序文（仅第一卷）：剥掉 docNumber 后再转纯文本，避免与上面的 No.X 行重复
    if preface_xml:
        preface_clean = RE_DOC_NUMBER.sub('', preface_xml)
        preface_txt   = _xml_to_plain(preface_clean, gaiji_map)
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
    if not re.search(rf'卷第[{CN_NUMS}]+', jh):
        # 单卷经 / jhead 不含卷号 → 补上。已有「一卷」则改成「卷第一」
        if re.search(rf'卷[{CN_NUMS}]+$', jh):
            jh = re.sub(rf'卷[{CN_NUMS}]+$', f'卷第{_cn_num(juan_no)}', jh)
        elif re.search(rf'[{CN_NUMS}]+卷$', jh):
            jh = re.sub(rf'[{CN_NUMS}]+卷$', f'卷第{_cn_num(juan_no)}', jh)
        else:
            jh = f"{jh}卷第{_cn_num(juan_no)}"
    lines.append(jh)
    lines.append("")

    # 译者/作者：优先卷首 byline（Translator 或 author），否则用 TSV。
    # 只看卷首，避免把后文某篇作者（如《遊方記抄》裡的金守溫）當成整书作者。
    # byline 常被 <lb/> 拆成多行，要合并成单行，否则 cbeta_txt_to_md.py 识别不到。
    byline = RE_BYLINE_TR.search(juan_xml[:4000])
    if byline:
        tr = _strip_tags(byline.group(1))
        tr = re.sub(r'\s+', '', tr).strip()
    else:
        tr = tsv_translator.replace(" ", "") or "失譯"
    if not any(mark in tr for mark in _AUTHORSHIP_END):
        tr += "譯"
    lines.append(tr)
    lines.append("")

    # 正文：把卷头 + 译者 byline 之外的内容转纯文本
    # 简单做法：把 <cb:juan>...</cb:juan> 标签和 jhead/byline 这几个 XML 块从 juan_xml 中去掉，
    # 剩下的扔给 _xml_to_plain
    body = juan_xml
    body = RE_CB_JUAN_OPEN.sub('', body)
    body = re.sub(r'<cb:juan\s+n="\d+"\s+fun="close"[^>]*>.*?</cb:juan>', '', body, flags=re.DOTALL)
    body = re.sub(r'<cb:juan\s+n="\d+"\s+fun="close"\s*/>', '', body)
    body = re.sub(r'<cb:jhead>.*?</cb:jhead>',  '', body, flags=re.DOTALL)
    # 大般若经会序的作者行（西明寺沙門玄則製）属正文，保留成单独一段
    if entry.get("sutra_no") == "0220":
        body = re.sub(r'<byline[^>]*>((?:(?!</byline>).)*玄則(?:(?!</byline>).)*)</byline>',
                      r'<p>\1</p>', body, flags=re.DOTALL)
    # 卷正文里的所有 byline（Translator/author/Scribe）已在头部处理过，全剥
    body = re.sub(r'<byline[^>]*>.*?</byline>', '', body, flags=re.DOTALL)
    body = RE_DOC_NUMBER.sub('', body)

    body_txt = _xml_to_plain(body, gaiji_map)
    if body_preface:
        body_txt = body_preface + "\n\n" + body_txt
    # 《高僧傳》部分卷只有 mulu 而无科名 <head>，按卷补科名，便于转 md 时分节
    if entry.get("sutra_no") == "2059":
        cat = T2059_JUAN_CATEGORY.get(juan_no)
        if cat:
            first_line = next((ln.strip() for ln in body_txt.split("\n") if ln.strip()), "")
            already = (
                first_line.startswith(cat)
                or first_line.startswith("譯經")
                or first_line.startswith("義解")
                or first_line.startswith("神異")
                or first_line.startswith("習禪")
                or first_line.startswith("亡身")
                or first_line.startswith("興福")
                or first_line.startswith("序")
            )
            if not already:
                body_txt = cat + "\n\n" + body_txt
    lines.append(body_txt)
    lines.append("")

    txt = "\n".join(lines)
    if entry.get("sutra_no") == "0220":
        # 会序的标题在 XML 里分成「大般若經第二會」「序」两个 <head>，合成一个
        txt = re.sub(
            r"^(大般若[^\n]{0,12}第[一二三四五六七八九十百]+會[^\n]{0,12})\n\n序\n",
            r"\1序\n", txt, flags=re.MULTILINE)
    return txt


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

    # 一部经分在几册（如 T0220 大般若经分 T05/T06/T07 三册）时，TSV 有多行，
    # 同一 sutra_id 的每一行各对应一个 XML 文件，逐个处理。
    if args.key.strip() != entry.get("cbeta_id"):
        rows = [r for r in load_tsv()
                if r["collection"] == entry["collection"]
                and r["sutra_no"] == entry["sutra_no"]]
    else:
        rows = [entry]
    for e in rows:
        process_entry(e, args)


def process_entry(entry: dict, args):
    sutra_id   = entry["collection"] + entry["sutra_no"]   # 如 T0001
    juan_total = int(entry["juan_count"])
    print(f"匹配到：{entry['cbeta_id']} {entry['title']}（共 {juan_total} 卷，{entry['category']}）")

    # 1. 下载 XML
    xml_file = download_xml(entry, force=args.force)
    if args.xml_only:
        return

    # 2. 解析切卷
    xml_text = xml_file.read_text(encoding="utf-8")
    gaiji_map = _load_gaiji_map(xml_text)
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
        txt = build_juan_txt(entry, juan_no, juan_xml, preface_xml, gaiji_map)
        out_path.write_text(txt, encoding="utf-8")
        written += 1

    print(f"写入 {written} 卷，跳过 {skipped} 卷 → {out_dir.relative_to(PROJECT_ROOT)}/")
    print(f"下一步：python3 scripts/cbeta_txt_to_md.py {sutra_id}")


if __name__ == "__main__":
    main()
