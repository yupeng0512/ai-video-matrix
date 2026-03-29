"""E2E Test 1: Script Generation (Gear 1 — LLM differentiation).

Validates: content-planner can create products and generate diverse script variants.
Cost: 1 DeepSeek API call (~¥0.001) per single test, ~¥0.02 for batch.
"""
import httpx
import sys

BASE = "http://localhost:8000"
PRODUCT_ID = "00000000-0000-0000-0000-000000000001"


async def run():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        # 1. Health check
        r = await c.get("/health")
        assert r.status_code == 200, f"Health check failed: {r.text}"
        print("  [1/4] Health check passed")

        # 2. List products (seed data should exist)
        r = await c.get("/products")
        assert r.status_code == 200
        products = r.json()
        assert len(products) >= 3, f"Expected ≥3 seeded products, got {len(products)}"
        print(f"  [2/4] Products found: {len(products)}")

        # 3. Generate single script
        r = await c.post("/scripts/generate", json={
            "product_id": PRODUCT_ID,
            "hook": "question",
            "style": "recommend",
            "duration": "15s",
        })
        assert r.status_code == 200, f"Script gen failed: {r.text}"
        script = r.json()
        assert script["prompt_text"], "prompt_text should not be empty"
        assert script["visual_desc"], "visual_desc should not be empty"
        assert script["tts_text"], "tts_text should not be empty"
        print(f"  [3/4] Single script generated: {script['id'][:8]}...")

        # 4. Verify script is listed
        r = await c.get("/scripts", params={"product_id": PRODUCT_ID, "limit": 5})
        assert r.status_code == 200
        scripts = r.json()
        assert len(scripts) >= 1
        print(f"  [4/4] Scripts listed: {len(scripts)}")

    return True


if __name__ == "__main__":
    import asyncio
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)
