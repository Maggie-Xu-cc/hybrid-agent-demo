"""运行记录与统计（SQLite，零依赖）。"""

import sqlite3
import time

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    query TEXT NOT NULL,
    route TEXT NOT NULL,
    reason TEXT,
    decided_by TEXT,
    model TEXT,
    latency_ms INTEGER,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_cny REAL,
    baseline_cost_cny REAL,
    escalated INTEGER DEFAULT 0
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with _conn() as conn:
        conn.executescript(SCHEMA)


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


def stats() -> dict:
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(cost_cny),0) cost,"
            " COALESCE(SUM(baseline_cost_cny),0) base,"
            " COALESCE(AVG(latency_ms),0) lat,"
            " COALESCE(SUM(escalated),0) esc FROM runs"
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
        "easy": by_route.get("easy", 0),
        "hard": by_route.get("hard", 0),
    }


def recent(limit: int = 10) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT ts, query, route, decided_by, latency_ms, cost_cny, escalated"
            " FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
