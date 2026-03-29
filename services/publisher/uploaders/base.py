"""Abstract base uploader — all platform uploaders implement this interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from playwright.async_api import BrowserContext


@dataclass
class UploadResult:
    success: bool
    post_url: str = ""
    error_message: str = ""
    platform_response: dict | None = None


class BaseUploader(ABC):
    """Base class for all platform uploaders.

    Subclasses implement the upload flow for a specific platform
    using Playwright browser automation.
    """

    def __init__(self, context: BrowserContext, account_info: dict):
        self.context = context
        self.account = account_info

    @abstractmethod
    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        cover_path: str | None = None,
    ) -> UploadResult:
        """Upload a video to the platform."""
        ...

    @abstractmethod
    async def check_login(self) -> bool:
        """Check if the current session is still logged in."""
        ...

    async def restore_cookies(self, cookies: list[dict]) -> None:
        """Restore saved cookies to the browser context."""
        await self.context.add_cookies(cookies)

    async def save_cookies(self) -> list[dict]:
        """Save current cookies for session persistence."""
        return await self.context.cookies()
