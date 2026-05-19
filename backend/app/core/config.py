from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # === 大模型 ===
    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"

    # === 数据库 ===
    database_url: str = "mysql+aiomysql://root:password@localhost:3306/ai_stock"

    # === Redis ===
    redis_url: str = "redis://:your_redis_password@localhost:6379/0"

    # === 日志 ===
    log_level: str = "info"
    log_dir: str = "logs"
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 10

    # === 服务 ===
    host: str = "0.0.0.0"
    port: int = 8000

    # === 应用 ===
    cors_origins: List[str] = ["http://localhost:5173"]
    analysis_timeout: int = 120

    # === 相似检测 ===
    similarity_threshold: float = 0.3

    # === 个股分析 ===
    stock_analysis_timeout: int = 300  # 个股分析超时（秒）
    debate_rounds: int = 2  # 投资辩论默认轮次
    risk_debate_rounds: int = 2  # 风险辩论默认轮次
    max_tool_calls: int = 3  # 分析师最大工具调用次数
    stock_cache_ttl: int = 300  # 股票数据缓存时间（秒）
    llm_deep_model: str = ""  # 深度思考模型（为空则用 llm_model）

    # === 搜索 ===
    tavily_api_key: str = ""           # 兼容：单 Tavily Key
    bocha_api_keys: str = ""           # 逗号分隔的博查 Key 列表
    anspire_api_keys: str = ""         # 逗号分隔的 Anspire Key 列表
    tavily_api_keys: str = ""          # 逗号分隔的多个 Tavily Key
    news_max_age_days: int = 3         # 新闻最大时效（天）
    news_strategy_profile: str = "short"  # 新闻窗口策略
    search_cache_ttl: int = 600        # 搜索缓存 TTL（秒）
    search_request_timeout: int = 10   # 搜索请求超时（秒）

    # === 分时数据源 ===
    twelvedata_api_key: str = ""       # TwelveData API Key（免费层 800次/天）
    minute_cache_ttl: int = 30         # 分时数据缓存 TTL（秒），匹配前端轮询间隔

    # === 数据源加密 ===
    datasource_encryption_key: str = ""

    # === RAG 语义检索 ===
    rag_enabled: bool = True                                      # RAG 全局开关
    rag_embedding_model: str = "BAAI/bge-large-zh-v1.5"          # Embedding 模型
    rag_vector_db_path: str = "./data/vector_db"                 # ChromaDB 持久化目录
    rag_similarity_threshold: float = 0.6                        # 语义检索阈值（中文语义建议 0.5-0.65）
    rag_dedup_threshold: float = 0.85                             # 去重引擎阈值
    rag_max_context_length: int = 2000                            # Agent 注入上下文最大字数

    # === 邮件 (SMTP) ===
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
