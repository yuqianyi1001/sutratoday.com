#!/usr/bin/env python3
"""
dashboard.py — 翻译任务实时监控面板

用法:
  python3 scripts/dashboard.py
  然后打开浏览器访问 http://localhost:7788
"""

import sys
import os
import json
import time
import signal
import subprocess
import threading
import uuid
from pathlib import Path
from flask import Flask, jsonify, request, Response, render_template_string

# ── 路径 ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

# ── 从 .env 加载 ───────────────────────────────────────────────────────────────
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

import job_queue

app = Flask(__name__)
LOG_DIR = Path("/tmp/sutra_workers")
LOG_DIR.mkdir(exist_ok=True)
WORKERS_STATE_FILE = ROOT / "data" / "workers_state.json"
WORKERS_STATE_FILE.parent.mkdir(exist_ok=True)

# 内存中追踪运行中的 worker 进程
_workers: dict = {}
_workers_lock = threading.Lock()


class AttachedProcess:
    """重新接管已有 PID 的进程（dashboard 重启后恢复）。"""
    def __init__(self, pid: int):
        self.pid = pid

    def poll(self):
        try:
            os.kill(self.pid, 0)
            return None       # 进程还活着
        except ProcessLookupError:
            return -1         # 已退出
        except PermissionError:
            return None       # 活着但无权限（不太可能）

    def send_signal(self, sig):
        os.kill(self.pid, sig)


def _save_workers_state():
    """将当前 _workers 序列化到磁盘（调用前必须持有 _workers_lock）。"""
    state = {}
    for wid, w in _workers.items():
        state[wid] = {
            "wid":         wid,
            "pid":         w["process"].pid,
            "backend":     w["backend"],
            "backend_key": w["backend_key"],
            "model":       w["model"],
            "batch_size":  w.get("batch_size", 5),
            "log_path":    str(w["log_path"]),
            "started_at":  w["started_at"],
        }
    try:
        WORKERS_STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        print(f"[dashboard] 保存 worker 状态失败: {e}")


def _load_workers_state():
    """
    启动时自动纳管所有仍在运行的 agent_worker.py 进程。
    策略：
      1. 扫描 ps aux，找出所有 agent_worker.py 进程，解析其命令行参数
      2. 用磁盘状态文件补充 log_path / started_at（如有）
      3. 合并写入 _workers，并保存更新后的状态
    """
    # ── 1. 读磁盘状态（pid → info）用于补充元数据 ─────────────────────────────
    saved: dict = {}
    if WORKERS_STATE_FILE.exists():
        try:
            for info in json.loads(WORKERS_STATE_FILE.read_text()).values():
                saved[info["pid"]] = info
        except Exception:
            pass

    # ── 2. 扫描系统进程 ────────────────────────────────────────────────────────
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    except Exception:
        return

    _BACKEND_KEY_MAP = {
        ("azure",      "DeepSeek-V3.2"):                  "azure-deepseek",
        ("azure",      "Kimi-K2.5"):                      "azure-kimi",
        ("azure",      "grok-4-1-fast-reasoning"):        "azure-grok41",
        ("azure2",     "gpt-5.3-chat"):                   "azure2-gpt53",
        ("azure2",     "gpt-5.4-mini"):                   "azure2-gpt54mini",
        ("lmstudio",   ""):                               "lmstudio",
        ("anyrouter",  "claude-3-5-haiku-20241022"):      "anyrouter",
        ("gemini",     "gemini-2.5-flash"):               "gemini-flash",
        ("gemini",     "gemini-2.5-pro"):                 "gemini-pro",
        ("openrouter", "qwen/qwen3.6-plus-preview:free"): "openrouter-qwen36",
    }

    found = []
    for line in result.stdout.splitlines():
        if "agent_worker.py" not in line or "grep" in line:
            continue
        parts = line.split()
        try:
            pid = int(parts[1])
        except (IndexError, ValueError):
            continue

        # 解析 --backend / --model / --batch-size
        args = parts[10:]   # skip ps columns
        backend = model = ""
        batch_size = 5
        for i, a in enumerate(args):
            if a == "--backend"    and i + 1 < len(args): backend    = args[i + 1]
            if a == "--model"      and i + 1 < len(args): model      = args[i + 1]
            if a == "--batch-size" and i + 1 < len(args):
                try: batch_size = int(args[i + 1])
                except ValueError: pass

        backend_key = _BACKEND_KEY_MAP.get((backend, model), backend)
        sup = saved.get(pid, {})

        # ── 找实际 log 文件：优先 state 文件，其次 lsof ──────────────────────
        log_path_str = sup.get("log_path", "")
        if not log_path_str or not Path(log_path_str).exists():
            # 用 lsof 找该进程打开的 sutra_workers/*.log
            try:
                lsof_r = subprocess.run(
                    ["lsof", "-p", str(pid), "-F", "n"],
                    capture_output=True, text=True, timeout=3
                )
                for lline in lsof_r.stdout.splitlines():
                    if lline.startswith("n") and "sutra_workers" in lline and lline.endswith(".log"):
                        log_path_str = lline[1:]  # strip leading 'n'
                        break
            except Exception:
                pass
        log_path = Path(log_path_str) if log_path_str else LOG_DIR / f"worker_recovered_{pid}.log"

        started_at = sup.get("started_at", time.time())
        found.append((pid, backend, backend_key, model, batch_size, log_path, started_at))

    if not found:
        return

    with _workers_lock:
        # 避免重复添加已在 _workers 中的进程
        existing_pids = {w["process"].pid for w in _workers.values()}
        added = 0
        for pid, backend, backend_key, model, batch_size, log_path, started_at in found:
            if pid in existing_pids:
                continue
            wid = saved.get(pid, {}).get("wid") or str(uuid.uuid4())[:8]
            _workers[wid] = {
                "process":     AttachedProcess(pid),
                "backend":     backend,
                "backend_key": backend_key,
                "model":       model,
                "batch_size":  batch_size,
                "log_path":    log_path,
                "started_at":  started_at,
            }
            added += 1
        if added:
            print(f"[dashboard] 自动纳管了 {added} 个 worker: "
                  + ", ".join(f"PID {p[0]}" for p in found))
            _save_workers_state()

BACKENDS_CONFIG_FILE = ROOT / "config" / "backends.json"


def load_backends() -> dict:
    """每次调用都从 config/backends.json 动态读取，不需要重启 dashboard。"""
    try:
        items = json.loads(BACKENDS_CONFIG_FILE.read_text(encoding="utf-8"))
        return {item["key"]: item for item in items}
    except Exception as e:
        print(f"[dashboard] 读取 backends.json 失败: {e}")
        return {}

# ── HTML 模板 ─────────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>今文佛典 · 翻译任务面板</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body { font-family: -apple-system, "PingFang SC", sans-serif; background: #0f172a; color: #e2e8f0; }
  .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; }
  .badge-pending  { background: #1e40af22; color: #60a5fa; border: 1px solid #3b82f6; }
  .badge-running  { background: #15803d22; color: #4ade80; border: 1px solid #22c55e; }
  .badge-done     { background: #71717a22; color: #a1a1aa; border: 1px solid #52525b; }
  .badge-failed   { background: #dc262622; color: #f87171; border: 1px solid #ef4444; }
  .progress-bar   { height: 6px; border-radius: 3px; background: #0f172a; overflow: hidden; }
  .progress-fill  { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #3b82f6, #06b6d4); transition: width 0.5s; }
  .progress-fill-done { background: linear-gradient(90deg, #4ade80, #22c55e); }
  .log-box { background: #0f172a; border: 1px solid #334155; border-radius: 8px; font-family: monospace; font-size: 12px; height: 100px; overflow-y: auto; padding: 8px 12px; color: #94a3b8; }
  .btn { padding: 6px 14px; border-radius: 6px; font-size: 13px; cursor: pointer; border: none; }
  .btn-start { background: #2563eb; color: white; }
  .btn-stop  { background: #dc2626; color: white; }
  .btn-start:hover { background: #1d4ed8; }
  .btn-stop:hover  { background: #b91c1c; }
  .stat-num { font-size: 2rem; font-weight: 700; line-height: 1; }
  select, input { background: #0f172a; border: 1px solid #334155; color: #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 13px; }
  .scroll-panel { max-height: 420px; overflow-y: auto; }
  .scroll-panel-lg { /* 自然延伸，不限高度 */ }
  .tag { display: inline-block; padding: 1px 7px; border-radius: 9999px; font-size: 11px; }
</style>
</head>
<body class="p-6">

<div class="max-w-7xl mx-auto">

  <!-- 标题 -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-2xl font-bold text-white">今文佛典 · 翻译面板</h1>
      <p class="text-slate-400 text-sm mt-1">实时监控多 Agent 翻译进度 · 按经分配</p>
    </div>
    <div class="text-slate-400 text-sm" id="last-update">-</div>
  </div>

  <!-- 统计卡片（卷） -->
  <div class="grid grid-cols-5 gap-4 mb-4" id="stats">
    <div class="card p-4 text-center"><div class="stat-num text-white" id="s-total">-</div><div class="text-slate-400 text-xs mt-1">总卷数</div></div>
    <div class="card p-4 text-center"><div class="stat-num text-blue-400" id="s-pending">-</div><div class="text-slate-400 text-xs mt-1">待翻译</div></div>
    <div class="card p-4 text-center"><div class="stat-num text-green-400" id="s-running">-</div><div class="text-slate-400 text-xs mt-1">进行中</div></div>
    <div class="card p-4 text-center"><div class="stat-num text-slate-400" id="s-done">-</div><div class="text-slate-400 text-xs mt-1">已完成</div></div>
    <div class="card p-4 text-center"><div class="stat-num text-red-400" id="s-failed">-</div><div class="text-slate-400 text-xs mt-1">失败</div></div>
  </div>

  <!-- 统计卡片（经） -->
  <div class="grid grid-cols-3 gap-4 mb-4">
    <div class="card p-4 text-center"><div class="stat-num text-white" id="st-total">-</div><div class="text-slate-400 text-xs mt-1">总部经数</div></div>
    <div class="card p-4 text-center"><div class="stat-num text-green-400" id="st-translating">-</div><div class="text-slate-400 text-xs mt-1">翻译中（部经）</div></div>
    <div class="card p-4 text-center"><div class="stat-num text-slate-400" id="st-done">-</div><div class="text-slate-400 text-xs mt-1">已完成（部经）</div></div>
  </div>

  <!-- 总进度条 -->
  <div class="card p-4 mb-6">
    <div class="flex justify-between text-sm text-slate-400 mb-2">
      <span>总翻译进度（卷）</span>
      <span id="pct-label">0%</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="total-bar" style="width:0%"></div></div>
  </div>

  <!-- 三栏布局：items-start 让各列独立高度，向下自然延伸 -->
  <div class="grid grid-cols-3 gap-6 items-start">

    <!-- 左栏：Worker 控制 -->
    <div>
      <h2 class="text-white font-semibold mb-3 text-sm uppercase tracking-wider">Worker 控制</h2>

      <!-- 启动新 Worker：sticky 置顶，不随列表滚走 -->
      <div class="card p-4 mb-4" style="position:sticky;top:16px;z-index:10;">
        <div class="text-slate-300 text-sm font-medium mb-3">启动新 Worker</div>
        <div class="flex gap-2 items-center mb-2">
          <select id="sel-backend" class="flex-1">
            <option value="">加载中…</option>
          </select>
          <button class="btn btn-start" onclick="startWorker()">▶ 启动</button>
        </div>
        <div class="flex items-center gap-2 mt-2">
          <span class="text-slate-400 text-xs whitespace-nowrap">批量段数</span>
          <input type="range" id="sel-batch" min="1" max="20" value="5"
                 oninput="document.getElementById('batch-label').textContent=this.value"
                 style="flex:1;accent-color:#3b82f6;">
          <span class="text-blue-400 text-xs font-mono w-5 text-right" id="batch-label">5</span>
          <span class="text-slate-500 text-xs">段/次</span>
        </div>
        <div class="text-slate-500 text-xs mt-1.5">
          推荐：远端 API 用 5~10，本地模型用 3~5
        </div>
        <div id="start-msg" class="text-xs mt-2" style="display:none"></div>
      </div>

      <!-- 运行中的 Worker 列表 -->
      <div id="workers-list">
        <div class="text-slate-500 text-sm text-center py-8">暂无运行中的 Worker</div>
      </div>

      <!-- 最近失败 -->
      <h2 class="text-white font-semibold mb-3 mt-6 text-sm uppercase tracking-wider">最近失败</h2>
      <div id="failed-jobs">
        <div class="text-slate-500 text-sm text-center py-4">暂无失败任务</div>
      </div>
    </div>

    <!-- 中栏：翻译中的经 -->
    <div>
      <h2 class="text-white font-semibold mb-3 text-sm uppercase tracking-wider">
        翻译中的经
        <span class="text-slate-500 font-normal normal-case text-xs ml-1" id="in-progress-count"></span>
      </h2>
      <div class="scroll-panel-lg" id="in-progress-sutras">
        <div class="text-slate-500 text-sm text-center py-8">暂无翻译中的经</div>
      </div>
    </div>

    <!-- 右栏：已翻译的经 -->
    <div>
      <h2 class="text-white font-semibold mb-3 text-sm uppercase tracking-wider">
        已翻译完成的经
        <span class="text-slate-500 font-normal normal-case text-xs ml-1" id="done-count"></span>
      </h2>
      <div class="scroll-panel-lg" id="completed-sutras">
        <div class="text-slate-500 text-sm text-center py-8">尚无已完成的经</div>
      </div>
    </div>

  </div>
</div>

<script>
let workerLogs = {};
let allLogsSource = null;

function fmt(n) { return n?.toLocaleString() ?? '-'; }

async function refresh() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    const q = d.queue;

    // 卷统计
    document.getElementById('s-total').textContent   = fmt(q.total);
    document.getElementById('s-pending').textContent  = fmt(q.pending);
    document.getElementById('s-running').textContent  = fmt(q.running);
    document.getElementById('s-done').textContent     = fmt(q.done);
    document.getElementById('s-failed').textContent   = fmt(q.failed);

    // 经统计（用后端真实计数，避免被 LIMIT 截断）
    const inpCount  = q.sutra_in_progress_count ?? q.in_progress_sutras?.length ?? 0;
    const doneCount = q.sutra_done_count        ?? q.completed_sutras?.length   ?? 0;
    document.getElementById('st-total').textContent       = fmt(q.sutra_total);
    document.getElementById('st-translating').textContent = fmt(inpCount);
    document.getElementById('st-done').textContent        = fmt(doneCount);

    const pct = q.total ? (q.done / q.total * 100).toFixed(1) : 0;
    document.getElementById('pct-label').textContent = pct + '%';
    document.getElementById('total-bar').style.width = pct + '%';
    document.getElementById('last-update').textContent = '更新于 ' + new Date().toLocaleTimeString();

    // ── Workers ─────────────────────────────────────────────────────────────
    const wEl = document.getElementById('workers-list');
    if (d.workers.length === 0) {
      wEl.innerHTML = '<div class="text-slate-500 text-sm text-center py-8">暂无运行中的 Worker</div>';
    } else {
      wEl.innerHTML = d.workers.map(w => `
        <div class="card p-4 mb-3">
          <div class="flex justify-between items-start mb-2">
            <div>
              <span class="text-white text-sm font-medium">${w.label}</span>
              <span class="text-slate-500 text-xs ml-2">PID ${w.pid}</span>
              <span class="text-blue-400 text-xs ml-2">batch=${w.batch_size}</span>
            </div>
            <button class="btn btn-stop text-xs" onclick="stopWorker('${w.id}')">■ 停止</button>
          </div>
          <div class="text-slate-400 text-xs mb-2">运行 ${w.uptime}</div>
          <div class="log-box" id="log-${w.id}">
            ${(workerLogs[w.id] || []).join('<br>')}
          </div>
        </div>
      `).join('');

      subscribeAllLogs();
    }

    // ── 翻译中的经 ───────────────────────────────────────────────────────────
    const ipsEl = document.getElementById('in-progress-sutras');
    const ipList = q.in_progress_sutras || [];
    document.getElementById('in-progress-count').textContent = ipList.length ? `(${ipList.length})` : '';
    if (ipList.length === 0) {
      ipsEl.innerHTML = '<div class="text-slate-500 text-sm text-center py-8">暂无翻译中的经</div>';
    } else {
      ipsEl.innerHTML = ipList.map(s => {
        const pct = s.vol_total ? Math.round(s.vol_done / s.vol_total * 100) : 0;
        const statusTag = s.vol_running > 0
          ? '<span class="tag badge-running">翻译中</span>'
          : '<span class="tag" style="background:#78350f22;color:#fbbf24;border:1px solid #f59e0b">暂停</span>';
        return `
        <div class="card p-3 mb-2">
          <div class="flex justify-between items-center mb-1">
            <span class="text-white font-mono text-sm font-bold">${s.cbeta_id}</span>
            <div class="flex items-center gap-2">
              ${statusTag}
              <span class="text-slate-400 text-xs">${s.vol_done}/${s.vol_total} 卷</span>
            </div>
          </div>
          <div class="progress-bar mb-1.5">
            <div class="progress-fill" style="width:${pct}%"></div>
          </div>
          <div class="flex justify-between text-slate-500 text-xs">
            <span>${s.model || '-'}</span>
            <span>${s.done_segs}/${s.total_segs} 段</span>
          </div>
        </div>`;
      }).join('');
    }

    // ── 已翻译完成的经 ────────────────────────────────────────────────────────
    const csEl = document.getElementById('completed-sutras');
    const csList = q.completed_sutras || [];
    document.getElementById('done-count').textContent = csList.length ? `(${csList.length})` : '';
    if (csList.length === 0) {
      csEl.innerHTML = '<div class="text-slate-500 text-sm text-center py-8">尚无已完成的经</div>';
    } else {
      csEl.innerHTML = csList.map(s => `
        <div class="card p-3 mb-2">
          <div class="flex justify-between items-center">
            <span class="text-slate-200 font-mono text-sm font-bold">${s.cbeta_id}</span>
            <span class="tag badge-done">✓ ${s.vol_total} 卷</span>
          </div>
          <div class="flex justify-between text-slate-500 text-xs mt-1">
            <span>${s.model || '-'}</span>
            <span>${s.completed_at ? s.completed_at.slice(0,10) : '-'}</span>
          </div>
        </div>`).join('');
    }

    // ── 最近失败 ─────────────────────────────────────────────────────────────
    const fjEl = document.getElementById('failed-jobs');
    const fjList = q.failed_jobs || [];
    if (fjList.length === 0) {
      fjEl.innerHTML = '<div class="text-slate-500 text-sm text-center py-4">暂无失败任务</div>';
    } else {
      fjEl.innerHTML = fjList.slice(0, 5).map(j => `
        <div class="card p-3 mb-2 border-red-900">
          <div class="flex justify-between items-center">
            <span class="text-red-400 font-mono text-sm">${j.slug}</span>
            <button class="btn btn-start text-xs" onclick="resetJob('${j.slug}')">重置</button>
          </div>
          <div class="text-slate-500 text-xs mt-1 truncate">${j.error || ''}</div>
        </div>`).join('');
    }

  } catch(e) {
    console.error('refresh error:', e);
  }
}

function subscribeAllLogs() {
  if (allLogsSource) return;
  allLogsSource = new EventSource('/api/logs/all');
  allLogsSource.onmessage = (e) => {
    if (e.data === 'ping') return;
    const idx = e.data.indexOf('|');
    if (idx === -1) return;
    const workerId = e.data.slice(0, idx);
    const line = e.data.slice(idx + 1);
    if (!workerLogs[workerId]) workerLogs[workerId] = [];
    workerLogs[workerId].unshift(line);
    if (workerLogs[workerId].length > 200) workerLogs[workerId].pop();
    const el = document.getElementById('log-' + workerId);
    if (el) el.innerHTML = workerLogs[workerId].slice(0, 50).join('<br>');
  };
  allLogsSource.onerror = () => {
    allLogsSource.close();
    allLogsSource = null;
  };
}

async function startWorker() {
  const btn     = document.querySelector('button.btn-start');
  const msgEl   = document.getElementById('start-msg');
  const backend    = document.getElementById('sel-backend').value;
  const batch_size = parseInt(document.getElementById('sel-batch').value) || 5;

  const showMsg = (text, color) => {
    msgEl.textContent = text;
    msgEl.style.color = color;
    msgEl.style.display = 'block';
    setTimeout(() => { msgEl.style.display = 'none'; }, 4000);
  };

  if (!backend) { showMsg('请先选择模型', '#f87171'); return; }
  btn.disabled = true;
  btn.textContent = '启动中…';
  try {
    const r = await fetch('/api/worker/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({backend, batch_size})
    });
    const d = await r.json();
    if (d.ok) {
      showMsg(`✓ 已启动 PID ${d.pid}`, '#4ade80');
      refresh();
    } else {
      showMsg('启动失败: ' + d.error, '#f87171');
    }
  } catch(e) {
    showMsg('请求失败: ' + e.message, '#f87171');
  } finally {
    btn.disabled = false;
    btn.textContent = '▶ 启动';
  }
}

async function stopWorker(workerId) {
  if (!confirm('确认停止该 Worker？当前段翻译完成后停止。')) return;
  await fetch('/api/worker/stop', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({worker_id: workerId})
  });
  refresh();
}

async function resetJob(slug) {
  await fetch('/api/job/reset', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({slug})
  });
  refresh();
}

// ── 动态加载 Backend 下拉菜单 ────────────────────────────────────────────────
async function loadBackends() {
  try {
    const r = await fetch('/api/backends');
    const d = await r.json();
    const sel = document.getElementById('sel-backend');
    const prev = sel.value;   // 保留当前选中值
    sel.innerHTML = '';
    for (const [group, items] of Object.entries(d.groups)) {
      const og = document.createElement('optgroup');
      og.label = group;
      items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.key;
        opt.textContent = item.label;
        if (item.key === prev) opt.selected = true;
        og.appendChild(opt);
      });
      sel.appendChild(og);
    }
    // 若没有保留到原选项，默认选第一个
    if (!sel.value && sel.options.length) sel.selectedIndex = 0;
  } catch(e) {
    console.error('加载 backends 失败', e);
  }
}

// 页面加载时和每次手动刷新时都重新拉 backends
loadBackends();
refresh();
setInterval(refresh, 1000);
</script>
</body>
</html>
"""


# ── API 路由 ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/status")
def api_status():
    job_queue.init_db()
    with job_queue.get_conn() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
        running = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]
        done    = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='done'").fetchone()[0]
        failed  = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='failed'").fetchone()[0]

        # 总部经数（有 cbeta_id 的不同经）
        sutra_total = conn.execute(
            "SELECT COUNT(DISTINCT cbeta_id) FROM jobs WHERE cbeta_id IS NOT NULL AND cbeta_id != ''"
        ).fetchone()[0]

        # 翻译中的经：有至少一卷 running 或 done，但未全部 done
        in_progress_sutras = [dict(r) for r in conn.execute("""
            SELECT
                cbeta_id,
                COUNT(*) AS vol_total,
                SUM(CASE WHEN status='done'    THEN 1 ELSE 0 END) AS vol_done,
                SUM(CASE WHEN status='running' THEN 1 ELSE 0 END) AS vol_running,
                SUM(seg_done)  AS done_segs,
                SUM(seg_total) AS total_segs,
                MAX(model)     AS model,
                MAX(agent_id)  AS agent_id,
                MAX(updated_at) AS last_updated
            FROM jobs
            WHERE cbeta_id IS NOT NULL AND cbeta_id != ''
            GROUP BY cbeta_id
            HAVING (vol_done + vol_running) > 0
               AND vol_done < COUNT(*)
            ORDER BY vol_running DESC, last_updated DESC
            LIMIT 50
        """).fetchall()]

        # 已翻译完成的经：所有卷均为 done（真实总数 + 最近100条展示）
        sutra_done_count = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT cbeta_id FROM jobs
                WHERE cbeta_id IS NOT NULL AND cbeta_id != ''
                GROUP BY cbeta_id
                HAVING SUM(CASE WHEN status != 'done' THEN 1 ELSE 0 END) = 0
                   AND COUNT(*) > 0
            )
        """).fetchone()[0]

        sutra_in_progress_count = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT cbeta_id FROM jobs
                WHERE cbeta_id IS NOT NULL AND cbeta_id != ''
                GROUP BY cbeta_id
                HAVING (SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN status='running' THEN 1 ELSE 0 END)) > 0
                   AND SUM(CASE WHEN status != 'done' THEN 1 ELSE 0 END) > 0
            )
        """).fetchone()[0]

        completed_sutras = [dict(r) for r in conn.execute("""
            SELECT
                cbeta_id,
                COUNT(*) AS vol_total,
                SUM(seg_done) AS done_segs,
                MAX(model)    AS model,
                MAX(completed_at) AS completed_at
            FROM jobs
            WHERE cbeta_id IS NOT NULL AND cbeta_id != ''
            GROUP BY cbeta_id
            HAVING SUM(CASE WHEN status != 'done' THEN 1 ELSE 0 END) = 0
               AND COUNT(*) > 0
            ORDER BY MAX(completed_at) DESC
            LIMIT 100
        """).fetchall()]

        failed_jobs = [dict(r) for r in conn.execute("""
            SELECT slug, error FROM jobs WHERE status='failed'
            ORDER BY updated_at DESC LIMIT 10
        """).fetchall()]

    with _workers_lock:
        workers_list = []
        dead = []
        for wid, w in _workers.items():
            if w["process"].poll() is not None:
                dead.append(wid)
                continue
            elapsed = int(time.time() - w["started_at"])
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            workers_list.append({
                "id":         wid,
                "pid":        w["process"].pid,
                "backend":    w["backend"],
                "model":      w["model"],
                "batch_size": w.get("batch_size", 5),
                "label":      load_backends().get(w["backend_key"], {}).get("label", w["backend"]),
                "uptime":     f"{h:02d}:{m:02d}:{s:02d}",
                "log_path":   str(w["log_path"]),
            })
        for wid in dead:
            del _workers[wid]
        if dead:
            _save_workers_state()

    return jsonify({
        "queue": {
            "total": total, "pending": pending, "running": running,
            "done": done, "failed": failed,
            "sutra_total":              sutra_total,
            "sutra_done_count":         sutra_done_count,
            "sutra_in_progress_count":  sutra_in_progress_count,
            "in_progress_sutras": in_progress_sutras,
            "completed_sutras":   completed_sutras,
            "failed_jobs":        failed_jobs,
        },
        "workers": workers_list,
    })


@app.route("/api/worker/start", methods=["POST"])
def api_worker_start():
    data = request.json or {}
    backend_key = data.get("backend", "azure-deepseek")
    batch_size  = int(data.get("batch_size", 5))
    batch_size  = max(1, min(batch_size, 50))   # 限制在 1~50

    cfg = load_backends().get(backend_key)
    if not cfg:
        return jsonify({"ok": False, "error": f"unknown backend: {backend_key}"}), 400

    worker_id = str(uuid.uuid4())[:8]
    log_path  = LOG_DIR / f"worker_{worker_id}.log"

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "agent_worker.py"),
        "--backend",    cfg["backend"],
        "--batch-size", str(batch_size),
    ]
    if cfg["model"]:
        cmd += ["--model", cfg["model"]]

    log_f = open(log_path, "w", buffering=1)
    process = subprocess.Popen(
        cmd,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        cwd=str(ROOT),
        text=True,
        start_new_session=True,   # 脱离 dashboard 进程组，停 dashboard 不影响 worker
    )

    with _workers_lock:
        _workers[worker_id] = {
            "process":     process,
            "backend":     cfg["backend"],
            "backend_key": backend_key,
            "model":       cfg["model"] or os.environ.get("LMSTUDIO_MODEL", "local"),
            "batch_size":  batch_size,
            "log_path":    log_path,
            "started_at":  time.time(),
        }
        _save_workers_state()

    return jsonify({"ok": True, "worker_id": worker_id, "pid": process.pid})


@app.route("/api/worker/stop", methods=["POST"])
def api_worker_stop():
    data = request.json or {}
    worker_id = data.get("worker_id")
    with _workers_lock:
        w = _workers.get(worker_id)
        if not w:
            return jsonify({"ok": False, "error": "worker not found"}), 404
        try:
            w["process"].send_signal(signal.SIGTERM)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        del _workers[worker_id]
        _save_workers_state()
    return jsonify({"ok": True})


@app.route("/api/logs/all")
def api_logs_all():
    """统一 SSE：所有 worker 日志合流，格式 'worker_id|line'，避免多连接占满浏览器池。"""
    import queue as _queue, threading as _threading

    q = _queue.Queue()

    def _tail(wid, log_path):
        try:
            with open(log_path, "r") as f:
                for line in f:
                    q.put(f"{wid}|{line.rstrip()}")
                while True:
                    line = f.readline()
                    if line:
                        q.put(f"{wid}|{line.rstrip()}")
                    else:
                        with _workers_lock:
                            alive = (wid in _workers and
                                     _workers[wid]["process"].poll() is None)
                        if not alive:
                            q.put(f"{wid}|[Worker 已停止]")
                            return
                        time.sleep(1)
        except FileNotFoundError:
            q.put(f"{wid}|[日志文件不存在]")

    def generate():
        with _workers_lock:
            snap = {wid: dict(w) for wid, w in _workers.items()}
        active_wids = set(snap)

        for wid, w in snap.items():
            _threading.Thread(target=_tail, args=(wid, w["log_path"]),
                              daemon=True).start()

        while True:
            # 检测新启动的 worker
            with _workers_lock:
                cur_wids = set(_workers)
            for wid in cur_wids - active_wids:
                with _workers_lock:
                    if wid in _workers:
                        _threading.Thread(target=_tail,
                                          args=(wid, _workers[wid]["log_path"]),
                                          daemon=True).start()
                active_wids.add(wid)

            try:
                msg = q.get(timeout=5)
                yield f"data: {msg}\n\n"
            except _queue.Empty:
                yield "data: ping\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/logs/<worker_id>")
def api_logs(worker_id):
    """SSE 实时日志流"""
    with _workers_lock:
        w = _workers.get(worker_id)
        log_path = w["log_path"] if w else LOG_DIR / f"worker_{worker_id}.log"

    def generate():
        try:
            with open(log_path, "r") as f:
                for line in f:
                    yield f"data: {line.rstrip()}\n\n"
                while True:
                    line = f.readline()
                    if line:
                        yield f"data: {line.rstrip()}\n\n"
                    else:
                        time.sleep(1)
                        with _workers_lock:
                            alive = worker_id in _workers and _workers[worker_id]["process"].poll() is None
                        if not alive:
                            yield "data: [Worker 已停止]\n\n"
                            break
        except FileNotFoundError:
            yield "data: [日志文件不存在]\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/job/reset", methods=["POST"])
def api_job_reset():
    data = request.json or {}
    slug = data.get("slug")
    if not slug:
        return jsonify({"ok": False, "error": "missing slug"}), 400
    job_queue.reset_job(slug)
    return jsonify({"ok": True})


@app.route("/api/backends")
def api_backends():
    """动态返回 config/backends.json，刷新页面即可加载最新配置。"""
    backends = load_backends()
    # 按 group 分组返回
    groups = {}
    for key, cfg in backends.items():
        g = cfg.get("group", "其他")
        groups.setdefault(g, []).append({
            "key":   key,
            "label": cfg.get("label", key),
        })
    return jsonify({"groups": groups, "backends": backends})


# ── 启动 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    job_queue.init_db()
    _load_workers_state()
    print("🪷  今文佛典翻译面板")
    print("   打开浏览器访问: http://localhost:7788")
    print("   Ctrl+C 退出（已启动的 worker 会继续在后台运行）\n")
    app.run(host="0.0.0.0", port=7788, debug=False, threaded=True)
