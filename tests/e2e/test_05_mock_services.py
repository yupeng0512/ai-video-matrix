"""E2E Test 5: Mock Services (Cross-Gear validation).

Validates: mock-kling-api and mock-platform are functional.
Cost: Zero (no real API calls).
"""
import httpx
import sys

KLING_BASE = "http://localhost:8100"
PLATFORM_BASE = "http://localhost:8101"


async def run():
    # ── Mock Kling API ──
    async with httpx.AsyncClient(base_url=KLING_BASE, timeout=30) as c:
        # 1. Health
        r = await c.get("/health")
        assert r.status_code == 200
        print("  [1/5] Mock Kling API healthy")

        # 2. Create video task
        r = await c.post("/v1/videos/text2video", json={
            "prompt": "A smart watch on a white table, professional lighting",
            "duration": "5",
        })
        assert r.status_code == 200
        data = r.json()
        task_id = data["data"]["task_id"]
        print(f"  [2/5] Video task created: {task_id[:8]}...")

        # 3. Query task status
        r = await c.get(f"/v1/videos/text2video/{task_id}")
        assert r.status_code == 200
        task_data = r.json()["data"]
        assert task_data["task_status"] == "succeed"
        print(f"  [3/5] Task status: {task_data['task_status']}")

    # ── Mock Platform ──
    async with httpx.AsyncClient(base_url=PLATFORM_BASE, timeout=30) as c:
        # 4. Health
        r = await c.get("/health")
        assert r.status_code == 200
        print("  [4/5] Mock Platform healthy")

        # 5. Upload test
        r = await c.post("/upload", files={
            "video": ("test.mp4", b"\x00" * 100, "video/mp4"),
        }, data={
            "title": "Test Product Video",
            "description": "E2E test upload",
        })
        assert r.status_code == 200
        result = r.json()
        assert result["success"] is True
        print(f"  [5/5] Mock upload success: {result['post_url']}")

    return True


if __name__ == "__main__":
    import asyncio
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)
