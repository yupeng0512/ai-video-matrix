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
                results[name] = (
                    {"status": "up", "detail": r.json()}
                    if r.status_code == 200
                    else {"status": "down"}
                )
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


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(html_path) as f:
        return f.read()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "portal"}
