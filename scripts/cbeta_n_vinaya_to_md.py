#!/usr/bin/env python3
"""
漢譯南傳大藏經（N 部）律藏 XML → md。

通用的 cbeta_txt_to_md.py 读的是已拍平的 TXT，N 部的多层目录
（經分別 > 波羅夷 > 波羅夷一〔不淨戒〕 > 一 > （一））在 TXT 里会粘在
第一段，（一）（二）这类纯序号也会被当成空的 ## 标题。本脚本直接读 XML：

- 有名称的目录（波羅夷一〔不淨戒〕、第一　大犍度、誦品一……）→ `## ` 标题，
  连续打开的几层用「・」连起来；第一层（經分別一、大品、小品、附隨）就是本部名，不出标题
- 纯序号目录（一、（一）、（七．八））→ 放在下一段原文开头
- 散文段超过 MAX_PARA_LEN 按句末标点拆；偈颂每 4 句一段

用法：
  python3 scripts/cbeta_n_vinaya_to_md.py N0001 [--force]
只覆盖 translation_status 为 untranslated 的文稿。
"""
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_cbeta as fc            # noqa: E402
import cbeta_txt_to_md as tm        # noqa: E402

OUT_DIR = ROOT / "content" / "sutras-raw"
MAX_PARA_LEN = tm.MAX_PARA_LEN
VERSE_GROUP = 4

RE_NUMERIC = re.compile(r'^[（(]?[一二三四五六七八九十百〇零．・、～\-—\s]+[）)]?$')
TOKEN_RE = re.compile(
    r'<milestone\b[^>]*unit="juan"[^>]*n="(?P<juan>\d+)"[^>]*/>'
    r'|<cb:mulu\b[^>]*level="(?P<lv>\d+)"[^>]*>(?P<mulu>.*?)</cb:mulu>'
    r'|<p\b[^>]*>(?P<p>.*?)</p>'
    r'|<lg\b[^>]*>(?P<lg>.*?)</lg>'
    r'|<item\b[^>]*>(?P<item>.*?)</item>',
    re.DOTALL,
)


def inline_text(xml, gaiji):
    s = fc._replace_gaiji(xml, gaiji)
    s = re.sub(r'<note[^>]*>.*?</note>', '', s, flags=re.DOTALL)
    s = re.sub(r'<rdg[^>]*>.*?</rdg>', '', s, flags=re.DOTALL)
    s = re.sub(r'<caesura[^>]*/>', '　', s)
    s = re.sub(r'<lb[^>]*/>|<pb[^>]*/>', '', s)
    s = fc._strip_tags(s)
    s = fc._normalize_text(s).replace("\n", "")
    return s.strip()


def verse_lines(xml, gaiji):
    lines = [inline_text(m, gaiji) for m in re.findall(r'<l\b[^>]*>(.*?)</l>', xml, re.DOTALL)]
    return [ln for ln in lines if ln]


def parse_body(xml_text):
    gaiji = fc._load_gaiji_map(xml_text)
    body = fc.RE_BODY.search(xml_text).group(1)
    juans = {}          # juan_no -> list of events
    cur = None
    for m in TOKEN_RE.finditer(body):
        if m.group("juan"):
            cur = int(m.group("juan"))
            juans[cur] = []
            continue
        if cur is None:
            continue
        ev = juans[cur]
        if m.group("lv"):
            ev.append(("mulu", int(m.group("lv")), inline_text(m.group("mulu"), gaiji)))
        elif m.group("p") is not None:
            t = inline_text(m.group("p"), gaiji)
            if t:
                ev.append(("p", t))
        elif m.group("lg") is not None:
            ls = verse_lines(m.group("lg"), gaiji)
            if ls:
                ev.append(("lg", ls))
        elif m.group("item") is not None:
            t = inline_text(m.group("item"), gaiji)
            if t:
                ev.append(("p", t))
    return juans


def split_long(text):
    """先按句末标点、逗号拆；仍超过 250 字的名相列举，再按顿号、「……」拆。"""
    parts = tm.split_prose(text)
    out = []
    for x in parts:
        if len(x) <= tm.HARD_MAX_PARA_LEN:
            out.append(x)
            continue
        points = [i + 1 for i, ch in enumerate(x) if ch == "、"]
        points += [m.end() for m in re.finditer(r'……', x)]
        out += tm._split_at_points(x, sorted(points))
    return out


def fix_quote_splits(parts):
    """拆段落在句号与后引号之间时，把段首的 」』）〕和标点移回上一段末尾。"""
    out = []
    for x in parts:
        m = re.match(r'^[」』）〕，、。；：！？]+', x)
        if out and m:
            out[-1] += m.group(0)
            x = x[m.end():]
        if x:
            out.append(x)
    return out


def build_juan(events, stack):
    """stack: 当前各层目录名 {level: text}，跨卷延续。返回 (blocks, stack)。
    blocks: ("h", text) / ("seg", text)"""
    blocks = []
    opened = []         # 自上一段内容以来新打开的有名称目录
    prefix = []         # 待放到下一段开头的序号
    # 卷首：若上卷有未结束的标题，先补一个标题让读者知道所在位置
    named = [stack[k] for k in sorted(stack) if k > 1 and not RE_NUMERIC.match(stack[k])]
    if named and events and events[0][0] != "mulu":
        blocks.append(("h", named[-1]))

    def flush_heading():
        if opened:
            blocks.append(("h", "・".join(opened)))
            opened.clear()

    for ev in events:
        if ev[0] == "mulu":
            lv, text = ev[1], ev[2]
            for k in [k for k in stack if k >= lv]:
                del stack[k]
            stack[lv] = text
            if lv == 1 or not text:
                continue
            if RE_NUMERIC.match(text):
                prefix.append(text)
            else:
                if prefix:          # 序号后面又来了有名目录：序号作废并入标题
                    opened.append("".join(prefix))
                    prefix.clear()
                opened.append(text)
            continue
        flush_heading()
        pre = "".join(prefix)
        prefix.clear()
        if ev[0] == "p":
            parts = fix_quote_splits(split_long(ev[1]))
            if pre:
                parts[0] = pre + parts[0]
            blocks += [("seg", x) for x in parts]
        else:
            lines = ev[1]
            groups = ["\n".join(lines[i:i + VERSE_GROUP]) for i in range(0, len(lines), VERSE_GROUP)]
            if pre:
                groups[0] = pre + "\n" + groups[0]
            blocks += [("seg", g) for g in groups]
    flush_heading()
    return blocks, stack


def merge_short(blocks, limit=150):
    """同一标题下相邻的短散文段合并到 ~limit 字；以序号开头的段不并入上一段。"""
    out = []
    for b in blocks:
        if (b[0] == "seg" and out and out[-1][0] == "seg"
                and "\n" not in b[1] and "\n" not in out[-1][1]
                and not RE_LEAD_NUM.match(b[1])
                and len(out[-1][1]) + len(b[1]) <= limit):
            out[-1] = ("seg", out[-1][1] + b[1])
        else:
            out.append(b)
    return out


RE_LEAD_NUM = re.compile(r'^[（(]?[一二三四五六七八九十百〇．]+[）)]')


def render(fm, title, blocks):
    md = ["---"] + [f"{k}: {v}" for k, v in fm.items()] + ["---", "", f"# {title}", ""]
    sid = 0
    for kind, text in blocks:
        if kind == "h":
            md += [f"## {text}", ""]
        else:
            sid += 1
            md += ["### 原文", f"<!-- sid:{sid:03d} -->", "", text, "",
                   "### 現代語譯", f"<!-- sid:{sid:03d} -->", "", ""]
    return "\n".join(md).rstrip() + "\n"


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python3 scripts/cbeta_n_vinaya_to_md.py N0001 [--force]")
    sutra_id = sys.argv[1]
    force = "--force" in sys.argv
    entries = tm.load_tsv_entries(sutra_id)
    if not entries:
        sys.exit(f"{sutra_id} 不在 target_sutra_list.tsv")
    title = tm.RE_TITLE_RANGE.sub("", entries[0]["title"])
    juan_total = sum(int(e["juan_count"]) for e in entries)
    stack = {}
    created = 0
    for e in entries:
        xml_path = fc.xml_path(e)
        juans = parse_body(xml_path.read_text(encoding="utf-8"))
        for j in sorted(juans):
            slug = f"{sutra_id}-{j:03d}"
            out = OUT_DIR / f"{slug}.md"
            blocks, stack = build_juan(juans[j], stack)
            if out.exists():
                status = tm._read_translation_status(str(out))
                if not force or status != "untranslated":
                    continue
            cn = tm.CHINESE_NUMS.get(j, str(j))
            fm = {
                "title": f"{title} 卷第{cn}",
                "short_title": f"{title}卷{cn}",
                "slug": slug,
                "cbeta_id": sutra_id,
                "cbeta_web_source": f"https://cbetaonline.dila.edu.tw/{e['collection']}{e['volume']}n{e['sutra_no']}_{j:03d}",
                "category": e["category"],
                "translator": e["translator"],
                "juan_index": j,
                "juan_total": juan_total,
                "translation_status": "untranslated",
                "review_status": "unreviewed",
                "updated_at": date.today().isoformat(),
                "volume_label": f"卷第{cn}",
            }
            out.write_text(render(fm, title, merge_short(blocks)), encoding="utf-8")
            created += 1
    print(f"{sutra_id} ({title}): 生成 {created} 卷")


if __name__ == "__main__":
    main()
