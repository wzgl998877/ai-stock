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
    redis_url: str = "redis://localhost:6379/0"

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
    tavily_api_key: str = ""

    # === 数据源加密 ===
    datasource_encryption_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
