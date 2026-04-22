"""消息清除节点 — 清理指定 Agent 的工具调用中间消息，只保留最终分析结果"""

import logging

logger = logging.getLogger(__name__)


def create_msg_clear_node(agent_name: str):
    """
    闭包工厂：创建消息清除节点。

    清除 state["messages"] 中指定 agent 的工具调用消息（role=tool），
    只保留最终的分析结果消息。

    Args:
        agent_name: Agent 名称，用于日志标识
    """

    async def msg_clear_node(state: dict) -> dict:
        messages = state.get("messages", [])
        if not messages:
            logger.info("[msg_clear] %s: messages 为空，跳过清理", agent_name)
            return {"messages": []}

        cleaned_messages = []
        for msg in messages:
            role = msg.get("role", "")
            # 保留 system、user、assistant 消息，清除 tool 消息
            if role != "tool":
                cleaned_messages.append(msg)

        removed_count = len(messages) - len(cleaned_messages)
        logger.info(
            "[msg_clear] %s: 清理完成, 原始=%d, 清理后=%d, 移除tool消息=%d",
            agent_name, len(messages), len(cleaned_messages), removed_count,
        )

        return {"messages": cleaned_messages}

    return msg_clear_node
