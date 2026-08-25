"""微信指令工具基类与注册表（specs/010 contracts/tool-registry.md）。

扩展契约核心：新增一条微信指令 = 新建 WeChatTool 子类 + ``registry.register``
一行，**不得改动 gateway / router / dispatcher**（spec FR-020/021）。

- 声明即文档：``description`` + ``parameters`` 被 ``export_llm_tools`` 原样
  导出为 OpenAI tools schema，质量直接决定 LLM 识别率；
- 执行契约：dispatcher 注入 ``ToolContext``（参数已校验），工具返回
  ``ToolResult``；异常由 dispatcher 兜底记 failed 推 FAIL，禁止静默吞。
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

# 摘要硬上限（iLink 单条 ~4000 字符，留余量；research D11）
SUMMARY_MAX_CHARS = 3800
# 信号类摘要统一尾注（宪法 II：不构成投资建议）
DISCLAIMER_SUFFIX = "（数据为算法计算结果，不构成投资建议）"


@dataclass
class ToolContext:
    """dispatcher 注入的执行上下文。"""

    user_id: str                      # 已通过授权校验的发送者
    params: dict                      # 已通过 schema + 白名单校验的参数
    session_factory: Any              # async_sessionmaker；每次用独立 session
    report_progress: Callable[[str], Awaitable[None]]  # 更新进度（"3/10"）；快指令为 no-op
    cmd_id: int = 0                   # 当前指令自身 id（find_running 排除自己，防自查询误报）


@dataclass
class ToolResult:
    """工具执行结果。"""

    summary: str                                  # 推送给用户的终态摘要
    succeeded: int = 0                            # 成功数
    failed_items: list[dict] = field(default_factory=list)  # [{code, reason}]
    meta: dict = field(default_factory=dict)      # 附加数据（如 task_id）

    def __post_init__(self) -> None:
        if len(self.summary) > SUMMARY_MAX_CHARS:
            self.summary = self.summary[: SUMMARY_MAX_CHARS - 3] + "..."


class WeChatTool(ABC):
    """一条微信指令的声明与执行体（契约见 contracts/tool-registry.md §1）。"""

    name: str = ""              # ^[a-z_]+$，全局唯一，即 LLM function name
    domain: str = ""            # strategy | market | sync | analysis | system
    description: str = ""       # 给 LLM 的中文能力描述，须含触发示例
    parameters: dict = {}       # JSON Schema 风格参数声明
    kind: str = "fast"          # "fast"（同步秒回）| "slow"（后台+两段式应答）
    lock_key: Optional[str] = None  # 同类互斥锁类别；None=允许并行
    risk: str = "read_only"     # "read_only" | "write"（write 强制二次确认）
    patterns: list[str] = []    # 精确匹配正则（规则层）；空=仅 LLM 可达
    usage: str = ""             # 帮助文案展示的命令示例（如"跑缠论 / 缠论 002940"）

    @abstractmethod
    async def execute(self, ctx: ToolContext) -> ToolResult:
        """执行体：参数已校验；内部异常上抛由 dispatcher 兜底。"""

    def match_pattern(self, text: str) -> Optional[dict]:
        """规则层匹配：命中返回参数 dict（含命名分组），未命中返回 None。"""
        for pat in self.patterns:
            m = re.match(pat, text.strip())
            if m:
                params = {k: v for k, v in m.groupdict().items() if v is not None}
                return params or {}
        return None


class ToolRegistry:
    """注册表：register / 规则匹配 / 导出 LLM tools schema。"""

    def __init__(self) -> None:
        self._tools: dict[str, WeChatTool] = {}

    def register(self, tool: WeChatTool) -> None:
        if not re.fullmatch(r"[a-z_]+", tool.name):
            raise ValueError(f"工具名须匹配 ^[a-z_]+$: {tool.name!r}")
        if tool.name in self._tools:
            raise ValueError(f"工具重名: {tool.name}")
        if tool.risk == "write" and tool.patterns:
            # 契约禁止：写操作必须走 LLM 显式意图 + 二次确认，不进规则快路径
            raise ValueError(f"write 工具不允许配置 patterns: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[WeChatTool]:
        return self._tools.get(name)

    def all(self) -> list[WeChatTool]:
        return list(self._tools.values())

    def match_pattern(self, text: str) -> Optional[tuple[WeChatTool, dict]]:
        """全注册表规则匹配：返回 (tool, params) 或 None。"""
        for tool in self._tools.values():
            params = tool.match_pattern(text)
            if params is not None:
                return tool, params
        return None

    def export_llm_tools(self) -> list[dict]:
        """导出 OpenAI tools schema（含 chat 兜底意图，research D2）。"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters,
                    },
                },
            }
            for tool in self._tools.values()
        ]
        tools.append({
            "type": "function",
            "function": {
                "name": "chat",
                "description": (
                    "闲聊、与系统功能无关的对话、或无法确定用户想执行哪个指令时选择此项。"
                    "不要把模糊指令强行映射到具体工具。"
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        })
        return tools


# 全局注册表（tools/__init__.py 中 import 即注册）
registry = ToolRegistry()
