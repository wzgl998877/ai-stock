"""事件雷达用例 — 面板查询、详情、统计、采集管线"""

import json
import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import text

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
        vector_search_repo=None,
        embedding_service=None,
    ):
        self.event_repo = event_repo
        self.article_repo = article_repo
        self.impact_repo = impact_repo
        self.ai_service = ai_service
        self.vector_search_repo = vector_search_repo
        self.embedding_service = embedding_service

    async def get_user_impacts(self, user_id: str, status: str = "all",
                                start_date: Optional[date] = None, end_date: Optional[date] = None,
                                sentiment: Optional[str] = None,
                                limit: int = 20, offset: int = 0):
        """获取用户影响事件列表"""
        impacts = await self.impact_repo.list_by_user(
            user_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            sentiment=sentiment,
            limit=limit,
            offset=offset,
        )

        sd = start_date or date.today()
        stats = await self.impact_repo.get_stats(user_id, sd)

        # Enrich with event details
        event_ids = list(set(imp.event_id for imp in impacts))
        events_map = {}
        if event_ids:
            events = await self.event_repo.get_by_ids(event_ids)
            events_map = {e.event_id: e for e in events}

        # Count affected stocks
        all_stock_codes = set()
        for imp in impacts:
            for s in (imp.matched_stocks or []):
                code = s.get("code", "")
                if code:
                    all_stock_codes.add(code)

        stats["affected_stocks_count"] = len(all_stock_codes)

        return {
            "impacts": impacts,
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
            result = await assess_event(
                title=article.title,
                content=article.content,
                source_url=article.url,
                existing_url_hashes=existing_hashes,
                existing_titles=existing_titles,
                embedding_service=self.embedding_service,
                vector_search_repo=self.vector_search_repo,
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

            # 生成事件 embedding 写入向量数据库
            if self.vector_search_repo and self.embedding_service and self.embedding_service.is_ready():
                try:
                    embed_text = f"{event.title}\n{event.summary or ''}"
                    event_embedding = await self.embedding_service.embed(embed_text)
                    event_metadata = {
                        "title": event.title,
                        "affected_stocks": ",".join(
                            s.get("code", "") for s in (event.affected_stocks or [])
                        ),
                        "affected_industries": ",".join(
                            i.get("code", "") for i in (event.affected_industries or [])
                        ),
                        "sentiment": event.sentiment or "neutral",
                    }
                    await self.vector_search_repo.add(
                        collection="impact_events",
                        doc_id=f"event_{event.event_id}",
                        embedding=event_embedding,
                        metadata=event_metadata,
                        document=embed_text,
                    )
                except Exception as e:
                    logger.warning("事件 embedding 写入失败(event_id=%s): %s", event.event_id, e)

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
        from app.domain.services.impact_assessment import compute_user_impact

        session = self.impact_repo.session

        # 获取所有有自选股的用户及其股票信息
        stmt = text(
            "SELECT wg.user_id, wi.stock_code, wi.stock_name "
            "FROM t_watchlist_group wg "
            "JOIN t_watchlist_item wi ON wg.id = wi.group_id"
        )
        result = await session.execute(stmt)
        user_watchlists: dict[str, list[dict]] = {}
        for row in result.fetchall():
            user_watchlists.setdefault(row[0], []).append({"code": row[1], "name": row[2] or ""})

        if not user_watchlists:
            logger.info("无自选股用户，跳过用户匹配")
            return

        matched_count = 0
        for event in events:
            for user_id, watchlist in user_watchlists.items():
                # 跳过已存在的记录
                existing = await self.impact_repo.get_by_user_and_event(user_id, event.event_id)
                if existing:
                    continue

                # 使用领域服务的双维度匹配（股票+行业）和加权优先级
                impact = compute_user_impact(event, watchlist)

                if impact:
                    impact.user_id = user_id
                elif event.importance in ("high", "medium"):
                    # 高/中重要性事件广播给所有用户
                    impact = UserImpact(
                        user_id=user_id,
                        event_id=event.event_id,
                        matched_stocks=event.affected_stocks or [],
                        matched_industries=event.affected_industries or [],
                        priority="P3",
                    )
                else:
                    continue

                await self.impact_repo.create(impact)
                matched_count += 1

                # P0/P1 级别触发预警创建
                if impact.priority in ("P0", "P1"):
                    await self._create_alert_if_needed(user_id, impact, event, session)

        await session.flush()
        logger.info("用户影响匹配完成: %d 条记录", matched_count)

    async def _create_alert_if_needed(self, user_id: str, impact: UserImpact, event: ImpactEvent, session):
        """检查约束后创建预警记录"""
        try:
            from app.infrastructure.repositories.mysql_user_alert_repo import MySQLUserAlertRepository
            from app.domain.entities.user_alert import UserAlert

            alert_repo = MySQLUserAlertRepository(session)

            # 每日预警上限 5 条
            today_count = await alert_repo.count_today_alerts(user_id)
            if today_count >= 5:
                return

            # 检查免打扰时段
            from app.infrastructure.repositories.mysql_radar_config_repo import MySQLRadarConfigRepository
            config_repo = MySQLRadarConfigRepository(session)
            config = await config_repo.get_by_user(user_id)
            if config and config.quiet_hours_start and config.quiet_hours_end:
                from datetime import time as dt_time
                now_time = datetime.now().time()
                if config.quiet_hours_start <= now_time <= config.quiet_hours_end:
                    return

            stock_names = [s.get("name", s.get("code", "")) for s in (impact.matched_stocks or [])[:3]]
            summary = f"影响股票：{', '.join(stock_names)}" if stock_names else ""

            alert = UserAlert(
                user_id=user_id,
                user_impact_id=impact.id or 0,
                priority=impact.priority,
                title=event.title[:200],
                summary=summary[:500],
            )
            await alert_repo.create(alert)
        except Exception as e:
            logger.warning("预警创建失败: %s", e)

    async def _find_related_analyses(self, event: ImpactEvent) -> list[dict]:
        """查询知识库中的历史分析文章。

        优先使用语义向量检索，无结果时回退到行业+股票交集匹配。
        """
        # 1. 尝试语义向量检索
        if self.vector_search_repo and self.embedding_service and self.embedding_service.is_ready():
            try:
                from app.core.config import settings

                embed_text = f"{event.title}\n{event.summary or ''}"
                event_embedding = await self.embedding_service.embed(embed_text)
                vector_results = await self.vector_search_repo.search(
                    query_embedding=event_embedding,
                    top_k=3,
                    threshold=settings.rag_similarity_threshold,
                    collection="knowledge_articles",
                )

                if vector_results:
                    analyses = []
                    for r in vector_results:
                        # 从 doc_id 提取 article_id
                        article_id = r.doc_id.replace("article_", "") if r.doc_id.startswith("article_") else r.doc_id
                        analyses.append({
                            "article_id": article_id,
                            "title": r.metadata.get("title", ""),
                            "analyzed_at": None,
                            "summary": r.document,
                            "similarity_score": round(r.score * 100, 1),
                        })
                    return analyses
            except Exception as e:
                logger.warning("语义检索关联分析失败，回退到交集匹配: %s", e)

        # 2. 回退到行业+股票交集匹配
        return await self._find_related_analyses_by_intersection(event)

    async def _find_related_analyses_by_intersection(self, event: ImpactEvent) -> list[dict]:
        """基于行业+股票交集匹配的关联分析查询（原有逻辑）"""
        try:
            session = self.impact_repo.session

            stock_codes: list[str] = []
            for s in (event.affected_stocks or []):
                code = s.get("code", "") if isinstance(s, dict) else ""
                if code:
                    stock_codes.append(code)

            industry_codes: list[str] = []
            for ind in (event.affected_industries or []):
                code = ind.get("code", "") if isinstance(ind, dict) else ""
                if code:
                    industry_codes.append(code)

            if not stock_codes and not industry_codes:
                return []

            # 收集关联的 article_id
            article_ids: set[str] = set()

            if stock_codes:
                placeholders = ",".join([f":s{i}" for i in range(len(stock_codes))])
                stmt = text(
                    f"SELECT DISTINCT article_id FROM t_article_stock "
                    f"WHERE stock_code IN ({placeholders}) AND deleted = '0'"
                )
                params = {f"s{i}": code for i, code in enumerate(stock_codes)}
                result = await session.execute(stmt, params)
                for row in result.fetchall():
                    article_ids.add(row[0])

            if industry_codes:
                placeholders = ",".join([f":i{i}" for i in range(len(industry_codes))])
                stmt = text(
                    f"SELECT DISTINCT article_id FROM t_article_industry "
                    f"WHERE industry_code IN ({placeholders}) AND deleted = '0'"
                )
                params = {f"i{i}": code for i, code in enumerate(industry_codes)}
                result = await session.execute(stmt, params)
                for row in result.fetchall():
                    article_ids.add(row[0])

            if not article_ids:
                return []

            # 查询文章详情
            placeholders = ",".join([f":a{i}" for i in range(len(article_ids))])
            stmt = text(
                f"SELECT article_id, title, summary, create_time "
                f"FROM t_analysis_article "
                f"WHERE article_id IN ({placeholders}) AND deleted = '0' AND status = 'completed' "
                f"ORDER BY create_time DESC LIMIT 5"
            )
            params = {f"a{i}": aid for i, aid in enumerate(article_ids)}
            result = await session.execute(stmt, params)

            analyses = []
            for row in result.fetchall():
                analyses.append({
                    "article_id": row[0],
                    "title": row[1],
                    "analyzed_at": row[3].isoformat() if row[3] else None,
                    "summary": row[2] or "",
                })
            return analyses

        except Exception as e:
            logger.warning("查询关联分析失败: %s", e)
            return []
