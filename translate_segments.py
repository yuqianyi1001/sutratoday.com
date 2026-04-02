
import os
import json
import time
from pathlib import Path
import anthropic

# Load environment variables from .env
_env_file = Path('.env')
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

ANYROUTER_API_KEY = os.environ["ANYROUTER_API_KEY"]
ANYROUTER_BASE_URL = os.environ["ANYROUTER_BASE_URL"]
MODEL_ID = "claude-3-5-haiku-20241022"

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

client = anthropic.Anthropic(
    api_key=ANYROUTER_API_KEY,
    base_url=ANYROUTER_BASE_URL,
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
        except Exception as e:
            if attempt < retries:
                print(f"    [重试 {attempt+1}] {e}")
                time.sleep(5)
            else:
                print(f"    [跳过] 多次失败: {e}")
                return "【翻译失败，待补充】"
    return "【翻译失败，待补充】"

def main():
    with open('extracted_segments_011.json', 'r', encoding='utf-8') as f:
        all_segments = json.load(f)
    
    # We want to translate segments 80 to 123 (0-indexed)
    target_segments = all_segments[80:124]
    print(f"Translating {len(target_segments)} segments (80 to 123)...")
    
    translated_segments = []
    for i, seg in enumerate(target_segments):
        print(f"[{i+1}/{len(target_segments)}] {seg[:40]}...")
        translation = call_api(seg)
        translated_segments.append(translation)
        # Small delay to avoid hitting rate limits too hard if any
        time.sleep(0.5)
        
    with open('translated_segments_011_part3.json', 'w', encoding='utf-8') as f:
        json.dump(translated_segments, f, ensure_ascii=False, indent=2)
    print("Saved to translated_segments_011_part3.json")

if __name__ == "__main__":
    main()
