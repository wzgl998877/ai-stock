"""文章管理用例 — 保存/列表/详情/删除"""

import logging
from typing import List, Optional, Tuple

from app.domain.entities.article import Article, IndustryRef, StockRef
from app.domain.repositories.article_repo import ArticleRepository
from app.domain.repositories.industry_repo import IndustryRepository
from app.core.exceptions import EmptyContentError, NoIndustryTagError

logger = logging.getLogger(__name__)


class SaveArticleUseCase:
    """保存分析结果到知识库"""

    def __init__(self, article_repo: ArticleRepository, industry_repo: IndustryRepository):
        self.article_repo = article_repo
        self.industry_repo = industry_repo

    async def execute(
        self,
        title: str,
        summary: str,
        content: str,
        event_type: str,
        raw_input: str,
        industry_codes: List[str],
        stock_refs: List[dict],
        chain_table: Optional[List[dict]] = None,
        user_id: str = "default",
    ) -> Article:
        if not content or not content.strip():
            raise EmptyContentError()

        # 摘要降级：为空时截取正文前80字
        if not summary or not summary.strip():
            summary = content.strip()[:80] + "..." if len(content.strip()) > 80 else content.strip()

        # 将行业名称转换为行业代码
        resolved_codes: List[str] = []
        for name in industry_codes:
            industry = await self.industry_repo.find_by_name(name)
            if industry:
                resolved_codes.append(industry.industry_code)
            else:
                logger.warning("行业名称未找到对应代码: %s", name)

        if not resolved_codes:
            raise NoIndustryTagError()

        article = Article(
            article_id="",
            title=title,
            summary=summary,
            content=content,
            event_type=event_type,
            raw_input=raw_input,
            user_id=user_id,
            chain_table=chain_table,
            industries=[
                IndustryRef(
                    industry_code=code,
                    chain_level=None,
                )
                for code in resolved_codes
            ],
            stocks=[
                StockRef(stock_code=s["code"], stock_name=s["name"])
                for s in stock_refs
            ],
        )

        saved = await self.article_repo.save(article)
        logger.info("文章已保存: id=%s, title=%s, industries=%d", saved.article_id, title, len(resolved_codes))
        return saved


class ListArticlesUseCase:
    """知识库文章列表查询（三视图）"""

    def __init__(self, article_repo: ArticleRepository):
        self.article_repo = article_repo

    async def execute(
        self,
        user_id: str,
        view: str = "timeline",
        industry_code: Optional[str] = None,
        stock_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        if view == "industry" and industry_code:
            return await self.article_repo.list_by_industry(
                industry_code, user_id, page, page_size,
            )
        elif view == "stock" and stock_code:
            return await self.article_repo.list_by_stock(
                stock_code, user_id, page, page_size,
            )
        else:
            return await self.article_repo.list_articles(
                user_id, page, page_size,
            )


class GetArticleDetailUseCase:
    """获取文章详情"""

    def __init__(self, article_repo: ArticleRepository, industry_repo: IndustryRepository):
        self.article_repo = article_repo
        self.industry_repo = industry_repo

    async def execute(self, article_id: str) -> Optional[Article]:
        article = await self.article_repo.get_by_id(article_id)
        return article


class DeleteArticleUseCase:
    """软删除文章"""

    def __init__(self, article_repo: ArticleRepository):
        self.article_repo = article_repo

    async def execute(self, article_id: str) -> bool:
        return await self.article_repo.delete(article_id)
