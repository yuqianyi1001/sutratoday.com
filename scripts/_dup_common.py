"""
共享的检测函数，供 detect / fix / review 三个脚本复用。
"""

import re

# ── 偈颂 / 有效行数 ────────────────────────────────────────────────────────────

def effective_orig_count(orig_text: str, orig_lines: list[str]) -> int:
    """偈颂按半句计数（\\u3000\\u3000 分隔），散文按行计数。"""
    if "\u3000\u3000" in orig_text:
        return sum(line.count("\u3000\u3000") + 1 for line in orig_lines)
    return len(orig_lines)


# ── 字符 Jaccard ────────────────────────────────────────────────────────────────

def char_jaccard(s1: str, s2: str) -> float:
    a = set(s1.replace(" ", "").replace("\u3000", ""))
    b = set(s2.replace(" ", "").replace("\u3000", ""))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ── 繁简混排检测 ────────────────────────────────────────────────────────────────

# 高频繁简字对（佛经翻译常见字）
_TRAD_SIMP_PAIRS = [
    ("們", "们"), ("國", "国"), ("說", "说"), ("當", "当"), ("時", "时"),
    ("這", "这"), ("從", "从"), ("後", "后"), ("學", "学"), ("對", "对"),
    ("還", "还"), ("過", "过"), ("門", "门"), ("問", "问"), ("觀", "观"),
    ("見", "见"), ("無", "无"), ("為", "为"), ("開", "开"), ("種", "种"),
    ("應", "应"), ("聽", "听"), ("頭", "头"), ("樣", "样"), ("語", "语"),
    ("護", "护"), ("報", "报"), ("壞", "坏"), ("滅", "灭"), ("聞", "闻"),
    ("離", "离"), ("斷", "断"), ("煩", "烦"), ("羅", "罗"), ("頌", "颂"),
    ("經", "经"), ("義", "义"), ("難", "难"), ("龍", "龙"), ("師", "师"),
    ("處", "处"), ("間", "间"), ("實", "实"), ("輔", "辅"), ("親", "亲"),
    ("願", "愿"), ("讓", "让"), ("請", "请"), ("議", "议"), ("認", "认"),
    ("話", "话"), ("體", "体"), ("號", "号"), ("稱", "称"), ("響", "响"),
]


def has_trad_simp_mixing(text: str) -> bool:
    """检测文本中是否同时含有繁体和对应简体字（表明来自不同翻译批次）。"""
    chars = set(text)
    count = 0
    for trad, simp in _TRAD_SIMP_PAIRS:
        if trad in chars and simp in chars:
            count += 1
            if count >= 2:  # 至少 2 对才判定（避免偶然巧合）
                return True
    return False


# ── 枚举序号检测 ────────────────────────────────────────────────────────────────

_ENUM_RE = re.compile(
    r'第[一二三四五六七八九十百千\d]+'
    r'|[一二三四五六七八九十]+[者為是为]'
    r'|[一二三四五六七八九十\d]+[、．.]'  # "一、" "二、" "1、" 等
)


def is_sequential_enum(lines: list[str], group_size: int) -> bool:
    """检测各组是否含不同的序号标记，若是则为枚举展开。"""
    n = len(lines)
    if group_size <= 0 or n < 2 * group_size:
        return False
    groups_text = []
    for start in range(0, n - group_size + 1, group_size):
        groups_text.append(" ".join(lines[start:start + group_size]))
    markers_per_group = [set(_ENUM_RE.findall(g)) for g in groups_text]
    for i in range(len(markers_per_group) - 1):
        a, b = markers_per_group[i], markers_per_group[i + 1]
        if a and b and a != b:
            return True
    return False
