"""SQLAlchemy ORM models for all 10 tables.

DDL source: docs/FEATURES/AI_Analysis/ai-analysis.ddl.md
"""

import uuid
from datetime import date, datetime
from typing import Optional

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
from sqlalchemy.dialects.mysql import JSON
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
    content: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(
        Enum("geopolitical", "policy", "earnings", "supply_chain", "other"),
        nullable=False,
    )
    raw_input: Mapped[str] = mapped_column(String(500), nullable=False)
    chain_table: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
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
    )


# ---------------------------------------------------------------------------
# 6. t_article_industry
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

    messages = relationship(
        "ChatMessage", backref="session", lazy="selectin", order_by="ChatMessage.create_time"
    )

    __table_args__ = (
        Index("idx_user_id", "user_id"),
    )


# ---------------------------------------------------------------------------
# 10. t_chat_message
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
    content: Mapped[str] = mapped_column(Text, nullable=False)
    thinking_steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        Index("idx_session_id", "session_id"),
    )
