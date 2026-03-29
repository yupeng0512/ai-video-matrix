"""Seed script — register test accounts for multi-platform operation.

Usage:
    python scripts/seed_accounts.py --platform douyin --count 20
    python scripts/seed_accounts.py --all --count 5
"""
import argparse
import asyncio

import httpx

ROUTER_URL = "http://localhost:8012"
PLATFORMS = ["douyin", "kuaishou", "xiaohongshu", "weixin_channel"]


async def seed_accounts(platform: str, count: int):
    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(count):
            resp = await client.post(
                f"{ROUTER_URL}/accounts",
                json={
                    "platform": platform,
                    "username": f"{platform}_account_{i+1:03d}",
                    "display_name": f"{platform.title()} Account {i+1}",
                    "daily_limit": 3,
                },
            )
            if resp.status_code == 200:
                print(f"  Created: {platform}_account_{i+1:03d}")
            else:
                print(f"  Failed: {resp.text[:100]}")


async def main(args):
    platforms = PLATFORMS if args.all else [args.platform]
    for platform in platforms:
        print(f"\nSeeding {args.count} accounts for {platform}...")
        await seed_accounts(platform, args.count)

    print(f"\nDone. Total: {len(platforms) * args.count} accounts")
    print(f"View accounts: curl {ROUTER_URL}/accounts | python -m json.tool")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=PLATFORMS, default="douyin")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--all", action="store_true", help="Seed for all platforms")
    args = parser.parse_args()
    asyncio.run(main(args))
