#!/usr/bin/env python3
"""
azure_translate.py — 用 Azure AI (DeepSeek-V3.2 / Kimi-K2.5) 翻译佛经
用法:
  python3 scripts/azure_translate.py T0002-001        # 翻译单卷（默认 DeepSeek）
  python3 scripts/azure_translate.py T0002            # 翻译全部卷
  python3 scripts/azure_translate.py T0002-001 --model kimi
  python3 scripts/azure_translate.py T0002-001 --dry-run
"""

import sys
import re
import time
import argparse
import os
from pathlib import Path
import urllib.request
import urllib.error
import json

# ── 从 .env 加载环境变量 ───────────────────────────────────────────────────────
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _v = _v.strip().strip('"').strip("'")
            os.environ.setdefault(_k.strip(), _v)

# ── Azure 配置 ────────────────────────────────────────────────────────────────
AZURE_ENDPOINT = os.environ["AZURE_ENDPOINT"]
AZURE_KEY      = os.environ["AZURE_API_KEY"]
API_VERSION    = "2024-12-01-preview"

MODELS = {
    "deepseek": "DeepSeek-V3.2",
    "kimi":     "Kimi-K2.5",
}
DEFAULT_MODEL = "deepseek"

SUTRAS_DIR = Path(__file__).parent.parent / "content" / "sutras-raw"

SYSTEM_PROMPT = """你是一位精通汉语佛教典籍的学者，擅长将古代佛经文言文翻译成通俗易懂的现代汉语白话文。

翻译原则：
1. 忠实于原文含义，不增不减
2. 用现代汉语表达，流畅自然
3. 保留佛教专有名词（如：比丘、菩萨、涅槃、阿含等），首次出现时可加简短括注
4. 偈颂保持诗歌韵律感，按原文换行
5. 只输出译文，不加任何解释或前言后语
6. 原文是繁体时，翻译也用繁体；原文是简体时，翻译用简体
"""

USER_TEMPLATE = "请将以下佛经原文翻译成现代汉语白话文：\n\n{text}"
# ─────────────────────────────────────────────────────────────────────────────

RE_SECTION = re.compile(
    r'(### 原文\n)(.*?)(\n### 现代语译\n)(.*?)(?=\n### 原文|\Z)',
    re.DOTALL
)


def get_url(deployment: str) -> str:
    return (f"{AZURE_ENDPOINT}/openai/deployments/{deployment}"
            f"/chat/completions?api-version={API_VERSION}")


def call_api(text: str, deployment: str, retries: int = 3) -> str:
    url = get_url(deployment)
    payload = json.dumps({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": USER_TEMPLATE.format(text=text.strip())},
        ],
        "max_tokens": 4096,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json", "api-key": AZURE_KEY},
        method="POST",
    )

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code == 429:  # rate limit
                wait = 30 * (attempt + 1)
                print(f"    [限速，等 {wait}s]", end="", flush=True)
                time.sleep(wait)
            elif attempt < retries:
                print(f"    [重试 {attempt+1}] HTTP {e.code}: {body[:80]}")
                time.sleep(5)
            else:
                print(f"    [跳过] HTTP {e.code}: {body[:120]}")
                return "【翻译失败，待补充】"
        except Exception as e:
            if attempt < retries:
                print(f"    [重试 {attempt+1}] {e}")
                time.sleep(5)
            else:
                print(f"    [跳过] {e}")
                return "【翻译失败，待补充】"
    return "【翻译失败，待补充】"


def translate_file(md_path: Path, deployment: str, dry_run: bool = False) -> int:
    content = md_path.read_text(encoding="utf-8")
    sections = list(RE_SECTION.finditer(content))
    untranslated = [s for s in sections if not s.group(4).strip()]

    if not untranslated:
        print(f"  ✓ {md_path.name} — 已全部翻译，跳过")
        return 0

    print(f"  → {md_path.name}：{len(untranslated)}/{len(sections)} 段待翻译")

    translated_count = 0
    for i, match in enumerate(untranslated):
        original_text = match.group(2).strip()
        if not original_text:
            continue

        print(f"    [{i+1}/{len(untranslated)}] {original_text[:40].replace(chr(10),' ')}…",
              end="", flush=True)

        if dry_run:
            translation = "（dry-run）"
        else:
            t0 = time.time()
            translation = call_api(original_text, deployment)
            print(f" ({time.time()-t0:.1f}s)", end="")

        print()

        # 每段翻完立即写回（断点续跑安全）
        if not dry_run:
            current = md_path.read_text(encoding="utf-8")
            old_block = match.group(0)
            new_block = (
                match.group(1)
                + match.group(2)
                + match.group(3)
                + "\n" + translation + "\n"
            )
            current = current.replace(old_block, new_block, 1)
            md_path.write_text(current, encoding="utf-8")
        translated_count += 1

    # 全卷完成后更新状态
    if not dry_run and translated_count > 0:
        final = md_path.read_text(encoding="utf-8")
        if not [s for s in RE_SECTION.finditer(final) if not s.group(4).strip()]:
            final = re.sub(
                r'^translation_status: untranslated',
                'translation_status: translated',
                final, flags=re.MULTILINE
            )
            md_path.write_text(final, encoding="utf-8")
        print(f"    ✓ {md_path.name} 完成（{translated_count} 段）")

    return translated_count


def main():
    parser = argparse.ArgumentParser(description="用 Azure AI 翻译佛经")
    parser.add_argument("target", help="slug 前缀，如 T0002 或 T0002-001")
    parser.add_argument("--model", choices=["deepseek", "kimi"], default=DEFAULT_MODEL,
                        help="使用的模型（默认 deepseek）")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delay", type=float, default=0.5, help="段间延迟秒数")
    args = parser.parse_args()

    deployment = MODELS[args.model]
    pattern = f"{args.target}*.md"
    files = sorted(SUTRAS_DIR.glob(pattern))

    if not files:
        print(f"错误：未找到匹配 {pattern} 的文件")
        sys.exit(1)

    print(f"目标：{len(files)} 个文件，模型：{deployment}")
    if args.dry_run:
        print("[dry-run 模式]\n")

    total = 0
    for f in files:
        count = translate_file(f, deployment, dry_run=args.dry_run)
        total += count
        if count > 0 and not args.dry_run:
            time.sleep(args.delay)

    print(f"\n完成。共翻译 {total} 段。")


if __name__ == "__main__":
    main()
