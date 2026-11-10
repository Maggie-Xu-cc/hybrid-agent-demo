"""Zero-dependency local demo; shares the exact agent/store with FastAPI."""
import argparse
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import agent, store
from app.config import settings

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def send(self, data, status=200, content_type="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path == "/": return self.send((ROOT / "web/index.html").read_bytes(),content_type="text/html; charset=utf-8")
        if self.path == "/healthz": return self.send({"ok": True, "mock": settings.mock_mode})
        if self.path == "/api/stats": return self.send({"summary": store.stats(), "recent": store.recent(8)})
        self.send({"error": "not found"},404)
    def do_POST(self):
        if self.path != "/api/chat": return self.send({"error": "not found"},404)
        try:
            size = int(self.headers.get("Content-Length",0))
            if size <= 0 or size > 65536: return self.send({"error": "invalid body size"},413)
            body = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(body,dict) or not isinstance(body.get("query"),str): return self.send({"error": "query must be a string"},400)
            force = body.get("force_route")
            if force not in (None,"easy","hard"): return self.send({"error": "invalid force_route"},400)
            result = agent.run(body["query"],force)
            return self.send(result,400 if result.get("error")=="empty query" else 200)
        except (ValueError,UnicodeDecodeError): return self.send({"error": "invalid JSON"},400)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8081)
    args=parser.parse_args();store.init()
    server=ThreadingHTTPServer(("127.0.0.1",args.port),Handler)
    print(f"READY http://127.0.0.1:{args.port} MOCK_MODE={int(settings.mock_mode)}",flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=="__main__":main()
