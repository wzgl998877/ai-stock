"""AI Service — 基于 httpx 流式调用 OpenAI 兼容 API"""

import json
import logging
import re
from typing import AsyncGenerator, NamedTuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# DSML 标签正则（DeepSeek Function Calling 格式泄漏）
# 匹配完整 <｜｜DSML｜｜tool_calls>...</｜｜DSML｜｜tool_calls> 块
_DSML_BLOCK = re.compile(
    r'<\uff5c\uff5cDSML\uff5c\uff5ctool_calls>.*?</\uff5c\uff5cDSML\uff5c\uff5ctool_calls>',
    re.DOTALL,
)
# 匹配残留的零散标签（开标签和闭合标签）
_DSML_TAG = re.compile(r'</?\uff5c\uff5cDSML\uff5c\uff5c[^>]*>')


def strip_dsml(text: str) -> str:
    """清除 DeepSeek DSML 标签（Function Calling 格式泄漏）"""
    if not text:
        return text
    text = _DSML_BLOCK.sub('', text)
    text = _DSML_TAG.sub('', text)
    return text


class StreamChunk(NamedTuple):
    """流式输出块：区分正式回答和推理思考"""
    type: str   # "content" = 正式回答, "reasoning" = 推理思考
    text: str
    agent_id: str = ""  # 可选：标识产出该块的Agent


class AIService:
    """统一 AI 服务抽象层，支持 OpenAI/DeepSeek/GLM 等兼容接口"""

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
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 100000,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        流式调用 LLM，逐块 yield StreamChunk。

        支持两种调用方式：
        1. 兼容旧接口：system_prompt + user_message（无 history_messages）
        2. 多轮对话：传入 history_messages 完整消息列表

        返回 StreamChunk，type 为 "content"（正式回答）或 "reasoning"（推理思考）。

        注意：部分推理模型（如 GLM-5.1）可能只输出 reasoning_content 而无 content，
        此时自动将 reasoning_content 作为 content 输出，确保前端有内容展示。
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

        use_model = model or self.model
        payload = {
            "model": use_model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info("AI 流式调用开始: url=%s, model=%s, messages数=%d", url, use_model, len(messages))
        for i, msg in enumerate(messages):
            role = msg.get("role", "?")
            content = msg.get("content", "")
            logger.info("  messages[%d] role=%s, content前200字=%s", i, role, (content or "")[:200])
        chunk_count = 0
        has_content = False  # 跟踪是否有正式 content 输出

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        logger.error("AI API error: status=%d body=%s", response.status_code, error_body[:500])
                        if response.status_code in (502, 503, 504):
                            raise RuntimeError(f"AI 服务暂时不可用（{response.status_code}），请稍后重试")
                        raise RuntimeError(f"AI API error: {response.status_code} - {error_body[:200]}")

                    raw_line_count = 0
                    first_data_line_found = False
                    reasoning_buffer = ""  # 缓存 reasoning_content，在无 content 时使用

                    async for line in response.aiter_lines():
                        raw_line_count += 1
                        line = line.strip()
                        if not line:
                            continue
                        if raw_line_count <= 10:
                            logger.info("SSE raw line %d: %s", raw_line_count, line[:300])

                        # 检测非 SSE 响应（如 HTML 错误页面）
                        if not first_data_line_found and raw_line_count == 1:
                            if line.startswith("<!") or line.startswith("<html") or line.startswith("<HTML"):
                                error_body = await response.aread()
                                logger.error("AI API 返回非 SSE 响应（HTML）: %s", error_body[:500])
                                raise RuntimeError(f"AI API 返回了 HTML 页面而非 SSE 流，请检查 base_url 配置。当前 URL: {url}")

                        if not line.startswith("data: "):
                            try:
                                err_obj = json.loads(line)
                                if err_obj.get("code") or err_obj.get("error"):
                                    err_msg = err_obj.get("msg") or err_obj.get("error", {}).get("message", line[:200])
                                    logger.error("AI API 业务错误: %s", err_msg)
                                    raise RuntimeError(f"AI API 业务错误: {err_msg}")
                            except json.JSONDecodeError:
                                pass
                            continue

                        first_data_line_found = True
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            # 防御：chunk 可能不是 dict，或 choices 为空
                            if not isinstance(chunk, dict):
                                continue
                            choices = chunk.get("choices")
                            if not choices or not isinstance(choices, list):
                                continue
                            choice = choices[0] if len(choices) > 0 else {}
                            delta = choice.get("delta", {}) or choice.get("message", {})
                            if not isinstance(delta, dict):
                                continue

                            # GLM 等推理模型：reasoning_content = 思考过程
                            reasoning = delta.get("reasoning_content", "")
                            if reasoning:
                                chunk_count += 1
                                reasoning_buffer += reasoning
                                yield StreamChunk("reasoning", reasoning)

                            # 正式回答内容
                            content = delta.get("content", "")
                            if content:
                                has_content = True
                                chunk_count += 1
                                yield StreamChunk("content", content)

                        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
                            logger.warning("SSE chunk 解析跳过: %s, data=%s", e, data[:200])
                            continue

                    # 流结束后，如果只有 reasoning_content 没有 content，将 reasoning 作为 content 输出
                    if not has_content and reasoning_buffer:
                        logger.warning(
                            "LLM 只输出了 reasoning_content（%d 字符），没有 content。将 reasoning 作为 content 输出。",
                            len(reasoning_buffer),
                        )
                        yield StreamChunk("content", reasoning_buffer)

            logger.info("AI 流式调用完成: 共 %d 个有效 chunk, has_content=%s", chunk_count, has_content)
        except Exception as e:
            logger.error("AI 流式调用异常: %s", e, exc_info=True)
            raise

    async def generate_title_and_summary(
        self, system_prompt: str, user_message: str, max_tokens: int = 256,
    ) -> tuple[str, str]:
        """非流式调用 LLM，生成标题和摘要（降级方案）"""
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
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(f"AI API error: {response.status_code}")
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return content, content

    async def tool_call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        model: str | None = None,
        temperature: float = 0,
        max_tokens: int = 256,
    ) -> dict:
        """非流式调用 LLM，支持 function calling / tools"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        use_model = model or self.model
        payload: dict = {
            "model": use_model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        logger.info("AI tool_call: url=%s, model=%s, tools=%d", url, use_model, len(tools or []))

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                error_body = response.text[:500]
                logger.error("AI tool_call error: status=%d body=%s", response.status_code, error_body)
                raise RuntimeError(f"AI API error: {response.status_code} - {error_body}")
            result = response.json()
            message = result["choices"][0]["message"]

            # DeepSeek 等模型在返回 tool_calls 时会同时在 content 中写入 DSML 标签和推理文本
            # 清除 content 防止泄漏到下游消息
            if message.get("tool_calls"):
                message["content"] = None

            return message

    async def stream_chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 100000,
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式调用 LLM，支持 function calling + 流式输出"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        use_model = model or self.model
        payload: dict = {
            "model": use_model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        logger.info("AI stream_chat_with_tools: url=%s, model=%s, tools=%d", url, use_model, len(tools or []))
        for i, msg in enumerate(messages):
            role = msg.get("role", "?")
            content = msg.get("content", "")
            logger.info("  messages[%d] role=%s, content前200字=%s", i, role, (content or "")[:200])

        has_content = False
        reasoning_buffer = ""

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise RuntimeError(f"AI API error: {response.status_code} - {error_body[:200]}")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if not isinstance(chunk, dict):
                            continue
                        choices = chunk.get("choices")
                        if not choices or not isinstance(choices, list):
                            continue
                        choice = choices[0] if len(choices) > 0 else {}
                        delta = choice.get("delta", {}) or choice.get("message", {})
                        if not isinstance(delta, dict):
                            continue

                        reasoning = delta.get("reasoning_content", "")
                        if reasoning:
                            reasoning_buffer += reasoning
                            yield StreamChunk("reasoning", reasoning)

                        content = delta.get("content", "")
                        if content:
                            has_content = True
                            yield StreamChunk("content", content)
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        continue

                # 如果只有 reasoning_content 没有 content，将 reasoning 作为 content 输出
                if not has_content and reasoning_buffer:
                    logger.warning(
                        "stream_chat_with_tools: LLM 只输出了 reasoning_content，将 reasoning 作为 content 输出",
                    )
                    yield StreamChunk("content", reasoning_buffer)
