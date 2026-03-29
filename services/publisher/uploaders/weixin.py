"""Weixin Channel (微信视频号) uploader — Playwright-based video upload automation."""
import asyncio
from playwright.async_api import BrowserContext, TimeoutError as PwTimeout

from .base import BaseUploader, UploadResult

CREATOR_URL = "https://channels.weixin.qq.com/platform/post/create"


class WeixinChannelUploader(BaseUploader):

    async def check_login(self) -> bool:
        page = await self.context.new_page()
        try:
            await page.goto(CREATOR_URL, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            return "login" not in page.url.lower()
        except Exception:
            return False
        finally:
            await page.close()

    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        cover_path: str | None = None,
    ) -> UploadResult:
        page = await self.context.new_page()
        try:
            await page.goto(CREATOR_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            if "login" in page.url.lower():
                return UploadResult(success=False, error_message="Not logged in - scan QR code required")

            file_input = page.locator('input[type="file"]')
            await file_input.set_input_files(video_path)

            await page.wait_for_selector('[class*="success"], [class*="uploaded"]', timeout=120000)

            desc_area = page.locator('[class*="desc"] textarea, [contenteditable="true"]').first
            if await desc_area.count() > 0:
                full_text = f"{title}\n{description}"
                if tags:
                    full_text += "\n" + " ".join(f"#{t}" for t in tags[:5])
                await desc_area.fill(full_text)

            publish_btn = page.locator('button:has-text("发表")').first
            await publish_btn.click()
            await asyncio.sleep(3)

            return UploadResult(success=True, post_url=page.url)

        except PwTimeout as e:
            return UploadResult(success=False, error_message=f"Timeout: {str(e)[:200]}")
        except Exception as e:
            return UploadResult(success=False, error_message=str(e)[:500])
        finally:
            await page.close()
