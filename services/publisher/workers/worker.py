"""Publish worker — picks tasks from the queue and executes uploads.

Each worker manages one Playwright browser context per account,
ensuring profile-level isolation.
"""
import asyncio
import json
import os
import tempfile
import logging

from playwright.async_api import async_playwright
from minio import Minio
import httpx

from config import settings
from uploaders import get_uploader

logger = logging.getLogger(__name__)


class PublishWorker:
    """A single publish worker that processes one task at a time."""

    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self._playwright = None
        self._browser = None
        self._contexts: dict[str, any] = {}

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        logger.info(f"Worker {self.worker_id} started")

    async def stop(self):
        for ctx in self._contexts.values():
            await ctx.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info(f"Worker {self.worker_id} stopped")

    async def _get_context(self, account_id: str, proxy_url: str = "", cookies: str = ""):
        """Get or create a browser context for an account (LRU, max 20)."""
        if account_id in self._contexts:
            return self._contexts[account_id]

        MAX_CONTEXTS = 20
        if len(self._contexts) >= MAX_CONTEXTS:
            oldest_key = next(iter(self._contexts))
            await self._contexts[oldest_key].close()
            del self._contexts[oldest_key]

        context_opts = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        if proxy_url:
            context_opts["proxy"] = {"server": proxy_url}

        ctx = await self._browser.new_context(**context_opts)

        if cookies:
            try:
                cookie_list = json.loads(cookies)
                await ctx.add_cookies(cookie_list)
            except (json.JSONDecodeError, TypeError):
                pass

        self._contexts[account_id] = ctx
        return ctx

    async def process_task(self, task: dict) -> dict:
        """Process a single publish task.

        task keys: task_id, video_id, account_id, platform, minio_key,
                   title, description, tags, proxy_url, cookie_data
        """
        task_id = task["task_id"]
        platform = task["platform"]
        account_id = task["account_id"]

        logger.info(f"Worker {self.worker_id} processing task {task_id} for {platform}/{account_id}")

        minio_client = _get_minio()
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            minio_client.fget_object(settings.minio_bucket, task["minio_key"], video_path)

            ctx = await self._get_context(
                account_id,
                proxy_url=task.get("proxy_url", ""),
                cookies=task.get("cookie_data", ""),
            )

            uploader_cls = get_uploader(platform)
            uploader = uploader_cls(ctx, {"id": account_id, "platform": platform})

            result = await uploader.upload(
                video_path=video_path,
                title=task.get("title", ""),
                description=task.get("description", ""),
                tags=task.get("tags", []),
            )

            new_cookies = await uploader.save_cookies()

            await _report_result(task_id, result, new_cookies)

            return {
                "task_id": task_id,
                "success": result.success,
                "post_url": result.post_url,
                "error": result.error_message,
            }


def _get_minio() -> Minio:
    endpoint = settings.minio_endpoint.replace("http://", "").replace("https://", "")
    return Minio(
        endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_endpoint.startswith("https"),
    )


async def _report_result(task_id: str, result, cookies: list[dict]):
    """Report publish result back to content-router."""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{settings.content_router_url}/callback",
                json={
                    "task_id": task_id,
                    "success": result.success,
                    "error_message": result.error_message,
                    "result_data": {
                        "post_url": result.post_url,
                        "cookies_updated": len(cookies) > 0,
                    },
                },
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Failed to report result for task {task_id}: {e}")
