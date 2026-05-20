"""
向量索引重建脚本 — 从 MySQL 全量重建 ChromaDB 向量索引

用法:
    # 重建所有集合
    python -m scripts.rebuild_vector_index

    # 仅重建知识库文章集合
    python -m scripts.rebuild_vector_index --collection knowledge_articles

    # 仅重建影响事件集合
    python -m scripts.rebuild_vector_index --collection impact_events

    # 仅统计不写入
    python -m scripts.rebuild_vector_index --dry-run
"""

import argparse
import asyncio
import logging
import os
import sys

# 确保可以导入 app 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 32


async def rebuild_knowledge_articles(embedding_svc, vector_repo, chroma_store, dry_run: bool = False):
    """重建 knowledge_articles 集合（chunk 化写入）"""
    from sqlalchemy import text
    from app.core.database import async_session
    from app.domain.services.text_chunker import chunk_article

    async with async_session() as session:
        # 统计总数
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM t_analysis_article WHERE status='completed' AND deleted='0'")
        )
        total = count_result.scalar()
        logger.info("知识库文章总数: %d", total)

        if dry_run:
            return total

        # 清除旧集合再重建
        chroma_store.delete_collection("knowledge_articles")
        logger.info("已清除旧 knowledge_articles 集合")

        # 分批查询
        offset = 0
        rebuilt_chunks = 0
        rebuilt_articles = 0
        while offset < total:
            result = await session.execute(
                text(
                    "SELECT article_id, title, summary, content, user_id, event_type "
                    "FROM t_analysis_article "
                    "WHERE status='completed' AND deleted='0' "
                    "ORDER BY article_id LIMIT :limit OFFSET :offset"
                ),
                {"limit": BATCH_SIZE, "offset": offset},
            )
            rows = result.fetchall()
            if not rows:
                break

            for row in rows:
                article_id, title, summary, content, user_id, event_type = row

                # 获取关联股票和行业
                stock_result = await session.execute(
                    text("SELECT stock_code FROM t_article_stock WHERE article_id = :aid AND deleted = '0'"),
                    {"aid": article_id},
                )
                stock_codes = ",".join(r[0] for r in stock_result.fetchall())

                ind_result = await session.execute(
                    text("SELECT industry_code FROM t_article_industry WHERE article_id = :aid AND deleted = '0'"),
                    {"aid": article_id},
                )
                industries = ",".join(r[0] for r in ind_result.fetchall())

                # 切分为 chunks
                chunks = chunk_article(title, summary or "", content or "")
                texts = [c.content for c in chunks]

                # 批量生成 embedding
                try:
                    embeddings = await embedding_svc.embed_batch(texts)
                except Exception as e:
                    logger.warning("embedding 生成失败(article_id=%s): %s", article_id, e)
                    continue

                base_metadata = {
                    "user_id": user_id or "default",
                    "title": title,
                    "stock_codes": stock_codes,
                    "industries": industries,
                    "event_type": event_type or "other",
                }

                for chunk, embedding in zip(chunks, embeddings):
                    chunk_metadata = {
                        **base_metadata,
                        "article_id": str(article_id),
                        "chunk_index": chunk.index,
                        "chunk_type": chunk.chunk_type,
                    }
                    try:
                        await vector_repo.add(
                            collection="knowledge_articles",
                            doc_id=f"article_{article_id}_chunk_{chunk.index}",
                            embedding=embedding,
                            metadata=chunk_metadata,
                            document=chunk.content,
                        )
                        rebuilt_chunks += 1
                    except Exception as e:
                        logger.warning("写入失败(article_id=%s, chunk=%d): %s", article_id, chunk.index, e)

                rebuilt_articles += 1

            offset += BATCH_SIZE
            logger.info("知识库重建进度: %d/%d 文章, %d chunks", rebuilt_articles, total, rebuilt_chunks)

    logger.info("知识库重建完成: %d 文章, %d chunks", rebuilt_articles, rebuilt_chunks)
    return rebuilt_articles


async def rebuild_impact_events(embedding_svc, vector_repo, dry_run: bool = False):
    """重建 impact_events 集合"""
    from sqlalchemy import text
    from app.core.database import async_session

    async with async_session() as session:
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM t_impact_event WHERE is_active = 1")
        )
        total = count_result.scalar()
        logger.info("影响事件总数: %d", total)

        if dry_run:
            return total

        offset = 0
        rebuilt = 0
        while offset < total:
            result = await session.execute(
                text(
                    "SELECT event_id, title, summary, sentiment "
                    "FROM t_impact_event WHERE is_active = 1 "
                    "ORDER BY event_id LIMIT :limit OFFSET :offset"
                ),
                {"limit": BATCH_SIZE, "offset": offset},
            )
            rows = result.fetchall()
            if not rows:
                break

            texts = []
            for row in rows:
                event_id, title, summary, sentiment = row
                texts.append(f"{title}\n{summary or ''}")

            embeddings = await embedding_svc.embed_batch(texts)

            for i, row in enumerate(rows):
                event_id, title, summary, sentiment = row

                # 获取关联股票和行业
                stock_result = await session.execute(
                    text("SELECT affected_stocks FROM t_impact_event WHERE event_id = :eid"),
                    {"eid": event_id},
                )
                stock_row = stock_result.fetchone()
                stock_codes = ""
                if stock_row and stock_row[0]:
                    import json
                    try:
                        stocks = json.loads(stock_row[0]) if isinstance(stock_row[0], str) else stock_row[0]
                        stock_codes = ",".join(s.get("code", "") for s in stocks if isinstance(s, dict))
                    except (json.JSONDecodeError, TypeError):
                        pass

                metadata = {
                    "title": title,
                    "affected_stocks": stock_codes,
                    "affected_industries": "",
                    "sentiment": sentiment or "neutral",
                }

                try:
                    await vector_repo.add(
                        collection="impact_events",
                        doc_id=f"event_{event_id}",
                        embedding=embeddings[i],
                        metadata=metadata,
                        document=texts[i],
                    )
                    rebuilt += 1
                except Exception as e:
                    logger.warning("写入失败(event_id=%s): %s", event_id, e)

            offset += BATCH_SIZE
            logger.info("事件重建进度: %d/%d", rebuilt, total)

    return rebuilt


async def main():
    parser = argparse.ArgumentParser(description="重建向量索引")
    parser.add_argument("--collection", choices=["knowledge_articles", "impact_events"], help="仅重建指定集合")
    parser.add_argument("--dry-run", action="store_true", help="仅统计数量，不写入")
    args = parser.parse_args()

    from app.core.config import settings

    if not settings.rag_enabled:
        logger.error("RAG 未启用 (rag_enabled=false)，无法重建索引")
        sys.exit(1)

    logger.info("开始重建向量索引 (model=%s, db=%s)", settings.rag_embedding_model, settings.rag_vector_db_path)

    from app.infrastructure.vector.embedding_client import LocalEmbeddingService
    from app.infrastructure.vector.chroma_store import ChromaVectorStore
    from app.infrastructure.repositories.chroma_vector_search_repo import ChromaVectorSearchRepo

    embedding_svc = LocalEmbeddingService(model_name=settings.rag_embedding_model)
    if not embedding_svc.is_ready():
        logger.error("Embedding 模型加载失败，无法重建索引")
        sys.exit(1)

    chroma_store = ChromaVectorStore(persist_dir=settings.rag_vector_db_path)
    vector_repo = ChromaVectorSearchRepo(chroma_store)

    if args.dry_run:
        logger.info("=== DRY RUN 模式 ===")

    results = {}
    if not args.collection or args.collection == "knowledge_articles":
        count = await rebuild_knowledge_articles(embedding_svc, vector_repo, chroma_store, dry_run=args.dry_run)
        results["knowledge_articles"] = count

    if not args.collection or args.collection == "impact_events":
        count = await rebuild_impact_events(embedding_svc, vector_repo, dry_run=args.dry_run)
        results["impact_events"] = count

    logger.info("重建完成: %s", results)


if __name__ == "__main__":
    asyncio.run(main())
