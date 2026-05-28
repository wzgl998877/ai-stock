"""AI Service — 基于 httpx 流式调用 OpenAI 兼容 API"""

import json
import logging
import re
import time
import uuid
from typing import AsyncGenerator, NamedTuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# DeepSeek DSML 兼容层
# ============================================================
# DeepSeek 模型内部使用 DSML 格式表达 tool calls。
# 当 API 未能正确解析为结构化 tool_calls 时，需从 content 中手动提取。
#
# 核心原则：
#   - DSML 标签只出现在「工具调用」场景（tool_call / stream_chat_with_tools）
#   - 纯内容生成（stream_chat）不传递 tools，模型不应输出 DSML，无需处理
#   - content 中的 DSML 是工具调用的序列化形式，对调用方无用，应丢弃

DSML_TOOL_CALLS_RE = re.compile(
    r"<｜｜DSML｜｜tool_calls>(.*?)</｜｜DSML｜｜tool_calls>",
    re.DOTALL,
)
DSML_INVOKE_RE = re.compile(
    r"<｜｜DSML｜｜invoke\s+name=\"([^\"]+)\">(.*?)</｜｜DSML｜｜invoke>",
    re.DOTALL,
)
DSML_PARAM_RE = re.compile(
    r"<｜｜DSML｜｜parameter\s+name=\"([^\"]+)\"(?:\s+string=\"([^\"]*)\")?>(.*?)</｜｜DSML｜｜parameter>",
    re.DOTALL,
)

# 检测 content 中是否包含 DSML 标签（用于流式场景判断）
_DSML_MARKER = "<｜｜"


def _parse_dsml_tool_calls(content: str) -> list[dict]:
    """将 DeepSeek DSML 格式的 tool_calls 解析为 OpenAI 兼容结构"""
    tool_calls = []
    for tc_match in DSML_TOOL_CALLS_RE.finditer(content):
        tc_body = tc_match.group(1)
        for inv_match in DSML_INVOKE_RE.finditer(tc_body):
            func_name = inv_match.group(1)
            inv_body = inv_match.group(2)
            args = {}
            for param_match in DSML_PARAM_RE.finditer(inv_body):
                p_name = param_match.group(1)
                p_value = param_match.group(3).strip()
                args[p_name] = p_value
            tool_calls.append({
                "id": f"call_{uuid.uuid4().hex[:24]}",
                "type": "function",
                "function": {
                    "name": func_name,
                    "arguments": json.dumps(args, ensure_ascii=False),
                },
            })
    return tool_calls


def _is_dsml_chunk(text: str) -> bool:
    """判断文本是否包含 DSML 标签（快速检测，不做正则匹配）"""
    return _DSML_MARKER in text


class StreamChunk(NamedTuple):
    """流式输出块：区分正式回答和推理思考"""
    type: str   # "content" = 正式回答, "reasoning" = 推理思考, "tool_calls" = 工具调用
    text: str
    tool_calls: list[dict] | None = None  # DSML 解析出的工具调用
    agent_id: str = ""  # 可选：标识产出该块的Agent


class AIService:
    """统一 AI 服务抽象层，支持 OpenAI/DeepSeek/GLM 等兼容接口"""

    # 流式调用专用超时：connect 短，read 长（推理模型思考阶段可能数分钟无数据）
    STREAM_TIMEOUT = httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=30.0)
    # 非流式调用超时：单次请求总耗时上限
    API_TIMEOUT = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.llm_model
        logger.info("AIService 初始化: base_url=%s, model=%s", self.base_url, self.model)

    # ------------------------------------------------------------------
    # stream_chat — 纯内容生成，不涉及 tools
    # ------------------------------------------------------------------

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

        纯内容生成场景（分析师报告、辩论等），不传递 tools。
        content 原样透传，不做任何 DSML 处理。
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
            async with httpx.AsyncClient(timeout=self.STREAM_TIMEOUT) as client:
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
                    dsml_buffer = ""
                    saw_dsml_tool_call = False

                    # === 诊断统计 ===
                    t_stream_start = time.time()
                    t_last_log = t_stream_start
                    reasoning_chunks = 0
                    content_chunks = 0
                    reasoning_chars = 0
                    content_chars = 0
                    finish_reason = None
                    phase = "init"  # init → reasoning → content → done

                    async for line in response.aiter_lines():
                        raw_line_count += 1
                        line = line.strip()
                        if not line:
                            continue
                        # 前 5 行详细日志，之后只在关键时刻打日志
                        if raw_line_count <= 5:
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
                            logger.info(
                                "[stream] 收到 [DONE], phase=%s, chunks=%d(reasoning=%d,content=%d), "
                                "finish_reason=%s, 耗时 %.1fs",
                                phase, chunk_count, reasoning_chunks, content_chunks,
                                finish_reason, time.time() - t_stream_start,
                            )
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

                            # GLM 等推理模型：reasoning_content = 思考过程
                            reasoning = delta.get("reasoning_content", "")
                            if reasoning:
                                chunk_count += 1
                                reasoning_chunks += 1
                                reasoning_chars += len(reasoning)
                                reasoning_buffer += reasoning
                                if phase == "init":
                                    phase = "reasoning"
                                    logger.info("[stream] 进入推理阶段, 耗时 %.1fs", time.time() - t_stream_start)
                                yield StreamChunk("reasoning", reasoning)

                            # 正式回答内容 — 原样透传
                            content = delta.get("content", "")
                            if content:
                                combined = dsml_buffer + content
                                if _is_dsml_chunk(combined):
                                    dsml_buffer = combined
                                    if "</｜｜DSML｜｜tool_calls>" in dsml_buffer:
                                        parsed = _parse_dsml_tool_calls(dsml_buffer)
                                        saw_dsml_tool_call = bool(parsed)
                                        logger.warning(
                                            "stream_chat 收到 DSML tool_calls，已拦截不作为正文输出: parsed=%d",
                                            len(parsed),
                                        )
                                        dsml_buffer = ""
                                    continue

                                has_content = True
                                chunk_count += 1
                                content_chunks += 1
                                content_chars += len(content)
                                if phase == "reasoning" or phase == "init":
                                    phase = "content"
                                    logger.info(
                                        "[stream] 推理→内容阶段切换, 推理 %d chunks/%d 字符, 耗时 %.1fs",
                                        reasoning_chunks, reasoning_chars, time.time() - t_stream_start,
                                    )
                                yield StreamChunk("content", content)

                            # 检测 finish_reason
                            fr = choice.get("finish_reason")
                            if fr:
                                finish_reason = fr

                            # === 周期性诊断日志（每 30 秒或每 500 chunks）===
                            t_now = time.time()
                            if t_now - t_last_log >= 30 or chunk_count % 500 == 0:
                                logger.info(
                                    "[stream] 心跳: phase=%s, chunks=%d(reasoning=%d,content=%d), "
                                    "reasoning_chars=%d, content_chars=%d, raw_lines=%d, finish_reason=%s, 耗时 %.1fs",
                                    phase, chunk_count, reasoning_chunks, content_chunks,
                                    reasoning_chars, content_chars, raw_line_count,
                                    finish_reason, t_now - t_stream_start,
                                )
                                t_last_log = t_now

                        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
                            logger.warning("SSE chunk 解析跳过: %s, data=%s", e, data[:200])
                            continue

                    if dsml_buffer and _is_dsml_chunk(dsml_buffer):
                        parsed = _parse_dsml_tool_calls(dsml_buffer)
                        saw_dsml_tool_call = saw_dsml_tool_call or bool(parsed)
                        logger.warning(
                            "stream_chat 收到未闭合 DSML 内容，已拦截不作为正文输出: parsed=%d",
                            len(parsed),
                        )

                    if not has_content and saw_dsml_tool_call:
                        logger.warning("stream_chat 只收到 DSML tool_calls，没有正文内容。")
                    elif not has_content and reasoning_buffer:
                        logger.warning(
                            "LLM 只输出了 reasoning_content（%d 字符），没有 content。将 reasoning 作为 content 输出。",
                            len(reasoning_buffer),
                        )
                        yield StreamChunk("content", reasoning_buffer)

            logger.info(
                "AI 流式调用完成: 共 %d chunks(reasoning=%d,content=%d), "
                "reasoning_chars=%d, content_chars=%d, has_content=%s, 耗时 %.1fs",
                chunk_count, reasoning_chunks, content_chunks,
                reasoning_chars, content_chars, has_content,
                time.time() - t_stream_start,
            )
        except httpx.ReadTimeout as e:
            logger.error(
                "AI 流式调用 ReadTimeout: 已等待 %.1fs, 收到 %d chunks(reasoning=%d,content=%d), "
                "phase=%s, finish_reason=%s — 模型思考阶段可能超过 read timeout",
                time.time() - t_stream_start, chunk_count, reasoning_chunks, content_chunks,
                phase, finish_reason,
            )
            raise
        except Exception as e:
            logger.error(
                "AI 流式调用异常: %s, phase=%s, chunks=%d, 耗时 %.1fs",
                e, phase, chunk_count, time.time() - t_stream_start, exc_info=True,
            )
            raise

    # ------------------------------------------------------------------
    # generate_title_and_summary — 非流式，纯内容
    # ------------------------------------------------------------------

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

        async with httpx.AsyncClient(timeout=self.API_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(f"AI API error: {response.status_code}")
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return content, content

    # ------------------------------------------------------------------
    # tool_call — 非流式工具调用
    # ------------------------------------------------------------------

    async def tool_call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        model: str | None = None,
        temperature: float = 0,
        max_tokens: int = 4096,
    ) -> dict:
        """非流式调用 LLM，支持 function calling / tools。

        DeepSeek 兼容：当 API 未将 DSML 转为结构化 tool_calls 时，
        从 content 中解析并补充 tool_calls，然后清空 content。
        """
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

        async with httpx.AsyncClient(timeout=self.API_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                error_body = response.text[:500]
                logger.error("AI tool_call error: status=%d body=%s", response.status_code, error_body)
                raise RuntimeError(f"AI API error: {response.status_code} - {error_body}")
            result = response.json()
            message = result["choices"][0]["message"]

            # DeepSeek DSML 兼容：API 未返回结构化 tool_calls 时，从 content 中解析
            if tools and not message.get("tool_calls"):
                content = message.get("content", "") or ""
                if _is_dsml_chunk(content):
                    dsml_calls = _parse_dsml_tool_calls(content)
                    if dsml_calls:
                        logger.info(
                            "DSML 兼容：从 content 中解析出 %d 个 tool_calls（模型: %s）",
                            len(dsml_calls), use_model,
                        )
                        message["tool_calls"] = dsml_calls
                    # content 是 DSML 格式的工具调用，对调用方无用，清空
                    message["content"] = None

            return message

    # ------------------------------------------------------------------
    # stream_chat_with_tools — 流式 + 工具调用
    # ------------------------------------------------------------------

    async def stream_chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 100000,
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式调用 LLM，支持 function calling + 流式输出。

        DeepSeek 兼容：content 中的 DSML 标签是工具调用的序列化形式，
        缓冲后解析为 tool_calls，不作为内容透传。
        """
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
        dsml_buffer = ""  # 缓冲跨 chunk 的 DSML 内容，用于解析 tool_calls

        async with httpx.AsyncClient(timeout=self.STREAM_TIMEOUT) as client:
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
                            # 判断是否为 DSML 内容
                            # DSML 是工具调用的序列化形式，不应作为内容透传
                            combined = dsml_buffer + content
                            if _is_dsml_chunk(combined):
                                # 缓冲 DSML 内容，等完整后再解析为 tool_calls
                                dsml_buffer = combined
                                # 检查是否已闭合（包含完整的 tool_calls 块）
                                if "</｜｜DSML｜｜tool_calls>" in dsml_buffer:
                                    parsed = _parse_dsml_tool_calls(dsml_buffer)
                                    if parsed:
                                        logger.info(
                                            "DSML 流式：解析出 %d 个 tool_calls（模型: %s）",
                                            len(parsed), use_model,
                                        )
                                        yield StreamChunk("tool_calls", "", tool_calls=parsed)
                                    dsml_buffer = ""
                                continue

                            # 非 DSML 内容：原样透传
                            dsml_buffer = ""
                            has_content = True
                            yield StreamChunk("content", content)

                        # 结构化 tool_calls（API 正常返回时走这里）
                        tool_calls_delta = delta.get("tool_calls")
                        if tool_calls_delta:
                            yield StreamChunk("tool_calls", "", tool_calls=tool_calls_delta)

                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        continue

                # 流结束时处理残余 DSML 缓冲
                if dsml_buffer and _is_dsml_chunk(dsml_buffer):
                    parsed = _parse_dsml_tool_calls(dsml_buffer)
                    if parsed:
                        logger.info("DSML 流式（残余）：解析出 %d 个 tool_calls", len(parsed))
                        yield StreamChunk("tool_calls", "", tool_calls=parsed)

                # 如果只有 reasoning_content 没有 content，将 reasoning 作为 content 输出
                if not has_content and reasoning_buffer:
                    logger.warning(
                        "stream_chat_with_tools: LLM 只输出了 reasoning_content，将 reasoning 作为 content 输出",
                    )
                    yield StreamChunk("content", reasoning_buffer)
