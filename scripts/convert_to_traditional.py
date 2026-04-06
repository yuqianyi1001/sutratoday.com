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
    r'(### (?:現代語譯|现代语译)\n)(.*?)(?=\n### 原文|\Z)',
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
    '捲': '卷',   # s2tw 誤轉：卷上/卷下（卷冊）不是「捲」（捲起）
}

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
_SHI_PROPER = re.compile(r'屍(?=棄|羅|利沙|婆|吉|城|叉|迦)')

# H. 痴→癡：佛教用「癡」（愚癡、貪瞋癡）
#    opencc 把繁體「癡」轉成了簡化的「痴」，需要轉回
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

    return text


def convert_text(text: str) -> str:
    """簡體→繁體 + 佛教回退。"""
    return _buddhist_fixup(cc.convert(text))


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
