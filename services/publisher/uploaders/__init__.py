"""Platform uploaders — abstract base + concrete implementations."""
from .base import BaseUploader
from .douyin import DouyinUploader
from .kuaishou import KuaishouUploader
from .xiaohongshu import XiaohongshuUploader
from .weixin import WeixinChannelUploader

UPLOADERS = {
    "douyin": DouyinUploader,
    "kuaishou": KuaishouUploader,
    "xiaohongshu": XiaohongshuUploader,
    "weixin_channel": WeixinChannelUploader,
}


def get_uploader(platform: str) -> type[BaseUploader]:
    cls = UPLOADERS.get(platform)
    if not cls:
        raise ValueError(f"Unsupported platform: {platform}")
    return cls
