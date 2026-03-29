"""Mock social platform upload endpoint.

Simulates Douyin/Kuaishou/XHS/WeChat upload pages for testing.
Accepts any file upload and returns success.
"""
import uuid
import time

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse

app = FastAPI(title="Mock Platform")

_uploads: list[dict] = []


@app.get("/")
async def index():
    return HTMLResponse("""
    <html><body>
    <h1>Mock Platform — Upload Test</h1>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="video" accept="video/*"><br>
        <input type="text" name="title" placeholder="Title"><br>
        <input type="text" name="description" placeholder="Description"><br>
        <button type="submit">Upload</button>
    </form>
    </body></html>
    """)


@app.post("/upload")
async def upload_video(
    video: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
):
    """Accept video upload and return mock success."""
    content = await video.read()
    post_id = str(uuid.uuid4())[:8]

    record = {
        "post_id": post_id,
        "filename": video.filename,
        "size_bytes": len(content),
        "title": title,
        "description": description,
        "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "post_url": f"https://mock-platform.test/video/{post_id}",
    }
    _uploads.append(record)

    return {
        "success": True,
        "post_url": record["post_url"],
        "post_id": post_id,
    }


@app.get("/uploads")
async def list_uploads():
    return {"total": len(_uploads), "uploads": _uploads}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-platform", "total_uploads": len(_uploads)}
