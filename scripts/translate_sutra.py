#!/usr/bin/env python3
"""
translate_sutra.py — 用 LM Studio 本地模型翻译佛经卷文
用法:
  python3 scripts/translate_sutra.py T0001          # 翻译 T0001 全部卷
  python3 scripts/translate_sutra.py T0001-001      # 翻译单卷
  python3 scripts/translate_sutra.py T0001 --dry-run  # 只打印，不写文件
"""

import sys
import re
import time
import argparse
from pathlib import Path
import urllib.request
import urllib.error
import json

# ── 配置 ──────────────────────────────────────────────────────────────────────
LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_ID = "qwen3.5-9b"
SUTRAS_DIR = Path(__file__).parent.parent / "content" / "sutras-raw"

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

def call_lmstudio_stream(text: str, retries: int = 2) -> str:
    """用 streaming 模式调用，收集 content 字段（跳过 reasoning_content）"""
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(text=text.strip())},
            {"role": "assistant", "content": "<think>\n\n</think>\n"},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
        "stream": True,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        LMSTUDIO_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(retries + 1):
        try:
            content_parts = []
            last_chunk_time = time.time()
            CHUNK_TIMEOUT = 60  # 超过60秒无新 token 视为卡死
            with urllib.request.urlopen(req, timeout=30) as resp:
                # streaming: 每行是 "data: {...}" 或 "data: [DONE]"
                for raw_line in resp:
                    if time.time() - last_chunk_time > CHUNK_TIMEOUT:
                        raise TimeoutError("超过60秒无新token，视为卡死")
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    payload_str = line[5:].strip()
                    if payload_str == "[DONE]":
                        break
                    chunk = json.loads(payload_str)
                    delta = chunk["choices"][0].get("delta", {})
                    # 只收集实际 content，跳过 reasoning_content
                    piece = delta.get("content", "")
                    if piece:
                        content_parts.append(piece)
                        last_chunk_time = time.time()
            result = "".join(content_parts).strip()
            if result:
                return result
            # content 为空说明 thinking 用尽了 tokens，抛出让上层处理
            raise ValueError("模型输出内容为空（thinking tokens 耗尽）")
        except (urllib.error.URLError, ValueError, TimeoutError, OSError) as e:
            if attempt < retries:
                print(f"    [重试 {attempt+1}] {e}")
                time.sleep(5)
            else:
                print(f"    [跳过] 多次失败: {e}")
                return "【翻译失败，待补充】"


def translate_file(md_path: Path, dry_run: bool = False) -> int:
    """翻译单个 md 文件，返回翻译的段落数"""
    content = md_path.read_text(encoding="utf-8")

    # 找出所有未翻译的段落（现代语译为空）
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
            translation = "（dry-run，不实际调用）"
        else:
            t0 = time.time()
            translation = call_lmstudio_stream(original_text)
            elapsed = time.time() - t0
            print(f" ({elapsed:.1f}s)", end="")

        print()

        # 每段翻完立即读取最新文件内容，替换后写回（断点续跑安全）
        current = md_path.read_text(encoding="utf-8")
        old_block = match.group(0)
        new_block = (
            match.group(1)          # ### 原文\n
            + match.group(2)        # 原文内容
            + match.group(3)        # \n### 现代语译\n
            + "\n" + translation + "\n"
        )
        current = current.replace(old_block, new_block, 1)
        if not dry_run:
            md_path.write_text(current, encoding="utf-8")
        translated_count += 1

    # 全卷完成后更新 translation_status
    if not dry_run and translated_count > 0:
        final = md_path.read_text(encoding="utf-8")
        # 只有所有段都翻了才标记为 translated
        remaining = [s for s in RE_SECTION.finditer(final) if not s.group(4).strip()]
        if not remaining:
            final = re.sub(
                r'^translation_status: untranslated',
                'translation_status: translated',
                final,
                flags=re.MULTILINE
            )
            md_path.write_text(final, encoding="utf-8")
        print(f"    ✓ {md_path.name} 写入完成（{translated_count} 段）")

    return translated_count


def main():
    parser = argparse.ArgumentParser(description="用 LM Studio 翻译佛经")
    parser.add_argument("target", help="经文 slug 前缀，如 T0001 或 T0001-001")
    parser.add_argument("--dry-run", action="store_true", help="不实际调用 API，只打印流程")
    parser.add_argument("--delay", type=float, default=0.5, help="每段翻译后等待秒数（默认 0.5）")
    args = parser.parse_args()

    # 找目标文件
    pattern = f"{args.target}*.md" if not args.target.endswith(".md") else args.target
    files = sorted(SUTRAS_DIR.glob(pattern))

    if not files:
        print(f"错误：未找到匹配 {pattern} 的文件")
        sys.exit(1)

    print(f"目标：{len(files)} 个文件，模型：{MODEL_ID}")
    if args.dry_run:
        print("[dry-run 模式，不会写入文件]\n")

    total = 0
    for f in files:
        count = translate_file(f, dry_run=args.dry_run)
        total += count
        if count > 0 and not args.dry_run:
            time.sleep(args.delay)

    print(f"\n完成。共翻译 {total} 段。")


if __name__ == "__main__":
    main()
