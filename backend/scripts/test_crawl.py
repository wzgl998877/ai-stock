"""手动触发采集任务 — 用于调试"""

import asyncio
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    from app.core.database import async_session
    from app.core.config import settings

    # 1. 初始化 Embedding 服务
    from app.infrastructure.vector.embedding_client import LocalEmbeddingService
    embedding_svc = LocalEmbeddingService(model_name=settings.rag_embedding_model)

    # 2. 初始化 ChromaDB
    from app.infrastructure.vector.chroma_store import ChromaVectorStore
    from app.infrastructure.repositories.chroma_vector_search_repo import ChromaVectorSearchRepo
    chroma_store = ChromaVectorStore(persist_dir=settings.rag_vector_db_path)
    vector_repo = ChromaVectorSearchRepo(chroma_store)

    # 3. 执行采集
    from app.infrastructure.repositories.mysql_impact_event_repo import MySQLImpactEventRepository
    from app.infrastructure.repositories.mysql_impact_article_repo import MySQLImpactArticleRepository
    from app.infrastructure.repositories.mysql_user_impact_repo import MySQLUserImpactRepository
    from app.application.use_cases.event_radar import EventRadarUseCase

    async with async_session() as session:
        uc = EventRadarUseCase(
            event_repo=MySQLImpactEventRepository(session),
            article_repo=MySQLImpactArticleRepository(session),
            impact_repo=MySQLUserImpactRepository(session),
            vector_search_repo=vector_repo,
            embedding_service=embedding_svc,
        )
        t0 = time.time()
        result = await uc.crawl_and_process()
        await session.commit()
        elapsed = time.time() - t0
        logger.info("采集完成: %s, 耗时 %.1fs", result, elapsed)


if __name__ == "__main__":
    asyncio.run(main())
