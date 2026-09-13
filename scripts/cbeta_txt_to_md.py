#!/usr/bin/env python3
"""
CBETA 纯文本 → Markdown 转换脚本

将 content/cbeta-raw/T/TXXXX/ 下的 txt 文件转为 content/sutras-raw/ 下的 md 文件。
逐段生成 "### 原文 / ### 现代语译" 结构，为后续翻译做准备。

用法:
  python3 scripts/cbeta_txt_to_md.py T0001
  python3 scripts/cbeta_txt_to_md.py T0001 --force   # 覆盖已有文件
"""

import os
import re
import sys
from datetime import date

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CBETA_RAW = os.path.join(PROJECT_ROOT, "content", "cbeta-raw")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "content", "sutras-raw")
TSV_PATH = os.path.join(PROJECT_ROOT, "target_sutra_list.tsv")

# ── 中文数字 ──────────────────────────────────────────────
CHINESE_NUMS = {
    1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
    6: "六", 7: "七", 8: "八", 9: "九", 10: "十",
    11: "十一", 12: "十二", 13: "十三", 14: "十四", 15: "十五",
    16: "十六", 17: "十七", 18: "十八", 19: "十九", 20: "二十",
    21: "二十一", 22: "二十二", 23: "二十三", 24: "二十四", 25: "二十五",
    26: "二十六", 27: "二十七", 28: "二十八", 29: "二十九", 30: "三十",
    31: "三十一", 32: "三十二", 33: "三十三", 34: "三十四", 35: "三十五",
    36: "三十六", 37: "三十七", 38: "三十八", 39: "三十九", 40: "四十",
    41: "四十一", 42: "四十二", 43: "四十三", 44: "四十四", 45: "四十五",
    46: "四十六", 47: "四十七", 48: "四十八", 49: "四十九", 50: "五十",
}

# ── 段落分类 ──────────────────────────────────────────────
# 经文标题行：如 （一）第一分初大本經第一
RE_SECTION = re.compile(r"^（[一二三四五六七八九十〇百千]+）(.+)")
# 仅有序号的经号：如杂阿含 （一八）、（一四〇、一四一）、（七五五～七）。
# CBETA 里这是 <head>，应单独成章。
RE_SUTRA_NUM = re.compile(
    r"^（[一二三四五六七八九十〇百千]+(?:[、～][一二三四五六七八九十〇百千]+)*）$"
)
# 品目行：如 閻浮提州品第一 / 佛說長阿含第四分世記經XX品第N
RE_PIN = re.compile(r"^(佛說.+)?(.+品第[一二三四五六七八九十百千]+.*)$")
# 续卷标题：如 遊行經第二中
RE_CONTINUATION = re.compile(r"^(.+經第[一二三四五六七八九十]+[初中後]?)$")
# 卷标题行
RE_VOLUME_TITLE = re.compile(r".*卷第?[一二三四五六七八九十百千廿卅]+")
# 译者/作者行
RE_TRANSLATOR = re.compile(
    r"^.{3,50}(譯|撰|述|集|編|錄|記|箋)(遊天竺事)?$"
)

# 《高僧傳》科名、传主标题、论曰、目录卷标
RE_GSZ_CATEGORY = re.compile(
    r"^(譯經[上中下]|義解[一二三四五]|神異[上下]|"
    r"習禪(第[一二三四五六七八九十]+)?(（[^）]*）)?(　明律.*)?"
    r"|明律(第[一二三四五六七八九十]+)?(（[^）]*）)?"
    r"|亡身(第[一二三四五六七八九十]+)?(（[^）]*）)?"
    r"|誦經(第[一二三四五六七八九十]+)?(（[^）]*）)?"
    r"|興福(第[一二三四五六七八九十]+)?(（[^）]*）)?"
    r"|經師(第[一二三四五六七八九十]+)?(（[^）]*）)?"
    r"|唱導(第[一二三四五六七八九十]+)?(（[^）]*）)?"
    r"|序錄|序)$"
)
RE_GSZ_BIO_NUM_PREFIX = re.compile(r"^(\d+)\s+(\S{2,20})$")
RE_GSZ_BIO_NUM_SUFFIX = re.compile(
    r"^(.{2,20}?)第?([一二三四五六七八九十百]+)$"
)
RE_GSZ_LUN = re.compile(r"^論曰[：:]?")
RE_GSZ_CATALOG = re.compile(r"^((續)?高僧傳|比丘尼傳)第.+卷")
# 求法僧传：太州玄照法師 / 并州常愍禪師
RE_BIO_PERSON = re.compile(
    r"^(.{2,24}(?:法師|禪師|律師|尊者|和尚)|.{2,16}師)$"
)
# 比丘尼傳：晉竹林寺淨撿尼傳一
RE_NI_BIO = re.compile(
    r"^(.{2,30}尼傳[一二三四五六七八九十]*)$"
)
# 遊方記抄等：徃五天竺國傳 / 悟空入竺記 / 繼業西域行程
RE_TRAVEL_HEAD = re.compile(
    r"^(.{2,40}(?:傳考|記逸文|銘并序|行程|傳|記|考|碑))$"
)
# 出三藏記集：法顯法師傳第六 / 新集經律論錄第一（目錄條目帶頓號的不在此列）
RE_CSZJJ_HEAD = re.compile(
    r"^(.{2,40}?(?:傳|記|錄|序|緣記))第([一二三四五六七八九十百]+)$"
)
# 神僧傳短人名標題
RE_SHORT_NAME_HEAD = re.compile(r"^[\u4e00-\u9fff]{2,8}$")
# 南海寄歸內法傳：一破夏非小 / 四十古德不為
RE_CN_ENUM_HEAD = re.compile(
    r"^([一二三四五六七八九十百]+)([\u4e00-\u9fff]{2,8})$"
)
# 釋迦方志：釋迦方志封疆篇第一
RE_PIAN = re.compile(r"^(.{2,40}篇第[一二三四五六七八九十百]+.*)$")


def load_tsv_entry(sutra_id):
    """从 target_sutra_list.tsv 读取元数据"""
    with open(TSV_PATH, "r", encoding="utf-8") as f:
        header = f.readline().strip().split("\t")
        for line in f:
            row = dict(zip(header, line.strip().split("\t")))
            if row.get("collection") + row.get("sutra_no") == sutra_id:
                return row
    return None


# ── 文本预处理 ────────────────────────────────────────────

def strip_cbeta_header(lines):
    """去掉 CBETA 注释头 (以 # 开头的行及紧随的空行)"""
    i = 0
    while i < len(lines) and (lines[i].startswith("#") or lines[i].strip() == ""):
        i += 1
    return lines[i:]


def strip_tail_title(lines, title_prefix):
    """去掉文末重复的卷标题行"""
    while lines and lines[-1].strip() == "":
        lines.pop()
    if lines and title_prefix in lines[-1]:
        lines.pop()
    while lines and lines[-1].strip() == "":
        lines.pop()
    return lines


def extract_header(lines):
    """
    从正文开头提取：序文、卷标题、译者行，返回 (preface_paragraphs, body_lines)
    """
    i = 0

    # 跳过 "No. X" 行
    if i < len(lines) and lines[i].strip().startswith("No."):
        i += 1
        while i < len(lines) and lines[i].strip() == "":
            i += 1

    # 找卷标题行位置
    vol_line = -1
    for j in range(i, min(i + 40, len(lines))):
        if RE_VOLUME_TITLE.match(lines[j].strip()):
            vol_line = j
            break

    # 卷标题之前的内容 = 序文
    preface_lines = []
    if vol_line > i:
        preface_lines = lines[i:vol_line]
    if vol_line >= 0:
        i = vol_line + 1

    # 跳空行
    while i < len(lines) and lines[i].strip() == "":
        i += 1

    # 跳译者行
    if i < len(lines):
        tr = lines[i].strip()
        looks_like_byline = (
            RE_TRANSLATOR.match(tr)
            or (
                3 <= len(tr) <= 50
                and "。" not in tr
                and any(m in tr for m in ("譯", "撰", "述", "集", "編", "錄", "自記", "箋"))
            )
        )
        if looks_like_byline:
            i += 1
            while i < len(lines) and lines[i].strip() == "":
                i += 1

    preface_paragraphs = split_paragraphs(preface_lines) if preface_lines else []
    return preface_paragraphs, lines[i:]


# ── 分段逻辑 (核心) ──────────────────────────────────────

MAX_PARA_LEN = 150  # 散文段落最大汉字数（中文 1 字 = 1 字符）
VERSE_GROUP_SIZE = 4  # 偈颂每 N 行一段


def is_verse_line(line):
    """判断是否为偈颂行（含全角空格对齐）"""
    return "　　" in line and line.strip() != ""


def _split_at_points(text, split_points):
    """在给定的拆分点列表处，按 MAX_PARA_LEN 拆分文本。"""
    if not split_points:
        return [text]

    result = []
    start = 0
    current_end = 0

    for sp in split_points:
        if sp - start <= MAX_PARA_LEN:
            current_end = sp
        else:
            if current_end > start:
                result.append(text[start:current_end].strip())
                start = current_end
            current_end = sp
            if sp - start > MAX_PARA_LEN:
                result.append(text[start:sp].strip())
                start = sp
                current_end = sp

    remaining = text[start:].strip()
    if remaining:
        result.append(remaining)

    return [p for p in result if p]


def split_prose(text):
    """
    将超过 MAX_PARA_LEN 的散文段落按标点拆分。
    优先级：。！？；」 → 若仍超长则用 ，
    """
    if len(text) <= MAX_PARA_LEN:
        return [text]

    # 第一轮：用句末标点拆分
    primary_points = []
    for i, ch in enumerate(text):
        if ch in "。！？；":
            primary_points.append(i + 1)
        elif ch == "」" and i + 1 < len(text) and text[i + 1] != "\n":
            primary_points.append(i + 1)

    result = _split_at_points(text, primary_points)

    # 第二轮：对仍然超长的段落，用逗号再拆
    final = []
    for para in result:
        if len(para) <= MAX_PARA_LEN:
            final.append(para)
        else:
            comma_points = []
            for i, ch in enumerate(para):
                if ch == "，":
                    comma_points.append(i + 1)
            parts = _split_at_points(para, comma_points)
            final.extend(parts)

    return final


def split_verse(lines):
    """将偈颂行按每 VERSE_GROUP_SIZE 行一组拆分"""
    groups = []
    for i in range(0, len(lines), VERSE_GROUP_SIZE):
        group = lines[i:i + VERSE_GROUP_SIZE]
        groups.append("\n".join(group))
    return groups


def split_paragraphs(lines):
    """
    将连续的文本行按空行分割，再对段落做细分：
    - 偈颂：每 4 行一段
    - 散文：超过 100 字在句末标点处拆分
    """
    # 第一步：按空行切成原始块；独立经号即使没有空行也单独成块
    raw_blocks = []
    current = []
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if current:
                raw_blocks.append(current)
                current = []
        elif RE_SUTRA_NUM.match(stripped):
            if current:
                raw_blocks.append(current)
                current = []
            raw_blocks.append([stripped])
        else:
            current.append(line)
    if current:
        raw_blocks.append(current)

    # 第二步：对每个块做细分
    paragraphs = []
    for block in raw_blocks:
        # 判断是否为偈颂块（多数行含全角空格）
        verse_count = sum(1 for l in block if is_verse_line(l))
        if verse_count > len(block) / 2:
            # 偈颂：每 4 行一段
            paragraphs.extend(split_verse(block))
        else:
            # 散文：合并为一个文本，再按长度拆分
            text = "".join(block)  # 散文块的行直接拼接（CBETA 一段就是一行）
            paragraphs.extend(split_prose(text))

    # 第三步：处理段首闭合引号
    # 1. 纯标点段（如孤立的 」）→ 并入上一段末尾
    # 2. 以 」』）】 开头的段落 → 把开头连续闭合引号剥离，并入上一段末尾
    CLOSING_QUOTES = set("」』）】")
    merged = []
    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            continue
        if all(c in CLOSING_QUOTES | set("。；，！？、：") for c in stripped):
            # 纯标点段，全部并入上一段
            if merged:
                merged[-1] = merged[-1] + stripped
            continue
        # 检查段首是否有闭合引号
        if stripped[0] in CLOSING_QUOTES and merged:
            # 剥离开头连续的闭合引号
            i = 0
            while i < len(stripped) and stripped[i] in CLOSING_QUOTES:
                i += 1
            prefix = stripped[:i]
            rest = stripped[i:]
            merged[-1] = merged[-1] + prefix
            if rest:
                merged.append(rest)
        else:
            merged.append(para)

    # 第四步：合并连续短段落
    # 连续的短散文段（非偈颂）合并，直到接近 MAX_PARA_LEN
    MIN_PARA_LEN = 30  # 低于此长度视为"短段"，尝试与相邻段合并
    consolidated = []
    for para in merged:
        para_len = len(para.replace("\n", ""))
        is_verse = is_verse_line(para.split("\n")[0]) if para else False

        if (consolidated
                and not is_verse
                and not is_section_heading(para)
                and para_len < MIN_PARA_LEN):
            prev = consolidated[-1]
            prev_is_verse = is_verse_line(prev.split("\n")[0]) if prev else False
            combined_len = len(prev.replace("\n", "")) + para_len
            # 经号标题即使很短，也不能并入上一段，也不能把后文并进来。
            if (not prev_is_verse
                    and not is_section_heading(prev)
                    and combined_len <= MAX_PARA_LEN):
                consolidated[-1] = prev + "\n" + para
                continue

        consolidated.append(para)

    # 第五步：上一句未结束（不以 。！？；」』 收尾）则与下一段拼接，避免「而奉戒 / 精峻」
    SENTENCE_END = "。！？；」』"
    CATALOG_START = "漢魏晉宋齊梁秦"

    def _is_catalog_line(line: str) -> bool:
        line = line.strip()
        return bool(line) and line[0] in CATALOG_START and "。" not in line

    glued = []
    for para in consolidated:
        prev = glued[-1] if glued else ""
        prev_first = prev.split("\n")[0] if prev else ""
        para_first = para.split("\n")[0] if para else ""
        prev_last = prev.rstrip().split("\n")[-1] if prev.rstrip() else ""
        prev_tail = prev.rstrip()[-1] if prev.rstrip() else ""
        if (glued
                and not is_verse_line(para_first)
                and not is_verse_line(prev_first)
                and not is_section_heading(para)
                and not is_section_heading(prev)
                and prev_tail
                and prev_tail not in SENTENCE_END):
            # 目录人名行本身不以句号收尾，应换行保留，不可黏成「帛尸梨蜜晉長安…」
            if _is_catalog_line(prev_last) and _is_catalog_line(para_first) and len(prev_last) >= 6:
                glued[-1] = prev.rstrip() + "\n" + para.lstrip()
                continue
            glued[-1] = prev.rstrip() + para.lstrip()
            continue
        glued.append(para)

    return glued


def is_gsz_bio_heading(first_line):
    """高僧传传主标题：`1 攝摩騰` 或 `鳩摩羅什一`。"""
    if RE_GSZ_BIO_NUM_PREFIX.match(first_line):
        return True
    if RE_GSZ_CATEGORY.match(first_line):
        return False
    if RE_GSZ_BIO_NUM_SUFFIX.match(first_line) and len(first_line) < 24:
        return True
    return False


def is_section_heading(text):
    """判断段落是否为章节标题"""
    first_line = text.split("\n")[0].strip().lstrip("、")
    if RE_SUTRA_NUM.match(first_line):
        return True
    if RE_SECTION.match(first_line):
        return True
    if RE_PIN.match(first_line) and len(first_line) < 40:
        return True
    if RE_CONTINUATION.match(first_line) and len(first_line) < 20:
        return True
    if RE_GSZ_CATEGORY.match(first_line):
        return True
    if RE_GSZ_LUN.match(first_line):
        return True
    if RE_GSZ_CATALOG.match(first_line) and len(first_line) < 40:
        return True
    if is_gsz_bio_heading(first_line) and "\n" not in text.strip():
        return True
    if "\n" in text.strip() or "。" in first_line or "！" in first_line:
        return False
    if first_line in ("序", "并序", "序文"):
        return True
    if RE_PIAN.match(first_line) and len(first_line) < 40:
        return True
    if RE_NI_BIO.match(first_line):
        return True
    if RE_CSZJJ_HEAD.match(first_line) and len(first_line) <= 50:
        return True
    if (
        RE_SHORT_NAME_HEAD.match(first_line)
        and "\n" not in text.strip()
        and not any(ch in first_line for ch in "經律論卷品")
    ):
        return True
    if RE_BIO_PERSON.match(first_line) and len(first_line) < 24:
        return True
    if RE_TRAVEL_HEAD.match(first_line) and 4 <= len(first_line) <= 40:
        return True
    if RE_CN_ENUM_HEAD.match(first_line) and len(first_line) <= 14:
        return True
    return False


def format_section_heading(text):
    """把传主标题规范成 `一、攝摩騰`；科名、论曰保持原样。"""
    first = text.split("\n")[0].strip().lstrip("、")
    if RE_GSZ_CATEGORY.match(first) or RE_GSZ_CATALOG.match(first):
        return first
    if first in ("論曰", "論曰：", "論曰:"):
        return "論曰"
    m = RE_GSZ_BIO_NUM_PREFIX.match(first)
    if m:
        n = int(m.group(1))
        cn = CHINESE_NUMS.get(n, str(n))
        return f"{cn}、{m.group(2)}"
    m = RE_GSZ_BIO_NUM_SUFFIX.match(first)
    if m and not RE_GSZ_CATEGORY.match(first):
        return f"{m.group(2)}、{m.group(1)}"
    m = RE_CN_ENUM_HEAD.match(first)
    if m and len(first) <= 14:
        return f"{m.group(1)}、{m.group(2)}"
    m = RE_NI_BIO.match(first)
    if m:
        body = first
        num = ""
        nm = re.search(r"([一二三四五六七八九十]+)$", body)
        if nm:
            num = nm.group(1)
            body = body[: nm.start()]
        if num:
            return f"{num}、{body}"
        return first
    m = RE_CSZJJ_HEAD.match(first)
    if m:
        return f"{m.group(2)}、{m.group(1)}"
    return first


def build_md(frontmatter, title, preface_paras, body_lines):
    """
    组装最终 md 内容。

    结构：
    ---
    frontmatter
    ---
    # 经名

    ## 序                          (如有)
    ### 原文
    ...
    ### 现代语译

    ## （一）第一分初大本經第一     (章节标题)
    ### 原文
    ...
    ### 现代语译
    ### 原文
    ...
    ### 现代语译
    """
    md = []

    # frontmatter
    md.append("---")
    for k, v in frontmatter.items():
        md.append(f"{k}: {v}")
    md.append("---")
    md.append("")
    md.append(f"# {title}")
    md.append("")

    # sid 计数器：从 001 开始，每对 `### 原文 / ### 现代语译` 共用一个 sid。
    # 注入格式与现有文件一致：header 紧接 `<!-- sid:NNN -->` 行，再空行再内容。
    sid_counter = [0]

    def emit_pair(content: str):
        sid_counter[0] += 1
        sid = f"{sid_counter[0]:03d}"
        md.append("### 原文")
        md.append(f"<!-- sid:{sid} -->")
        md.append("")
        md.append(content)
        md.append("")
        md.append("### 现代语译")
        md.append(f"<!-- sid:{sid} -->")
        md.append("")
        md.append("")

    # 序文
    if preface_paras:
        md.append("## 序")
        md.append("")
        for para in preface_paras:
            emit_pair(para)

    # 正文
    paragraphs = split_paragraphs(body_lines)
    catalog_heads = []

    def flush_catalog():
        if not catalog_heads:
            return
        emit_pair("、".join(catalog_heads) + "、")
        catalog_heads.clear()

    for para in paragraphs:
        first_line = para.split("\n")[0].strip()

        if is_section_heading(first_line):
            heading = format_section_heading(first_line)
            rest = "\n".join(para.split("\n")[1:]).strip()
            # （一八）如是我聞： 被粘成一行时，经号仍是标题，后文归入正文
            sec_m = RE_SECTION.match(first_line)
            if sec_m and not RE_SUTRA_NUM.match(first_line):
                after_num = sec_m.group(1).lstrip()
                if after_num.startswith(("如是我聞", "我聞如是", "爾時")):
                    heading = first_line[: sec_m.start(1)]
                    rest = after_num + (("\n" + rest) if rest else "")
            lun = RE_GSZ_LUN.match(first_line)
            if lun and len(first_line) > 4:
                heading = "論曰"
                rest = first_line[lun.end():].lstrip("：:").strip() or rest
            if rest:
                flush_catalog()
                md.append(f"## {heading}")
                md.append("")
                emit_pair(rest)
            else:
                catalog_heads.append(heading)
        else:
            if len(catalog_heads) == 1:
                md.append(f"## {catalog_heads[0]}")
                md.append("")
                catalog_heads.clear()
                emit_pair(para)
            else:
                flush_catalog()
                emit_pair(para)
    if len(catalog_heads) == 1:
        md.append(f"## {catalog_heads[0]}")
        md.append("")
        catalog_heads.clear()
    flush_catalog()

    # 清理末尾空行
    while md and md[-1].strip() == "":
        md.pop()
    md.append("")

    return "\n".join(md)


# ── 单卷转换 ──────────────────────────────────────────────

def convert_volume(sutra_id, collection, sutra_no, juan_idx, juan_total,
                   title, translator, category, vol_str):
    """转换单卷 txt → md 字符串"""

    txt_path = os.path.join(
        CBETA_RAW, collection, sutra_id,
        f"{sutra_id}_{juan_idx:03d}.txt"
    )
    if not os.path.exists(txt_path):
        return None

    with open(txt_path, "r", encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    # 预处理
    lines = strip_cbeta_header(raw_lines)
    lines = strip_tail_title(lines, title[:4])

    # 提取序文和正文
    preface_paras, body_lines = extract_header(lines)

    # 构建 frontmatter
    cn = CHINESE_NUMS.get(juan_idx, str(juan_idx))
    volume_label = f"卷第{cn}" if juan_total > 1 else ""
    vol_suffix = f" {volume_label}" if volume_label else ""

    slug = f"{collection}{sutra_no}-{juan_idx:03d}"
    cbeta_web = f"https://cbetaonline.dila.edu.tw/{collection}{vol_str}n{sutra_no}_{juan_idx:03d}"

    fm = {
        "title": f"{title}{vol_suffix}",
        "short_title": f"{title}卷{cn}" if juan_total > 1 else title,
        "slug": slug,
        "cbeta_id": sutra_id,
        "cbeta_web_source": cbeta_web,
        "category": category,
        "translator": translator,
        "juan_index": juan_idx,
        "juan_total": juan_total,
        "translation_status": "untranslated",
        "review_status": "unreviewed",
        "updated_at": date.today().isoformat(),
    }
    if volume_label:
        fm["volume_label"] = volume_label

    return build_md(fm, title, preface_paras, body_lines)


# ── 主入口 ────────────────────────────────────────────────

def _read_translation_status(md_path):
    """从已有 md 的 frontmatter 读 translation_status，读不到就当 untranslated。"""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            head = f.read(1024)
        m = re.search(r'^translation_status:\s*(\w+)', head, re.MULTILINE)
        return m.group(1) if m else "untranslated"
    except Exception:
        return "untranslated"


def main():
    if len(sys.argv) < 2:
        print("用法: python3 scripts/cbeta_txt_to_md.py T0001 "
              "[--force | --force-overwrite-translated]")
        sys.exit(1)

    sutra_id = sys.argv[1]
    force = "--force" in sys.argv
    # 危险开关：连已翻译的 md 也覆盖。仅在确认要重做时使用。
    force_overwrite = "--force-overwrite-translated" in sys.argv

    collection = sutra_id[0]
    sutra_no = sutra_id[1:]

    entry = load_tsv_entry(sutra_id)
    if not entry:
        print(f"错误: {sutra_id} 不在 target_sutra_list.tsv 中")
        sys.exit(1)

    title = entry["title"]
    translator = entry.get("translator", "")
    juan_total = int(entry.get("juan_count", "1"))
    category = entry.get("category", "")
    vol_str = entry.get("volume", "")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    created = 0
    skipped = 0

    for juan_idx in range(1, juan_total + 1):
        slug = f"{collection}{sutra_no}-{juan_idx:03d}"
        out_path = os.path.join(OUTPUT_DIR, f"{slug}.md")

        if os.path.exists(out_path):
            existing_status = _read_translation_status(out_path)
            if not force:
                skipped += 1
                continue
            # 已翻译的文件除非显式要求，否则不许覆盖
            if existing_status != "untranslated" and not force_overwrite:
                print(f"  跳过 {slug}.md：translation_status={existing_status}。"
                      "如确需重做，加 --force-overwrite-translated。")
                skipped += 1
                continue

        md_content = convert_volume(
            sutra_id, collection, sutra_no, juan_idx, juan_total,
            title, translator, category, vol_str
        )

        if md_content is None:
            print(f"  警告: {sutra_id}_{juan_idx:03d}.txt 不存在，跳过")
            continue

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        created += 1

    print(f"{sutra_id} ({title}): 生成 {created} 卷, 跳过 {skipped} 卷")


if __name__ == "__main__":
    main()
