#!/usr/bin/env python3
"""
anyrouter_translate.py — 用 AnyRouter (Claude API) 翻译佛经
用法:
  python3 scripts/anyrouter_translate.py T0001-004      # 翻译单卷
  python3 scripts/anyrouter_translate.py T0001          # 翻译全部卷
  python3 scripts/anyrouter_translate.py T0001-004 --dry-run
"""

import sys
import re
import time
import argparse
import os
from pathlib import Path
import anthropic

# ── 从 .env 加载环境变量 ───────────────────────────────────────────────────────
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _v = _v.strip().strip('"').strip("'")
            os.environ.setdefault(_k.strip(), _v)

# ── 配置 ──────────────────────────────────────────────────────────────────────
ANYROUTER_API_KEY  = os.environ["ANYROUTER_API_KEY"]
ANYROUTER_BASE_URL = os.environ["ANYROUTER_BASE_URL"]
MODEL_ID           = "claude-3-5-haiku-20241022"   # 可换 claude-3-5-sonnet-20241022
SUTRAS_DIR         = Path(__file__).parent.parent / "content" / "sutras-raw"

SYSTEM_PROMPT = """你是一位精通汉语佛教典籍的学者，擅长将古代佛经文言文翻译成通俗易懂的现代汉语白话文。

翻译原则：
1. 忠实于原文含义，不增不减
2. 用现代汉语表达，流畅自然
3. 保留佛教专有名词（如：比丘、菩萨、涅槃、阿含等），首次出现时可加简短括注
4. 偈颂保持诗歌韵律感，按原文换行
5. 只输出译文，不加任何解释或前言后语
6. 原文是繁体时，翻译也用繁体，原文是简体时，翻译用简体
"""

USER_TEMPLATE = "请将以下佛经原文翻译成现代汉语白话文：\n\n{text}"
# ─────────────────────────────────────────────────────────────────────────────

RE_SECTION = re.compile(
    r'(### 原文\n)(.*?)(\n### 现代语译\n)(.*?)(?=\n### 原文|\Z)',
    re.DOTALL
)

client = anthropic.Anthropic(
    api_key=ANYROUTER_API_KEY,
    base_url=ANYROUTER_BASE_URL,
    default_headers={"user-agent": "claude-code/1.0"},
)


def call_api(text: str, retries: int = 5) -> str:
    for attempt in range(retries + 1):
        try:
            message = client.messages.create(
                model=MODEL_ID,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": USER_TEMPLATE.format(text=text.strip())}
                ],
            )
            return message.content[0].text.strip()
        except anthropic.InternalServerError as e:
            err_str = str(e)
            if "负载" in err_str or "overload" in err_str.lower():
                wait = 10 * (attempt + 1)
                print(f"    [超载，{wait}s 后重试]", end="", flush=True)
                time.sleep(wait)
            elif attempt < retries:
                print(f"    [重试 {attempt+1}] {e}")
                time.sleep(5)
            else:
                print(f"    [跳过] 多次失败: {e}")
                return "【翻译失败，待补充】"
        except Exception as e:
            if attempt < retries:
                print(f"    [重试 {attempt+1}] {e}")
                time.sleep(5)
            else:
                print(f"    [跳过] 多次失败: {e}")
                return "【翻译失败，待补充】"
    return "【翻译失败，待补充】"


def translate_file(md_path: Path, dry_run: bool = False) -> int:
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

        print(f"    [{i+1}/{len(untranslated)}] {original_text[:40].replace(chr(10), ' ')}…", end="", flush=True)

        if dry_run:
            translation = "（dry-run）"
        else:
            t0 = time.time()
            translation = call_api(original_text)
            elapsed = time.time() - t0
            print(f" ({elapsed:.1f}s)", end="")

        print()

        # 每段翻完立即写回文件（断点续跑安全）
        current = md_path.read_text(encoding="utf-8")
        old_block = match.group(0)
        new_block = (
            match.group(1)
            + match.group(2)
            + match.group(3)
            + "\n" + translation + "\n"
        )
        current = current.replace(old_block, new_block, 1)
        if not dry_run:
            md_path.write_text(current, encoding="utf-8")
        translated_count += 1

    # 全卷完成后更新 translation_status
    if not dry_run and translated_count > 0:
        final = md_path.read_text(encoding="utf-8")
        remaining = [s for s in RE_SECTION.finditer(final) if not s.group(4).strip()]
        if not remaining:
            final = re.sub(
                r'^translation_status: untranslated',
                'translation_status: translated',
                final, flags=re.MULTILINE
            )
            md_path.write_text(final, encoding="utf-8")
        print(f"    ✓ {md_path.name} 完成（{translated_count} 段）")

    return translated_count


def main():
    parser = argparse.ArgumentParser(description="用 AnyRouter Claude API 翻译佛经")
    parser.add_argument("target", help="slug 前缀，如 T0001 或 T0001-004")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default=MODEL_ID, help=f"模型 ID（默认 {MODEL_ID}）")
    parser.add_argument("--delay", type=float, default=0.5, help="段间延迟秒数")
    args = parser.parse_args()

    global client
    if args.model != MODEL_ID:
        globals()["MODEL_ID"] = args.model
    client = anthropic.Anthropic(
        api_key=ANYROUTER_API_KEY,
        base_url=ANYROUTER_BASE_URL,
        default_headers={"user-agent": "claude-code/1.0"},
    )

    pattern = f"{args.target}*.md"
    files = sorted(SUTRAS_DIR.glob(pattern))
    if not files:
        print(f"错误：未找到匹配 {pattern} 的文件")
        sys.exit(1)

    print(f"目标：{len(files)} 个文件，模型：{MODEL_ID}")
    if args.dry_run:
        print("[dry-run 模式]\n")

    total = 0
    for f in files:
        count = translate_file(f, dry_run=args.dry_run)
        total += count
        if count > 0 and not args.dry_run:
            time.sleep(args.delay)

    print(f"\n完成。共翻译 {total} 段。")


if __name__ == "__main__":
    main()
