# Quickstart: RAG 语义检索增强

**Feature**: 008-rag-semantic-retrieval
**Date**: 2026-05-19

## Prerequisites

- Python 3.x 环境
- 磁盘空间 ≥ 2GB（模型 ~1.3GB + ChromaDB 数据）
- 网络环境（首次下载模型）或手动下载模型文件

## Setup

### 1. 安装依赖

```bash
cd backend
pip install sentence-transformers>=2.2.0 chromadb>=0.4.0
```

### 2. 配置环境变量

在 `.env` 中添加（可选，有默认值）：

```env
# RAG 配置
RAG_ENABLED=true
RAG_EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
RAG_VECTOR_DB_PATH=./data/vector_db
RAG_SIMILARITY_THRESHOLD=0.7
RAG_DEDUP_THRESHOLD=0.85
RAG_MAX_CONTEXT_LENGTH=2000
```

### 3. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

首次启动时，模型会自动下载到 `~/.cache/huggingface/`（约 1.3GB）。

## Verification

### 检查模型加载

启动日志中应看到：
```
INFO: RAG enabled, loading embedding model: BAAI/bge-large-zh-v1.5
INFO: Embedding model loaded successfully (1024 dim)
INFO: ChromaDB initialized at ./data/vector_db
```

### 检查降级行为

如果模型加载失败：
```
WARNING: Failed to load embedding model, RAG degraded to FULLTEXT mode
```
系统正常运行，所有检索走 FULLTEXT。

### 功能验证

1. **retrieve 节点**：触发一次事件分析，检查日志中是否出现 "retrieve: using vector search" 或 "retrieve: falling back to FULLTEXT"
2. **文章保存**：保存一篇文章到知识库，检查日志中是否出现 "embedding generated for article xxx"
3. **事件雷达**：查看影响事件的"知识库关联"区域是否展示相关度百分比

## Troubleshooting

| 问题 | 解决方案 |
|------|----------|
| 模型下载慢/失败 | 手动下载：`huggingface-cli download BAAI/bge-large-zh-v1.5` |
| ChromaDB 权限错误 | 检查 `RAG_VECTOR_DB_PATH` 目录是否有写权限 |
| 内存不足 | 模型加载需约 2GB 内存，确保服务器有足够 RAM |
| 关闭 RAG | 设置 `RAG_ENABLED=false`，所有检索走 FULLTEXT |
