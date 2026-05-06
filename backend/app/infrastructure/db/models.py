"""SQLAlchemy ORM models for all 10 tables.

DDL source: docs/FEATURES/AI_Analysis/ai-analysis.ddl.md
"""

import uuid
from datetime import date, datetime
from typing import Optional

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CHAR,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DECIMAL, JSON, MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Mixin: 审计字段 + 软删除
# ---------------------------------------------------------------------------

class AuditMixin:
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    create_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    update_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    deleted: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="0"
    )


# ---------------------------------------------------------------------------
# 1. t_user
# ---------------------------------------------------------------------------

class User(AuditMixin, Base):
    __tablename__ = "t_user"

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_account: Mapped[str] = mapped_column(String(32), nullable=False)
    user_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    password: Mapped[str] = mapped_column(String(128), nullable=False)
    nick_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    icon_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(CHAR(1), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(35), nullable=True)
    user_type: Mapped[Optional[str]] = mapped_column(CHAR(1), nullable=True)
    status: Mapped[str] = mapped_column(CHAR(1), nullable=False, default="0")
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# 2. t_industry
# ---------------------------------------------------------------------------

class Industry(AuditMixin, Base):
    __tablename__ = "t_industry"

    industry_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_parent", "parent_code"),
    )


# ---------------------------------------------------------------------------
# 3. t_stock
# ---------------------------------------------------------------------------

class Stock(AuditMixin, Base):
    __tablename__ = "t_stock"

    stock_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    exchange: Mapped[str] = mapped_column(
        Enum("SH", "SZ", "BJ"), nullable=False
    )
    list_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="")
    market_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    industry_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    industry_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    total_market_cap: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 2), nullable=True)
    float_market_cap: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 2), nullable=True)


# ---------------------------------------------------------------------------
# 4. t_stock_industry
# ---------------------------------------------------------------------------

class StockIndustry(AuditMixin, Base):
    __tablename__ = "t_stock_industry"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    stock_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("t_stock.stock_code"), nullable=False
    )
    industry_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("t_industry.industry_code"), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    classification_source: Mapped[str] = mapped_column(
        Enum("official", "ai_extracted", "user_defined"), nullable=False, default="official"
    )

    __table_args__ = (
        UniqueConstraint("stock_code", "industry_code", name="uk_stock_industry"),
    )


# ---------------------------------------------------------------------------
# 5. t_analysis_article
# ---------------------------------------------------------------------------

class AnalysisArticle(AuditMixin, Base):
    __tablename__ = "t_analysis_article"

    article_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(MEDIUMTEXT, nullable=False)
    event_type: Mapped[str] = mapped_column(
        Enum("geopolitical", "policy", "earnings", "supply_chain", "other"),
        nullable=False,
    )
    raw_input: Mapped[str] = mapped_column(String(500), nullable=False)
    chain_table: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    article_type: Mapped[str] = mapped_column(String(20), nullable=False, default="event")
    analysis_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("t_user.user_id"), nullable=False
    )

    # relationships
    article_industries = relationship(
        "ArticleIndustry", backref="article", lazy="selectin"
    )
    article_stocks = relationship(
        "ArticleStock", backref="article", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_article_type", "article_type"),
    )
# ---------------------------------------------------------------------------

class ArticleIndustry(AuditMixin, Base):
    __tablename__ = "t_article_industry"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    article_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("t_analysis_article.article_id", ondelete="CASCADE"),
        nullable=False,
    )
    industry_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("t_industry.industry_code"), nullable=False
    )
    chain_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("article_id", "industry_code", name="uk_article_industry"),
        Index("idx_article_id", "article_id"),
        Index("idx_industry_code", "industry_code"),
    )


# ---------------------------------------------------------------------------
# 7. t_article_stock
# ---------------------------------------------------------------------------

class ArticleStock(AuditMixin, Base):
    __tablename__ = "t_article_stock"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    article_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("t_analysis_article.article_id", ondelete="CASCADE"),
        nullable=False,
    )
    stock_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("t_stock.stock_code"), nullable=False
    )
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint("article_id", "stock_code", name="uk_article_stock"),
        Index("idx_article_id", "article_id"),
        Index("idx_stock_code", "stock_code"),
    )


# ---------------------------------------------------------------------------
# 8. t_event_reminder
# ---------------------------------------------------------------------------

class EventReminder(AuditMixin, Base):
    __tablename__ = "t_event_reminder"

    reminder_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    industry_tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "reminded_3day", "reminded_today", "archived"),
        nullable=False,
        default="pending",
    )
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("t_user.user_id"), nullable=False
    )

    __table_args__ = (
        Index("idx_user_id", "user_id"),
    )


# ---------------------------------------------------------------------------
# 9. t_chat_session
# ---------------------------------------------------------------------------

class ChatSession(AuditMixin, Base):
    __tablename__ = "t_chat_session"

    session_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("t_user.user_id"), nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    session_type: Mapped[str] = mapped_column(String(20), nullable=False, default="event_analysis")
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    messages = relationship(
        "ChatMessage", backref="session", lazy="selectin", order_by="ChatMessage.create_time"
    )

    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_session_type", "session_type"),
    )
# ---------------------------------------------------------------------------

class ChatMessage(AuditMixin, Base):
    __tablename__ = "t_chat_message"

    message_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("t_chat_session.session_id"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", "system"), nullable=False
    )
    content: Mapped[str] = mapped_column(MEDIUMTEXT, nullable=False)
    thinking_steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    agent_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_session_id", "session_id"),
    )


# ---------------------------------------------------------------------------
# 11. t_datasource_config
# ---------------------------------------------------------------------------

class DataSourceConfigModel(AuditMixin, Base):
    __tablename__ = "t_datasource_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    api_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=99)
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


# ---------------------------------------------------------------------------
# 12. t_sync_task
# ---------------------------------------------------------------------------

class SyncTaskModel(Base):
    __tablename__ = "t_sync_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    data_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    total_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fail_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        Index("idx_source_status", "source_type", "status"),
        Index("idx_create_time", "create_time"),
    )


# ---------------------------------------------------------------------------
# 13. t_market_quote
# ---------------------------------------------------------------------------

class MarketQuoteModel(Base):
    __tablename__ = "t_market_quote"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    change_pct: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(8, 2), nullable=True)
    change_amount: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    volume: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 0), nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 2), nullable=True)
    open_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    high_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    low_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    pre_close: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    quote_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_source: Mapped[str] = mapped_column(String(20), nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    pe_ttm: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True)
    pb: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint("code", "data_source", name="uk_code_source"),
    )


# ---------------------------------------------------------------------------
# 14. t_stock_daily_quote
# ---------------------------------------------------------------------------

class StockDailyQuoteModel(Base):
    __tablename__ = "t_stock_daily_quote"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    open_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    high_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    low_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    close_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    pre_close: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    volume: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 0), nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 2), nullable=True)
    pct_chg: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(8, 2), nullable=True)
    data_source: Mapped[str] = mapped_column(String(20), nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("code", "trade_date", "data_source", "period", name="uk_code_date_source_period"),
    )


# ---------------------------------------------------------------------------
# 16. t_stock_analysis（个股分析主表）
# ---------------------------------------------------------------------------

class StockAnalysisModel(AuditMixin, Base):
    __tablename__ = "t_stock_analysis"

    analysis_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)
    analysis_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="full")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    current_phase: Mapped[str] = mapped_column(String(20), nullable=False, default="analysts")
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    full_content: Mapped[Optional[str]] = mapped_column(MEDIUMTEXT, nullable=True)
    decision_action: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    target_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    stop_loss_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    confidence: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 4), nullable=True)
    risk_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 4), nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industries: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    data_source: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    article_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    user_id: Mapped[str] = mapped_column(
        String(32), nullable=False
    )

    details = relationship(
        "StockAnalysisDetailModel",
        backref="analysis",
        lazy="selectin",
        order_by="StockAnalysisDetailModel.display_order",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_sa_stock_code", "stock_code"),
        Index("idx_sa_status", "status"),
        Index("idx_sa_user_id", "user_id"),
        Index("idx_sa_create_time", "create_time"),
        Index("idx_sa_article_id", "article_id"),
    )


# ---------------------------------------------------------------------------
# 17. t_stock_analysis_detail（分析详情表）
# ---------------------------------------------------------------------------

class StockAnalysisDetailModel(AuditMixin, Base):
    __tablename__ = "t_stock_analysis_detail"

    detail_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("t_stock_analysis.analysis_id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phase: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    full_report: Mapped[Optional[str]] = mapped_column(MEDIUMTEXT, nullable=True)
    thinking_steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    debate_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_sad_analysis_id", "analysis_id"),
        Index("idx_sad_agent_name", "agent_name"),
        Index("idx_sad_phase", "phase"),
        Index("idx_sad_status", "status"),
    )


# ---------------------------------------------------------------------------
# 15. t_stock_financial
# ---------------------------------------------------------------------------

class StockFinancialModel(Base):
    __tablename__ = "t_stock_financial"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    roe: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(8, 2), nullable=True)
    net_profit: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 2), nullable=True)
    revenue: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 2), nullable=True)
    eps: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(8, 4), nullable=True)
    gross_margin: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(8, 2), nullable=True)
    debt_ratio: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(8, 2), nullable=True)
    data_source: Mapped[str] = mapped_column(String(20), nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("code", "report_date", "data_source", name="uk_code_date_source"),
    )


# ---------------------------------------------------------------------------
# Module 2: 自选股分组
# ---------------------------------------------------------------------------

class WatchlistGroupModel(Base):
    __tablename__ = "t_watchlist_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(10), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("idx_wg_user_id", "user_id"),
    )


class WatchlistItemModel(Base):
    __tablename__ = "t_watchlist_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("t_watchlist_group.id", ondelete="CASCADE"), nullable=False
    )
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)
    add_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("group_id", "stock_code", name="uk_group_stock"),
        Index("idx_wi_group_id", "group_id"),
        Index("idx_wi_stock_code", "stock_code"),
    )


class StockIndicatorModel(Base):
    __tablename__ = "t_stock_indicator"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False, default="daily")
    macd_dif: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 4), nullable=True)
    macd_dea: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 4), nullable=True)
    macd_bar: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 4), nullable=True)
    kdj_k: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(8, 4), nullable=True)
    kdj_d: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(8, 4), nullable=True)
    kdj_j: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(8, 4), nullable=True)
    ma5: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    ma10: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    ma20: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 3), nullable=True)
    data_source: Mapped[str] = mapped_column(String(20), nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", "period", name="uk_stock_indicator"),
        Index("idx_si_stock_date", "stock_code", "trade_date"),
    )
