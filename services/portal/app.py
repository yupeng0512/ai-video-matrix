"""AI Video Matrix — Unified Portal with reverse proxy."""
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
import os

app = FastAPI(title="AI Video Matrix Portal")

PROXY_TARGETS = {
    "n8n": "http://n8n:5678",
    "grafana": "http://grafana:3000",
    "minio": "http://minio:9001",
    "rabbitmq": "http://rabbitmq:15672",
}


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


@app.api_route("/proxy/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def reverse_proxy(service: str, path: str, request: Request):
    """Reverse proxy to internal services."""
    target = PROXY_TARGETS.get(service)
    if not target:
        return Response(content=f"Unknown service: {service}", status_code=404)

    url = f"{target}/{path}"
    if request.query_params:
        url += f"?{request.query_params}"

    headers = dict(request.headers)
    for h in ["host", "connection", "transfer-encoding"]:
        headers.pop(h, None)

    body = await request.body()

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body if body else None,
            )
            resp_headers = dict(resp.headers)
            for h in ["transfer-encoding", "connection", "content-encoding", "content-length"]:
                resp_headers.pop(h, None)

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp_headers,
            )
        except Exception as e:
            return Response(content=f"Proxy error: {str(e)}", status_code=502)


@app.get("/", response_class=HTMLResponse)
async def index():
    return open(os.path.join(os.path.dirname(__file__), "static", "index.html")).read()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "portal"}
