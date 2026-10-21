"""三种策略跑同一套测试集，输出对比表。

用法（在项目根目录）：
    python eval/run_eval.py

产物：
    eval/result.csv        逐条明细（路由判定、延迟、成本）
    终端输出一份 markdown 表格，可直接贴进报告
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EVAL_DB = ROOT / "eval" / "eval_runs.db"
os.environ["DB_PATH"] = str(EVAL_DB)

from app import store  # noqa: E402
from app.agent import run  # noqa: E402
from app.config import settings  # noqa: E402


def load_cases() -> list[dict]:
    path = ROOT / "eval" / "testset.jsonl"
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_strategy(cases: list[dict], force: str | None, escalate: bool) -> list[dict]:
    settings.enable_escalation = escalate
    out = []
    for case in cases:
        result = run(case["q"], force_route=force)
        out.append({"case": case, "result": result})
    return out


def summarize(name: str, rows: list[dict]) -> dict:
    n = len(rows)
    lat = sum(r["result"].get("latency_ms", 0) for r in rows) / max(n, 1)
    cost = sum(r["result"].get("cost_cny", 0) for r in rows)
    base = sum(r["result"].get("baseline_cost_cny", 0) for r in rows)
    ans_len = sum(len(r["result"].get("answer", "")) for r in rows) / max(n, 1)
    esc = sum(1 for r in rows if r["result"].get("escalated"))
    deg = sum(1 for r in rows if r["result"].get("degraded"))
    hit = sum(1 for r in rows if r["result"].get("route") == r["case"]["difficulty"])
    return {
        "strategy": name,
        "n": n,
        "avg_latency_ms": round(lat),
        "total_cost": round(cost, 4),
        "vs_cloud": round(cost / base, 3) if base else 0,
        "avg_answer_chars": round(ans_len),
        "routing_acc": round(hit / n, 3) if n else 0,
        "escalated": esc,
        "degraded": deg,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="三策略对比评测")
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 条，用于快速验证")
    args = parser.parse_args()

    if EVAL_DB.exists():
        EVAL_DB.unlink()
    store.init()

    cases = load_cases()
    if args.limit > 0:
        cases = cases[: args.limit]
    print(f"测试集：{len(cases)} 条\n")

    local_rows = run_strategy(cases, force="easy", escalate=False)
    cloud_rows = run_strategy(cases, force="hard", escalate=False)
    hybrid_rows = run_strategy(cases, force=None, escalate=True)

    summary = [
        summarize("全本地", local_rows),
        summarize("全云端", cloud_rows),
        summarize("混合路由", hybrid_rows),
    ]

    header = "| 策略 | 请求数 | 平均延迟 | 总成本 | 相对全云端 | 平均答案长度 | 路由准确率 | 升级次数 | 降级次数 |"
    sep = "|---|---|---|---|---|---|---|---|---|"
    print(header)
    print(sep)
    for s in summary:
        acc = "—" if s["strategy"] != "混合路由" else f"{s['routing_acc'] * 100:.1f}%"
        ratio = "—" if s["strategy"] == "全云端" else f"{s['vs_cloud'] * 100:.1f}%"
        print(
            f"| {s['strategy']} | {s['n']} | {s['avg_latency_ms']}ms | "
            f"¥{s['total_cost']:.4f} | {ratio} | "
            f"{s['avg_answer_chars']} 字 | {acc} | "
            f"{s['escalated']} | {s['degraded']} |"
        )

    # 逐条明细
    out_csv = ROOT / "eval" / "result.csv"
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["query", "gold", "pred", "decided_by", "reason", "model",
             "latency_ms", "tokens_in", "tokens_out", "cost_cny", "baseline_cny", "escalated"]
        )
        for row in hybrid_rows:
            case, res = row["case"], row["result"]
            writer.writerow([
                case["q"][:80], case["difficulty"], res.get("route"), res.get("decided_by"),
                res.get("reason"), res.get("model"), res.get("latency_ms"),
                res.get("tokens_in"), res.get("tokens_out"),
                res.get("cost_cny"), res.get("baseline_cost_cny"), res.get("escalated"),
            ])
    print(f"\n明细已写入：{out_csv}")

    # 误判清单，用来调规则阈值
    misses = [
        (r["case"]["q"][:40], r["case"]["difficulty"], r["result"].get("route"),
         r["result"].get("reason"))
        for r in hybrid_rows
        if r["result"].get("route") != r["case"]["difficulty"]
    ]
    if misses:
        print(f"\n路由误判 {len(misses)} 条：")
        for q, gold, pred, reason in misses:
            print(f"  [{gold} -> {pred}] {q} | {reason}")


if __name__ == "__main__":
    main()
