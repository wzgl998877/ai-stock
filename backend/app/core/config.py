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

    # === 应用 ===
    cors_origins: List[str] = ["http://localhost:5173"]
    analysis_timeout: int = 120

    # === 相似检测 ===
    similarity_threshold: float = 0.3

    # === 搜索 ===
    tavily_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
