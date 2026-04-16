"""AI Service — 基于 httpx 流式调用 OpenAI 兼容 API"""

import json
import logging
from typing import AsyncGenerator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """统一 AI 服务抽象层，支持 OpenAI/DeepSeek 等兼容接口"""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.llm_model
        self.timeout = settings.analysis_timeout

    async def stream_chat(
        self, system_prompt: str, user_message: str,
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 LLM，逐块 yield 文本内容。

        使用 OpenAI Chat Completions API (stream=True)。
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error("AI API error: status=%d body=%s", response.status_code, error_body[:200])
                    raise RuntimeError(f"AI API error: {response.status_code}")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]  # strip "data: " prefix
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def generate_title_and_summary(
        self, system_prompt: str, user_message: str,
    ) -> tuple[str, str]:
        """
        非流式调用 LLM，生成标题和摘要。
        仅作为降级方案使用（正常流程从流式输出中提取）。
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 256,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(f"AI API error: {response.status_code}")
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return content, content  # 简化：返回相同内容，由调用方解析
