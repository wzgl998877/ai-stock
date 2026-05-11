"""MetadataExtractor — 从 AI 分析内容中统一提取股票和行业元数据"""

import json
import logging
import re
from typing import List

from app.domain.services.analysis_parser import AnalysisParser
from app.infrastructure.ai.ai_service import AIService
from app.infrastructure.ai.prompts import SW_LEVEL1_INDUSTRIES

logger = logging.getLogger(__name__)

# 申万一级行业标准名集合（用于校验）
SW_INDUSTRIES_SET = set(SW_LEVEL1_INDUSTRIES.split("、"))


class MetadataExtractor:
    """统一元数据提取：股票（数据库匹配）+ 行业（解析器 + LLM 兜底）"""

    def __init__(self, ai_service: AIService, stock_list: list[dict] | None = None):
        self.ai_service = ai_service
        self.stock_list = stock_list or []
        self.parser = AnalysisParser()

        # 构建股票查找索引
        self._code_map: dict[str, dict] = {}    # code → stock info
        self._name_map: dict[str, dict] = {}    # name → stock info
        for s in self.stock_list:
            self._code_map[s["code"]] = s
            self._name_map[s["name"]] = s

    # ================================================================
    # 公共入口
    # ================================================================

    async def extract(self, content: str, event_type: str) -> dict:
        """
        从 AI 输出内容中提取行业和股票（含利好/利空标注），全部用正则，不额外调 LLM。

        Returns:
            {"industries": ["电子", ...], "industry_sentiments": [{"name": "电子", "sentiment": "positive"}, ...],
             "stocks": [{"code": "600519", "name": "贵州茅台", "sentiment": "positive"}, ...]}
        """
        # 1. 解析器提取行业（含利好/利空方向）
        parse_result = self.parser.parse(content, event_type)
        raw_industries = parse_result.industry_names
        raw_sentiments = parse_result.industry_sentiments

        # 2. 校验行业名（申万标准）
        validated = self._validate_industries(raw_industries)
        if not validated:
            logger.info("[行业提取] 解析器未提取到有效行业，降级调用 LLM")
            validated = await self._extract_industries_by_llm(content)
            raw_sentiments = []  # LLM 兜底时无方向信息

        # 3. 过滤 sentiments 只保留校验通过的行业名
        validated_set = set(validated)
        industry_sentiments = [
            s for s in raw_sentiments
            if s["name"] in validated_set or any(v in s["name"] or s["name"] in v for v in validated_set)
        ]
        # 模糊匹配修正：把 sentiments 中的 name 替换为校验后的标准名
        name_map = {}
        for s in industry_sentiments:
            for v in validated:
                if v in s["name"] or s["name"] in v:
                    name_map[s["name"]] = v
                    break
        industry_sentiments = [
            {"name": name_map.get(s["name"], s["name"]), "sentiment": s["sentiment"]}
            for s in industry_sentiments
        ]

        # 4. 提取股票并根据上下文判断利好/利空
        stocks = self._extract_stocks_with_sentiment(content)

        # 5. 统一去重
        industries = list(dict.fromkeys(validated))
        seen_codes: set[str] = set()
        unique_stocks = []
        for s in stocks:
            if s["code"] not in seen_codes:
                seen_codes.add(s["code"])
                unique_stocks.append(s)
        seen_industries = set()
        unique_industry_sentiments = []
        for item in industry_sentiments:
            if item["name"] not in seen_industries:
                seen_industries.add(item["name"])
                unique_industry_sentiments.append(item)

        logger.info("[元数据提取] 行业=%s, sentiments=%s, stocks=%d",
                    industries, unique_industry_sentiments, len(unique_stocks))

        return {
            "industries": industries,
            "industry_sentiments": unique_industry_sentiments,
            "stocks": unique_stocks,
        }

    # ================================================================
    # 行业校验 + LLM 兜底
    # ================================================================

    def _validate_industries(self, names: List[str]) -> List[str]:
        """校验行业名是否属于 31 个申万一级行业（支持模糊匹配），去重"""
        validated: list[str] = []
        seen = set()
        for name in names:
            name = name.strip()
            if not name:
                continue
            matched = None
            # 精确匹配
            if name in SW_INDUSTRIES_SET:
                matched = name
            else:
                # 模糊匹配：包含关系（如 "电子行业" → "电子"）
                for sw_name in SW_INDUSTRIES_SET:
                    if sw_name in name or name in sw_name:
                        matched = sw_name
                        break
            if matched and matched not in seen:
                seen.add(matched)
                validated.append(matched)
        return validated

    async def _extract_industries_by_llm(self, content: str) -> List[str]:
        """LLM 兜底提取行业"""
        prompt = _INDUSTRY_PROMPT.format(
            industries=SW_LEVEL1_INDUSTRIES,
            content=content,
        )
        try:
            result, _ = await self.ai_service.generate_title_and_summary(
                system_prompt="请从文章中提取申万一级行业名称，返回 JSON 数组。",
                user_message=prompt,
            )
            return self._parse_llm_industries(result)
        except Exception as e:
            logger.error("[行业提取] LLM 调用失败: %s", e)
            return []

    @staticmethod
    def _parse_llm_industries(text: str) -> List[str]:
        """解析 LLM 返回的行业 JSON"""
        if not text:
            return []
        # markdown code block
        code_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if code_match:
            text = code_match.group(1)
        text = text.strip()
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [s for s in data if isinstance(s, str) and s.strip() in SW_INDUSTRIES_SET]
        except json.JSONDecodeError:
            pass
        # 降级：正则匹配引号内的词，校验是否标准
        items = re.findall(r'["\u201c\u201d]([^"\u201c\u201d]+)["\u201c\u201d]', text)
        return [s.strip() for s in items if s.strip() in SW_INDUSTRIES_SET]

    # ================================================================
    # 股票提取 + sentiment（纯正则，根据章节上下文判断）
    # ================================================================

    def _extract_stocks_with_sentiment(self, content: str) -> List[dict]:
        """提取股票并根据所在章节判断利好/利空"""
        stocks = self._extract_stocks(content)
        if not stocks:
            return stocks

        # 按 ## 拆分内容为段落，记录每段所属章节
        sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
        # 构建"章节名 → 正文"映射
        section_map: dict[str, str] = {}
        for section_text in sections:
            lines = section_text.strip().split("\n", 1)
            if not lines:
                continue
            section_title = lines[0].strip()
            section_body = lines[1].strip() if len(lines) > 1 else ""
            if section_title.startswith("TITLE:") or section_title.startswith("SUMMARY:"):
                continue
            section_map[section_title] = section_body

        # 获取"受损行业"章节的正文
        negative_body = section_map.get("受损行业", "")
        # 合并"受益行业"和"推荐关注股票"作为 positive 区域
        positive_bodies = [
            section_map.get("受益行业", ""),
            section_map.get("推荐关注股票", ""),
        ]
        positive_body = "\n".join(positive_bodies)

        for s in stocks:
            code = s["code"]
            name = s["name"]
            # 先检查是否在"受损行业"段落中
            if name in negative_body or code in negative_body:
                s["sentiment"] = "negative"
            # 再检查是否在"受益行业"/"推荐关注股票"段落中
            elif name in positive_body or code in positive_body:
                s["sentiment"] = "positive"

        return stocks

    def _extract_stocks(self, content: str) -> List[dict]:
        """
        从内容中提取股票，分三轮扫描：
        1. 标准格式：中文名(代码)  如 贵州茅台(600519)
        2. 代码格式：6 位数字      如 600519
        3. 纯名称格式：数据库名称精确匹配
        """
        found: dict[str, dict] = {}  # code → info（去重）

        # 第 1 轮：标准格式 中文名(600519) 或 中文名（600519）
        for match in re.finditer(
            r"([\u4e00-\u9fa5]{2,10})\s*[\(（]?\s*(\d{6})\s*[\)）]?",
            content,
        ):
            name, code = match.group(1), match.group(2)
            stock = self._code_map.get(code)
            if stock and code not in found:
                found[code] = {"code": code, "name": stock["name"]}

        # 第 2 轮：裸代码格式（前后无中文括号，避免重复匹配第 1 轮的）
        for match in re.finditer(r"(?<![`\u4e00-\u9fa5\(（])\b(\d{6})\b(?![\d\(（])", content):
            code = match.group(1)
            if code in found:
                continue
            stock = self._code_map.get(code)
            if stock:
                found[code] = {"code": code, "name": stock["name"]}

        # 第 3 轮：纯名称匹配（遍历数据库中所有股票名，在内容中搜索）
        for name, stock in self._name_map.items():
            if stock["code"] in found:
                continue
            if name in content:
                found[stock["code"]] = {"code": stock["code"], "name": name}

        return list(found.values())
_INDUSTRY_PROMPT = """你是一名行业分析助手。请从以下文章内容中提取涉及的申万一级行业名称。

## 要求
1. 只从标准申万一级行业名称中选择，不要自创行业名称
2. 返回 JSON 数组格式，如：["电子", "汽车", "计算机"]
3. 如果文章没有明确提到任何行业，返回空数组 []
4. 最多返回 10 个行业

## 标准行业名称（31个申万一级行业）
{industries}

## 文章内容
{content}

请直接返回 JSON 数组，不要有其他文字。"""
