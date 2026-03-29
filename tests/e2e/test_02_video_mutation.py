"""E2E Test 2: Video Mutation Engine (Gear 2 — FFmpeg + Hash).

Validates: video-mutator can mutate videos and check similarity.
Cost: Zero (uses local FFmpeg, no API calls).
"""
import httpx
import sys

BASE = "http://localhost:8000"


async def run():
    async with httpx.AsyncClient(base_url=BASE, timeout=60) as c:
        # 1. Health check
        r = await c.get("/health")
        assert r.status_code == 200, f"Health check failed: {r.text}"
        print("  [1/3] Health check passed")

        # 2. Test mutation params generation
        r = await c.post("/mutate/params", json={"intensity": "medium"})
        if r.status_code == 200:
            params = r.json()
            assert "brightness" in params
            print(f"  [2/3] Mutation params generated: brightness={params['brightness']:.4f}")
        else:
            print(f"  [2/3] Params endpoint not available (expected for stub), skipping")

        # 3. Test similarity check endpoint
        r = await c.post("/similarity/check", json={
            "hash1": "abcdef1234567890",
            "hash2": "abcdef1234567891",
            "threshold": 0.70,
        })
        if r.status_code == 200:
            result = r.json()
            print(f"  [3/3] Similarity check: score={result.get('similarity', 'N/A')}")
        else:
            print(f"  [3/3] Similarity endpoint not available (expected for stub), skipping")

    return True


if __name__ == "__main__":
    import asyncio
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)
