"""Run all E2E tests against the Docker test harness.

Service port mapping (via docker compose exec or host ports):
  - content-planner:  8000 (internal) → test uses docker exec
  - video-mutator:    8000 (internal)
  - content-router:   8000 (internal)
  - publisher:        8000 (internal)
  - mock-kling-api:   8000 (internal)
  - mock-platform:    8000 (internal)

For simplicity, tests are run inside the Docker network via a test-runner
container, OR from host using port-forwarded connections.
"""
import asyncio
import importlib
import sys
import time
import os

# Port map: service → host port for direct testing
# These match docker-compose.test.yml port forwards (if any)
# For harness-based testing, we use docker exec instead
SERVICE_URLS = {
    "content-planner": os.getenv("CONTENT_PLANNER_URL", "http://localhost:8010"),
    "video-mutator": os.getenv("VIDEO_MUTATOR_URL", "http://localhost:8011"),
    "content-router": os.getenv("CONTENT_ROUTER_URL", "http://localhost:8012"),
    "publisher": os.getenv("PUBLISHER_URL", "http://localhost:8013"),
}

TESTS = [
    ("test_01_script_generation", "Gear 1: Script Generation"),
    ("test_02_video_mutation", "Gear 2: Video Mutation"),
    ("test_03_content_routing", "Gear 4: Content Routing"),
    ("test_04_account_lifecycle", "Gear 5: Account Lifecycle"),
    ("test_05_mock_services", "Cross-Gear: Mock Services"),
]


async def run_test(module_name: str, label: str) -> bool:
    try:
        mod = importlib.import_module(module_name)
        await mod.run()
        return True
    except AssertionError as e:
        print(f"  ASSERTION FAILED: {e}")
        return False
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        return False


async def main():
    print("=" * 60)
    print("  AI Video Matrix — E2E Test Suite")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    skipped = 0
    start = time.time()

    for module_name, label in TESTS:
        print(f"▶ {label}")
        ok = await run_test(module_name, label)
        if ok:
            print(f"  ✅ PASSED\n")
            passed += 1
        else:
            print(f"  ❌ FAILED\n")
            failed += 1

    elapsed = time.time() - start
    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"  Time: {elapsed:.1f}s")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
