"""Test script for video generation APIs — compares quality and cost.

Usage:
    python scripts/test_video_api.py --provider kling --prompt "产品展示视频"
    python scripts/test_video_api.py --provider jimeng --prompt "产品展示视频"
"""
import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx


async def test_kling_api(prompt: str, api_key: str, base_url: str) -> dict:
    """Test Kling (可灵) video generation API."""
    start = time.time()
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{base_url}/v1/videos/generations",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "prompt": prompt,
                "duration": 5,
                "aspect_ratio": "9:16",
            },
        )
        elapsed = time.time() - start

        if resp.status_code == 200:
            data = resp.json()
            return {
                "provider": "kling",
                "status": "success",
                "elapsed_seconds": round(elapsed, 1),
                "response": data,
            }
        return {
            "provider": "kling",
            "status": "error",
            "status_code": resp.status_code,
            "error": resp.text[:500],
            "elapsed_seconds": round(elapsed, 1),
        }


async def test_jimeng_api(prompt: str, api_key: str, base_url: str) -> dict:
    """Test Jimeng (即梦) video generation API."""
    start = time.time()
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{base_url}/v1/video/generate",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "prompt": prompt,
                "duration": 5,
                "resolution": "720p",
            },
        )
        elapsed = time.time() - start

        if resp.status_code == 200:
            data = resp.json()
            return {
                "provider": "jimeng",
                "status": "success",
                "elapsed_seconds": round(elapsed, 1),
                "response": data,
            }
        return {
            "provider": "jimeng",
            "status": "error",
            "status_code": resp.status_code,
            "error": resp.text[:500],
            "elapsed_seconds": round(elapsed, 1),
        }


SAMPLE_PRODUCTS = [
    {
        "name": "智能手表",
        "prompts": [
            "A sleek smartwatch on a modern desk, cinematic lighting, product showcase, 9:16 aspect ratio",
            "Person wearing a smart watch while exercising, dynamic camera movement, product video",
            "Close-up of smartwatch face showing health metrics, soft bokeh background",
        ],
    },
    {
        "name": "蓝牙耳机",
        "prompts": [
            "Premium wireless earbuds floating in air, studio lighting, product photography style",
            "Young person enjoying music with bluetooth earphones on subway, lifestyle video",
            "Earbuds case opening with dramatic lighting, slow motion, luxury product showcase",
        ],
    },
    {
        "name": "便携充电器",
        "prompts": [
            "Portable charger powering up multiple devices on a travel desk, top-down view",
            "Traveler using power bank at airport, cinematic color grading, lifestyle video",
            "Close-up of charging cable connecting to power bank, LED indicators glowing",
        ],
    },
]


async def run_comparison(provider: str, api_key: str, base_url: str):
    """Run quality comparison tests for 3 products."""
    test_fn = test_kling_api if provider == "kling" else test_jimeng_api

    results = []
    for product in SAMPLE_PRODUCTS:
        print(f"\n{'='*60}")
        print(f"Testing product: {product['name']}")
        for prompt in product["prompts"]:
            print(f"  Prompt: {prompt[:60]}...")
            result = await test_fn(prompt, api_key, base_url)
            result["product"] = product["name"]
            result["prompt"] = prompt
            results.append(result)
            print(f"  Status: {result['status']} | Time: {result['elapsed_seconds']}s")

    output_path = Path(f"output/api_test_{provider}_{int(time.time())}.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nResults saved to: {output_path}")

    success = sum(1 for r in results if r["status"] == "success")
    print(f"\nSummary: {success}/{len(results)} succeeded")
    if success > 0:
        avg_time = sum(r["elapsed_seconds"] for r in results if r["status"] == "success") / success
        print(f"Average generation time: {avg_time:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Test video generation APIs")
    parser.add_argument("--provider", choices=["kling", "jimeng"], required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--prompt", help="Single prompt to test (overrides built-in samples)")
    args = parser.parse_args()

    if not args.base_url:
        args.base_url = (
            "https://api.klingai.com" if args.provider == "kling"
            else "https://api.jimeng.jianying.com"
        )

    asyncio.run(run_comparison(args.provider, args.api_key, args.base_url))


if __name__ == "__main__":
    main()
