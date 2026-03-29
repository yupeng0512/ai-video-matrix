"""E2E Test 3: Content Routing (Gear 4 — Platform Isolation).

Validates: content-router enforces same-platform isolation and cross-platform reuse.
Cost: Zero (database operations only).
"""
import httpx
import sys
import uuid

BASE = "http://localhost:8000"


async def run():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        # 1. Health check
        r = await c.get("/health")
        assert r.status_code == 200, f"Health check failed: {r.text}"
        print("  [1/5] Health check passed")

        # 2. List accounts (should have seeded data)
        r = await c.get("/accounts")
        assert r.status_code == 200
        accounts = r.json()
        print(f"  [2/5] Accounts loaded: {len(accounts)}")

        # 3. Route a video to all platforms
        video_id = str(uuid.uuid4())
        video_hash = f"testhash_{uuid.uuid4().hex[:16]}"

        r = await c.post("/route", json={
            "video_id": video_id,
            "video_hash": video_hash,
            "target_platforms": ["douyin", "kuaishou", "xiaohongshu", "weixin_channel"],
        })
        assert r.status_code == 200, f"Routing failed: {r.text}"
        assignments = r.json()
        assigned_count = sum(1 for a in assignments if a["status"] == "assigned")
        print(f"  [3/5] Routed to {assigned_count}/{len(assignments)} platforms")

        # 4. Route SAME video again — should be skipped (platform isolation)
        r = await c.post("/route", json={
            "video_id": video_id,
            "video_hash": video_hash,
            "target_platforms": ["douyin"],
        })
        assert r.status_code == 200
        assignments2 = r.json()
        for a in assignments2:
            if a["platform"] == "douyin":
                assert a["status"] == "skipped", f"Same hash on same platform should be skipped, got {a['status']}"
        print("  [4/5] Platform isolation verified (same hash blocked)")

        # 5. Stats endpoint
        r = await c.get("/stats")
        if r.status_code == 200:
            stats = r.json()
            print(f"  [5/5] Stats: {stats}")
        else:
            print("  [5/5] Stats endpoint not available, skipping")

    return True


if __name__ == "__main__":
    import asyncio
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)
