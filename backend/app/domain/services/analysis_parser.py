"""AnalysisParser — 解析 LLM 输出为六段/七段结构化结果"""

import re
from typing import Optional, Dict, List, Tuple

from app.domain.value_objects.event_type import EventType


class AnalysisParseResult:
    """解析结果"""
    def __init__(self):
        self.sections: Dict[str, str] = {}
        self.title: Optional[str] = None
        self.summary: Optional[str] = None
        self.raw_content: str = ""
        self.industry_names: List[str] = []
        self.chain_table_raw: Optional[str] = None
        self.is_degraded: bool = False  # 降级标记


class AnalysisParser:
    """解析 LLM 流式输出的结构化内容"""

    # 固定章节标题映射
    STANDARD_SECTIONS = [
        "事件背景", "影响逻辑", "受益行业", "受损行业", "推荐关注股票", "风险提示"
    ]
    CHAIN_SECTION = "产业链传导表"

    def parse(self, full_content: str, event_type: str) -> AnalysisParseResult:
        result = AnalysisParseResult()
        result.raw_content = full_content

        # 提取 TITLE 和 SUMMARY
        title_match = re.search(r"^TITLE:\s*(.+)$", full_content, re.MULTILINE)
        summary_match = re.search(r"^SUMMARY:\s*(.+)$", full_content, re.MULTILINE)
        if title_match:
            result.title = title_match.group(1).strip()[:50]  # ≤15字中文 ≈ 50字节
        if summary_match:
            result.summary = summary_match.group(1).strip()[:200]

        # 按二级标题拆分章节
        sections = re.split(r"^##\s+", full_content, flags=re.MULTILINE)
        for section_text in sections:
            lines = section_text.strip().split("\n", 1)
            if not lines:
                continue
            section_title = lines[0].strip()
            section_body = lines[1].strip() if len(lines) > 1 else ""

            # 跳过 TITLE/SUMMARY 行
            if section_title.startswith("TITLE:") or section_title.startswith("SUMMARY:"):
                continue

            result.sections[section_title] = section_body

            # 提取产业链传导表原始内容
            if self.CHAIN_SECTION in section_title:
                result.chain_table_raw = section_body

        # 从"受益行业"和"受损行业"章节提取行业名称
        self._extract_industry_names(result)

        # 检查是否需要降级
        expected_count = 7 if event_type == EventType.SUPPLY_CHAIN else 6
        if len(result.sections) < expected_count - 1:
            result.is_degraded = True

        return result

    def _extract_industry_names(self, result: AnalysisParseResult) -> None:
        """从受益行业/受损行业章节提取行业名称"""
        names = set()
        for section_key in ["受益行业", "受损行业"]:
            content = result.sections.get(section_key, "")
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # 去掉常见的前缀符号: "- ", "* ", "**", "1. ", "1) " 等
                cleaned = re.sub(r"^[-*•]\s*", "", line)
                cleaned = re.sub(r"^\*+", "", cleaned)
                cleaned = re.sub(r"^\d+[\.\)、]\s*", "", cleaned)
                # 去掉尾部 markdown 加粗标记
                cleaned = re.sub(r"\*+$", "", cleaned)

                # 格式1: "行业名称：逻辑" 或 "行业名称:逻辑"
                match = re.match(r"^([^：:]+)[：:]", cleaned)
                if match:
                    name = match.group(1).strip()
                    if self._is_valid_industry_name(name):
                        names.add(name)
                        continue

                # 格式2: "**行业名称**：逻辑" 或 "**行业名称**"
                match = re.match(r"^\*{1,2}([^*]+)\*{1,2}", cleaned)
                if match:
                    name = match.group(1).strip()
                    if self._is_valid_industry_name(name):
                        names.add(name)
                        continue

        # 从产业链传导表中提取行业名称
        chain_content = result.sections.get("产业链传导表", "")
        if chain_content:
            for line in chain_content.split("\n"):
                line = line.strip()
                if not line or line.startswith("|---") or line.startswith("| --") or line.startswith("|-"):
                    continue
                if "传导层级" in line or "受影响行业" in line:
                    continue
                cells = [c.strip() for c in line.split("|")]
                cells = [c for c in cells if c]
                if len(cells) >= 2:
                    industry_name = cells[1].strip()
                    if self._is_valid_industry_name(industry_name):
                        names.add(industry_name)

        result.industry_names = list(names)

    @staticmethod
    def _is_valid_industry_name(name: str) -> bool:
        """判断提取的名称是否像行业名称"""
        if not name or len(name) > 10:
            return False
        if name.startswith("-") or name.startswith("|"):
            return False
        # 排除明显的非行业文本
        skip_words = ["注意", "提示", "风险", "免责", "以上", "以下", "投资建议"]
        if any(w in name for w in skip_words):
            return False
        return True

    def extract_chain_table(self, chain_raw: str) -> List[Dict]:
        """解析产业链传导表 Markdown 表格为结构化数据"""
        if not chain_raw:
            return []

        rows = []
        lines = chain_raw.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("|---") or line.startswith("| ---"):
                continue
            if line.startswith("| 传导层级"):
                continue  # skip header

            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c]  # remove empty from leading/trailing |

            if len(cells) >= 3:
                rows.append({
                    "level": len(rows) + 1,
                    "industry": cells[1] if len(cells) > 1 else "",
                    "logic": cells[2] if len(cells) > 2 else "",
                    "direction": cells[3] if len(cells) > 3 else "",
                    "degree": cells[4] if len(cells) > 4 else "",
                    "timing": cells[5] if len(cells) > 5 else "",
                    "stocks_raw": cells[6] if len(cells) > 6 else "",
                })

        # 最多5层
        return rows[:5]

    def parse_stock_analysis(self, analysis_data: dict) -> AnalysisParseResult:
        """解析多Agent个股分析的结构化数据，生成标题和摘要"""
        result = AnalysisParseResult()

        stock_name = analysis_data.get("stock_name", "")
        decision = analysis_data.get("decision", {})
        action = decision.get("action", "")

        # 生成标题：股票名 + 操作方向
        if stock_name:
            result.title = f"{stock_name}{'看多' if action == '买入' else '看空' if action == '卖出' else '分析'}报告"
            if len(result.title) > 15:
                result.title = result.title[:15]

        # 生成摘要：从各Agent报告中提取关键信息
        summaries = []
        agents = analysis_data.get("agents", {})
        for agent_key in ["market", "fundamentals", "news", "sentiment"]:
            agent_data = agents.get(agent_key, {})
            summary = agent_data.get("summary", "")
            if summary:
                summaries.append(summary)

        if summaries:
            combined = "；".join(summaries[:3])
            result.summary = combined[:80] if len(combined) > 80 else combined
        elif action:
            result.summary = f"建议{action}，置信度{decision.get('confidence', 0)*100:.0f}%"

        # 从分析数据中提取行业
        industries = analysis_data.get("industries", [])
        if industries:
            result.industry_names = industries

        # 从基本面报告中尝试提取行业
        if not result.industry_names:
            fundamentals = agents.get("fundamentals", {}).get("summary", "")
            for industry in ["电力设备", "食品饮料", "医药生物", "银行", "非银金融",
                           "电子", "计算机", "通信", "汽车", "有色金属", "基础化工"]:
                if industry in fundamentals:
                    result.industry_names.append(industry)

        return result
