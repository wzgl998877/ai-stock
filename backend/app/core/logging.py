"""日志配置 — 控制台 + RotatingFileHandler 动态切分"""

import os
import logging
from logging.handlers import RotatingFileHandler

from app.core.config import settings


def setup_logging() -> None:
    """初始化全局日志：控制台 + 文件（按大小自动切分）"""
    log_dir = os.path.abspath(settings.log_dir)
    os.makedirs(log_dir, exist_ok=True)

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # 全局格式
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # root logger
    root = logging.getLogger()
    root.setLevel(log_level)

    # 避免重复添加 handler（reload 场景）
    if root.handlers:
        return

    # 控制台
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(fmt)
    root.addHandler(console)

    # 主日志文件（按大小切分）
    main_file = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    main_file.setLevel(log_level)
    main_file.setFormatter(fmt)
    root.addHandler(main_file)

    # AI 调用单独日志（方便排查 AI 问题）
    ai_file = RotatingFileHandler(
        os.path.join(log_dir, "ai.log"),
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    ai_file.setLevel(logging.DEBUG)
    ai_file.setFormatter(fmt)
    ai_logger = logging.getLogger("app.infrastructure.ai")
    ai_logger.addHandler(ai_file)

    # 过滤敏感信息：禁止 API Key 泄露到日志
    for handler in root.handlers + ai_logger.handlers:
        handler.addFilter(_sanitize_filter)

    logging.getLogger(__name__).info("日志初始化完成, 目录=%s, 级别=%s", log_dir, settings.log_level)


def _sanitize_filter(record: logging.LogRecord) -> bool:
    """过滤日志中的 API Key 等敏感信息"""
    sensitive_keys = ["api_key", "apikey", "authorization", "password", "secret"]
    msg = record.getMessage().lower()
    for key in sensitive_keys:
        if key in msg:
            # 将整个 record 的 msg 替换为脱敏版本
            original = record.getMessage()
            record.msg = _redact(original)
            record.args = ()
            break
    return True


def _redact(text: str) -> str:
    """将可能包含 key 的值脱敏"""
    import re
    # 匹配 Bearer xxx / sk-xxx / key=xxx 等
    text = re.sub(r"(Bearer\s+)\S+", r"\1***", text)
    text = re.sub(r"(sk-)\w{4}\w+", r"\1****", text)
    return text
