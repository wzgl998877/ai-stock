"""AI Service — 基于 httpx 流式调用 OpenAI 兼容 API"""

import json
import logging
from typing import AsyncGenerator, Union

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
        logger.info("AIService 初始化: base_url=%s, model=%s", self.base_url, self.model)

    async def stream_chat(
        self,
        system_prompt: str,
        user_message: str,
        history_messages: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 LLM，逐块 yield 文本内容。

        支持两种调用方式：
        1. 兼容旧接口：system_prompt + user_message（无 history_messages）
        2. 多轮对话：传入 history_messages 完整消息列表
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if history_messages is not None:
            messages = history_messages
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        logger.info("AI 流式调用开始: url=%s, model=%s, messages数=%d", url, self.model, len(messages))
        logger.info("AI system_prompt: %s", system_prompt[:500])
        logger.info("AI user_message: %s", user_message[:300])
        chunk_count = 0

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        logger.error("AI API error: status=%d body=%s", response.status_code, error_body[:500])
                        raise RuntimeError(f"AI API error: {response.status_code} - {error_body[:200]}")

                    raw_line_count = 0
                    async for line in response.aiter_lines():
                        raw_line_count += 1
                        line = line.strip()
                        if not line:
                            continue
                        # 打印前 10 行原始数据，方便排查格式问题
                        if raw_line_count <= 10:
                            logger.info("SSE raw line %d: %s", raw_line_count, line[:300])
                        if not line.startswith("data: "):
                            # 非 SSE 格式行，可能是错误 JSON
                            try:
                                err_obj = json.loads(line)
                                if err_obj.get("code") or err_obj.get("error"):
                                    err_msg = err_obj.get("msg") or err_obj.get("error", {}).get("message", line[:200])
                                    logger.error("AI API 业务错误: %s", err_msg)
                                    raise RuntimeError(f"AI API 业务错误: {err_msg}")
                            except json.JSONDecodeError:
                                pass
                            continue
                        data = line[6:]  # strip "data: " prefix
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            # 兼容不同 API 返回格式：choices[0].delta.content 或 choices[0].message.content
                            choice = chunk.get("choices", [{}])[0]
                            delta = choice.get("delta", {}) or choice.get("message", {})
                            content = delta.get("content", "")
                            if content:
                                chunk_count += 1
                                yield content
                        except json.JSONDecodeError:
                            logger.warning("JSON 解析失败: %s", data[:200])
                            continue

            logger.info("AI 流式调用完成: 共 %d 个有效 chunk", chunk_count)
        except Exception as e:
            logger.error("AI 流式调用异常: %s", e, exc_info=True)
            raise

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

    async def tool_call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> dict:
        """
        非流式调用 LLM，支持 function calling / tools。

        Returns:
            dict: message 对象，包含 content 和/或 tool_calls
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": 0,
            "max_tokens": 256,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        logger.info("AI tool_call: url=%s, model=%s, tools=%d", url, self.model, len(tools or []))

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                error_body = response.text[:500]
                logger.error("AI tool_call error: status=%d body=%s", response.status_code, error_body)
                raise RuntimeError(f"AI API error: {response.status_code} - {error_body}")
            result = response.json()
            return result["choices"][0]["message"]
