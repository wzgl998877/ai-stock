"""文章管理用例 — 保存/列表/详情/删除"""

import logging
from typing import List, Optional, Tuple

from app.domain.entities.article import Article, IndustryRef, StockRef
from app.domain.repositories.article_repo import ArticleRepository
from app.domain.repositories.industry_repo import IndustryRepository
from app.domain.repositories.vector_search_repo import VectorSearchRepository
from app.domain.services.embedding_service import EmbeddingService
from app.domain.services.text_chunker import chunk_article
from app.core.exceptions import EmptyContentError, NoIndustryTagError

logger = logging.getLogger(__name__)


class SaveArticleUseCase:
    """保存分析结果到知识库"""

    def __init__(
        self,
        article_repo: ArticleRepository,
        industry_repo: IndustryRepository,
        vector_search_repo: Optional[VectorSearchRepository] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.article_repo = article_repo
        self.industry_repo = industry_repo
        self.vector_search_repo = vector_search_repo
        self.embedding_service = embedding_service

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
        industry_sentiments: Optional[List[dict]] = None,
    ) -> Article:
        if not content or not content.strip():
            raise EmptyContentError()

        # 摘要降级：为空时截取正文前80字
        if not summary or not summary.strip():
            summary = content.strip()[:80] + "..." if len(content.strip()) > 80 else content.strip()

        # 将行业名称转换为行业代码
        resolved_codes: List[str] = []
        name_to_code: dict = {}
        for name in industry_codes:
            industry = await self.industry_repo.find_by_name(name)
            if industry:
                resolved_codes.append(industry.industry_code)
                name_to_code[name] = industry.industry_code
            else:
                logger.warning("行业名称未找到对应代码: %s", name)

        if not resolved_codes:
            raise NoIndustryTagError()

        # 构建行业 sentiment 映射
        ind_sent_map: dict = {}
        if industry_sentiments:
            for item in industry_sentiments:
                code = name_to_code.get(item.get("name", ""))
                if code:
                    ind_sent_map[code] = item.get("sentiment")

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
                    sentiment=ind_sent_map.get(code),
                )
                for code in resolved_codes
            ],
            stocks=[
                StockRef(stock_code=s["code"], stock_name=s["name"], sentiment=s.get("sentiment"))
                for s in stock_refs
            ],
        )

        saved = await self.article_repo.save(article)
        logger.info("文章已保存: id=%s, title=%s, industries=%d", saved.article_id, title, len(resolved_codes))

        return saved

    async def save_embeddings(self, article: Article) -> None:
        """异步生成 embedding 并写入向量数据库（不阻塞主流程）"""
        if not self.vector_search_repo or not self.embedding_service or not self.embedding_service.is_ready():
            return
        try:
            chunks = chunk_article(article.title, article.summary or "", article.content or "")
            texts = [c.content for c in chunks]
            embeddings = await self.embedding_service.embed_batch(texts)

            base_metadata = {
                "user_id": article.user_id,
                "title": article.title,
                "stock_codes": ",".join(s.stock_code for s in article.stocks),
                "industries": ",".join(i.industry_code for i in article.industries),
                "event_type": article.event_type,
            }

            doc_ids = []
            chunk_metadatas = []
            chunk_documents = []
            for chunk, embedding in zip(chunks, embeddings):
                doc_ids.append(f"article_{article.article_id}_chunk_{chunk.index}")
                chunk_metadatas.append({
                    **base_metadata,
                    "article_id": str(article.article_id),
                    "chunk_index": chunk.index,
                    "chunk_type": chunk.chunk_type,
                })
                chunk_documents.append(chunk.content)

            await self.vector_search_repo.add_batch(
                collection="knowledge_articles",
                doc_ids=doc_ids,
                embeddings=embeddings,
                metadatas=chunk_metadatas,
                documents=chunk_documents,
            )
            logger.info("文章 embedding 写入成功: article_id=%s, chunks=%d", article.article_id, len(chunks))
        except Exception as e:
            logger.warning("文章 embedding 写入失败(article_id=%s): %s", article.article_id, e)


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

    def __init__(self, article_repo: ArticleRepository, vector_search_repo: Optional[VectorSearchRepository] = None):
        self.article_repo = article_repo
        self.vector_search_repo = vector_search_repo

    async def execute(self, article_id: str) -> bool:
        result = await self.article_repo.delete(article_id)
        # 同步删除向量数据（不阻塞主流程）
        if self.vector_search_repo and result:
            try:
                # 按过滤条件删除所有 chunk
                deleted = await self.vector_search_repo.delete_by_filter(
                    collection="knowledge_articles",
                    filters={"article_id": str(article_id)},
                )
                if deleted > 0:
                    logger.info("文章向量删除成功: article_id=%s, chunks=%d", article_id, deleted)
                else:
                    # 兼容旧数据：旧格式 doc_id 无 article_id metadata
                    try:
                        await self.vector_search_repo.delete(
                            collection="knowledge_articles",
                            doc_id=f"article_{article_id}",
                        )
                        logger.info("文章向量删除成功(旧格式): article_id=%s", article_id)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("文章向量删除失败(article_id=%s): %s", article_id, e)
        return result
