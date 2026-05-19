"""
向量数据库查询工具 — 查看 ChromaDB 中的数据

用法:
    # 查看所有集合的统计信息
    python -m scripts.query_vector_db status

    # 查看知识库文章集合（最新 10 条）
    python -m scripts.query_vector_db list knowledge_articles

    # 查看影响事件集合（最新 10 条）
    python -m scripts.query_vector_db list impact_events --limit 5

    # 语义检索测试
    python -m scripts.query_vector_db search "新能源补贴政策" --collection knowledge_articles --top-k 3

    # 查看指定文档详情
    python -m scripts.query_vector_db get knowledge_articles article_art_123
"""

import argparse
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.WARNING)


def _get_chroma():
    """获取 ChromaDB 客户端"""
    from app.core.config import settings
    import chromadb

    client = chromadb.PersistentClient(path=settings.rag_vector_db_path)
    return client


def _get_db_path():
    """获取 ChromaDB 存储路径"""
    from app.core.config import settings
    return settings.rag_vector_db_path


def cmd_status(args):
    """查看所有集合统计"""
    client = _get_chroma()
    collections = client.list_collections()

    if not collections:
        print("ChromaDB 中没有任何集合（数据库为空）")
        print(f"路径: {_get_db_path()}")
        return

    print(f"ChromaDB 路径: {_get_db_path()}\n")
    print(f"{'集合名称':<25} {'文档数':>8} {'元数据':<20}")
    print("-" * 55)

    total = 0
    for col_info in collections:
        try:
            col = client.get_collection(col_info.name)
            count = col.count()
            total += count
            print(f"{col_info.name:<25} {count:>8} {json.dumps(col_info.metadata or {}, ensure_ascii=False)[:20]}")
        except Exception as e:
            print(f"{col_info.name:<25} {'ERROR':>8} {e}")

    print("-" * 55)
    print(f"{'总计':<25} {total:>8}")


def cmd_list(args):
    """列出集合中的文档"""
    client = _get_chroma()
    limit = args.limit or 10

    try:
        col = client.get_collection(args.collection)
    except Exception:
        print(f"集合 '{args.collection}' 不存在")
        return

    count = col.count()
    print(f"集合: {args.collection} | 总文档数: {count} | 显示最近 {min(limit, count)} 条\n")

    if count == 0:
        print("（空集合）")
        return

    # 获取所有文档（ChromaDB 没有 offset，用 peek + get）
    result = col.get(
        limit=min(limit, count),
        include=["metadatas", "documents"],
    )

    if not result["ids"]:
        print("（无数据）")
        return

    for i, doc_id in enumerate(result["ids"]):
        metadata = result["metadatas"][i] if result["metadatas"] else {}
        document = result["documents"][i] if result["documents"] else ""
        print(f"[{i+1}] ID: {doc_id}")
        print(f"    文档: {document[:100]}{'...' if len(document) > 100 else ''}")
        if metadata:
            meta_str = json.dumps(metadata, ensure_ascii=False)
            print(f"    元数据: {meta_str[:150]}{'...' if len(meta_str) > 150 else ''}")
        print()


def cmd_search(args):
    """语义检索测试"""
    query = args.query
    top_k = args.top_k or 5
    collection = args.collection or "knowledge_articles"

    from app.infrastructure.vector.embedding_client import LocalEmbeddingService

    print(f"加载 Embedding 模型...")
    svc = LocalEmbeddingService()
    if not svc.is_ready():
        print("ERROR: Embedding 模型未就绪")
        return

    print(f"生成查询向量: \"{query}\"\n")

    async def _search():
        embedding = await svc.embed(query)

        client = _get_chroma()
        try:
            col = client.get_collection(collection)
        except Exception:
            print(f"集合 '{collection}' 不存在")
            return []

        results = col.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["metadatas", "documents", "distances"],
        )

        return results

    results = asyncio.run(_search())

    if not results or not results["ids"] or not results["ids"][0]:
        print("无检索结果")
        return

    print(f"集合: {collection} | Top-{top_k} 结果\n")
    print(f"{'#':<3} {'相似度':>7} {'ID':<25} {'文档':<40}")
    print("-" * 80)

    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i] if results["distances"] else 0
        similarity = 1.0 - distance
        document = results["documents"][0][i] if results["documents"] else ""
        metadata = results["metadatas"][0][i] if results["metadatas"] else {}

        print(f"{i+1:<3} {similarity:>7.2%}  {doc_id:<25} {document[:40]}")
        if metadata:
            title = metadata.get("title", "")
            if title:
                print(f"         标题: {title}")
            user_id = metadata.get("user_id", "")
            if user_id:
                print(f"         用户: {user_id}")
        print()


def cmd_get(args):
    """查看指定文档详情"""
    client = _get_chroma()

    try:
        col = client.get_collection(args.collection)
    except Exception:
        print(f"集合 '{args.collection}' 不存在")
        return

    result = col.get(
        ids=[args.doc_id],
        include=["metadatas", "documents", "embeddings"],
    )

    if not result["ids"]:
        print(f"文档 '{args.doc_id}' 不存在")
        return

    print(f"ID: {result['ids'][0]}")
    print(f"文档: {result['documents'][0] if result['documents'] else 'N/A'}")
    print(f"元数据: {json.dumps(result['metadatas'][0] if result['metadatas'] else {}, ensure_ascii=False, indent=2)}")
    if result["embeddings"]:
        emb = result["embeddings"][0]
        print(f"向量维度: {len(emb)}")
        print(f"向量前5维: {emb[:5]}")


def main():
    parser = argparse.ArgumentParser(description="向量数据库查询工具")
    subparsers = parser.add_subparsers(dest="command")

    # status
    subparsers.add_parser("status", help="查看所有集合统计")

    # list
    list_parser = subparsers.add_parser("list", help="列出集合中的文档")
    list_parser.add_argument("collection", help="集合名称")
    list_parser.add_argument("--limit", type=int, default=10, help="显示条数")

    # search
    search_parser = subparsers.add_parser("search", help="语义检索")
    search_parser.add_argument("query", help="查询文本")
    search_parser.add_argument("--collection", default="knowledge_articles", help="集合名称")
    search_parser.add_argument("--top-k", type=int, default=5, help="返回条数")

    # get
    get_parser = subparsers.add_parser("get", help="查看文档详情")
    get_parser.add_argument("collection", help="集合名称")
    get_parser.add_argument("doc_id", help="文档 ID")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "get":
        cmd_get(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
