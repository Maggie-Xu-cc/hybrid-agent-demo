"""运行记录与统计（SQLite，零依赖）。"""

import sqlite3
import time
from contextlib import contextmanager

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,   -- 自增主键，一条请求一行
    ts TEXT NOT NULL,                        -- 时间戳
    query TEXT NOT NULL,                     -- 原始问题
    route TEXT NOT NULL,                     -- 判定结果 easy/hard
    reason TEXT,                             -- 判定理由
    decided_by TEXT,                         -- 谁判定的：rule/model/default
    model TEXT,                              -- 模型
    latency_ms INTEGER,                      -- 端到端延迟
    tokens_in INTEGER,                       -- 输入 token
    tokens_out INTEGER,                      -- 输出 token
    cost_cny REAL,                           -- 实付成本
    baseline_cost_cny REAL,                  -- 全云端基线成本
    escalated INTEGER DEFAULT 0              -- 是否触发升级重答
);
"""


@contextmanager
def _conn():
    conn = sqlite3.connect(settings.db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init() -> None:
    with _conn() as conn:
        conn.executescript(SCHEMA)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(runs)")}
        additions = {"degraded": "INTEGER DEFAULT 0", "escalation_attempted": "INTEGER DEFAULT 0",
            "escalation_failed": "INTEGER DEFAULT 0", "error": "TEXT DEFAULT ''",
            "local_tokens_in": "INTEGER DEFAULT 0", "local_tokens_out": "INTEGER DEFAULT 0",
            "cloud_tokens_in": "INTEGER DEFAULT 0", "cloud_tokens_out": "INTEGER DEFAULT 0"}
        for name, sql_type in additions.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE runs ADD COLUMN {name} {sql_type}")


def record(
    query: str,
    route: str,
    reason: str,
    decided_by: str,
    model: str,
    latency_ms: int,
    tokens_in: int,
    tokens_out: int,
    cost: float,
    baseline_cost: float,
    escalated: bool,
    degraded: bool = False, escalation_attempted: bool = False, escalation_failed: bool = False,
    error: str = "", local_tokens_in: int = 0, local_tokens_out: int = 0,
    cloud_tokens_in: int = 0, cloud_tokens_out: int = 0,
) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO runs (ts, query, route, reason, decided_by, model, latency_ms,"
            " tokens_in, tokens_out, cost_cny, baseline_cost_cny, escalated)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                time.strftime("%Y-%m-%d %H:%M:%S"),
                query[:500],
                route,
                reason,
                decided_by,
                model,
                latency_ms,
                tokens_in,
                tokens_out,
                round(cost, 6),
                round(baseline_cost, 6),
                1 if escalated else 0,
            ),
        )
        conn.execute("UPDATE runs SET degraded=?, escalation_attempted=?, escalation_failed=?, error=?, "
            "local_tokens_in=?, local_tokens_out=?, cloud_tokens_in=?, cloud_tokens_out=? "
            "WHERE id=last_insert_rowid()",
            (int(degraded), int(escalation_attempted), int(escalation_failed), error,
             local_tokens_in, local_tokens_out, cloud_tokens_in, cloud_tokens_out))


def clear() -> int:
    """删除全部记账记录，返回删除的条数（不可恢复）。"""
    with _conn() as conn:
        cur = conn.execute("DELETE FROM runs")
        return cur.rowcount or 0


def stats() -> dict:
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(cost_cny),0) cost,"
            " COALESCE(SUM(baseline_cost_cny),0) base,"
            " COALESCE(AVG(latency_ms),0) lat,"
            " COALESCE(SUM(escalated),0) esc, COALESCE(SUM(degraded),0) deg,"
            " COALESCE(SUM(escalation_attempted),0) attempts, COALESCE(SUM(escalation_failed),0) failed,"
            " COALESCE(SUM(CASE WHEN error != '' THEN 1 ELSE 0 END),0) errors FROM runs"
        ).fetchone()
        by_route = {
            r["route"]: r["n"]
            for r in conn.execute(
                "SELECT route, COUNT(*) n FROM runs GROUP BY route"
            ).fetchall()
        }

    total = row["n"] or 0
    cost = row["cost"] or 0.0
    base = row["base"] or 0.0
    saved = (1 - cost / base) if base > 0 else 0.0
    return {
        "runs": total,
        "cost_cny": round(cost, 4),
        "baseline_cost_cny": round(base, 4),
        "saved_ratio": round(saved, 4),
        "avg_latency_ms": int(row["lat"] or 0),
        "escalated": int(row["esc"] or 0),
        "degraded": int(row["deg"] or 0), "escalation_attempted": int(row["attempts"] or 0),
        "escalation_failed": int(row["failed"] or 0), "errors": int(row["errors"] or 0),
        "easy": by_route.get("easy", 0),
        "hard": by_route.get("hard", 0),
    }

# 给演示页面底部“最近 10 条调用记录”
def recent(limit: int = 10) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT ts, query, route, decided_by, latency_ms, cost_cny, escalated"
            " FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
