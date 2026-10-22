"""FastAPI 服务：一个页面 + 两个接口。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import store
from .agent import run

app = FastAPI(title="Hybrid Routing Agent Demo", version="1.0.0")
WEB = Path(__file__).resolve().parent.parent / "web" / "index.html"


class ChatIn(BaseModel):
    query: str
    force_route: str | None = None


@app.on_event("startup")
def _startup() -> None:
    store.init()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB)


@app.post("/api/chat")
def api_chat(body: ChatIn) -> dict:
    return run(body.query, force_route=body.force_route)


@app.get("/api/stats")
def api_stats() -> dict:
    return {"summary": store.stats(), "recent": store.recent(8)}


@app.post("/api/clear")
def api_clear() -> dict:
    deleted = store.clear()
    return {"deleted": deleted, "summary": store.stats()}


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}
