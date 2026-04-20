"""分析工作流 State 定义（三层结构）"""

from typing import TypedDict, Optional, Literal


class AnalysisState(TypedDict, total=False):
    """LangGraph 工作流全局状态

    Input:      source, event_type
    Working:    input_type, raw_text, search_results
    Output:     error, thinking_done_msg
    """

    # === Input ===
    source: str                          # 用户原始输入（URL / 文件路径 / 文本）
    event_type: str                      # 事件类型

    # === Working ===
    input_type: Literal["url", "file", "text"]  # classify 节点判断结果
    raw_text: str                        # load 节点输出：清洗后的纯文本
    search_results: list[dict]           # retrieve 节点输出：相关历史文章

    # === Output ===
    error: Optional[str]                 # 错误信息（各节点内部捕获后填充）
    thinking_done_msg: str               # 节点完成时的思维链描述（供 ChatUseCase 使用）
