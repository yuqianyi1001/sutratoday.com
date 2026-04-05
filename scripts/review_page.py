#!/usr/bin/env python3
"""
review_page.py — Review UI Blueprint (Flask)

在 dashboard.py 中注册：
  from review_page import review_bp
  app.register_blueprint(review_bp)
"""

import re
import os
import sys
import json
import signal
import subprocess
import uuid
import time
from pathlib import Path
from flask import Blueprint, jsonify, request, render_template_string

sys.path.insert(0, str(Path(__file__).parent))
from _dup_common import (
    effective_orig_count, char_jaccard,
    has_trad_simp_mixing, is_sequential_enum,
)

review_bp = Blueprint("review", __name__)
ROOT = Path(__file__).parent.parent
SUTRAS_DIR = ROOT / "content" / "sutras-raw"
ALLOWLIST_FILE = ROOT / "data" / "review_allowlist.json"
SIM_T = 0.25


# ── Allowlist（无问题标记）──────────────────────────────────────────────────────

def _load_allowlist() -> dict:
    """加载 allowlist。格式: {"slug:index": {slug, index, original_preview, reason, ts}}"""
    if ALLOWLIST_FILE.exists():
        try:
            return json.loads(ALLOWLIST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_allowlist(data: dict):
    ALLOWLIST_FILE.parent.mkdir(exist_ok=True)
    ALLOWLIST_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _allowlist_key(slug: str, section_index: int) -> str:
    return f"{slug}:{section_index}"


def _is_allowed(slug: str, section_index: int) -> bool:
    return _allowlist_key(slug, section_index) in _load_allowlist()

RE_SECTION = re.compile(
    r'(### 原文\n)(.*?)(\n### 现代语译\n)(.*?)(?=\n### 原文|\Z)',
    re.DOTALL
)

RE_HEADING = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)


# ── 检测逻辑（复用 _dup_common） ───────────────────────────────────────────────

def _analyze_section(orig_text: str, trans_text: str):
    """返回 (issues_list, suggested_fix_lines, repeat_count) 或 ([], None, 1)
    repeat_count: 估算的重复次数（含连续重复 + 多版本叠加）
    """
    orig_lines = [l for l in orig_text.splitlines() if l.strip()]
    trans_nonempty = [l for l in trans_text.splitlines() if l.strip()]
    n_eff = effective_orig_count(orig_text, orig_lines)
    if n_eff == 0 or not trans_nonempty:
        return [], None, 1

    issues = []
    deduped = [trans_nonempty[0]]
    dup_count = 0
    for l in trans_nonempty[1:]:
        if l == deduped[-1]:
            dup_count += 1
        else:
            deduped.append(l)
    if dup_count:
        issues.append({"type": "A", "detail": f"{dup_count} 行连续相邻重复"})

    n_d = len(deduped)
    ratio = n_d / n_eff
    has_b = False
    k = 1
    if ratio >= 2.0:
        k = round(ratio)
        gs = n_eff
        if k >= 2 and not is_sequential_enum(deduped, gs):
            # 字符长度比检查：译文总字数 / 原文总字数
            # 合法拆行（长原文分成多行）字数比 ≈ 1.x；真正重复则 ≈ N 倍
            orig_chars = len(orig_text.replace(" ", "").replace("\u3000", "").replace("\n", ""))
            trans_chars = sum(len(l.replace(" ", "")) for l in deduped)
            char_ratio = trans_chars / orig_chars if orig_chars else 0

            if char_ratio >= 2.0:  # 总字数确实膨胀了，才算重复
                g1 = " ".join(deduped[:gs])
                gk = " ".join(deduped[-gs:])
                j = char_jaccard(g1, gk)
                mixed = has_trad_simp_mixing("\n".join(deduped))
                if j >= SIM_T or mixed:
                    has_b = True
                    is_verse = "\u3000\u3000" in orig_text
                    detail = (f"多版本（{n_d}/{n_eff}"
                              f"{'半句' if is_verse else '行'}={ratio:.1f}x，"
                              f"约{k}版，J={j:.2f}")
                    if mixed and j < SIM_T:
                        detail += "+繁简混排"
                    detail += "）"
                    issues.append({"type": "B", "detail": detail})
                    deduped = deduped[-gs:]

    # ── 后置校验：建议保留不能比原文短 ─────────────────────────────────────────
    # 翻译后的文本长度 ≥ 原文长度是基本常识。
    # 如果裁剪后的「建议保留」比原文还短，说明检测错了（合法逐句翻译被误判），
    # 撤销 Type B 判定。
    if has_b:
        sug_chars = sum(len(l.replace(" ", "")) for l in deduped)
        if sug_chars < orig_chars:
            # 撤销：恢复 deduped，移除 Type B issue
            has_b = False
            issues = [x for x in issues if x["type"] != "B"]
            # 重新做连续去重（恢复）
            deduped = [trans_nonempty[0]]
            for l in trans_nonempty[1:]:
                if l != deduped[-1]:
                    deduped.append(l)

    # 计算总重复次数
    if has_b and dup_count:
        repeat_count = round(len(trans_nonempty) / n_eff)
    elif has_b:
        repeat_count = k
    elif dup_count:
        repeat_count = round(len(trans_nonempty) / max(len(deduped), 1))
        if repeat_count < 2:
            repeat_count = 2
    else:
        repeat_count = 1

    if issues:
        return issues, deduped, repeat_count
    return [], None, 1


def _parse_file(md_path: Path):
    """解析整个 md 文件，返回 sections 列表"""
    content = md_path.read_text(encoding="utf-8")

    # 读 frontmatter
    fm = {}
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            for line in content[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()

    slug = fm.get("slug", md_path.stem)
    allowlist = _load_allowlist()
    sections = []
    for i, m in enumerate(RE_SECTION.finditer(content), 1):
        orig = m.group(2).strip()
        trans_raw = m.group(4)
        trans_lines = [l for l in trans_raw.splitlines() if l.strip()]
        issues, suggested, repeat_count = _analyze_section(orig, trans_raw)
        dismissed = _allowlist_key(slug, i) in allowlist
        if dismissed:
            issues = []
            suggested = None
        sections.append({
            "index": i,
            "original": orig,
            "translation_lines": trans_lines,
            "has_issue": bool(issues),
            "issues": issues,
            "suggested_fix": suggested,
            "is_empty": len(trans_lines) == 0,
            "dismissed": dismissed,
            "repeat_count": repeat_count,
        })
    return fm, sections


def _scan_all_files():
    """扫描已翻译完成的文件，返回 {cbeta_id: [{slug, title, issue_count, ...}, ...]}"""
    result = {}
    allowlist = _load_allowlist()
    for path in sorted(SUTRAS_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        # 快速读 frontmatter
        fm = {}
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                for line in content[3:end].splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        fm[k.strip()] = v.strip()

        # 只扫描已翻译完成的卷（跳过 untranslated / translating）
        ts = fm.get("translation_status", "untranslated")
        if ts != "translated":
            continue

        slug = fm.get("slug", path.stem)
        cbeta_id = fm.get("cbeta_id", slug.rsplit("-", 1)[0])
        title = fm.get("title", slug)
        juan_index = int(fm.get("juan_index", 0))

        issue_count = 0
        max_repeat = 1
        total_sections = 0
        for idx, m in enumerate(RE_SECTION.finditer(content), 1):
            total_sections += 1
            if _allowlist_key(slug, idx) in allowlist:
                continue
            issues, _, rc = _analyze_section(m.group(2).strip(), m.group(4))
            if issues:
                issue_count += 1
                if rc > max_repeat:
                    max_repeat = rc

        result.setdefault(cbeta_id, []).append({
            "slug": slug,
            "title": title,
            "juan_index": juan_index,
            "issue_count": issue_count,
            "max_repeat": max_repeat,
            "total_sections": total_sections,
        })

    # 排序
    for cid in result:
        result[cid].sort(key=lambda x: x["juan_index"])
    return result


# ── API 路由 ────────────────────────────────────────────────────────────────────

_index_cache = {"data": None, "ts": 0}
_INDEX_TTL = 60  # 缓存60秒


@review_bp.route("/api/review/index")
def api_review_index():
    now = time.time()
    if _index_cache["data"] and now - _index_cache["ts"] < _INDEX_TTL:
        return jsonify(_index_cache["data"])

    raw = _scan_all_files()
    filtered = {}
    for cid, juans in raw.items():
        if any(j["issue_count"] > 0 for j in juans):
            filtered[cid] = {
                "juans": juans,
                "total_issues": sum(j["issue_count"] for j in juans),
            }
    sorted_items = sorted(filtered.items(), key=lambda x: -x[1]["total_issues"])
    result = {"sutras": [{"cbeta_id": k, **v} for k, v in sorted_items]}
    _index_cache["data"] = result
    _index_cache["ts"] = now
    return jsonify(result)


@review_bp.route("/api/review/invalidate", methods=["POST"])
def api_review_invalidate():
    _index_cache["data"] = None
    _index_cache["ts"] = 0
    return jsonify({"ok": True})


@review_bp.route("/api/review/dismiss", methods=["POST"])
def api_review_dismiss():
    """标记段落为「无问题」，加入 allowlist。"""
    data = request.json or {}
    slug = data.get("slug")
    section_index = data.get("section_index")
    reason = data.get("reason", "")  # 可选备注

    if not slug or not section_index:
        return jsonify({"ok": False, "error": "missing slug or section_index"}), 400

    # 读取原文预览用于存档
    md_path = SUTRAS_DIR / f"{slug}.md"
    orig_preview = ""
    if md_path.exists():
        content = md_path.read_text(encoding="utf-8")
        matches = list(RE_SECTION.finditer(content))
        if 0 < section_index <= len(matches):
            orig_preview = matches[section_index - 1].group(2).strip()[:80]

    al = _load_allowlist()
    key = _allowlist_key(slug, section_index)
    al[key] = {
        "slug": slug,
        "section_index": section_index,
        "original_preview": orig_preview,
        "reason": reason,
        "dismissed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _save_allowlist(al)
    _index_cache["data"] = None
    return jsonify({"ok": True, "key": key})


@review_bp.route("/api/review/undismiss", methods=["POST"])
def api_review_undismiss():
    """移除「无问题」标记。"""
    data = request.json or {}
    slug = data.get("slug")
    section_index = data.get("section_index")
    key = _allowlist_key(slug, section_index)
    al = _load_allowlist()
    if key in al:
        del al[key]
        _save_allowlist(al)
        _index_cache["data"] = None
    return jsonify({"ok": True})


@review_bp.route("/api/review/allowlist")
def api_review_allowlist():
    """查看所有已标记为「无问题」的段落。"""
    al = _load_allowlist()
    return jsonify({"count": len(al), "items": list(al.values())})


@review_bp.route("/api/review/file/<slug>")
def api_review_file(slug):
    md_path = SUTRAS_DIR / f"{slug}.md"
    if not md_path.exists():
        return jsonify({"error": "file not found"}), 404
    fm, sections = _parse_file(md_path)
    return jsonify({
        "slug": slug,
        "title": fm.get("title", slug),
        "cbeta_id": fm.get("cbeta_id", ""),
        "ai_translator": fm.get("ai_translator", ""),
        "sections": sections,
    })


@review_bp.route("/api/review/fix", methods=["POST"])
def api_review_fix():
    data = request.json or {}
    slug = data.get("slug")
    section_index = data.get("section_index")  # 1-based
    action = data.get("action")  # keep_last / clear / edit
    new_text = data.get("new_text", "")  # for edit action

    md_path = SUTRAS_DIR / f"{slug}.md"
    if not md_path.exists():
        return jsonify({"ok": False, "error": "file not found"}), 404

    content = md_path.read_text(encoding="utf-8")
    matches = list(RE_SECTION.finditer(content))

    if section_index < 1 or section_index > len(matches):
        return jsonify({"ok": False, "error": "invalid section_index"}), 400

    m = matches[section_index - 1]
    orig_text = m.group(2).strip()
    trans_text = m.group(4)

    if action == "keep_last":
        issues, suggested, _ = _analyze_section(orig_text, trans_text)
        if suggested:
            replacement = "\n" + "\n".join(suggested) + "\n"
        else:
            return jsonify({"ok": False, "error": "no fix suggested"}), 400
    elif action == "clear":
        replacement = "\n\n"
    elif action == "edit":
        replacement = "\n" + new_text.strip() + "\n"
    else:
        return jsonify({"ok": False, "error": f"unknown action: {action}"}), 400

    old_block = m.group(0)
    new_block = m.group(1) + m.group(2) + m.group(3) + replacement
    new_content = content.replace(old_block, new_block, 1)
    md_path.write_text(new_content, encoding="utf-8")
    _index_cache["data"] = None  # 清缓存

    return jsonify({"ok": True, "action": action, "section_index": section_index})


@review_bp.route("/api/review/fix-all", methods=["POST"])
def api_review_fix_all():
    data = request.json or {}
    slug = data.get("slug")
    md_path = SUTRAS_DIR / f"{slug}.md"
    if not md_path.exists():
        return jsonify({"ok": False, "error": "file not found"}), 404

    content = md_path.read_text(encoding="utf-8")
    new_content = content
    fixed = 0
    for m in RE_SECTION.finditer(content):
        issues, suggested, _ = _analyze_section(m.group(2).strip(), m.group(4))
        if issues and suggested:
            replacement = "\n" + "\n".join(suggested) + "\n"
            old_block = m.group(0)
            new_block = m.group(1) + m.group(2) + m.group(3) + replacement
            new_content = new_content.replace(old_block, new_block, 1)
            fixed += 1

    if fixed > 0:
        md_path.write_text(new_content, encoding="utf-8")
        _index_cache["data"] = None
    return jsonify({"ok": True, "fixed_count": fixed})


@review_bp.route("/api/review/retranslate", methods=["POST"])
def api_review_retranslate():
    data = request.json or {}
    slug = data.get("slug")
    section_index = data.get("section_index")
    backend_key = data.get("backend", "azure-deepseek")

    # 先清空该段译文
    md_path = SUTRAS_DIR / f"{slug}.md"
    if not md_path.exists():
        return jsonify({"ok": False, "error": "file not found"}), 404

    content = md_path.read_text(encoding="utf-8")
    matches = list(RE_SECTION.finditer(content))
    if section_index < 1 or section_index > len(matches):
        return jsonify({"ok": False, "error": "invalid section_index"}), 400

    m = matches[section_index - 1]
    old_block = m.group(0)
    new_block = m.group(1) + m.group(2) + m.group(3) + "\n\n"
    new_content = content.replace(old_block, new_block, 1)
    md_path.write_text(new_content, encoding="utf-8")

    # 启动临时 worker 翻译该卷
    try:
        from dashboard import load_backends, LOG_DIR
        cfg = load_backends().get(backend_key, {})
        backend = cfg.get("backend", "azure")
        model = cfg.get("model", "")
    except Exception:
        backend = "azure"
        model = ""

    worker_id = f"retrans-{str(uuid.uuid4())[:6]}"
    log_path = Path("/tmp/sutra_workers") / f"worker_{worker_id}.log"
    log_path.parent.mkdir(exist_ok=True)

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "agent_worker.py"),
        "--backend", backend,
        "--slug", slug,
        "--limit", "1",
        "--batch-size", "1",
    ]
    if model:
        cmd += ["--model", model]

    log_f = open(log_path, "w", buffering=1)
    proc = subprocess.Popen(
        cmd, stdout=log_f, stderr=subprocess.STDOUT,
        cwd=str(ROOT), text=True, start_new_session=True,
    )

    return jsonify({
        "ok": True,
        "worker_id": worker_id,
        "pid": proc.pid,
        "section_index": section_index,
    })


# ── Review 页面 HTML ────────────────────────────────────────────────────────────

@review_bp.route("/review")
def review_page():
    return render_template_string(REVIEW_HTML)


REVIEW_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>今文佛典 · 译文审阅</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
body { font-family: -apple-system, "PingFang SC", "Noto Serif SC", serif; background: #0f172a; color: #e2e8f0; }
.card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; }
.sidebar { width: 340px; min-width: 340px; max-height: calc(100vh - 80px); overflow-y: auto; }
.main-content { flex: 1; max-height: calc(100vh - 80px); overflow-y: auto; }
.section-card { border-left: 4px solid transparent; transition: border-color 0.2s; }
.section-card.has-issue { border-left-color: #f59e0b; }
.dup-line { background: #78350f33; border-left: 3px solid #f59e0b; padding-left: 8px; }
.orig-block { background: #0f172a; border-radius: 8px; padding: 12px 16px; font-size: 15px; line-height: 1.9; color: #94a3b8; }
.trans-block { padding: 8px 0; font-size: 15px; line-height: 1.9; }
.trans-line { padding: 2px 12px; border-radius: 4px; }
.btn { padding: 5px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; border: none; font-weight: 500; }
.btn-fix { background: #059669; color: white; }
.btn-fix:hover { background: #047857; }
.btn-clear { background: #d97706; color: white; }
.btn-clear:hover { background: #b45309; }
.btn-edit { background: #2563eb; color: white; }
.btn-edit:hover { background: #1d4ed8; }
.btn-retrans { background: #7c3aed; color: white; }
.btn-retrans:hover { background: #6d28d9; }
.btn-fixall { background: #059669; color: white; padding: 8px 20px; font-size: 14px; }
.btn-dismiss { background: #475569; color: #e2e8f0; }
.btn-dismiss:hover { background: #64748b; }
.btn-undismiss { background: #92400e; color: #fbbf24; }
.btn-undismiss:hover { background: #78350f; }
.section-card.dismissed { opacity: 0.5; border-left-color: #475569; }
.badge { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.badge-warn { background: #78350f; color: #fbbf24; }
.badge-ok { background: #064e3b; color: #6ee7b7; }
.tree-item { cursor: pointer; padding: 6px 12px; border-radius: 6px; font-size: 13px; }
.tree-item:hover { background: #334155; }
.tree-item.active { background: #1e40af44; border: 1px solid #3b82f6; }
.sutra-group { margin-bottom: 4px; }
.sutra-header { cursor: pointer; padding: 8px 12px; border-radius: 8px; font-size: 13px; font-weight: 600; }
.sutra-header:hover { background: #334155; }
.edit-area { width: 100%; min-height: 80px; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; border-radius: 6px; padding: 8px; font-size: 14px; line-height: 1.8; resize: vertical; }
.suggested-line { background: #064e3b44; border-left: 3px solid #10b981; padding: 2px 12px; border-radius: 4px; }
.nav-tabs a { padding: 8px 20px; border-radius: 8px 8px 0 0; text-decoration: none; font-size: 14px; font-weight: 600; }
.nav-tabs a.active { background: #1e293b; color: #60a5fa; }
.nav-tabs a:not(.active) { background: #0f172a; color: #64748b; }
.loading { text-align: center; padding: 40px; color: #64748b; }
</style>
</head>
<body class="p-4">

<div class="max-w-[1600px] mx-auto">
  <!-- Nav -->
  <div class="flex items-center justify-between mb-4">
    <div class="nav-tabs flex gap-1">
      <a href="/">控制台</a>
      <a href="/review" class="active">译文审阅</a>
    </div>
    <h1 class="text-lg font-bold text-white">今文佛典 · 译文审阅</h1>
  </div>

  <div class="flex gap-4">
    <!-- 左栏：经/卷树 -->
    <div class="sidebar card p-3" id="sidebar">
      <div class="mb-3">
        <input type="text" id="search-input" placeholder="搜索经名或编号..." class="w-full text-sm mb-2"
               style="background:#0f172a; border:1px solid #334155; color:#e2e8f0; border-radius:6px; padding:6px 10px;">
        <select id="repeat-filter" class="w-full text-xs" onchange="applyTreeFilter()"
                style="background:#0f172a; border:1px solid #334155; color:#e2e8f0; border-radius:6px; padding:5px 8px;">
          <option value="0">全部重复次数</option>
        </select>
      </div>
      <div id="tree-loading" class="loading">加载中...</div>
      <div id="tree-container"></div>
    </div>

    <!-- 右栏：内容区 -->
    <div class="main-content card p-4" id="main">
      <div id="placeholder" class="text-center py-20 text-slate-500">
        <div class="text-4xl mb-4">📖</div>
        <div>从左侧选择一卷开始审阅</div>
      </div>
      <div id="file-content" style="display:none">
        <!-- 顶部工具栏 -->
        <div class="flex items-center justify-between mb-4 pb-3 border-b border-slate-700">
          <div>
            <h2 class="text-white font-bold text-lg" id="file-title"></h2>
            <span class="text-slate-400 text-sm" id="file-meta"></span>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <label class="text-slate-400 text-xs">筛选:</label>
            <select id="filter-select" class="text-xs" onchange="applyFilter()">
              <option value="all">全部段落</option>
              <option value="issues">仅有问题</option>
            </select>
            <label class="text-slate-400 text-xs ml-2">重翻模型:</label>
            <select id="backend-select" class="text-xs" style="min-width:160px">
              <option value="">加载中...</option>
            </select>
            <button class="btn btn-fixall" onclick="fixAll()">一键修复全部</button>
          </div>
        </div>
        <div id="sections-container"></div>
      </div>
    </div>
  </div>
</div>

<script>
let currentSlug = null;
let sectionsData = [];
let treeData = [];

// ── 加载左侧树 ──────────────────────────────────────────────────────
async function loadTree() {
  try {
    const r = await fetch('/api/review/index');
    const d = await r.json();
    treeData = d.sutras;
    buildRepeatFilter(treeData);
    renderTree(treeData);
  } catch(e) {
    document.getElementById('tree-loading').textContent = '加载失败: ' + e;
  }
}

function buildRepeatFilter(data) {
  // 统计各区间的卷数
  const ranges = [
    {key:'20', min:21, max:Infinity, label:'20x+'},
    {key:'11', min:11, max:20, label:'11x-20x'},
    {key:'6',  min:6,  max:10, label:'6x-10x'},
    {key:'4',  min:4,  max:5,  label:'4x-5x'},
    {key:'3',  min:3,  max:3,  label:'3x'},
    {key:'2',  min:2,  max:2,  label:'2x'},
  ];
  const counts = {};
  ranges.forEach(r => counts[r.key] = 0);
  data.forEach(sutra => {
    sutra.juans.forEach(j => {
      if (j.issue_count === 0) return;
      const mr = j.max_repeat;
      for (const r of ranges) {
        if (mr >= r.min && mr <= r.max) { counts[r.key]++; break; }
      }
    });
  });
  const sel = document.getElementById('repeat-filter');
  const curVal = sel.value;
  sel.innerHTML = '<option value="0">全部重复次数</option>';
  ranges.forEach(r => {
    if (counts[r.key] > 0) {
      const opt = document.createElement('option');
      opt.value = r.key;
      opt.textContent = `${r.label}（${counts[r.key]} 卷）`;
      sel.appendChild(opt);
    }
  });
  sel.value = curVal;  // 保持之前的选择
}

function renderTree(data) {
  const c = document.getElementById('tree-container');
  document.getElementById('tree-loading').style.display = 'none';
  c.innerHTML = '';
  if (!data.length) { c.innerHTML = '<div class="text-slate-500 text-sm p-4">没有发现重复问题</div>'; return; }

  data.forEach(sutra => {
    const div = document.createElement('div');
    div.className = 'sutra-group';
    const hasIssueJuans = sutra.juans.filter(j => j.issue_count > 0);
    div.innerHTML = `
      <div class="sutra-header flex justify-between items-center" onclick="toggleSutra(this)">
        <span class="text-slate-300 truncate">${sutra.cbeta_id}</span>
        <span class="badge badge-warn">${sutra.total_issues}</span>
      </div>
      <div class="sutra-juans hidden pl-2 mt-1">
        ${sutra.juans.map(j => `
          <div class="tree-item flex justify-between items-center ${j.issue_count === 0 ? 'text-slate-600' : 'text-slate-300'}"
               data-slug="${j.slug}" onclick="loadFile('${j.slug}', this)">
            <span class="truncate text-xs">${j.slug} ${j.title ? '· '+j.title.substring(0,12) : ''}</span>
            ${j.issue_count > 0 ? `<span class="badge badge-warn text-xs">${j.issue_count} · ${j.max_repeat}x</span>` : '<span class="badge badge-ok text-xs">✓</span>'}
          </div>
        `).join('')}
      </div>
    `;
    c.appendChild(div);
  });
}

function toggleSutra(el) {
  const juans = el.nextElementSibling;
  juans.classList.toggle('hidden');
}

// 筛选（搜索 + 重复次数）
function applyTreeFilter() {
  const q = document.getElementById('search-input').value.toLowerCase();
  const repeatMin = parseInt(document.getElementById('repeat-filter').value) || 0;
  const repeatRanges = {0:[0,Infinity], 2:[2,2], 3:[3,3], 4:[4,5], 6:[6,10], 11:[11,20], 20:[21,Infinity]};
  const [rMin, rMax] = repeatRanges[repeatMin] || [0, Infinity];

  const filtered = treeData.map(sutra => {
    // 按重复次数过滤卷
    const filteredJuans = sutra.juans.filter(j => {
      if (rMin > 0 && (j.max_repeat < rMin || j.max_repeat > rMax)) return false;
      return true;
    });
    if (!filteredJuans.length) return null;
    // 按搜索词过滤
    if (q && !sutra.cbeta_id.toLowerCase().includes(q) &&
        !filteredJuans.some(j => j.slug.toLowerCase().includes(q) || (j.title||'').toLowerCase().includes(q))) {
      return null;
    }
    return {...sutra, juans: filteredJuans, total_issues: filteredJuans.reduce((a,j) => a+j.issue_count, 0)};
  }).filter(Boolean);

  renderTree(filtered);
}
document.getElementById('search-input').addEventListener('input', applyTreeFilter);

// ── 加载文件 ────────────────────────────────────────────────────────
async function loadFile(slug, el) {
  // 高亮
  document.querySelectorAll('.tree-item').forEach(e => e.classList.remove('active'));
  if (el) el.classList.add('active');
  currentSlug = slug;

  document.getElementById('placeholder').style.display = 'none';
  document.getElementById('file-content').style.display = 'block';
  document.getElementById('sections-container').innerHTML = '<div class="loading">加载中...</div>';

  const r = await fetch(`/api/review/file/${slug}`);
  const d = await r.json();
  document.getElementById('file-title').textContent = d.title || slug;
  document.getElementById('file-meta').textContent =
    `${slug} · ${d.sections.length} 段 · ${d.sections.filter(s=>s.has_issue).length} 段有问题 · 翻译器: ${d.ai_translator || '未知'}`;
  sectionsData = d.sections;
  renderSections();
}

function renderSections() {
  const filter = document.getElementById('filter-select').value;
  const container = document.getElementById('sections-container');
  container.innerHTML = '';

  sectionsData.forEach((s, idx) => {
    if (filter === 'issues' && !s.has_issue) return;

    const div = document.createElement('div');
    div.className = `section-card card p-4 mb-3 ${s.has_issue ? 'has-issue' : ''} ${s.dismissed ? 'dismissed' : ''}`;
    div.id = `section-${s.index}`;

    // 原文
    let origHtml = s.original.replace(/\n/g, '<br>');

    // 译文行（高亮重复）
    let transHtml = '';
    if (s.translation_lines.length === 0) {
      transHtml = '<div class="text-slate-600 italic text-sm">（未翻译）</div>';
    } else {
      const dupSet = new Set();
      // 标记连续重复行
      for (let i = 1; i < s.translation_lines.length; i++) {
        if (s.translation_lines[i] === s.translation_lines[i-1]) {
          dupSet.add(i);
        }
      }
      // 如果有 suggested_fix，标记不在 suggested 中的行
      const sugSet = s.suggested_fix ? new Set(s.suggested_fix) : null;

      s.translation_lines.forEach((line, li) => {
        const isDup = dupSet.has(li);
        const isRemoved = sugSet && !sugSet.has(line) && s.has_issue;
        const cls = isDup ? 'dup-line' :
                    (isRemoved ? 'dup-line opacity-60' : 'trans-line');
        transHtml += `<div class="${cls}">${escHtml(line)}</div>`;
      });
    }

    // 建议保留
    let sugHtml = '';
    if (s.suggested_fix && s.has_issue) {
      sugHtml = `<div class="mt-2 pt-2 border-t border-slate-700">
        <div class="text-xs text-emerald-400 mb-1 font-semibold">建议保留：</div>
        ${s.suggested_fix.map(l => `<div class="suggested-line">${escHtml(l)}</div>`).join('')}
      </div>`;
    }

    // Issues
    let issueHtml = '';
    if (s.repeat_count > 1 && s.has_issue) {
      issueHtml += `<span class="badge mr-1" style="background:#7c2d12;color:#fb923c">${s.repeat_count}x</span>`;
    }
    issueHtml += s.issues.map(iss =>
      `<span class="badge badge-warn mr-1">${iss.type}: ${iss.detail}</span>`
    ).join('');

    // 操作按钮
    let btnsHtml = '';
    if (s.dismissed) {
      btnsHtml = `<div class="flex gap-2 mt-2 pt-2 border-t border-slate-700">
        <span class="text-xs text-slate-500 mr-2 leading-relaxed">已标记为无问题</span>
        <button class="btn btn-undismiss" onclick="undismiss(${s.index})">撤销标记</button>
      </div>`;
    } else if (s.has_issue) {
      btnsHtml = `<div class="flex gap-2 mt-2 pt-2 border-t border-slate-700">
        <button class="btn btn-fix" onclick="fixSection(${s.index}, 'keep_last')">✓ 保留最后版</button>
        <button class="btn btn-dismiss" onclick="dismiss(${s.index})">✓ 无问题</button>
        <button class="btn btn-clear" onclick="fixSection(${s.index}, 'clear')">✕ 清空译文</button>
        <button class="btn btn-edit" onclick="showEdit(${s.index})">✎ 编辑</button>
        <button class="btn btn-retrans" onclick="retranslate(${s.index})">↻ 重翻</button>
      </div>`;
    } else if (s.is_empty) {
      btnsHtml = `<div class="flex gap-2 mt-2 pt-2 border-t border-slate-700">
        <button class="btn btn-retrans" onclick="retranslate(${s.index})">↻ 翻译此段</button>
      </div>`;
    }

    div.innerHTML = `
      <div class="flex justify-between items-start mb-2">
        <span class="text-xs text-slate-500">第 ${s.index} 段 ${s.dismissed ? '<span class=\"badge\" style=\"background:#475569;color:#94a3b8\">已忽略</span>' : ''}</span>
        <div>${issueHtml}</div>
      </div>
      <div class="orig-block mb-2">${origHtml}</div>
      <div class="trans-block">${transHtml}</div>
      ${sugHtml}
      ${btnsHtml}
      <div class="edit-panel hidden mt-2" id="edit-panel-${s.index}">
        <textarea class="edit-area" id="edit-text-${s.index}">${s.suggested_fix ? s.suggested_fix.join('\n') : s.translation_lines.join('\n')}</textarea>
        <div class="flex gap-2 mt-2">
          <button class="btn btn-fix" onclick="saveEdit(${s.index})">保存</button>
          <button class="btn" style="background:#475569;color:white" onclick="hideEdit(${s.index})">取消</button>
        </div>
      </div>
    `;
    container.appendChild(div);
  });
}

function applyFilter() { renderSections(); }

// ── 操作 ────────────────────────────────────────────────────────────
async function fixSection(idx, action, newText) {
  const body = { slug: currentSlug, section_index: idx, action };
  if (action === 'edit') body.new_text = newText;
  const r = await fetch('/api/review/fix', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const d = await r.json();
  if (d.ok) {
    showToast(`第 ${idx} 段已${action === 'keep_last' ? '修复' : action === 'clear' ? '清空' : '保存'}`);
    loadFile(currentSlug);
  } else {
    showToast('操作失败: ' + (d.error || ''), true);
  }
}

async function fixAll() {
  if (!confirm(`确认一键修复 ${currentSlug} 的所有检测到的问题？`)) return;
  const r = await fetch('/api/review/fix-all', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({slug: currentSlug}) });
  const d = await r.json();
  if (d.ok) {
    showToast(`已修复 ${d.fixed_count} 段`);
    loadFile(currentSlug);
  }
}

async function retranslate(idx) {
  const sel = document.getElementById('backend-select');
  const backend = sel.value;
  if (!backend) { showToast('请先选择重翻模型', true); return; }
  const label = sel.options[sel.selectedIndex].text;
  if (!confirm(`用「${label}」重新翻译第 ${idx} 段？\n（会先清空该段译文再调用翻译）`)) return;
  const r = await fetch('/api/review/retranslate', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({slug: currentSlug, section_index: idx, backend})
  });
  const d = await r.json();
  if (d.ok) {
    showToast(`已启动重翻：${label}（PID ${d.pid}）`);
    setTimeout(() => loadFile(currentSlug), 8000);
  } else {
    showToast('重翻失败: ' + (d.error || ''), true);
  }
}

// 加载 backends 列表
async function loadBackends() {
  try {
    const r = await fetch('/api/backends');
    const d = await r.json();
    const sel = document.getElementById('backend-select');
    sel.innerHTML = '';
    for (const [group, items] of Object.entries(d.groups)) {
      const optgroup = document.createElement('optgroup');
      optgroup.label = group;
      items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.key;
        opt.textContent = item.label;
        optgroup.appendChild(opt);
      });
      sel.appendChild(optgroup);
    }
    // 默认选第一个
    if (sel.options.length) sel.selectedIndex = 0;
  } catch(e) {
    console.error('加载 backends 失败:', e);
  }
}

async function dismiss(idx) {
  const reason = prompt('备注（可选，直接按确定跳过）:', '') ?? '';
  const r = await fetch('/api/review/dismiss', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({slug: currentSlug, section_index: idx, reason})
  });
  const d = await r.json();
  if (d.ok) {
    showToast(`第 ${idx} 段已标记为无问题`);
    loadFile(currentSlug);
  }
}

async function undismiss(idx) {
  const r = await fetch('/api/review/undismiss', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({slug: currentSlug, section_index: idx})
  });
  const d = await r.json();
  if (d.ok) {
    showToast(`第 ${idx} 段标记已撤销`);
    loadFile(currentSlug);
  }
}

function showEdit(idx) {
  document.getElementById(`edit-panel-${idx}`).classList.remove('hidden');
}
function hideEdit(idx) {
  document.getElementById(`edit-panel-${idx}`).classList.add('hidden');
}
function saveEdit(idx) {
  const text = document.getElementById(`edit-text-${idx}`).value;
  fixSection(idx, 'edit', text);
}

// ── 工具函数 ────────────────────────────────────────────────────────
function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function showToast(msg, isError) {
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;top:20px;right:20px;z-index:9999;padding:12px 24px;border-radius:8px;font-size:14px;color:white;background:${isError?'#dc2626':'#059669'};box-shadow:0 4px 12px rgba(0,0,0,0.3);`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// ── 初始化 ──────────────────────────────────────────────────────────
loadTree();
loadBackends();

// URL hash 自动加载
if (location.hash) {
  const slug = location.hash.slice(1);
  setTimeout(() => loadFile(slug), 500);
}
</script>
</body>
</html>
"""
