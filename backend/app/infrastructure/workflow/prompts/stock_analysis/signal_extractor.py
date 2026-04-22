"""信号提取 Prompt模板"""

SYSTEM_PROMPT = """你是一位数据提取专家。从风险裁决中提取结构化的交易信号。所有分析内容仅供学习研究参考，不构成任何投资建议。"""

USER_TEMPLATE = """请从以下文本中提取结构化交易信号：{risk_judgment_text}\n\n请用以下JSON格式输出：```json\n{"action": "买入/持有/卖出", "target_price": 数字, "confidence": 0-100, "risk_score": 0-100, "reasoning": "简短决策理由"}\n```"""
