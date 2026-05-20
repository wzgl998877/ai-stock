"""分析工作流 State 定义（三层结构）"""

from typing import TypedDict, Optional, Literal


class AnalysisState(TypedDict, total=False):
    """LangGraph 工作流全局状态

    Input:      source, event_type
    Working:    input_type, need_search, search_query, web_search_results,
                raw_text, search_results
    Output:     error, thinking_done_msg
    """

    # === Input ===
    source: str                          # 用户原始输入（URL / 文件路径 / 文本）
    event_type: str                      # 事件类型
    user_id: str                         # 当前用户 ID
    use_knowledge_base: bool             # 是否启用知识库检索（用户前端开关）

    # === Working ===
    input_type: Literal["url", "file", "text"]  # classify 节点判断结果
    need_search: bool                    # agent_classify: 是否需要搜索互联网
    search_query: str                    # agent_classify: 搜索关键词
    web_search_results: list[dict]       # web_search 节点输出：互联网搜索结果
    raw_text: str                        # load 节点输出：清洗后的纯文本
    search_results: list[dict]           # retrieve 节点输出：相关历史文章
    summarized_context: str              # summarize_context 节点输出：提炼后的上下文摘要

    # === Output ===
    error: Optional[str]                 # 错误信息（各节点内部捕获后填充）
    thinking_done_msg: str               # 节点完成时的思维链描述（供 ChatUseCase 使用）
