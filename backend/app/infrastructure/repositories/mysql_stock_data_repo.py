"""MySQL Repository implementation for stock data (basic info, quotes, K-line, financial)."""

import logging
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import delete as sql_delete, select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.stock_data import (
    StockBasicInfo,
    MarketQuote,
    StockDailyQuote,
    StockFinancial,
    StockKline30m,
)
from app.domain.repositories.stock_data_repo import StockDataRepository
from app.domain.services.data_priority import get_highest_priority_source, SourceType
from app.infrastructure.db.models import (
    Stock,
    MarketQuoteModel,
    StockDailyQuoteModel,
    StockFinancialModel,
    StockKline30mModel,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 200


def _to_basic_info(model: Stock) -> StockBasicInfo:
    return StockBasicInfo(
        code=model.stock_code,
        name=model.name,
        exchange=model.exchange,
        market_type=model.market_type,
        industry=None,  # not stored on Stock model directly
        list_date=model.list_date,
        is_active=model.is_active,
        data_source=model.data_source or "",
        update_time=model.update_time,
    )


def _to_market_quote(model: MarketQuoteModel) -> MarketQuote:
    return MarketQuote(
        code=model.code,
        price=model.price,
        change_pct=model.change_pct,
        change_amount=model.change_amount,
        volume=model.volume,
        amount=model.amount,
        open_price=model.open_price,
        high_price=model.high_price,
        low_price=model.low_price,
        pre_close=model.pre_close,
        quote_time=model.quote_time,
        data_source=model.data_source,
        id=model.id,
        create_time=model.create_time,
        update_time=model.update_time,
    )


def _to_daily_quote(model: StockDailyQuoteModel) -> StockDailyQuote:
    return StockDailyQuote(
        code=model.code,
        trade_date=model.trade_date,
        period=model.period,
        open_price=model.open_price,
        high_price=model.high_price,
        low_price=model.low_price,
        close_price=model.close_price,
        pre_close=model.pre_close,
        volume=model.volume,
        amount=model.amount,
        pct_chg=model.pct_chg,
        data_source=model.data_source,
        id=model.id,
        create_time=model.create_time,
        update_time=model.update_time,
    )


def _to_financial(model: StockFinancialModel) -> StockFinancial:
    return StockFinancial(
        code=model.code,
        report_date=model.report_date,
        roe=model.roe,
        net_profit=model.net_profit,
        revenue=model.revenue,
        eps=model.eps,
        gross_margin=model.gross_margin,
        debt_ratio=model.debt_ratio,
        data_source=model.data_source,
        id=model.id,
        create_time=model.create_time,
        update_time=model.update_time,
    )


def _to_kline_30m(model: StockKline30mModel) -> StockKline30m:
    return StockKline30m(
        code=model.code,
        trade_time=model.trade_time,
        open_price=model.open_price,
        high_price=model.high_price,
        low_price=model.low_price,
        close_price=model.close_price,
        volume=model.volume,
        amount=model.amount,
        data_source=model.data_source,
        id=model.id,
        create_time=model.create_time,
        update_time=model.update_time,
    )


class MySQLStockDataRepository(StockDataRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Basic Info ---

    async def upsert_basic(self, info: StockBasicInfo) -> None:
        """Upsert stock basic info by stock_code (primary key)."""
        stmt = select(Stock).where(Stock.stock_code == info.code)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = info.name
            existing.exchange = info.exchange or existing.exchange
            existing.market_type = info.market_type or existing.market_type
            existing.list_date = info.list_date or existing.list_date
            existing.is_active = info.is_active
            existing.data_source = info.data_source or existing.data_source
            existing.update_time = datetime.now()
        else:
            new_stock = Stock(
                stock_code=info.code,
                name=info.name,
                exchange=info.exchange or "SH",
                market_type=info.market_type,
                list_date=info.list_date,
                is_active=info.is_active,
                data_source=info.data_source,
            )
            self.session.add(new_stock)

        await self.session.flush()

    async def get_basic(self, code: str) -> Optional[StockBasicInfo]:
        """Get basic info using highest priority data source."""
        stmt = select(Stock).where(Stock.stock_code == code)
        result = await self.session.execute(stmt)
        all_stocks = result.scalars().all()

        if not all_stocks:
            return None

        # Pick highest priority source
        available = [
            s for s in all_stocks
            if s.data_source
        ]
        if available:
            sources = []
            for s in available:
                try:
                    sources.append(SourceType(s.data_source))
                except ValueError:
                    continue
            best = get_highest_priority_source(sources)
            if best:
                best_str = best.value
                for s in all_stocks:
                    if s.data_source == best_str:
                        return _to_basic_info(s)

        return _to_basic_info(all_stocks[0])

    async def get_basic_all_sources(self, code: str) -> List[StockBasicInfo]:
        stmt = select(Stock).where(Stock.stock_code == code)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [_to_basic_info(m) for m in models]

    async def get_all_stocks(self) -> List[StockBasicInfo]:
        stmt = select(Stock).where(Stock.is_active == True)
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        # 去重：同一 code 取优先级最高的数据源
        by_code: dict[str, Stock] = {}
        for m in models:
            if m.stock_code not in by_code:
                by_code[m.stock_code] = m
            else:
                existing_src = by_code[m.stock_code].data_source
                try:
                    existing_type = SourceType(existing_src) if existing_src else None
                except ValueError:
                    existing_type = None
                try:
                    new_type = SourceType(m.data_source) if m.data_source else None
                except ValueError:
                    new_type = None
                best = get_highest_priority_source([t for t in [existing_type, new_type] if t])
                if best and best.value == m.data_source:
                    by_code[m.stock_code] = m

        return [_to_basic_info(m) for m in by_code.values()]

    # --- Market Quote ---

    async def upsert_quote(self, quote: MarketQuote) -> None:
        stmt = select(MarketQuoteModel).where(
            MarketQuoteModel.code == quote.code,
            MarketQuoteModel.data_source == quote.data_source,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.price = quote.price
            existing.change_pct = quote.change_pct
            existing.change_amount = quote.change_amount
            existing.volume = quote.volume
            existing.amount = quote.amount
            existing.open_price = quote.open_price
            existing.high_price = quote.high_price
            existing.low_price = quote.low_price
            existing.pre_close = quote.pre_close
            existing.quote_time = quote.quote_time
            existing.update_time = datetime.now()
        else:
            new_quote = MarketQuoteModel(
                code=quote.code,
                price=quote.price,
                change_pct=quote.change_pct,
                change_amount=quote.change_amount,
                volume=quote.volume,
                amount=quote.amount,
                open_price=quote.open_price,
                high_price=quote.high_price,
                low_price=quote.low_price,
                pre_close=quote.pre_close,
                quote_time=quote.quote_time or datetime.now(),
                data_source=quote.data_source,
            )
            self.session.add(new_quote)

        await self.session.flush()

    async def get_quote(self, code: str) -> Optional[MarketQuote]:
        stmt = (
            select(MarketQuoteModel)
            .where(MarketQuoteModel.code == code)
            .order_by(MarketQuoteModel.quote_time.desc())
        )
        result = await self.session.execute(stmt)
        all_quotes = result.scalars().all()

        if not all_quotes:
            return None

        available = []
        for q in all_quotes:
            try:
                available.append(SourceType(q.data_source))
            except ValueError:
                continue

        if available:
            best = get_highest_priority_source(available)
            if best:
                best_str = best.value
                for q in all_quotes:
                    if q.data_source == best_str:
                        return _to_market_quote(q)

        return _to_market_quote(all_quotes[0])

    async def get_quotes_batch(self, codes: List[str]) -> List[MarketQuote]:
        """批量获取多只股票最新行情，按 code 分组后取优先级最高的数据源"""
        if not codes:
            return []

        stmt = (
            select(MarketQuoteModel)
            .where(MarketQuoteModel.code.in_(codes))
            .order_by(MarketQuoteModel.code, MarketQuoteModel.quote_time.desc())
        )
        result = await self.session.execute(stmt)
        all_quotes = result.scalars().all()

        # Group by code
        quote_map: dict[str, list] = {}
        for q in all_quotes:
            quote_map.setdefault(q.code, []).append(q)

        results: List[MarketQuote] = []
        for code, quotes in quote_map.items():
            available = []
            for q in quotes:
                try:
                    available.append(SourceType(q.data_source))
                except ValueError:
                    continue
            if available:
                best = get_highest_priority_source(available)
                if best:
                    best_str = best.value
                    for q in quotes:
                        if q.data_source == best_str:
                            results.append(_to_market_quote(q))
                            break
                    else:
                        results.append(_to_market_quote(quotes[0]))
                else:
                    results.append(_to_market_quote(quotes[0]))
            else:
                results.append(_to_market_quote(quotes[0]))

        return results

    # --- Daily Quote ---

    async def upsert_daily(self, quote: StockDailyQuote) -> None:
        stmt = select(StockDailyQuoteModel).where(
            StockDailyQuoteModel.code == quote.code,
            StockDailyQuoteModel.trade_date == quote.trade_date,
            StockDailyQuoteModel.data_source == quote.data_source,
            StockDailyQuoteModel.period == quote.period,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.open_price = quote.open_price
            existing.high_price = quote.high_price
            existing.low_price = quote.low_price
            existing.close_price = quote.close_price
            existing.pre_close = quote.pre_close
            existing.volume = quote.volume
            existing.amount = quote.amount
            existing.pct_chg = quote.pct_chg
            existing.update_time = datetime.now()
        else:
            new_q = StockDailyQuoteModel(
                code=quote.code,
                trade_date=quote.trade_date,
                period=quote.period,
                open_price=quote.open_price,
                high_price=quote.high_price,
                low_price=quote.low_price,
                close_price=quote.close_price,
                pre_close=quote.pre_close,
                volume=quote.volume,
                amount=quote.amount,
                pct_chg=quote.pct_chg,
                data_source=quote.data_source,
            )
            self.session.add(new_q)

        await self.session.flush()

    async def upsert_daily_batch(self, quotes: List[StockDailyQuote]) -> None:
        """先删除后插入，避免不同数据源产生重复记录。

        同一批次数据必然来自同一 (code, period)，按日期范围先清除旧数据再插入新数据，
        确保每个交易日只有一条记录。
        """
        if not quotes:
            return

        for i in range(0, len(quotes), BATCH_SIZE):
            batch = quotes[i:i + BATCH_SIZE]

            dates = [q.trade_date for q in batch if q.trade_date]
            if not dates:
                continue

            code = batch[0].code
            period = batch[0].period
            data_source = batch[0].data_source

            # 先删除该 (code, period, data_source) 在日期范围内的旧记录。
            # data_source 必须精确匹配：唯一索引 uk_code_date_source_period 上
            # 若只用 (code, period, trade_date) 范围删，InnoDB 会给相邻区间（含
            # 其他 data_source 的记录）加 next-key/gap lock，并发 upsert 不同股票时
            # gap lock 互相重叠引发死锁（1213）。
            stmt = sql_delete(StockDailyQuoteModel).where(
                StockDailyQuoteModel.code == code,
                StockDailyQuoteModel.period == period,
                StockDailyQuoteModel.data_source == data_source,
                StockDailyQuoteModel.trade_date.in_(dates),
            )
            await self.session.execute(stmt)

            # 再插入新记录
            for quote in batch:
                new_q = StockDailyQuoteModel(
                    code=quote.code,
                    trade_date=quote.trade_date,
                    period=quote.period,
                    open_price=quote.open_price,
                    high_price=quote.high_price,
                    low_price=quote.low_price,
                    close_price=quote.close_price,
                    pre_close=quote.pre_close,
                    volume=quote.volume,
                    amount=quote.amount,
                    pct_chg=quote.pct_chg,
                    data_source=quote.data_source,
                )
                self.session.add(new_q)

            await self.session.flush()

    async def get_daily(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
    ) -> List[StockDailyQuote]:
        conditions = [
            StockDailyQuoteModel.code == code,
            StockDailyQuoteModel.period == period,
        ]
        conditions = [
            StockDailyQuoteModel.code == code,
            StockDailyQuoteModel.period == period,
        ]
        if start_date:
            conditions.append(StockDailyQuoteModel.trade_date >= start_date)
        if end_date:
            conditions.append(StockDailyQuoteModel.trade_date <= end_date)

        stmt = (
            select(StockDailyQuoteModel)
            .where(and_(*conditions))
            .order_by(StockDailyQuoteModel.trade_date.asc())
        )
        result = await self.session.execute(stmt)
        all_quotes = result.scalars().all()

        if not all_quotes:
            return []

        # Group by data_source
        by_source: dict[str, list] = {}
        for q in all_quotes:
            by_source.setdefault(q.data_source, []).append(q)

        # Pick highest priority source
        sources = []
        for src in by_source:
            try:
                sources.append(SourceType(src))
            except ValueError:
                continue

        best = get_highest_priority_source(sources)
        if best:
            best_str = best.value
            if best_str in by_source:
                return [_to_daily_quote(q) for q in by_source[best_str]]

        # Fallback: return first source
        first_key = list(by_source.keys())[0]
        return [_to_daily_quote(q) for q in by_source[first_key]]

    # --- 30 分钟 K 线（缠论模块三） ---

    async def upsert_kline_30m_batch(self, quotes: List[StockKline30m]) -> None:
        """先删后插，避免重复（同一批次必然同 code）。"""
        if not quotes:
            return
        for i in range(0, len(quotes), BATCH_SIZE):
            batch = quotes[i:i + BATCH_SIZE]
            times = [q.trade_time for q in batch if q.trade_time]
            if not times:
                continue
            code = batch[0].code
            # 先删除该 code 在时间范围内的旧记录（含多数据源，统一以最新批次为准）
            stmt = sql_delete(StockKline30mModel).where(
                StockKline30mModel.code == code,
                StockKline30mModel.trade_time.in_(times),
            )
            await self.session.execute(stmt)
            for q in batch:
                self.session.add(StockKline30mModel(
                    code=q.code,
                    trade_time=q.trade_time,
                    open_price=q.open_price,
                    high_price=q.high_price,
                    low_price=q.low_price,
                    close_price=q.close_price,
                    volume=q.volume,
                    amount=q.amount,
                    data_source=q.data_source,
                ))
            await self.session.flush()

    async def get_kline_30m(
        self,
        code: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[StockKline30m]:
        conditions = [StockKline30mModel.code == code]
        if start_time:
            conditions.append(StockKline30mModel.trade_time >= start_time)
        if end_time:
            conditions.append(StockKline30mModel.trade_time <= end_time)
        stmt = (
            select(StockKline30mModel)
            .where(and_(*conditions))
            .order_by(StockKline30mModel.trade_time.asc())
        )
        result = await self.session.execute(stmt)
        return [_to_kline_30m(m) for m in result.scalars().all()]

    async def get_latest_kline_30m_time(
        self, code: str, closed_before: Optional[datetime] = None
    ) -> Optional[datetime]:
        """最新 30m K 线时间；``closed_before`` 给定时只统计已收盘行。

        30m K 线时间戳=周期结束时点，盘中落库的 forming 行时间戳为未来时点；
        传 ``closed_before=now`` 可将其排除（与 ``chanlun_calc._load_m30_bars``
        的剔除口径一致，供 stale 判断使用）。
        """
        conditions = [StockKline30mModel.code == code]
        if closed_before is not None:
            conditions.append(StockKline30mModel.trade_time <= closed_before)
        stmt = (
            select(StockKline30mModel.trade_time)
            .where(and_(*conditions))
            .order_by(StockKline30mModel.trade_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # --- Financial Data ---

    async def upsert_financial(self, data: StockFinancial) -> None:
        stmt = select(StockFinancialModel).where(
            StockFinancialModel.code == data.code,
            StockFinancialModel.report_date == data.report_date,
            StockFinancialModel.data_source == data.data_source,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.roe = data.roe
            existing.net_profit = data.net_profit
            existing.revenue = data.revenue
            existing.eps = data.eps
            existing.gross_margin = data.gross_margin
            existing.debt_ratio = data.debt_ratio
            existing.update_time = datetime.now()
        else:
            new_f = StockFinancialModel(
                code=data.code,
                report_date=data.report_date,
                roe=data.roe,
                net_profit=data.net_profit,
                revenue=data.revenue,
                eps=data.eps,
                gross_margin=data.gross_margin,
                debt_ratio=data.debt_ratio,
                data_source=data.data_source,
            )
            self.session.add(new_f)

        await self.session.flush()

    async def upsert_financial_batch(self, data_list: List[StockFinancial]) -> None:
        for data in data_list:
            await self.upsert_financial(data)
        await self.session.flush()

    async def get_financial(self, code: str) -> List[StockFinancial]:
        stmt = (
            select(StockFinancialModel)
            .where(StockFinancialModel.code == code)
            .order_by(StockFinancialModel.report_date.desc())
        )
        result = await self.session.execute(stmt)
        all_data = result.scalars().all()

        if not all_data:
            return []

        by_source: dict[str, list] = {}
        for d in all_data:
            by_source.setdefault(d.data_source, []).append(d)

        sources = []
        for src in by_source:
            try:
                sources.append(SourceType(src))
            except ValueError:
                continue

        best = get_highest_priority_source(sources)
        if best:
            best_str = best.value
            if best_str in by_source:
                return [_to_financial(d) for d in by_source[best_str]]

        first_key = list(by_source.keys())[0]
        return [_to_financial(d) for d in by_source[first_key]]
