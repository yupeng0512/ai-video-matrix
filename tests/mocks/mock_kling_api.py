"""Mock Kling AI Video Generation API.

Returns a minimal valid MP4 for any video generation request.
Used in test harness to avoid real API costs.
"""
import base64
import hashlib
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock Kling API")

# Minimal valid MP4 file (ftyp + moov atoms) — ~600 bytes
# Generated once, served repeatedly
_MINIMAL_MP4 = None


def _generate_minimal_mp4() -> bytes:
    """Create a minimal but valid MP4 container.
    
    This creates a tiny MP4 with just the required atoms.
    Not a real video, but enough for hash testing and pipeline validation.
    """
    import struct

    def box(box_type: bytes, data: bytes = b"") -> bytes:
        return struct.pack(">I", len(data) + 8) + box_type + data

    ftyp = box(b"ftyp", b"isom" + b"\x00\x00\x02\x00" + b"isomiso2mp41")

    # mvhd (movie header)
    mvhd_data = (
        b"\x00\x00\x00\x00"  # version + flags
        + b"\x00\x00\x00\x00" * 2  # creation/modification time
        + struct.pack(">I", 1000)  # timescale
        + struct.pack(">I", 1000)  # duration (1 second)
        + b"\x00\x01\x00\x00"  # rate (1.0)
        + b"\x01\x00"  # volume (1.0)
        + b"\x00" * 10  # reserved
        + b"\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"  # matrix
        + b"\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00"
        + b"\x00" * 24  # pre-defined
        + struct.pack(">I", 2)  # next_track_ID
    )
    mvhd = box(b"mvhd", mvhd_data)
    moov = box(b"moov", mvhd)
    mdat = box(b"mdat", hashlib.sha256(str(time.time()).encode()).digest()[:64])

    return ftyp + moov + mdat


def _get_mp4() -> bytes:
    global _MINIMAL_MP4
    if _MINIMAL_MP4 is None:
        _MINIMAL_MP4 = _generate_minimal_mp4()
    return _MINIMAL_MP4


# In-memory task store
_tasks: dict[str, dict] = {}


@app.post("/v1/videos/text2video")
@app.post("/v1/videos/image2video")
async def create_video_task(request: Request):
    """Mock video generation — immediately marks task as complete."""
    body = await request.json()
    task_id = str(uuid.uuid4())

    _tasks[task_id] = {
        "task_id": task_id,
        "task_status": "succeed",
        "created_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
        "task_result": {
            "videos": [{
                "id": str(uuid.uuid4()),
                "url": f"http://mock-kling-api:8000/v1/videos/download/{task_id}",
                "duration": "5.0",
            }]
        },
    }

    return JSONResponse({
        "code": 0,
        "message": "success",
        "request_id": str(uuid.uuid4()),
        "data": {"task_id": task_id, "task_status": "submitted"},
    })


@app.get("/v1/videos/text2video/{task_id}")
@app.get("/v1/videos/image2video/{task_id}")
async def query_task(task_id: str):
    """Return task status — always succeed for mock."""
    task = _tasks.get(task_id)
    if not task:
        return JSONResponse({"code": 404, "message": "task not found"}, status_code=404)

    return JSONResponse({
        "code": 0,
        "message": "success",
        "data": task,
    })


@app.get("/v1/videos/download/{task_id}")
async def download_video(task_id: str):
    """Return a minimal MP4 file — unique per call via mdat hash."""
    mp4_data = _generate_minimal_mp4()
    return JSONResponse(
        content={"video_base64": base64.b64encode(mp4_data).decode()},
        media_type="application/json",
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-kling-api", "tasks": len(_tasks)}
