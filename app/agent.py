"""混合推理主流程：路由 -> 本地作答 -> 质量自检 -> 必要时升级到云端 -> 记账。

刻意不用 LangGraph：一周的 demo 里，显式三步流程比图编排更好调试，
而且报告里能讲清"每一步为什么存在"比"我用了框架"更有说服力。
"""

import time

from .clients import ProviderError, call_cloud, call_local
from .config import settings
from .router import decide, Route
from . import store

SYSTEM = (
    "你是一个严谨的助手。用中文回答，直接给结论，不要复述问题。"
    "如果不确定，明确说\"我不确定\"，不要编造。"
)

ESCALATE_MARKERS = [
    "我不确定",
    "不确定",
    "无法回答",
    "我不知道",
    "作为AI",
    "没有足够信息",
]


def _needs_escalation(text: str) -> bool:
    if len(text.strip()) < 12:
        return True
    return any(marker in text for marker in ESCALATE_MARKERS)


def run(query: str, force_route: str | None = None) -> dict:
    query = (query or "").strip()
    if not query:
        return {"error": "empty query"}
    started = time.perf_counter()
    route = (Route(force_route, f"强制{force_route}", "forced")
             if force_route in ("easy", "hard") else decide(query))
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": query}]
    local_in, local_out = route.tokens_in, route.tokens_out
    cloud_in = cloud_out = 0
    escalated = degraded = escalation_attempted = escalation_failed = False
    answer = model_used = error = ""
    if route.difficulty == "easy":
        try:
            answer, ti, to = call_local(messages)
            local_in += ti; local_out += to
            model_used = settings.local_model
        except ProviderError:
            degraded = True
            try:
                answer, ti, to = call_cloud(messages)
                cloud_in += ti; cloud_out += to
                model_used = settings.cloud_model
            except ProviderError:
                error = "local_and_cloud_failed"
        if not error and not degraded and settings.enable_escalation and _needs_escalation(answer):
            escalation_attempted = True
            try:
                answer2, ti, to = call_cloud(messages)
                cloud_in += ti; cloud_out += to
                answer = answer2
                model_used = f"{settings.local_model} -> {settings.cloud_model}"
                escalated = True
            except ProviderError:
                escalation_failed = True
    else:
        try:
            answer, ti, to = call_cloud(messages)
            cloud_in += ti; cloud_out += to
            model_used = settings.cloud_model
        except ProviderError:
            degraded = True
            try:
                answer, ti, to = call_local(messages)
                local_in += ti; local_out += to
                model_used = settings.local_model
            except ProviderError:
                error = "cloud_and_local_failed"
    tokens_in, tokens_out = local_in + cloud_in, local_out + cloud_out
    cost = ((local_in + local_out) / 1000 * settings.price_local_per_1k
            + cloud_in / 1000 * settings.price_cloud_in_per_1k
            + cloud_out / 1000 * settings.price_cloud_out_per_1k)
    baseline = (tokens_in / 1000 * settings.price_cloud_in_per_1k
                + tokens_out / 1000 * settings.price_cloud_out_per_1k)
    latency = int((time.perf_counter() - started) * 1000)
    store.record(query=query, route=route.difficulty, reason=route.reason, decided_by=route.by,
        model=model_used, latency_ms=latency, tokens_in=tokens_in, tokens_out=tokens_out,
        cost=cost, baseline_cost=baseline, escalated=escalated, degraded=degraded,
        escalation_attempted=escalation_attempted, escalation_failed=escalation_failed,
        error=error, local_tokens_in=local_in, local_tokens_out=local_out,
        cloud_tokens_in=cloud_in, cloud_tokens_out=cloud_out)
    result = {"answer": answer, "route": route.difficulty, "reason": route.reason,
        "decided_by": route.by, "model": model_used, "latency_ms": latency,
        "tokens_in": tokens_in, "tokens_out": tokens_out,
        "local_tokens_in": local_in, "local_tokens_out": local_out,
        "cloud_tokens_in": cloud_in, "cloud_tokens_out": cloud_out,
        "cost_cny": round(cost, 6), "baseline_cost_cny": round(baseline, 6),
        "escalated": escalated, "degraded": degraded,
        "escalation_attempted": escalation_attempted, "escalation_failed": escalation_failed}
    if error: result["error"] = error
    return result
