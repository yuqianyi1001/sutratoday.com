#!/usr/bin/env python3
"""
job_queue.py — 翻译任务队列核心库（基于 SQLite）

提供原子性任务抢占，支持多 agent 并发翻译，避免重复翻译同一卷。
"""

import sqlite3
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "translation_jobs.db"
STALE_TIMEOUT = 600  # 10分钟无心跳视为卡死，自动释放


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")   # 允许并发读
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """建表（幂等）"""
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            slug            TEXT PRIMARY KEY,
            file_path       TEXT NOT NULL,
            category        TEXT,
            cbeta_id        TEXT,
            juan_index      INTEGER DEFAULT 0,
            status          TEXT NOT NULL DEFAULT 'pending',
            backend         TEXT,
            model           TEXT,
            full_model      TEXT,
            agent_id        TEXT,
            priority        INTEGER DEFAULT 0,
            seg_total       INTEGER DEFAULT 0,
            seg_done        INTEGER DEFAULT 0,
            locked_backend  TEXT,
            locked_model    TEXT,
            locked_agent_id TEXT,
            created_at      TEXT,
            started_at      TEXT,
            updated_at      TEXT,
            completed_at    TEXT,
            error           TEXT
        )
        """)
        # 兼容旧 DB：若列不存在则 ADD
        for col, typedef in [
            ("locked_backend",  "TEXT"),
            ("locked_model",    "TEXT"),
            ("locked_agent_id", "TEXT"),
            ("full_model",      "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {typedef}")
            except Exception:
                pass
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON jobs(status, priority DESC)")


def upsert_job(slug: str, file_path: str, seg_total: int, seg_done: int,
               category: str = "", cbeta_id: str = "", juan_index: int = 0,
               priority: int = 0):
    """
    插入新任务（已存在则只更新 seg_total/seg_done/category，不覆盖 status）。
    若 md 文件标记为 translated，直接标记 done。
    """
    with get_conn() as conn:
        existing = conn.execute("SELECT status FROM jobs WHERE slug=?", (slug,)).fetchone()
        if existing:
            conn.execute("""
                UPDATE jobs SET seg_total=?, seg_done=?, category=?, updated_at=?
                WHERE slug=? AND status NOT IN ('running')
            """, (seg_total, seg_done, category, _now(), slug))
        else:
            status = "done" if seg_done >= seg_total and seg_total > 0 else "pending"
            conn.execute("""
                INSERT INTO jobs
                    (slug, file_path, category, cbeta_id, juan_index,
                     status, priority, seg_total, seg_done, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (slug, file_path, category, cbeta_id, juan_index,
                  status, priority, seg_total, seg_done, _now(), _now()))


def claim_job(agent_id: str, backend: str, model: str,
              slug: str = None, full_model: str = None):
    """
    原子性抢占一个 pending 任务。
    分配逻辑：一部经同一时间只分配给一个 agent，保证翻译风格一致。
      1. 优先继续本 agent 已锁定的经（locked_agent_id = 我）
      2. 其次选未被任何 agent 占用的经（按优先级排序）
    锁定粒度：backend + model 双重匹配，防止同 backend 不同模型互相抢占。
    slug 不为 None 时精确抢占指定卷。
    返回 job row dict，或 None（无可用任务）。
    """
    full_model = full_model or f"{backend}-{model}"
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if slug:
            row = conn.execute("""
                SELECT slug, file_path, seg_total, seg_done, cbeta_id
                FROM jobs WHERE slug = ? AND status = 'pending'
            """, (slug,)).fetchone()
        else:
            row = conn.execute("""
                SELECT j.slug, j.file_path, j.seg_total, j.seg_done, j.cbeta_id
                FROM jobs j
                WHERE j.status = 'pending'
                  -- backend + model 双重锁：同 backend 不同 model 不能互相抢
                  AND (j.locked_backend IS NULL OR j.locked_backend = ?)
                  AND (j.locked_model   IS NULL OR j.locked_model   = ?)
                ORDER BY
                  -- 1. 优先继续本 agent 正在翻的经
                  CASE WHEN j.locked_agent_id = ? THEN 0 ELSE 1 END,
                  -- 2. 再按 backend+model 锁匹配度
                  CASE WHEN j.locked_backend = ? AND j.locked_model = ? THEN 0 ELSE 1 END,
                  j.priority DESC,
                  j.cbeta_id ASC,
                  j.juan_index ASC
                LIMIT 1
            """, (backend, model, agent_id, backend, model)).fetchone()
        if not row:
            conn.execute("ROLLBACK")
            return None
        slug     = row["slug"]
        cbeta_id = row["cbeta_id"]
        conn.execute("""
            UPDATE jobs
            SET status='running', agent_id=?, backend=?, model=?, full_model=?,
                locked_backend=?, locked_model=?, locked_agent_id=?,
                started_at=?, updated_at=?
            WHERE slug=?
        """, (agent_id, backend, model, full_model,
              backend, model, agent_id, _now(), _now(), slug))
        # 锁定同一部经所有 pending 卷到本 agent（backend+model 双重锁）
        if cbeta_id:
            conn.execute("""
                UPDATE jobs
                SET locked_backend=?, locked_model=?, locked_agent_id=?, updated_at=?
                WHERE cbeta_id=? AND status='pending'
                  AND (locked_backend IS NULL OR locked_backend=?)
                  AND (locked_model   IS NULL OR locked_model=?)
            """, (backend, model, agent_id, _now(), cbeta_id, backend, model))
        conn.execute("COMMIT")
        return dict(row)
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def heartbeat(slug: str, agent_id: str, seg_done= None):
    """更新心跳时间（防止被误判为卡死）"""
    with get_conn() as conn:
        if seg_done is not None:
            conn.execute(
                "UPDATE jobs SET updated_at=?, seg_done=? WHERE slug=? AND agent_id=?",
                (_now(), seg_done, slug, agent_id)
            )
        else:
            conn.execute(
                "UPDATE jobs SET updated_at=? WHERE slug=? AND agent_id=?",
                (_now(), slug, agent_id)
            )


def mark_done(slug: str, agent_id: str, seg_done: int, full_model: str = None):
    with get_conn() as conn:
        if full_model:
            conn.execute("""
                UPDATE jobs SET status='done', seg_done=?, completed_at=?, updated_at=?,
                                full_model=?, error=NULL
                WHERE slug=? AND agent_id=?
            """, (seg_done, _now(), _now(), full_model, slug, agent_id))
        else:
            conn.execute("""
                UPDATE jobs SET status='done', seg_done=?, completed_at=?, updated_at=?,
                                error=NULL
                WHERE slug=? AND agent_id=?
            """, (seg_done, _now(), _now(), slug, agent_id))


def check_sutra_complete(slug: str):
    """
    检查 slug 所属的部经是否全部卷均已完成。
    若已全部完成，返回包含统计信息的 dict；否则返回 None。
    dict keys: cbeta_id, category, vol_total, seg_total, full_model
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT cbeta_id, category FROM jobs WHERE slug=?", (slug,)
        ).fetchone()
        if not row or not row["cbeta_id"]:
            return None
        cbeta_id = row["cbeta_id"]
        stats = conn.execute("""
            SELECT
                COUNT(*) AS vol_total,
                SUM(CASE WHEN status != 'done' THEN 1 ELSE 0 END) AS not_done,
                SUM(seg_done) AS seg_total,
                MAX(full_model) AS full_model
            FROM jobs
            WHERE cbeta_id = ?
        """, (cbeta_id,)).fetchone()
        if stats and stats["not_done"] == 0 and stats["vol_total"] > 0:
            return {
                "cbeta_id":  cbeta_id,
                "category":  row["category"] or "",
                "vol_total": stats["vol_total"],
                "seg_total": stats["seg_total"],
                "full_model": stats["full_model"] or "",
            }
    return None


def get_progress() -> dict:
    """返回整体翻译进度统计，包括最近2小时速率。"""
    with get_conn() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        done    = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='done'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
        running = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]
        remaining_segs = conn.execute("""
            SELECT COALESCE(SUM(CASE WHEN status='pending' THEN seg_total
                                     ELSE seg_total - seg_done END), 0)
            FROM jobs WHERE status IN ('pending', 'running')
        """).fetchone()[0]
        # 用多个窗口取最可靠的速率
        best_rate = 0
        for mins, hours in [(30, 0.5), (60, 1), (120, 2)]:
            segs = conn.execute(f"""
                SELECT COALESCE(SUM(seg_total), 0)
                FROM jobs
                WHERE status='done'
                  AND completed_at > datetime('now', '-{mins} minutes')
                  AND ABS(julianday(completed_at) - julianday(updated_at)) < 0.001
            """).fetchone()[0]
            if segs > 0:
                best_rate = segs / hours
                break  # 用最短有数据的窗口
        rate_2h = best_rate
    return {
        "total": total, "done": done, "pending": pending, "running": running,
        "remaining_segs": remaining_segs, "rate_2h": rate_2h,
    }


def mark_failed(slug: str, agent_id: str, error: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE jobs SET status='failed', error=?, updated_at=?
            WHERE slug=? AND agent_id=?
        """, (error[:500], _now(), slug, agent_id))


def release_stale(timeout_sec: int = STALE_TIMEOUT) -> int:
    """把超时未心跳的 running 任务重置为 pending"""
    threshold = datetime.now(timezone.utc).timestamp() - timeout_sec
    threshold_str = datetime.fromtimestamp(threshold, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_conn() as conn:
        cur = conn.execute("""
            UPDATE jobs SET status='pending', agent_id=NULL, backend=NULL, model=NULL,
                            started_at=NULL, locked_agent_id=NULL
            WHERE status='running' AND updated_at < ?
        """, (threshold_str,))
        return cur.rowcount


def reset_job(slug: str, clear_lock: bool = False):
    """
    手动将某任务重置为 pending。
    clear_lock=True 时同时解除该部经所有卷的 locked_backend 锁，
    允许换用不同的 backend 重新翻译。
    """
    with get_conn() as conn:
        if clear_lock:
            row = conn.execute("SELECT cbeta_id FROM jobs WHERE slug=?", (slug,)).fetchone()
            if row and row["cbeta_id"]:
                conn.execute("""
                    UPDATE jobs SET locked_backend=NULL, locked_model=NULL, locked_agent_id=NULL
                    WHERE cbeta_id=? AND status IN ('pending','failed')
                """, (row["cbeta_id"],))
        conn.execute("""
            UPDATE jobs SET status='pending', agent_id=NULL, backend=NULL, model=NULL,
                            started_at=NULL, completed_at=NULL, error=NULL, seg_done=0,
                            locked_agent_id=NULL
            WHERE slug=?
        """, (slug,))


def print_status():
    """打印任务队列汇总"""
    with get_conn() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
        running = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]
        done    = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='done'").fetchone()[0]
        failed  = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='failed'").fetchone()[0]

        print(f"\n{'='*50}")
        print(f"  翻译任务队列状态")
        print(f"{'='*50}")
        print(f"  总计   : {total:>6}")
        print(f"  待翻译 : {pending:>6}")
        print(f"  进行中 : {running:>6}")
        print(f"  已完成 : {done:>6}")
        print(f"  失败   : {failed:>6}")
        print(f"  完成率 : {done/total*100:.1f}%" if total else "  完成率 : N/A")

        if running:
            rows = conn.execute("""
                SELECT slug, agent_id, backend, model,
                       COALESCE(full_model, backend||'-'||model) as full_model,
                       seg_done, seg_total, updated_at
                FROM jobs WHERE status='running'
            """).fetchall()
            print(f"\n  进行中的任务:")
            for r in rows:
                pct = r['seg_done'] / r['seg_total'] * 100 if r['seg_total'] else 0
                print(f"    {r['slug']:15} {r['full_model']:30} "
                      f"{r['seg_done']}/{r['seg_total']} ({pct:.0f}%) @{r['updated_at']}")

        if failed:
            rows = conn.execute("SELECT slug, error FROM jobs WHERE status='failed' LIMIT 10").fetchall()
            print(f"\n  失败任务（最近10条）:")
            for r in rows:
                print(f"    {r['slug']:15} {r['error'][:60]}")
        print()


def _get_arg(args, flag, default=None):
    """从 sys.argv 列表中取 --flag value"""
    try:
        return args[args.index(flag) + 1]
    except (ValueError, IndexError):
        return default


if __name__ == "__main__":
    import sys, json as _json
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    # ── claim：抢占一个 pending 任务，输出 JSON ──────────────────────────────
    if cmd == "claim":
        backend  = _get_arg(args, "--backend", "unknown")
        model    = _get_arg(args, "--model", backend)
        slug     = _get_arg(args, "--slug")
        agent_id = _get_arg(args, "--agent-id", str(__import__("uuid").uuid4())[:8])
        init_db()
        release_stale()
        job = claim_job(agent_id, backend, model, slug=slug)
        if job:
            out = {
                "ok": True,
                "agent_id": agent_id,
                "slug": job["slug"],
                "file_path": job["file_path"],
                "seg_total": job["seg_total"],
                "seg_done":  job["seg_done"],
            }
            print(_json.dumps(out, ensure_ascii=False))
        else:
            print(_json.dumps({"ok": False, "reason": "no pending jobs"}))

    # ── heartbeat：更新心跳 + 进度 ─────────────────────────────────────────
    elif cmd == "heartbeat":
        if len(args) < 2:
            print("用法: job_queue.py heartbeat <slug> --agent-id <id> [--seg-done N]")
            sys.exit(1)
        slug     = args[1]
        agent_id = _get_arg(args, "--agent-id", "unknown")
        seg_done = _get_arg(args, "--seg-done")
        heartbeat(slug, agent_id, int(seg_done) if seg_done else None)
        print(_json.dumps({"ok": True}))

    # ── done：标记完成 ─────────────────────────────────────────────────────
    elif cmd == "done":
        if len(args) < 2:
            print("用法: job_queue.py done <slug> --agent-id <id> [--seg-done N]")
            sys.exit(1)
        slug     = args[1]
        agent_id = _get_arg(args, "--agent-id", "unknown")
        seg_done = int(_get_arg(args, "--seg-done", "0"))
        # 自动从 DB 读取 seg_total 填入
        with get_conn() as conn:
            row = conn.execute("SELECT seg_total FROM jobs WHERE slug=?", (slug,)).fetchone()
            if row and seg_done == 0:
                seg_done = row["seg_total"]
        mark_done(slug, agent_id, seg_done)
        # 同步更新 md 文件 translation_status
        with get_conn() as conn:
            fp = conn.execute("SELECT file_path FROM jobs WHERE slug=?", (slug,)).fetchone()
        if fp:
            import re as _re
            from pathlib import Path as _Path
            md = _Path(fp["file_path"])
            if md.exists():
                txt = md.read_text(encoding="utf-8")
                txt = _re.sub(r'^translation_status: \w+',
                              'translation_status: translated', txt, flags=_re.MULTILINE)
                md.write_text(txt, encoding="utf-8")
        print(_json.dumps({"ok": True, "slug": slug, "seg_done": seg_done}))

    # ── fail：标记失败 ─────────────────────────────────────────────────────
    elif cmd == "fail":
        if len(args) < 2:
            print("用法: job_queue.py fail <slug> --agent-id <id> [--error '原因']")
            sys.exit(1)
        slug     = args[1]
        agent_id = _get_arg(args, "--agent-id", "unknown")
        error    = _get_arg(args, "--error", "agent reported failure")
        mark_failed(slug, agent_id, error)
        print(_json.dumps({"ok": True}))

    # ── status ─────────────────────────────────────────────────────────────
    elif cmd == "status":
        print_status()

    # ── reset ──────────────────────────────────────────────────────────────
    elif cmd == "reset" and len(args) > 1:
        clear = "--clear-lock" in args
        reset_job(args[1], clear_lock=clear)
        print(f"已重置: {args[1]}" + (" (已解锁)" if clear else ""))

    # ── release-stale ──────────────────────────────────────────────────────
    elif cmd == "release-stale":
        n = release_stale()
        print(f"释放了 {n} 个超时任务")

    # ── locks ──────────────────────────────────────────────────────────────
    elif cmd == "locks":
        with get_conn() as conn:
            rows = conn.execute("""
                SELECT cbeta_id,
                       COALESCE(MAX(full_model), locked_backend||'-'||locked_model) as full_model,
                       COUNT(*) as total,
                       SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done,
                       SUM(CASE WHEN status='running' THEN 1 ELSE 0 END) as running
                FROM jobs WHERE locked_backend IS NOT NULL
                GROUP BY cbeta_id, locked_backend, locked_model
                ORDER BY cbeta_id
            """).fetchall()
        print(f"\n{'cbeta_id':10} {'full_model':35} {'状态':10}")
        print("-" * 60)
        for r in rows:
            status = "翻译中" if r['running'] else ("完成" if r['done'] == r['total'] else "暂停")
            print(f"{r['cbeta_id']:10} {r['full_model']:35} {r['done']}/{r['total']} {status}")

    else:
        print("""用法: python3 scripts/job_queue.py <命令>

任务协调命令（AI Agent 翻译前后必须调用）:
  claim   --backend <name> [--model <m>] [--agent-id <id>]
              抢占一个任务，输出 JSON {ok, slug, file_path, seg_total, seg_done}
  heartbeat <slug> --agent-id <id> [--seg-done N]
              更新心跳和翻译进度
  done    <slug> --agent-id <id> [--seg-done N]
              标记翻译完成，自动更新 md 文件状态
  fail    <slug> --agent-id <id> [--error '原因']
              标记翻译失败

运维命令:
  status          查看队列整体状态
  locks           查看各部经锁定情况
  reset <slug> [--clear-lock]   重置任务（含解锁）
  release-stale   释放超时卡死任务
""")
