"""影响判断 Prompt 模板"""

IMPACT_ASSESSMENT_PROMPT = """你是一位专业的投资分析师。请分析以下财经事件对中国A股市场的影响。

事件标题：{title}
事件摘要：{summary}

请以JSON格式输出分析结果，包含以下字段：
{{
    "event_nature": "事件的本质属性（如：地缘政治+大宗商品、产业政策+新能源等）",
    "affected_industries_detail": [
        {{
            "name": "行业名称",
            "direction": "positive/negative/neutral",
            "reason": "影响原因（一句话）"
        }}
    ],
    "stock_impact_reasons": [
        {{
            "code": "股票代码",
            "name": "股票名称",
            "reason": "影响该股票的具体原因（一句话）"
        }}
    ]
}}

注意：
- 影响原因要具体，避免笼统描述
- 输出必须是有效的JSON格式
- 摘要不超过200字
"""

MORNING_BRIEFING_PROMPT = """你是一位专业的投资顾问。请根据以下数据为用户生成今日投资影响晨报。

影响事件列表：
{events}

自选股概览：
{portfolio}

请以JSON格式输出晨报内容：
{{
    "ai_summary": "一句话总结（30字以内）",
    "content": {{
        "impact_events": [
            {{
                "event_id": 0,
                "title": "事件标题",
                "sentiment": "positive/negative/neutral",
                "matched_stocks": [],
                "source_count": 1
            }}
        ],
        "portfolio_overview": [
            {{
                "code": "股票代码",
                "name": "股票名称",
                "last_close": 0.0,
                "direction": "positive/negative",
                "news_count": 0
            }}
        ],
        "today_focus": [
            {{
                "time": "HH:MM（如有具体时间）",
                "event": "今日关注事件"
            }}
        ]
    }}
}}

注意：
- ai_summary 简洁有力，突出重点
- today_focus 列出今日值得关注的财经事件
- 输出必须是有效的JSON格式
"""
