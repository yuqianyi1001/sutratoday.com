#!/usr/bin/env python3
"""
convert_to_traditional.py — 將譯文（現代語譯）部分統一轉為繁體中文

策略：
  1. 用 opencc s2tw（簡體→臺灣繁體）做基礎轉換（比 s2t 保守：吃不轉喫、群不轉羣）
  2. 回退 12 類過度繁化的字符（佛教語境特殊字）
  3. 已是繁體的文本自動跳過（不會被誤改）

用法:
  python3 scripts/convert_to_traditional.py                         # dry-run
  python3 scripts/convert_to_traditional.py --write                 # 寫入
  python3 scripts/convert_to_traditional.py T0026-048.md            # 單文件
  python3 scripts/convert_to_traditional.py --stats                 # 統計
"""

import re
import argparse
from pathlib import Path
from datetime import date
from opencc import OpenCC

SUTRAS_DIR = Path(__file__).parent.parent / "content" / "sutras-raw"

RE_TRANS = re.compile(
    r'(### (?:現代語譯|现代语译)\n)(.*?)(?=\n### 原文|\n## |\Z)',
    re.DOTALL
)

cc = OpenCC('s2tw')

# ── 回退規則 ────────────────────────────────────────────────────────────────────

# A. 全局字符替換（這些字在佛教譯文中幾乎全該用左邊的形式）
_GLOBAL_CHAR_FIXES = {
    '唸': '念',   # 佛教「念」= 正念，非「唸」= 朗讀
    '燻': '熏',   # 佛教「熏習」用「熏」
    '薰': '熏',   # 同上
    '慾': '欲',   # 佛教「欲」= desire，不用「慾」（偏肉慾義）
    '纔': '才',   # s2t 遺留
    '喫': '吃',   # s2t 遺留
    '羣': '群',   # s2t 遺留
    '牀': '床',   # s2t 遺留
    '捱': '挨',   # s2tw 仍會轉
    '侷': '局',   # 侷限→局限，佛經用「局」
    '汙': '污',   # 染汙→染污，跟 CBETA 原文保持一致
    '擡': '抬',   # 古字→現代字
    '鍊': '煉',   # s2tw 誤轉：修煉/熔煉 用「煉」，「鍊」= 鏈條
    '痴': '癡',   # s2tw 誤轉：愚癡/貪瞋癡 用「癡」，s2tw 錯誤簡化為「痴」
    '睏': '困',   # 疲困、困乏
}

# 網頁上的簡→繁轉換用同一套規則：script-fixes.js。改這裡時那邊也要改。

# B. 瞭→了：除「瞭望」外全部回退
_LIAO_PATTERN = re.compile(r'瞭(?!望)')

# C. 佈→布：佛教固定詞
_BU_PATTERN = re.compile(r'佈(?=施|教|薩|道)')
_LIUBU_PATTERN = re.compile(r'流佈')
_XUANBU_PATTERN = re.compile(r'宣佈')

# D. X雲→X云：「云」= 說 的語境
_YUN_SAY = re.compile(r'([佛經偈論故所古頌疏律藏師祖章節品卷文謂曰])雲')

# E. 捨→舍：佛教專有名詞中的「舍」
_SHE_PROPER = re.compile(r'捨(?=利[弗子]|衛[國城]|那|身城|摩|頭)')

# F. 迴→回：日常用語用「回」（迴向 保留）
_HUI_DAILY = re.compile(r'迴(?=答|來|去|頭|覆|報|應|話|歸|到|家|國|復)')

# G. 屍→尸：佛名/地名用「尸」
_SHI_PROPER = re.compile(r'屍(?=棄|羅|利沙|婆|吉|城|叉|迦|呵|賒|葉)')
_SHI_AFTER = re.compile(r'([婆伐鉢缽迦伽])屍|(起)屍(?=鬼)|()屍(?=佉)')   # 毗婆尸、僧伽伐尸沙、毘鉢尸、迦尸國、起尸鬼

# I. 鹹→咸：「咸」= 都（咸言、咸皆）
_XIAN_ALL = re.compile(r'鹹(?=[言皆共歸悉同稱謂知來以作各曰得令使見聞願陽])')

# H. 痴→癡：佛教用「癡」（愚癡、貪瞋癡）
#    opencc 把繁體「癡」轉成了簡化的「痴」，需要轉回
# J. s2tw 對已是繁體的字詞誤轉
_MISC_FIXES = [
    (re.compile(r'(?<![一二三四五六七八九十兩幾每這那此某半])隻(?=能|應|有)'), '只'),
    (re.compile(r'幹(?=擾|涉|預)'), '干'),
    (re.compile(r'([親鄉鄰])裡'), r'\1里'),     # 親里、鄉里、鄰里
    (re.compile(r'製(?=度)'), '制'),
    (re.compile(r'矇(?=住)'), '蒙'),
    (re.compile(r'佔(?=卜)|(?<=筮)佔'), '占'),
    (re.compile(r'準(?=許|予)'), '准'),           # 准許、准予
    (re.compile(r'(?<=規)製'), '制'),             # 規制
    (re.compile(r'(?<=場)閤'), '合'),             # 場合
    (re.compile(r'(?<![寄依憑委拜付囑請推假信])託(?=腮|著|臉|頰)|(?<=襯)託'), '托'),  # 托腮、手托著、托臉頰、襯托；寄託著等不改
    (re.compile(r'(?<=長)幹(?=寺|里)'), '干'),    # 長干寺、長干里
    (re.compile(r'佔(?=相)'), '占'),              # 占相
    (re.compile(r'(?<=[小升一二三四五六七八九十百千半數])鬥(?![爭諍毆法志氣])|(?<=大)鬥(?=秤|量|入)'), '斗'),  # 小斗、升斗、三斗；大鬥爭、一鬥不改
    (re.compile(r'(?<=津)樑'), '梁'),             # 津梁
    (re.compile(r'(?<=殿)捨'), '舍'),              # 殿舍
    (re.compile(r'(?<=濃)鬱'), '郁'),              # 濃郁
    (re.compile(r'瀋(?=水|香)'), '沈'),            # 沈水、沈香
    (re.compile(r'(?<=瓦)鬥'), '斗'),              # 瓦斗
    (re.compile(r'(?<=阿)籲'), '吁'),              # 阿吁（地名）
    (re.compile(r'(?<=[、三])重製(?![作諳])'), '重制'),       # 制、重制（毘尼增一）
    (re.compile(r'(?<=升、)鬥|鬥(?=、斛|斛)|(?<=斛)鬥'), '斗'),  # 升、斗、斛；斛斗
    (re.compile(r'(?<=[取行捉受付與擲])捨(?=羅)'), '舍'),  # 舍羅（籌）
    (re.compile(r'(?<!沙彌)(?<=彌)卻'), '却'),       # 彌却（人名）；沙彌卻不改
    (re.compile(r'捲(?=[上下中第])|捲(?=[一二三四五六七八九十百千零〇两兩0-9])|(?<=[全共])捲'), '卷'),  # 經卷；捲曲、捲起不改（與 script-fixes.js 一致）
    (re.compile(r'徵(?=討|伐|戰|服)|(?<=出)徵(?![問兆驗詢詰起求象信稅收])|(?<=遠)徵(?!引)'), '征'),  # 征討、出征；提出徵問等不改
    (re.compile(r'佔(?=波)'), '占'),              # 占波國
    (re.compile(r'矇(?=昧)'), '蒙'),              # 蒙昧
    (re.compile(r'於(?=闐)'), '于'),              # 于闐
    (re.compile(r'(?<=羅)雲(?=經)'), '云'),       # 羅云經（羅睺羅）
    (re.compile(r'劃(?=臂|水|船|槳)'), '划'),      # 划臂、划水、划船
    (re.compile(r'鬥(?=頭)'), '斗'),              # 斗頭
    (re.compile(r'(?<=[才就不])準(?=你|我|他|她|汝)'), '准'),   # 才准你走（准許義）；對準他不改
    (re.compile(r'野[幹乾](?![淨燥枯涸])'), '野干'),  # 野干（狐類）
    (re.compile(r'(?:(?<=[幾千百萬十一二三四五六七八九])|(?<![劫定]數)(?<=數))裡(?![面頭邊外內])'), '里'),  # 幾里、萬里、數里；劫數裡不改
    (re.compile(r'幹(?=戰)'), '干'),              # 干戰（盾與戈）
    (re.compile(r'違揹'), '違背'),                # 違背
    (re.compile(r'(?<=[，。；])併(?=為(?![一二兩三])|發[願誓下起出])'), '並'),  # ，並為他人說、並發願；合併為一不改
    (re.compile(r'孃(?=家)'), '娘'),              # 娘家
    (re.compile(r'船伕'), '船夫'),                # 船夫
    (re.compile(r'(?<=煎)制'), '製'),             # 煎製
    (re.compile(r'(?<=[所立如])製(?=法)'), '制'),  # 所制法、立制法；木製法器不改
    (re.compile(r'(?<![房精寺館屋田廬宿坊])舍(?=給)'), '捨'),  # 捨給；房舍給、精舍給不改
    (re.compile(r'(?<!感到)(?<!讓人)(?<!令人)(?<!使人)(?<!覺得)(?<!暈、)(?<!嘔噦)噁心(?![嘔大煩]|、嘔)'), '惡心'),  # 生起惡心；感到噁心嘔吐不改
]

_CHI_BUDDHIST = re.compile(r'(?<=[愚貪瞋三])痴|^痴(?=[迷癡])')


def _buddhist_fixup(text: str) -> str:
    """回退過度繁化和佛教語境中的錯誤轉換。"""
    # A. 全局字符替換
    for wrong, right in _GLOBAL_CHAR_FIXES.items():
        text = text.replace(wrong, right)

    # B. 瞭→了
    text = _LIAO_PATTERN.sub('了', text)

    # C. 佈→布
    text = _BU_PATTERN.sub('布', text)
    text = _LIUBU_PATTERN.sub('流布', text)
    text = _XUANBU_PATTERN.sub('宣布', text)

    # D. X雲→X云
    text = _YUN_SAY.sub(r'\1云', text)

    # E. 捨→舍（專有名詞）
    text = _SHE_PROPER.sub('舍', text)

    # F. 迴→回（日常用語）
    text = _HUI_DAILY.sub('回', text)

    # G. 屍→尸（佛名/地名）
    text = _SHI_PROPER.sub('尸', text)
    text = _SHI_AFTER.sub(lambda m: (m.group(1) or m.group(2) or '') + '尸', text)

    # I. 鹹→咸
    text = _XIAN_ALL.sub('咸', text)

    # J. 其他誤轉
    for pat, rep in _MISC_FIXES:
        text = pat.sub(rep, text)

    return text


# 文稿的引號用 CBETA 的「」『』；簡體譯文若寫成“”‘’，一併換過來
_QUOTE_MAP = str.maketrans({"“": "「", "”": "」", "‘": "『", "’": "』"})


def convert_text(text: str) -> str:
    """簡體→繁體 + 佛教回退 + 引號換成「」『』。"""
    return _buddhist_fixup(cc.convert(text)).translate(_QUOTE_MAP)


def convert_file(md_path: Path, write: bool = False) -> dict:
    content = md_path.read_text(encoding="utf-8")
    new_content = content
    sections_converted = 0
    chars_converted = 0

    for m in RE_TRANS.finditer(content):
        orig_trans = m.group(2)
        converted = convert_text(orig_trans)
        if converted != orig_trans:
            sections_converted += 1
            chars_converted += sum(1 for a, b in zip(orig_trans, converted) if a != b)
            old_block = m.group(0)
            new_block = m.group(1) + converted
            new_content = new_content.replace(old_block, new_block, 1)

    changed = new_content != content
    if changed and write:
        today = date.today().strftime("%Y-%m-%d")
        new_content = re.sub(
            r'^(updated_at:\s*).*$', r'\g<1>' + today,
            new_content, count=1, flags=re.MULTILINE,
        )
        md_path.write_text(new_content, encoding="utf-8")

    return {"changed": changed, "sections_converted": sections_converted, "chars_converted": chars_converted}


def stats_file(md_path: Path) -> dict:
    content = md_path.read_text(encoding="utf-8")
    trans_text = ""
    for m in RE_TRANS.finditer(content):
        trans_text += m.group(2)
    if not trans_text.strip():
        return {"simp_chars": 0, "total": 0, "ratio": 0}
    converted = convert_text(trans_text)
    diff = sum(1 for a, b in zip(trans_text, converted) if a != b)
    total = len(trans_text.replace(" ", "").replace("\n", "").replace("\u3000", ""))
    return {"simp_chars": diff, "total": total, "ratio": diff / total if total else 0}


def main():
    parser = argparse.ArgumentParser(description="譯文統一轉繁體")
    parser.add_argument("files", nargs="*")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    def _resolve(f):
        p = Path(f)
        if p.is_absolute():
            return p
        # 如果是倉庫相對路徑（如 content/sutras-raw/T0005-001.md），直接用
        if p.exists():
            return p
        # 否則當作檔名拼到 SUTRAS_DIR
        return SUTRAS_DIR / p.name

    paths = ([_resolve(f) for f in args.files]
             if args.files else sorted(SUTRAS_DIR.glob("*.md")))

    if args.stats:
        print("統計譯文繁簡比例...\n")
        buckets = {"純繁體(0%)": 0, "少量(<5%)": 0, "混排(5-50%)": 0, "主要簡體(>50%)": 0, "無譯文": 0}
        for path in paths:
            if not path.exists(): continue
            s = stats_file(path)
            if s["total"] == 0: buckets["無譯文"] += 1
            elif s["ratio"] == 0: buckets["純繁體(0%)"] += 1
            elif s["ratio"] < 0.05: buckets["少量(<5%)"] += 1
            elif s["ratio"] < 0.5: buckets["混排(5-50%)"] += 1
            else: buckets["主要簡體(>50%)"] += 1
        for k, v in buckets.items():
            print(f"  {k}: {v}")
        return

    mode = "WRITE" if args.write else "DRY-RUN"
    print(f"[{mode}] s2tw + 佛教回退（12條規則）\n")
    tf = tc = ts = tch = 0
    for path in paths:
        if not path.exists(): continue
        tf += 1
        r = convert_file(path, write=args.write)
        if r["changed"]:
            tc += 1; ts += r["sections_converted"]; tch += r["chars_converted"]
    print(f"\n完成({mode}): 掃描{tf}, 轉換{tc}文件, {ts}段, {tch}字符")
    if not args.write and tc:
        print("  加 --write 寫入。")


if __name__ == "__main__":
    main()
