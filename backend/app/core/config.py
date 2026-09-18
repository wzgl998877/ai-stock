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
    app_name: str = "ai-stock"
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

    # === 事件采集 ===
    event_crawl_enabled: bool = True                              # 事件采集调度器开关（本地开发可关闭）

    # === 缠论策略监控（模块三） ===
    chanlun_scan_enabled: bool = True        # 缠论扫描调度器总开关（本地开发可关闭）
    chanlun_scan_daily_cron: str = "15:40"   # 日线收盘扫描触发时刻（HH:MM，工作日）
    chanlun_backtest_timeout: int = 300      # 回测任务整体超时（秒）
    chanlun_concurrency: int = 10            # 监控扫描并发上限
    chanlun_algo_version: str = "1.1.0"      # 缠论算法版本号（写入信号/结构/回测，保证可回放与一致性）
    chanlun_push_max_signal_age_days: int = 7  # 推送信号年龄上限（天）：bump 版本后全量重算重插时拦截陈年信号轰炸

    # === 缠论日线数据到位校验与扫描内重试 ===
    # 2026-09-14 事故：15:40 新浪 456 + 腾讯降级数据未更新 → 当日零新行入库 →
    # 扫描层把「数据没拉到」判成「无新数据」全量跳过，信号晚一个交易日才出。
    chanlun_daily_ready_after: str = "15:05"             # 当日日K就绪时刻（HH:MM）；早于此运行期望日回退上一交易日
    chanlun_daily_pull_retry_max: int = 3                # 拉取轮数（含首轮）；3 轮 ≈ 40 分钟，覆盖新浪 456 的 5-60 分钟自解窗口
    chanlun_daily_pull_retry_interval_sec: int = 1200    # 轮间等待秒数
    chanlun_daily_pull_stale_ratio: float = 0.3          # 未到位占比达此值 → 判数据源故障并重试
    chanlun_daily_pull_stale_min: int = 2                # 未到位最少只数（小自选股列表防误报）
    chanlun_daily_rescan_cron: str = "18:10"             # 日线兜底补扫时刻（HH:MM）；空串=关闭

    # === 缠论信号自动补推 ===
    # 2026-09-15 事故：iLink context_token 约 24h 过期，且 tokenless 降级通道
    # 亦被网关拒绝 → 推送失败只标 push_status='failed'，漏推信号永久丢失。
    chanlun_push_retry_enabled: bool = True              # 扫描收尾自动补推未送达信号
    # 补推回看窗口（天）；应 ≤ chanlun_push_max_signal_age_days。2026-09-18 从 2 放宽到 5：
    # 推送门禁是「用户最后发消息 +24h」窗口（见 wechat_keepalive_enabled 注释），窗口
    # 关闭期间信号全部 failed；5 天窗口让用户隔几天发一次消息也能一次补齐全部漏推。
    chanlun_push_retry_window_days: int = 5
    chanlun_push_retry_max_signals: int = 20             # 单轮补推条数上限（防轰炸）

    # === 微信 iLink Bot 推送（缠论信号） ===
    wechat_push_enabled: bool = False                   # 推送总开关（token 未配置时强制视为关闭）
    wechat_ilink_bot_token: str = ""                    # iLink Bot Token（Bearer）
    wechat_ilink_user_id: str = ""                      # 接收人 user_id（xxx@im.wechat 格式）
    wechat_ilink_base_url: str = "https://ilinkai.weixin.qq.com"
    wechat_ilink_client_version: int = 196608           # iLink-App-ClientVersion 头（0x30000）
    wechat_ilink_poll_timeout: int = 35                 # 长轮询挂起秒数（客户端超时 = 此值 + 5）
    wechat_ilink_backoff_max: int = 60                  # 长轮询异常退避封顶（秒）
    # 心跳保活：2026-09-18 证伪——窗口锚定用户发消息时刻固定 24h，bot 发消息
    # 不能续期（9/16 08:30 心跳成功但 token 当天 14:18 照死），反而每天白耗
    # 窗口内 10 条主动消息配额中的 2 条。默认关闭；置 True 可作链路探测留痕。
    wechat_keepalive_enabled: bool = False              # 心跳保活（已证伪无效，见上；仅作发送链路探测用）

    # === 微信指令助手（iLink 消息驱动系统功能，specs/010） ===
    wechat_cmd_enabled: bool = False                    # 指令功能总开关（与推送开关独立）
    wechat_cmd_authorized_users: str = ""               # 授权白名单（逗号分隔；空则回落 wechat_ilink_user_id 本人）
    wechat_cmd_llm_timeout: int = 10                    # 意图解析 LLM 超时秒数（超时走规则降级链）

    # === 邮件 (SMTP) ===
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
