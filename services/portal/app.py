"""AI Video Matrix — Unified Portal."""
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI(title="AI Video Matrix Portal")


@app.get("/api/status")
async def system_status():
    """Check health of all internal services."""
    services = {
        "content-planner": "http://content-planner:8000/health",
        "video-mutator": "http://video-mutator:8000/health",
        "content-router": "http://content-router:8000/health",
        "publisher": "http://publisher:8000/health",
    }
    results = {}
    async with httpx.AsyncClient(timeout=3) as client:
        for name, url in services.items():
            try:
                r = await client.get(url)
                results[name] = {"status": "up", "detail": r.json()} if r.status_code == 200 else {"status": "down"}
            except Exception:
                results[name] = {"status": "down"}
    return results


@app.get("/api/stats")
async def proxy_stats():
    """Proxy content-router stats."""
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get("http://content-router:8000/stats")
            return r.json() if r.status_code == 200 else {"error": "unavailable"}
        except Exception:
            return {"error": "content-router unreachable"}


@app.get("/api/tool-urls")
async def tool_urls():
    """Return tool service URLs and their internal reachability."""
    tools = {
        "n8n": {"url": "http://vm-n8n.dev.local", "internal": "http://n8n:5678", "name": "Workflow Engine"},
        "grafana": {"url": "http://vm-grafana.dev.local", "internal": "http://grafana:3000", "name": "Monitoring"},
        "minio": {"url": "http://vm-minio.dev.local", "internal": "http://minio:9001", "name": "Object Storage"},
        "rabbitmq": {"url": "http://vm-rabbitmq.dev.local", "internal": "http://rabbitmq:15672", "name": "Message Queue"},
    }
    results = {}
    async with httpx.AsyncClient(timeout=3) as client:
        for key, info in tools.items():
            try:
                r = await client.get(info["internal"])
                results[key] = {"url": info["url"], "name": info["name"], "internal_up": r.status_code < 500}
            except Exception:
                results[key] = {"url": info["url"], "name": info["name"], "internal_up": False}
    return results


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(html_path, "r") as f:
        return f.read()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "portal"}
