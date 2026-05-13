"""事件雷达用例 — 面板查询、详情、统计、采集管线"""

import json
import logging
from datetime import date, datetime
from typing import Optional

from app.domain.entities.impact_event import ImpactEvent
from app.domain.entities.user_impact import UserImpact
from app.domain.entities.impact_article import ImpactArticle
from app.domain.repositories.impact_event_repo import ImpactEventRepository
from app.domain.repositories.impact_article_repo import ImpactArticleRepository
from app.domain.repositories.user_impact_repo import UserImpactRepository
from app.domain.services.event_dedup import url_hash as calc_url_hash
from app.domain.services.impact_assessment import assess_event

logger = logging.getLogger(__name__)


class EventRadarUseCase:
    def __init__(
        self,
        event_repo: ImpactEventRepository,
        article_repo: ImpactArticleRepository,
        impact_repo: UserImpactRepository,
        ai_service=None,
    ):
        self.event_repo = event_repo
        self.article_repo = article_repo
        self.impact_repo = impact_repo
        self.ai_service = ai_service

    async def get_user_impacts(self, user_id: str, status: str = "all", d: Optional[date] = None):
        """获取用户影响事件列表"""
        d = d or date.today()
        active = []
        archived = []

        if status in ("active", "all"):
            active = await self.impact_repo.list_active_by_user(user_id)

        if status in ("archived", "all"):
            archived = await self.impact_repo.list_archived_by_user(user_id, d)

        stats = await self.impact_repo.get_stats(user_id, d)

        # Enrich with event details
        all_impacts = active + archived
        event_ids = list(set(imp.event_id for imp in all_impacts))
        events_map = {}
        if event_ids:
            events = await self.event_repo.get_by_ids(event_ids)
            events_map = {e.event_id: e for e in events}

        # Count affected stocks
        all_stock_codes = set()
        for imp in all_impacts:
            for s in (imp.matched_stocks or []):
                code = s.get("code", "")
                if code:
                    all_stock_codes.add(code)

        stats["affected_stocks_count"] = len(all_stock_codes)

        return {
            "active_impacts": active,
            "archived_impacts": archived,
            "stats": stats,
            "events_map": events_map,
        }

    async def get_impact_detail(self, user_id: str, impact_id: int):
        """获取单条影响事件详情"""
        impact = await self.impact_repo.get_by_id(impact_id)
        if not impact or impact.user_id != user_id:
            return None

        event = await self.event_repo.get_by_id(impact.event_id)
        articles = await self.article_repo.list_by_event(impact.event_id)

        # Mark as read
        await self.impact_repo.mark_as_read(impact_id)

        return {
            "impact": impact,
            "event": event,
            "articles": articles,
        }

    async def get_stats(self, user_id: str):
        """获取影响统计"""
        return await self.impact_repo.get_stats(user_id, date.today())

    async def get_stock_impacts(self, user_id: str, stock_codes: list[str]):
        """获取自选股影响状态"""
        return await self.impact_repo.get_stock_impacts(user_id, stock_codes)

    async def generate_ai_insight(self, user_id: str, impact_id: int) -> Optional[dict]:
        """生成 AI 影响解读（幂等：已生成则返回缓存）"""
        impact = await self.impact_repo.get_by_id(impact_id)
        if not impact or impact.user_id != user_id:
            return None

        event = await self.event_repo.get_by_id(impact.event_id)
        if not event:
            return None

        if not self.ai_service:
            return {
                "event_nature": "AI 服务未配置",
                "affected_industries_detail": [],
                "stock_impact_reasons": [],
            }

        try:
            from app.infrastructure.ai.prompts.impact_assessment import IMPACT_ASSESSMENT_PROMPT
            prompt = IMPACT_ASSESSMENT_PROMPT.format(
                title=event.title,
                summary=event.summary or "",
            )
            result = await self.ai_service.generate_title_and_summary(
                system_prompt="你是一位专业的投资分析师，请以JSON格式输出分析结果。",
                user_message=prompt,
                max_tokens=1024,
            )
            # generate_title_and_summary returns (title, content) tuple
            content = result[1] if isinstance(result, tuple) else str(result)
            # 尝试解析 JSON
            if isinstance(content, str):
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(content[start:end])
            return content
        except Exception as e:
            logger.warning("AI 解读生成失败: %s", e)
            return {
                "event_nature": "AI 解读生成失败",
                "affected_industries_detail": [],
                "stock_impact_reasons": [],
            }

    async def crawl_and_process(self):
        """采集并处理财经新闻"""
        from app.infrastructure.crawler.cls_provider import ClsProvider

        provider = ClsProvider()
        articles = await provider.fetch_latest(limit=50)

        if not articles:
            logger.info("未采集到新文章")
            return {"crawled": 0, "new_events": 0}

        existing_hashes = set()
        existing_titles = []

        new_count = 0
        new_events: list[ImpactEvent] = []
        for article in articles:
            result = assess_event(
                title=article.title,
                content=article.content,
                source_url=article.url,
                existing_url_hashes=existing_hashes,
                existing_titles=existing_titles,
            )
            if not result:
                continue

            event = ImpactEvent(
                title=result["title"],
                summary=result["summary"],
                sentiment=result["sentiment"],
                importance=result["importance"],
                affected_stocks=result["affected_stocks"],
                affected_industries=result["affected_industries"],
                source_count=1,
                first_seen_at=datetime.now(),
                last_seen_at=datetime.now(),
            )
            event = await self.event_repo.create(event)

            impact_article = ImpactArticle(
                event_id=event.event_id,
                title=article.title,
                content=article.content[:500],
                source=article.source,
                url=article.url,
                url_hash=result["url_hash"] or calc_url_hash(article.url),
                published_at=article.published_at,
            )
            await self.article_repo.create(impact_article)

            existing_hashes.add(impact_article.url_hash)
            existing_titles.append(article.title)
            new_events.append(event)
            new_count += 1

        if new_events:
            await self._match_users_for_events(new_events)

        logger.info("采集完成: 共 %d 条，新增 %d 条", len(articles), new_count)
        return {"crawled": len(articles), "new_events": new_count}

    async def _match_users_for_events(self, events: list[ImpactEvent]):
        """将新事件匹配到用户，生成 UserImpact 记录"""
        from sqlalchemy import text

        session = self.impact_repo.session

        # 获取所有有自选股的用户及其股票代码
        stmt = text(
            "SELECT wg.user_id, wi.stock_code "
            "FROM t_watchlist_group wg "
            "JOIN t_watchlist_item wi ON wg.id = wi.group_id"
        )
        result = await session.execute(stmt)
        user_stocks: dict[str, set[str]] = {}
        for row in result.fetchall():
            user_stocks.setdefault(row[0], set()).add(row[1])

        if not user_stocks:
            logger.info("无自选股用户，跳过用户匹配")
            return

        importance_priority = {"high": "P1", "medium": "P2", "low": "P3"}

        for event in events:
            event_stock_codes = set()
            for s in (event.affected_stocks or []):
                code = s.get("code", "")
                if code:
                    event_stock_codes.add(code)

            for user_id, watch_codes in user_stocks.items():
                matched = event_stock_codes & watch_codes
                priority = importance_priority.get(event.importance or "low", "P3")

                if matched:
                    matched_stocks = [
                        {"code": c, "direction": event.sentiment or "neutral"}
                        for c in matched
                    ]
                elif event.importance in ("high", "medium"):
                    # 高/中重要性事件广播给所有用户
                    matched_stocks = event.affected_stocks or []
                    priority = "P3"
                else:
                    continue

                existing = await self.impact_repo.get_by_user_and_event(user_id, event.event_id)
                if existing:
                    continue

                user_impact = UserImpact(
                    user_id=user_id,
                    event_id=event.event_id,
                    matched_stocks=matched_stocks,
                    matched_industries=event.affected_industries or [],
                    priority=priority,
                )
                await self.impact_repo.create(user_impact)

        await session.flush()
