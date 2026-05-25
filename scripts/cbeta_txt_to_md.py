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
# 品目行：如 閻浮提州品第一 / 佛說長阿含第四分世記經XX品第N
RE_PIN = re.compile(r"^(佛說.+)?(.+品第[一二三四五六七八九十百千]+.*)$")
# 续卷标题：如 遊行經第二中
RE_CONTINUATION = re.compile(r"^(.+經第[一二三四五六七八九十]+[初中後]?)$")
# 卷标题行
RE_VOLUME_TITLE = re.compile(r".*卷第?[一二三四五六七八九十百千廿卅]+")
# 译者行
RE_TRANSLATOR = re.compile(r"^.{3,25}譯$")


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
    if i < len(lines) and RE_TRANSLATOR.match(lines[i].strip()):
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
    # 第一步：按空行切成原始块
    raw_blocks = []
    current = []
    for line in lines:
        if line.strip() == "":
            if current:
                raw_blocks.append(current)
                current = []
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
            if not prev_is_verse and combined_len <= MAX_PARA_LEN:
                consolidated[-1] = prev + "\n" + para
                continue

        consolidated.append(para)

    return consolidated


def is_section_heading(text):
    """判断段落是否为章节标题"""
    first_line = text.split("\n")[0].strip()
    if RE_SECTION.match(first_line):
        return True
    if RE_PIN.match(first_line) and len(first_line) < 40:
        return True
    if RE_CONTINUATION.match(first_line) and len(first_line) < 20:
        return True
    return False


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

    for para in paragraphs:
        first_line = para.split("\n")[0].strip()

        if is_section_heading(first_line):
            # 章节标题 → ## 级
            md.append(f"## {first_line}")
            md.append("")
            # 如果标题段落里还有后续内容（极少见），也输出
            rest = "\n".join(para.split("\n")[1:]).strip()
            if rest:
                emit_pair(rest)
        else:
            emit_pair(para)

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
