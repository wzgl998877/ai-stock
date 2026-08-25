"""微信指令工具注册入口（specs/010 contracts/tool-registry.md §3）。

**新增指令的唯一扩展点**：新建 WeChatTool 子类文件 + 此处 import 即注册。
不得改动 gateway / intent_router / command_dispatcher（spec FR-020/021）。
"""

from app.application.wechat.tools.base import (  # noqa: F401
    ToolContext,
    ToolResult,
    WeChatTool,
    registry,
)
from app.application.wechat.tools.chanlun_tools import (  # noqa: F401
    ChanlunStatusTool,
    RunChanlunTool,
)
from app.application.wechat.tools.system_tools import CmdHistoryTool  # noqa: F401

# P1 三件套（specs/010 tasks.md Phase 3/4）
registry.register(RunChanlunTool())
registry.register(ChanlunStatusTool())
registry.register(CmdHistoryTool())
