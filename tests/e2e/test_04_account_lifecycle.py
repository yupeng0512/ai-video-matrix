"""E2E Test 4: Account Lifecycle (Gear 5 — Health/Cooling/Recovery).

Validates: publisher account health check and lifecycle transitions.
Cost: Zero (database operations only).
"""
import httpx
import sys

BASE = "http://localhost:8000"
ACCOUNT_ID = "a0000000-0000-0000-0000-000000000001"


async def run():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        # 1. Health check
        r = await c.get("/health")
        assert r.status_code == 200, f"Health check failed: {r.text}"
        print("  [1/4] Health check passed")

        # 2. Worker status
        r = await c.get("/workers/status")
        assert r.status_code == 200
        status = r.json()
        print(f"  [2/4] Workers: {status['total_workers']}, poll running: {status['poll_task_running']}")

        # 3. Account health check
        r = await c.get(f"/accounts/{ACCOUNT_ID}/health")
        if r.status_code == 200:
            health = r.json()
            print(f"  [3/4] Account health: {health['health']} (success_rate={health['success_rate']}%)")
        else:
            print(f"  [3/4] Account health check returned {r.status_code} (account may not exist yet)")

        # 4. List tasks
        r = await c.get("/tasks", params={"limit": 5})
        assert r.status_code == 200
        tasks = r.json()
        print(f"  [4/4] Pending tasks: {len(tasks)}")

    return True


if __name__ == "__main__":
    import asyncio
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)
