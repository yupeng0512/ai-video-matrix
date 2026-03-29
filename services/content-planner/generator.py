"""LLM-based script variant generator with multi-provider support."""
import json
import itertools
from typing import AsyncIterator

from openai import AsyncOpenAI
from config import settings
from models import HookType, StyleType, DurationType


def _build_client() -> AsyncOpenAI:
    if settings.llm_provider == "deepseek":
        return AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return AsyncOpenAI(api_key=settings.openai_api_key)


SYSTEM_PROMPT = """你是一个短视频营销文案专家。根据产品信息，生成差异化的短视频脚本。

输出 JSON 格式：
{
  "prompt_text": "完整的视频脚本（包含画面描述和旁白）",
  "visual_desc": "AI 视频生成 prompt（英文，描述画面内容和风格）",
  "tts_text": "TTS 朗读的旁白文案"
}

要求：
1. 根据指定的 hook 类型和文案风格创作
2. 适配指定的视频时长
3. 文案要有吸引力，适合社交媒体传播
4. 每次生成的内容必须与之前不同
"""


def _user_prompt(
    product_name: str,
    product_desc: str,
    keywords: list[str],
    hook: HookType,
    style: StyleType,
    duration: DurationType,
) -> str:
    hook_labels = {
        HookType.question: "提问式开头（抛出用户痛点）",
        HookType.suspense: "悬念式开头（制造好奇心）",
        HookType.data: "数据式开头（用数字说话）",
        HookType.empathy: "共鸣式开头（引发情感共鸣）",
    }
    style_labels = {
        StyleType.recommend: "种草推荐风格",
        StyleType.review: "测评对比风格",
        StyleType.tutorial: "使用教程风格",
        StyleType.story: "故事叙述风格",
    }
    return (
        f"产品名称：{product_name}\n"
        f"产品描述：{product_desc}\n"
        f"关键词：{', '.join(keywords or [])}\n\n"
        f"Hook 类型：{hook_labels[hook]}\n"
        f"文案风格：{style_labels[style]}\n"
        f"视频时长：{duration.value}\n\n"
        f"请生成一条短视频脚本。只输出 JSON，不要其他文字。"
    )


async def generate_script(
    product_name: str,
    product_desc: str,
    keywords: list[str],
    hook: HookType,
    style: StyleType,
    duration: DurationType,
) -> dict:
    client = _build_client()
    resp = await client.chat.completions.create(
        model="deepseek-chat" if settings.llm_provider == "deepseek" else "gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(
                product_name, product_desc, keywords, hook, style, duration,
            )},
        ],
        temperature=0.9,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    return json.loads(content)


async def generate_batch(
    product_name: str,
    product_desc: str,
    keywords: list[str],
    count: int = 20,
) -> AsyncIterator[dict]:
    """Generate `count` diverse script variants by cycling through hook x style x duration combinations."""
    combos = list(itertools.product(
        list(HookType),
        list(StyleType),
        list(DurationType),
    ))
    for i in range(count):
        hook, style, duration = combos[i % len(combos)]
        try:
            result = await generate_script(
                product_name, product_desc, keywords, hook, style, duration,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Script generation failed for combo {i}: {e}")
            continue
        result["hook"] = hook.value
        result["style"] = style.value
        result["duration"] = duration.value
        yield result
