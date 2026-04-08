#!/usr/bin/env python3
"""
agent_worker.py — 通用翻译 Worker，从任务队列抢占任务并批量翻译

用法:
  python3 scripts/agent_worker.py --backend azure              # Azure DeepSeek（默认）
  python3 scripts/agent_worker.py --backend azure --model Kimi-K2.5
  python3 scripts/agent_worker.py --backend lmstudio           # 本地 LM Studio
  python3 scripts/agent_worker.py --backend anyrouter          # AnyRouter Claude
  python3 scripts/agent_worker.py --backend gemini             # Gemini CLI
  python3 scripts/agent_worker.py --backend gemini --model gemini-2.5-pro
  python3 scripts/agent_worker.py --backend azure --slug T0003-001   # 只翻指定卷
  python3 scripts/agent_worker.py --backend azure --limit 5          # 最多翻 5 卷
  python3 scripts/agent_worker.py --backend azure --batch-size 10    # 每批 10 段
  python3 scripts/agent_worker.py --backend azure --batch-size 1     # 禁用批量（逐段）
  python3 scripts/agent_worker.py --backend groq                     # Groq qwen/qwen3-32b（默认）
  python3 scripts/agent_worker.py --backend groq --model llama-3.3-70b-versatile
  python3 scripts/agent_worker.py --backend dashscope                # 百炼 qwen3.5-plus（默认）
  python3 scripts/agent_worker.py --backend dashscope --model qwen3.5-flash
  python3 scripts/agent_worker.py --backend dashscope --model qwen3-max
"""

import sys
import re
import os
import json
import time
import uuid
import signal
import argparse
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import job_queue

# ── 从 .env 加载环境变量 ───────────────────────────────────────────────────────
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _v = _v.strip().strip('"').strip("'")
            os.environ.setdefault(_k.strip(), _v)

# ── Telegram 通知 ─────────────────────────────────────────────────────────────

def send_telegram(message: str) -> bool:
    """发送 Telegram 消息，失败时静默返回 False。"""
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return False
    try:
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id":    chat_id,
            "text":       message,
            "parse_mode": "HTML",
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"  [Telegram] 发送失败: {e}")
        return False


def _sutra_title_from_md(md_path: Path) -> str:
    """从 MD frontmatter 读取 title，读不到则返回空串。"""
    try:
        text = md_path.read_text(encoding="utf-8")
        m = re.search(r'^title:\s*(.+)$', text, re.MULTILINE)
        return m.group(1).strip() if m else ""
    except Exception:
        return ""


def notify_sutra_done(slug: str, md_path: Path, full_model: str):
    """检查部经是否全部完成，若是则发 Telegram 通知。"""
    info = job_queue.check_sutra_complete(slug)
    if not info:
        return
    title    = _sutra_title_from_md(md_path) or info["cbeta_id"]
    cbeta_id = info["cbeta_id"]
    category = info["category"]
    vol_total = info["vol_total"]
    seg_total = info["seg_total"]
    model_tag = full_model or info["full_model"] or "unknown"
    # 查询整体翻译进度
    progress = job_queue.get_progress()
    total_vols   = progress["total"]
    done_vols    = progress["done"]
    remain_vols  = progress["pending"] + progress["running"]
    remain_segs  = progress["remaining_segs"]
    pct          = done_vols * 100 / total_vols if total_vols else 0
    # 估算剩余时间：用最近2小时速率
    eta_str = ""
    rate_2h = progress.get("rate_2h", 0)
    if rate_2h > 0 and remain_segs > 0:
        hours_left = remain_segs / rate_2h
        if hours_left < 1:
            eta_str = f"⏱ 预计 {hours_left*60:.0f} 分钟后完成"
        else:
            eta_str = f"⏱ 预计 {hours_left:.1f} 小时后完成"

    msg = (
        f"🪷 <b>今文佛典</b> · 部经完成\n\n"
        f"📖 <b>{title}</b>\n"
        f"🔖 {cbeta_id}  ·  {category}\n"
        f"📚 {vol_total} 卷  ·  {seg_total} 段\n"
        f"🤖 {model_tag}\n\n"
        f"📊 总进度: {done_vols}/{total_vols}（{pct:.1f}%）\n"
        f"📝 剩余: {remain_vols} 卷 · {remain_segs} 段"
    )
    if eta_str:
        msg += f"\n{eta_str}"
    ok = send_telegram(msg)
    if ok:
        print(f"  [Telegram] ✓ 已通知完成: {cbeta_id} {title}")


# ── 翻译 Prompt ────────────────────────────────────────────────────────────────

# 单段翻译 system prompt
SYSTEM_PROMPT = """你是一位精通汉语佛教典籍的学者，擅长将古代佛经文言文翻译成通俗易懂的现代汉语白话文。

翻译原则：
1. 忠实于原文含义，不增不减
2. 用现代汉语表达，流畅自然
3. 保留佛教专有名词（如：比丘、菩萨、涅槃、阿含等），首次出现时可加简短括注
4. 偈颂保持诗歌韵律感，按原文换行
5. 只输出译文，不加任何解释或前言后语
6. 始終用繁體輸出翻譯。"""

# 批量翻译 system prompt
BATCH_SYSTEM_PROMPT = """你是一位精通汉语佛教典籍的学者，擅长将古代佛经文言文翻译成通俗易懂的现代汉语白话文。

翻译原则：
1. 忠实于原文含义，不增不减
2. 用现代汉语表达，流畅自然
3. 保留佛教专有名词（如：比丘、菩萨、涅槃、阿含等），首次出现时可加简短括注
4. 偈颂保持诗歌韵律感，按原文换行
5. 始終用繁體輸出翻譯。

任务：你将收到一个 JSON 数组，每项格式为 {"id": N, "text": "佛经原文"}。
请将每段分别翻译，以相同结构返回 [{"id": N, "translation": "现代汉语译文"}, ...]。
只输出 JSON 数组，不加任何前言后语。"""

RE_SECTION = re.compile(
    r'(### 原文\n(?:<!-- sid:(\d{3}) -->\n)?)(.*?)(\n### (?:现代语译|現代語譯)\n(?:<!-- sid:\d{3} -->\n)?)(.*?)(?=\n### 原文|\Z)',
    re.DOTALL
)

# ── 规范化模型全名 ─────────────────────────────────────────────────────────────
_CANONICAL = {
    ("azure",      "DeepSeek-V3.2"):                         "azure-deepseek-v3.2",
    ("azure",      "Kimi-K2.5"):                             "azure-kimi-k2.5",
    ("azure",      "grok-4-1-fast-reasoning"):               "azure-grok-4.1-fast",
    ("azure2",     "gpt-5.3-chat"):                          "azure2-gpt-5.3",
    ("azure2",     "gpt-5.4-mini"):                          "azure2-gpt-5.4-mini",
    ("lmstudio",   "qwen3.5-9b"):                            "lmstudio-qwen3.5-9b",
    ("anyrouter",  "claude-3-5-haiku-20241022"):             "anyrouter-claude-3.5-haiku",
    ("anyrouter",  "claude-3-5-sonnet-20241022"):            "anyrouter-claude-3.5-sonnet",
    ("anyrouter",  "claude-3-opus-20240229"):                "anyrouter-claude-3-opus",
    ("gemini",     "gemini-2.5-flash"):                      "gemini-2.5-flash",
    ("gemini",     "gemini-2.5-pro"):                        "gemini-2.5-pro",
    ("gemini",     "flash-nothink"):                         "gemini-2.5-flash-nothink",
    ("gemini",     "pro-nothink"):                           "gemini-2.5-pro-nothink",
    ("openrouter", "qwen/qwen3.6-plus-preview:free"):        "openrouter-qwen3.6-plus",
    ("openrouter", "qwen/qwen3-coder:free"):                 "openrouter-qwen3-coder",
    ("openrouter", "qwen/qwen3-next-80b-a3b-instruct:free"): "openrouter-qwen3-next-80b",
    ("openrouter", "qwen/qwen3-235b-a22b"):                  "openrouter-qwen3-235b",
    ("openrouter", "qwen/qwen3-32b"):                        "openrouter-qwen3-32b",
    ("nvidia",     "deepseek-ai/deepseek-v3.2"):             "nvidia-deepseek-v3.2",
    ("nvidia",     "meta/llama-3.3-70b-instruct"):           "nvidia-llama-3.3-70b",
    ("nvidia",     "mistralai/mistral-large-2-instruct"):    "nvidia-mistral-large-2",
    ("groq",       "qwen/qwen3-32b"):                        "groq-qwen3-32b",
    ("groq",       "llama-3.3-70b-versatile"):               "groq-llama3.3-70b",
    ("groq",       "llama3-70b-8192"):                       "groq-llama3-70b",
    ("groq",       "mixtral-8x7b-32768"):                    "groq-mixtral-8x7b",
    ("groq",       "gemma2-9b-it"):                          "groq-gemma2-9b",
    ("dashscope",  "qwen3.5-flash"):                         "dashscope-qwen3.5-flash",
    ("dashscope",  "qwen3.5-plus"):                          "dashscope-qwen3.5-plus",
    ("dashscope",  "qwen3-max"):                             "dashscope-qwen3-max",
    ("dashscope",  "qwen3.6-plus-2026-04-02"):               "dashscope-qwen3.6-plus",
    ("dashscope",  "qwen3.5-27b"):                           "dashscope-qwen3.5-27b",
    ("dashscope",  "glm-5"):                                 "dashscope-glm-5",
    ("dashscope",  "qwen3.5-122b-a10b"):                     "dashscope-qwen3.5-122b",
    ("dashscope",  "qwen3.5-35b-a3b"):                       "dashscope-qwen3.5-35b",
    ("dashscope",  "qwen3.5-plus-2026-02-15"):               "dashscope-qwen3.5-plus-0215",
    ("dashscope",  "kimi-k2.5"):                             "dashscope-kimi-k2.5",
    ("dashscope",  "MiniMax-M2.1"):                          "dashscope-minimax-m2.1",
    ("dashscope",  "qwen3-max-2026-01-23"):                  "dashscope-qwen3-max-0123",
    ("codex",      "gpt-5.4"):                              "codex-gpt-5.4",
    ("codex",      "gpt-5.4-mini"):                         "codex-gpt-5.4-mini",
}

def canonical_model(backend: str, model: str) -> str:
    """返回规范化模型全名，例如 azure-deepseek-v3.2 / gemini-2.5-flash"""
    key = (backend, model)
    if key in _CANONICAL:
        return _CANONICAL[key]
    # 通用规则：backend-model，清理特殊字符
    name = f"{backend}-{model}".lower()
    name = re.sub(r'[/:@]', '-', name)
    name = re.sub(r':free$|-free$', '', name)
    name = re.sub(r'-{2,}', '-', name).strip('-')
    return name

# ── 优雅退出 ───────────────────────────────────────────────────────────────────
_shutdown = False

def _handle_signal(sig, frame):
    global _shutdown
    print("\n[收到终止信号，完成当前批次后退出...]")
    _shutdown = True

signal.signal(signal.SIGINT,  _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ═══════════════════════════════════════════════════════════════════════════════
# 底层 Backend 实现（统一接受 messages list，便于批量和单段复用）
# ═══════════════════════════════════════════════════════════════════════════════

def _azure_call_base(messages: list, model: str, endpoint: str, key: str,
                     max_tokens: int = 4096, retries: int = 3) -> str:
    import urllib.error
    url = (f"{endpoint.rstrip('/')}/openai/deployments/{model}/chat/completions"
           f"?api-version=2024-12-01-preview")

    payload = json.dumps({
        "messages":   messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
        headers={"Content-Type": "application/json", "api-key": key}, method="POST")

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                msg = json.loads(resp.read())["choices"][0]["message"]
                # 推理模型（Kimi-K2.5 等）final answer 在 content，
                # 若 content 为 null 则兜底用 reasoning_content
                return (msg.get("content") or msg.get("reasoning_content") or "").strip()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f" [限速等{wait}s]", end="", flush=True)
                time.sleep(wait)
            elif attempt < retries:
                print(f" [重试{attempt+1}]", end="", flush=True)
                time.sleep(5)
            else:
                return f"【翻译失败: HTTP {e.code}】"
        except Exception as e:
            if attempt < retries:
                time.sleep(5)
            else:
                return f"【翻译失败: {e}】"
    return "【翻译失败，待补充】"


def _azure_call(messages: list, model: str, max_tokens: int = 4096, retries: int = 3) -> str:
    return _azure_call_base(messages, model,
                            os.environ["AZURE_ENDPOINT"], os.environ["AZURE_API_KEY"],
                            max_tokens, retries)


def _azure2_call(messages: list, model: str, max_tokens: int = 4096, retries: int = 3) -> str:
    """Azure AI #2（GPT-5系列），使用 max_completion_tokens 参数。"""
    import urllib.error
    endpoint = os.environ["AZURE2_ENDPOINT"]
    key      = os.environ["AZURE2_API_KEY"]
    url = (f"{endpoint.rstrip('/')}/openai/deployments/{model}/chat/completions"
           f"?api-version=2024-12-01-preview")
    payload = json.dumps({
        "messages":              messages,
        "max_completion_tokens": max_tokens,
        # GPT-5 系列不支持自定义 temperature，使用默认值
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
        headers={"Content-Type": "application/json", "api-key": key}, method="POST")
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f" [限速等{wait}s]", end="", flush=True)
                time.sleep(wait)
            elif attempt < retries:
                print(f" [重试{attempt+1}]", end="", flush=True)
                time.sleep(5)
            else:
                return f"【翻译失败: HTTP {e.code}】"
        except Exception as e:
            if attempt < retries:
                time.sleep(5)
            else:
                return f"【翻译失败: {e}】"
    return "【翻译失败，待补充】"


def _lmstudio_call(messages: list, model: str, max_tokens: int = 8192, retries: int = 2) -> str:
    import urllib.request

    url = os.environ.get("LMSTUDIO_URL", "http://localhost:1234/v1/chat/completions")
    # 注入空 think 块，抑制 Qwen thinking 模式
    msgs = messages + [{"role": "assistant", "content": "<think>\n\n</think>\n"}]
    payload = json.dumps({
        "model":       model,
        "messages":    msgs,
        "temperature": 0.3,
        "max_tokens":  max_tokens,
        "stream":      True,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")

    for attempt in range(retries + 1):
        try:
            parts = []
            last_chunk = time.time()
            with urllib.request.urlopen(req, timeout=30) as resp:
                for raw in resp:
                    if time.time() - last_chunk > 60:
                        raise TimeoutError("60s 无新 token")
                    line = raw.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    ps = line[5:].strip()
                    if ps == "[DONE]":
                        break
                    chunk = json.loads(ps)
                    piece = chunk["choices"][0].get("delta", {}).get("content", "")
                    if piece:
                        parts.append(piece)
                        last_chunk = time.time()
            result = "".join(parts).strip()
            if result:
                return result
            raise ValueError("content 为空")
        except Exception as e:
            if attempt < retries:
                print(f" [重试{attempt+1}]", end="", flush=True)
                time.sleep(5)
            else:
                return "【翻译失败，待补充】"
    return "【翻译失败，待补充】"


def _anyrouter_call(messages: list, model: str, max_tokens: int = 4096, retries: int = 5) -> str:
    try:
        import anthropic
    except ImportError:
        return "【翻译失败: 需要安装 anthropic 库】"

    # Anthropic SDK 要求 system 单独传，不放在 messages 里
    system_content = None
    user_messages  = []
    for m in messages:
        if m["role"] == "system":
            system_content = m["content"]
        else:
            user_messages.append(m)

    client = anthropic.Anthropic(
        api_key=os.environ["ANYROUTER_API_KEY"],
        base_url=os.environ["ANYROUTER_BASE_URL"],
        default_headers={"user-agent": "claude-code/1.0"},
    )
    kwargs = dict(model=model, max_tokens=max_tokens, messages=user_messages)
    if system_content:
        kwargs["system"] = system_content

    for attempt in range(retries + 1):
        try:
            msg = client.messages.create(**kwargs)
            return msg.content[0].text.strip()
        except Exception as e:
            err = str(e).lower()
            if "负载" in err or "overloaded" in err:
                wait = 10 * (attempt + 1)
                print(f" [超载等{wait}s]", end="", flush=True)
                time.sleep(wait)
            elif attempt < retries:
                time.sleep(5)
            else:
                return f"【翻译失败: {e}】"
    return "【翻译失败，待补充】"


# ════════════════════════════════════════════════════════════════════════════
# Backend: OpenRouter（OpenAI 兼容接口，支持 qwen3.6-plus:free 等）
# ════════════════════════════════════════════════════════════════════════════

def _nvidia_call(messages: list, model: str, max_tokens: int = 4096, retries: int = 3) -> str:
    """NVIDIA NIM API（OpenAI 兼容接口）"""
    import urllib.request, urllib.error

    key      = os.environ.get("NVIDIA_API_KEY", "")
    base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    url      = f"{base_url}/chat/completions"

    payload = json.dumps({
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST",
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {key}",
        })

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result  = json.loads(resp.read())
                content = (result["choices"][0]["message"].get("content") or "").strip()
                if content:
                    return content
                raise ValueError("content 为空")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f" [限速等{wait}s]", end="", flush=True)
                time.sleep(wait)
            elif attempt < retries:
                print(f" [重试{attempt+1} HTTP{e.code}]", end="", flush=True)
                time.sleep(5)
            else:
                return f"【翻译失败: HTTP {e.code} {body[:100]}】"
        except Exception as e:
            if attempt < retries:
                time.sleep(5)
            else:
                return f"【翻译失败: {e}】"
    return "【翻译失败，待补充】"


def _openrouter_call(messages: list, model: str, max_tokens: int = 4096, retries: int = 3) -> str:
    import urllib.request, urllib.error

    key = os.environ["OPEN_ROUTER_KEY"]
    url = "https://openrouter.ai/api/v1/chat/completions"

    # Qwen3 系列是混合思考模型，翻译任务不需要 thinking，关闭以节省 token 和时间
    payload = json.dumps({
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": 0.3,
        "enable_thinking": False,   # Qwen3 thinking 开关
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST",
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {key}",
            "HTTP-Referer":  "https://github.com/sutratoday",
            "X-Title":       "SutraToday",
        })

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                content = result["choices"][0]["message"]["content"] or ""
                # 过滤掉可能残留的 <think>...</think> 块
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                if content:
                    return content
                raise ValueError("content 为空")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f" [限速等{wait}s]", end="", flush=True)
                time.sleep(wait)
            elif e.code in (502, 503):
                wait = 10 * (attempt + 1)
                print(f" [服务器忙等{wait}s]", end="", flush=True)
                time.sleep(wait)
            elif attempt < retries:
                print(f" [重试{attempt+1} HTTP{e.code}]", end="", flush=True)
                time.sleep(5)
            else:
                return f"【翻译失败: HTTP {e.code} {body[:100]}】"
        except Exception as e:
            if attempt < retries:
                time.sleep(5)
            else:
                return f"【翻译失败: {e}】"
    return "【翻译失败，待补充】"


# ════════════════════════════════════════════════════════════════════════════
# Backend: Groq（OpenAI 兼容接口，支持 qwen/qwen3-32b 等）
# ════════════════════════════════════════════════════════════════════════════

def _groq_call(messages: list, model: str, max_tokens: int = 4096, retries: int = 3) -> str:
    """Groq Cloud API（OpenAI 兼容接口）。
    Qwen3 系列是混合思考模型，翻译任务不需要 thinking，
    通过注入空 think 块来抑制，兼容性好于 enable_thinking 参数。
    注意：用 requests 库而非 urllib，避免 Cloudflare 对 urllib TLS 指纹的 bot 检测（error 1010）。
    """
    import requests as _requests

    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return "【翻译失败: 未设置 GROQ_API_KEY】"

    url = "https://api.groq.com/openai/v1/chat/completions"

    # Qwen3 系列：注入空 think 块抑制 thinking 模式，节省 token
    is_qwen3 = "qwen3" in model.lower()
    if is_qwen3:
        messages = list(messages) + [
            {"role": "assistant", "content": "<think>\n\n</think>\n"}
        ]

    payload = {
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": 0.3,
    }
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {key}",
    }

    for attempt in range(retries + 1):
        try:
            resp = _requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.ok:
                result  = resp.json()
                content = (result["choices"][0]["message"].get("content") or "").strip()
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                if content:
                    return content
                raise ValueError("content 为空")
            code = resp.status_code
            body = resp.text
            if code == 429:
                wait = 30 * (attempt + 1)
                print(f" [限速等{wait}s]", end="", flush=True)
                time.sleep(wait)
            elif code in (502, 503):
                wait = 10 * (attempt + 1)
                print(f" [服务器忙等{wait}s]", end="", flush=True)
                time.sleep(wait)
            elif attempt < retries:
                print(f" [重试{attempt+1} HTTP{code}]", end="", flush=True)
                time.sleep(5)
            else:
                return f"【翻译失败: HTTP {code} {body[:100]}】"
        except Exception as e:
            if attempt < retries:
                time.sleep(5)
            else:
                return f"【翻译失败: {e}】"
    return "【翻译失败，待补充】"


# ════════════════════════════════════════════════════════════════════════════
# Backend: 百炼 DashScope（OpenAI 兼容接口，qwen3.5-flash/plus, qwen3-max 等）
# ════════════════════════════════════════════════════════════════════════════

def _dashscope_call(messages: list, model: str, max_tokens: int = 4096, retries: int = 3) -> str:
    """阿里云百炼 DashScope API（OpenAI 兼容接口）。
    Qwen3/Qwen3.5 系列为混合思考模型，翻译任务通过 enable_thinking=False 关闭。
    """
    import urllib.request, urllib.error

    key      = os.environ.get("DASHSCOPE_API_KEY", "")
    base_url = os.environ.get("DASHSCOPE_OPENAI_BASE_URL",
                              "https://dashscope.aliyuncs.com/compatible-mode/v1")
    if not key:
        return "【翻译失败: 未设置 DASHSCOPE_API_KEY】"

    url = f"{base_url.rstrip('/')}/chat/completions"

    body = {
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": 0.3,
    }
    # 只对 Qwen 系列关闭 thinking，其他模型不支持此参数
    if "qwen" in model.lower():
        body["enable_thinking"] = False
    payload = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST",
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {key}",
        })

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result  = json.loads(resp.read())
                content = (result["choices"][0]["message"].get("content") or "").strip()
                # 过滤掉可能残留的 <think>...</think> 块
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                if content:
                    return content
                raise ValueError("content 为空")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f" [限速等{wait}s]", end="", flush=True)
                time.sleep(wait)
            elif e.code in (500, 502, 503):
                wait = 10 * (attempt + 1)
                print(f" [服务器忙等{wait}s]", end="", flush=True)
                time.sleep(wait)
            elif attempt < retries:
                print(f" [重试{attempt+1} HTTP{e.code}]", end="", flush=True)
                time.sleep(5)
            else:
                return f"【翻译失败: HTTP {e.code} {body[:100]}】"
        except Exception as e:
            if attempt < retries:
                time.sleep(5)
            else:
                return f"【翻译失败: {e}】"
    return "【翻译失败，待补充】"


# ════════════════════════════════════════════════════════════════════════════
# Backend: Gemini CLI（子进程调用，支持批量 JSON 翻译）
# ════════════════════════════════════════════════════════════════════════════

def _gemini_call(messages: list, model: str, max_tokens: int = 8192, retries: int = 3) -> str:
    """
    通过 Gemini CLI 子进程翻译。
    - 合并 system+user 消息为单一 prompt
    - 使用 -o json 获取干净的 JSON 输出，取 data["response"]
    """
    gemini_bin = os.environ.get("GEMINI_CLI_PATH", "/opt/homebrew/bin/gemini")
    node_bin   = os.environ.get("GEMINI_NODE_PATH", "/opt/homebrew/opt/nodejs/bin")
    env = {**os.environ, "PATH": f"{node_bin}:{os.environ.get('PATH', '')}"}

    # 合并 system + user 内容为单一 prompt
    parts = [m["content"] for m in messages if m["role"] in ("system", "user")]
    prompt = "\n\n".join(parts)

    cmd = [gemini_bin, "-p", prompt, "--approval-mode", "plan", "-o", "json"]
    if model:
        cmd += ["-m", model]

    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, env=env
            )
            if result.returncode != 0:
                stderr = result.stderr[:500]
                # 配额/限速错误：长等待后重试
                if "QuotaError" in stderr or "TerminalQuota" in stderr or "429" in stderr:
                    wait = 60 * (attempt + 1)
                    print(f" [配额限制，等{wait}s]", end="", flush=True)
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"exit {result.returncode}: {stderr[:300]}")
            data = json.loads(result.stdout)
            response = data.get("response", "").strip()
            if response:
                return response
            raise ValueError("response 为空")
        except Exception as e:
            if attempt < retries:
                print(f" [重试{attempt+1}: {e}]", end="", flush=True)
                time.sleep(5)
            else:
                return f"【翻译失败: {e}】"
    return "【翻译失败，待补充】"


# ════════════════════════════════════════════════════════════════════════════
# Backend: Codex CLI（子进程调用，read-only sandbox，纯文本输出）
# ════════════════════════════════════════════════════════════════════════════

def _codex_call(messages: list, model: str, max_tokens: int = 8192, retries: int = 3) -> str:
    """
    通过 Codex CLI 子进程翻译。
    - 使用 codex exec --sandbox read-only 禁止一切写操作
    - --ephemeral 不持久化会话
    - --skip-git-repo-check 不依赖 git
    - -o tempfile 获取纯文本输出
    """
    codex_bin = os.environ.get("CODEX_CLI_PATH", "/opt/homebrew/bin/codex")
    env = {**os.environ, "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"}

    # 合并 system + user 内容为单一 prompt
    parts = [m["content"] for m in messages if m["role"] in ("system", "user")]
    prompt = "\n\n".join(parts)

    import tempfile
    for attempt in range(retries + 1):
        tmp_out = None
        try:
            tmp_out = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
            tmp_out.close()

            cmd = [
                codex_bin, "exec", prompt,
                "--sandbox", "read-only",
                "--ephemeral",
                "--skip-git-repo-check",
                "-c", 'model_reasoning_effort="low"',
                "-o", tmp_out.name,
            ]
            if model:
                cmd += ["-m", model]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, env=env,
                stdin=subprocess.DEVNULL,
            )
            if result.returncode != 0:
                raise RuntimeError(f"exit {result.returncode}: {result.stderr[:300]}")
            response = Path(tmp_out.name).read_text(encoding="utf-8").strip()
            # 过滤 Codex CLI 可能混入的日志头
            response = re.sub(
                r'(?:OpenAI Codex v[\d.]+.*?session id: [^\n]*\n?)',
                '', response, flags=re.DOTALL).strip()
            response = re.sub(
                r'(?:Reading additional input from stdin[^\n]*\n?)',
                '', response).strip()
            response = re.sub(r'^tokens used\n[\d,]+\n?', '', response, flags=re.MULTILINE).strip()
            if response and 'OpenAI Codex' not in response:
                return response
            raise ValueError("output 为空或含 CLI 日志")
        except Exception as e:
            if attempt < retries:
                print(f" [重试{attempt+1}: {e}]", end="", flush=True)
                time.sleep(5)
            else:
                return f"【翻译失败: {e}】"
        finally:
            if tmp_out and Path(tmp_out.name).exists():
                Path(tmp_out.name).unlink(missing_ok=True)
    return "【翻译失败，待补充】"


# ═══════════════════════════════════════════════════════════════════════════════
# 单段翻译包装（给外部直接调用 / 批量回退使用）
# ═══════════════════════════════════════════════════════════════════════════════

def _single_messages(text: str) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"请将以下佛经原文翻译成现代汉语白话文：\n\n{text.strip()}"},
    ]

def call_azure(text: str, model: str, retries: int = 3) -> str:
    return _azure_call(_single_messages(text), model, max_tokens=4096, retries=retries)

def call_azure2(text: str, model: str, retries: int = 3) -> str:
    return _azure2_call(_single_messages(text), model, max_tokens=4096, retries=retries)

def call_lmstudio(text: str, model: str, retries: int = 2) -> str:
    return _lmstudio_call(_single_messages(text), model, max_tokens=8192, retries=retries)

def call_anyrouter(text: str, model: str, retries: int = 5) -> str:
    return _anyrouter_call(_single_messages(text), model, max_tokens=4096, retries=retries)

def call_gemini(text: str, model: str, retries: int = 3) -> str:
    return _gemini_call(_single_messages(text), model, retries=retries)

def call_nvidia(text: str, model: str, retries: int = 3) -> str:
    return _nvidia_call(_single_messages(text), model, retries=retries)

def call_openrouter(text: str, model: str, retries: int = 3) -> str:
    return _openrouter_call(_single_messages(text), model, retries=retries)

def call_groq(text: str, model: str, retries: int = 3) -> str:
    return _groq_call(_single_messages(text), model, retries=retries)

def call_dashscope(text: str, model: str, retries: int = 3) -> str:
    return _dashscope_call(_single_messages(text), model, retries=retries)

def call_codex(text: str, model: str, retries: int = 3) -> str:
    return _codex_call(_single_messages(text), model, retries=retries)


BACKENDS = {
    "azure":     {"call": call_azure,     "raw": _azure_call,
                  "default_model": "DeepSeek-V3.2"},
    "azure2":    {"call": call_azure2,    "raw": _azure2_call,
                  "default_model": os.environ.get("AZURE2_DEFAULT_MODEL", "gpt-5.3-chat")},
    "lmstudio":  {"call": call_lmstudio,  "raw": _lmstudio_call,
                  "default_model": os.environ.get("LMSTUDIO_MODEL", "qwen3.5-9b")},
    "anyrouter": {"call": call_anyrouter, "raw": _anyrouter_call,
                  "default_model": "claude-3-5-haiku-20241022"},
    "gemini":      {"call": call_gemini,      "raw": _gemini_call,
                    "default_model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                    "force_batch_size": 1},
    "openrouter":  {"call": call_openrouter,  "raw": _openrouter_call,
                    "default_model": os.environ.get("OPENROUTER_MODEL", "qwen/qwen3.6-plus-preview:free")},
    "nvidia":      {"call": call_nvidia,      "raw": _nvidia_call,
                    "default_model": os.environ.get("NVIDIA_DEFAULT_MODEL", "deepseek-ai/deepseek-v3.2")},
    "groq":        {"call": call_groq,        "raw": _groq_call,
                    "default_model": "qwen/qwen3-32b"},
    "dashscope":   {"call": call_dashscope,   "raw": _dashscope_call,
                    "default_model": "qwen3.5-plus"},
    "codex":       {"call": call_codex,       "raw": _codex_call,
                    "default_model": os.environ.get("CODEX_DEFAULT_MODEL", "gpt-5.4"),
                    "force_batch_size": 1},
}


# ═══════════════════════════════════════════════════════════════════════════════
# 批量翻译核心
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_json_array(text: str):
    """从 LLM 响应中提取第一个完整 JSON 数组，容忍前后多余文字"""
    start = text.find('[')
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except Exception:
                    return None
    return None


def _translate_batch(segs: list, raw_fn, model: str) -> dict:
    """
    批量翻译。
    segs:  [{"id": int, "text": str}, ...]
    返回:  {id: translation_str}  ── 失败的 id 不在结果里，调用方自行回退。
    """
    batch_input = json.dumps(segs, ensure_ascii=False, indent=2)
    messages = [
        {"role": "system", "content": BATCH_SYSTEM_PROMPT},
        {"role": "user",   "content": batch_input},
    ]
    max_tok = min(max(4096, len(segs) * 1200), 16000)
    raw = raw_fn(messages, model, max_tokens=max_tok)

    arr = _extract_json_array(raw)
    if not arr or not isinstance(arr, list):
        return {}

    result = {}
    for item in arr:
        if isinstance(item, dict) and "id" in item and "translation" in item:
            result[int(item["id"])] = str(item["translation"]).strip()
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 翻译单个文件
# ═══════════════════════════════════════════════════════════════════════════════

def translate_file(md_path: Path, backend_key: str, model: str,
                   slug: str, agent_id: str, batch_size: int = 5,
                   full_model: str = "") -> tuple:
    """
    翻译单个文件的所有未翻译段落。
    - batch_size > 1: 先尝试批量，失败时逐段回退。
    - 每批只写一次文件（减少磁盘 IO）。
    返回 (seg_done, seg_total)。
    """
    cfg     = BACKENDS[backend_key]
    call_fn = cfg["call"]   # 单段: call_fn(text, model) -> str
    raw_fn  = cfg["raw"]    # 底层: raw_fn(messages, model, max_tokens) -> str

    content      = md_path.read_text(encoding="utf-8")
    sections     = list(RE_SECTION.finditer(content))
    # group 索引: 1=原文头(含sid), 2=sid号, 3=原文, 4=译文头(含sid), 5=译文
    untranslated = [s for s in sections if not s.group(5).strip()]
    seg_done_base = len(sections) - len(untranslated)

    print(f"  → {md_path.name}: {len(untranslated)}/{len(sections)} 段待翻译  "
          f"[batch={batch_size}, 预计{-(-len(untranslated)//batch_size)}次请求]")

    i = 0
    while i < len(untranslated) and not _shutdown:
        batch = untranslated[i : i + batch_size]

        # 筛出有内容的段（id = 在 batch 内的位置索引）
        segs = [{"id": j, "text": m.group(3).strip()}
                for j, m in enumerate(batch) if m.group(3).strip()]

        if not segs:
            i += len(batch)
            continue

        label = f"{i+1}~{i+len(batch)}/{len(untranslated)}"
        print(f"    [{label}] {len(segs)}段", end="", flush=True)
        t0 = time.time()

        # ── 1. 批量翻译 ──────────────────────────────────────────────────────
        translations: dict = {}
        if batch_size > 1 and len(segs) > 1:
            translations = _translate_batch(segs, raw_fn, model)
            missing = len(segs) - len(translations)
            if missing > 0:
                print(f" [缺{missing}项→逐段补]", end="", flush=True)

        # ── 2. 对缺失项逐段回退 ──────────────────────────────────────────────
        for seg in segs:
            if seg["id"] not in translations:
                translations[seg["id"]] = call_fn(seg["text"], model)

        elapsed = time.time() - t0
        print(f" ({elapsed:.1f}s)")

        # ── 3. 用 sid 精确匹配写回 ──────────────────────────────────────────
        current = md_path.read_text(encoding="utf-8")
        for j, orig_match in enumerate(batch):
            trans = translations.get(j)
            if trans is None:
                continue
            sid = orig_match.group(2)  # sid 编号，如 "001"
            if sid:
                # 有 sid：用 sid 精确定位
                pattern = re.compile(
                    r'(### 原文\n<!-- sid:' + re.escape(sid) + r' -->\n)'
                    r'(.*?)'
                    r'(\n### (?:现代语译|現代語譯)\n<!-- sid:' + re.escape(sid) + r' -->\n)'
                    r'(.*?)'
                    r'(?=\n### 原文|\Z)',
                    re.DOTALL
                )
                m = pattern.search(current)
                if m:
                    new_block = m.group(1) + m.group(2) + m.group(3) + "\n" + trans + "\n"
                    current = current[:m.start()] + new_block + current[m.end():]
            else:
                # 无 sid（旧文件）：回退到按原文内容匹配空段
                cur_sections = list(RE_SECTION.finditer(current))
                cur_empty = [s for s in cur_sections if not s.group(5).strip()]
                orig_text = orig_match.group(3).strip()
                for cm in cur_empty:
                    if cm.group(3).strip() == orig_text:
                        new_block = (cm.group(1) + cm.group(3) + cm.group(4)
                                     + "\n" + trans + "\n")
                        current = current[:cm.start()] + new_block + current[cm.end():]
                        break
        md_path.write_text(current, encoding="utf-8")

        i += len(batch)
        job_queue.heartbeat(slug, agent_id, seg_done=seg_done_base + i)

    # ── 全卷完成：更新 frontmatter ────────────────────────────────────────────
    if not _shutdown:
        final = md_path.read_text(encoding="utf-8")
        remaining = [s for s in RE_SECTION.finditer(final) if not s.group(5).strip()]
        if not remaining:
            final = re.sub(r'^translation_status: \w+',
                           'translation_status: translated', final, flags=re.MULTILINE)
            # 写入或更新 ai_translator 为规范全名
            label = full_model or model
            if "ai_translator:" in final:
                final = re.sub(r'^ai_translator:.*$', f'ai_translator: {label}',
                               final, flags=re.MULTILINE)
            else:
                final = re.sub(r'^(updated_at:.*)$',
                               f'\\1\nai_translator: {label}',
                               final, flags=re.MULTILINE, count=1)
            md_path.write_text(final, encoding="utf-8")

    seg_total      = len(sections)
    final_content  = md_path.read_text(encoding="utf-8")
    seg_done_final = sum(1 for s in RE_SECTION.finditer(final_content) if s.group(5).strip())
    return seg_done_final, seg_total


# ═══════════════════════════════════════════════════════════════════════════════
# 主循环
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="翻译 Worker — 批量从任务队列抢占并翻译")
    parser.add_argument("--backend",    required=True, choices=BACKENDS.keys())
    parser.add_argument("--model",      help="覆盖默认模型名")
    parser.add_argument("--slug",       help="只翻译指定 slug（精确抢占）")
    parser.add_argument("--limit",      type=int, default=0, help="最多翻译 N 卷后退出（0=不限）")
    parser.add_argument("--batch-size", type=int, default=5,
                        help="每次请求翻译的段落数（默认5；设1可禁用批量）")
    args = parser.parse_args()

    model      = args.model or BACKENDS[args.backend]["default_model"]
    full_model = canonical_model(args.backend, model)
    agent_id   = str(uuid.uuid4())[:8]

    # CLI 型 backend 强制逐段翻译（避免超长 prompt 导致超时）
    forced = BACKENDS[args.backend].get("force_batch_size")
    if forced is not None:
        args.batch_size = forced

    print(f"[Worker {agent_id}] {full_model}  batch={args.batch_size}")

    job_queue.init_db()

    jobs_done = 0
    while not _shutdown:
        if args.limit and jobs_done >= args.limit:
            print(f"已达到 --limit {args.limit}，退出。")
            break

        released = job_queue.release_stale()
        if released:
            print(f"  [释放 {released} 个超时任务]")

        if args.slug:
            job_queue.reset_job(args.slug)

        job = job_queue.claim_job(agent_id, args.backend, model,
                                  slug=args.slug if args.slug else None,
                                  full_model=full_model)
        if not job:
            if args.slug:
                print(f"无法抢占任务: {args.slug}")
                break
            print("无可用任务，等待 30s...")
            time.sleep(30)
            continue

        slug    = job["slug"]
        md_path = Path(job["file_path"])
        print(f"\n[{agent_id}] 开始翻译: {slug}")

        if not md_path.exists():
            job_queue.mark_failed(slug, agent_id, "文件不存在")
            print(f"  文件不存在，跳过: {md_path}")
            continue

        try:
            seg_done, seg_total = translate_file(
                md_path, args.backend, model, slug, agent_id,
                batch_size=args.batch_size,
                full_model=full_model,
            )
            if _shutdown:
                job_queue.mark_failed(slug, agent_id, "worker 被中断，下次继续")
                job_queue.reset_job(slug)
                break
            job_queue.mark_done(slug, agent_id, seg_done, full_model=full_model)
            print(f"  ✓ {slug} 完成（{seg_done}/{seg_total} 段）")
            jobs_done += 1
            notify_sutra_done(slug, md_path, full_model)
        except Exception as e:
            job_queue.mark_failed(slug, agent_id, str(e))
            print(f"  ✗ {slug} 失败: {e}")
            import traceback; traceback.print_exc()

        if args.slug:
            break  # 单卷模式翻完即退出

    print(f"\n[Worker {agent_id}] 共翻译 {jobs_done} 卷，退出。")


if __name__ == "__main__":
    main()
