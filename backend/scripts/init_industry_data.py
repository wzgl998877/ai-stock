"""一次性初始化脚本：从 AKShare 获取申万一级行业分类数据并写入数据库。

功能：
  1. 获取所有 A 股股票代码 + 名称（ak.stock_info_a_code_name）
  2. 获取申万一级行业分类及其成分股（ak.stock_board_industry_name_em + ak.stock_board_industry_cons_em）
  3. 确保 t_industry 表中已有 31 个行业（缺失则插入）
  4. 更新 t_stock 的 industry_code / industry_name 字段
  5. 写入 t_stock_industry 映射关系

用法（在 backend 目录下运行）：
    python -m scripts.init_industry_data

幂等性：可安全重复运行，已存在的行业记录和映射关系不会重复创建。
"""

import asyncio
import logging
import os
import sys
import time
import uuid

# 确保可以导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.infrastructure.db.models import Industry, Stock, StockIndustry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 申万一级行业：东方财富行业名称 → 数据库 industry_code 映射
# 来源：seed_industries.sql 中的 31 个行业
# ---------------------------------------------------------------------------

# AKShare stock_board_industry_name_em 返回的「板块名称」可能与数据库
# 中的「name」字段有细微差异，所以用 name 作为映射的 key。
# 这里列出所有 31 个行业名称，用于精确匹配。
INDUSTRY_NAME_TO_CODE: dict[str, str] = {
    "农林牧渔": "110000",
    "基础化工": "220000",
    "钢铁": "230000",
    "有色金属": "240000",
    "电子": "270000",
    "汽车": "280000",
    "家用电器": "330000",
    "食品饮料": "340000",
    "纺织服饰": "350000",
    "纺织服装": "350000",
    "轻工制造": "360000",
    "医药生物": "370000",
    "公用事业": "410000",
    "交通运输": "420000",
    "房地产": "430000",
    "商贸零售": "440000",
    "社会服务": "450000",
    "银行": "480000",
    "非银金融": "490000",
    "综合": "510000",
    "建筑材料": "610000",
    "建筑装饰": "620000",
    "电力设备": "630000",
    "机械设备": "640000",
    "国防军工": "650000",
    "计算机": "710000",
    "传媒": "720000",
    "通信": "730000",
    "煤炭": "810000",
    "石油石化": "820000",
    "环保": "830000",
    "美容护理": "840000",
}

# 反向映射：industry_code → name（取规范名称）
INDUSTRY_CODE_TO_NAME: dict[str, str] = {}
_seen_codes: set[str] = set()
for _name, _code in INDUSTRY_NAME_TO_CODE.items():
    if _code not in _seen_codes:
        INDUSTRY_CODE_TO_NAME[_code] = _name
        _seen_codes.add(_code)

# 规范化名称映射（东方财富可能的别名 → 规范名称）
# 例如 "纺织服饰" 和 "纺织服装" 都映射到 "350000"
CANONICAL_INDUSTRY_NAMES: dict[str, str] = {}
for _name, _code in INDUSTRY_NAME_TO_CODE.items():
    if _name not in CANONICAL_INDUSTRY_NAMES:
        CANONICAL_INDUSTRY_NAMES[_name] = INDUSTRY_CODE_TO_NAME[_code]


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return uuid.uuid4().hex


def _infer_exchange(code: str) -> str:
    """根据股票代码前缀推断交易所。"""
    if not code:
        return ""
    first = code[0]
    if first == "6":
        return "SH"
    if first in ("0", "3"):
        return "SZ"
    if first in ("4", "8"):
        return "BJ"
    return ""


def _safe_fetch(func, *args, **kwargs):
    """带重试的安全 AKShare 调用，返回 DataFrame 或空 DataFrame。"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            df = func(*args, **kwargs)
            if df is None:
                return pd.DataFrame()
            return df
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning("AKShare 调用失败(第%d次重试): %s", attempt + 1, e)
                time.sleep(wait)
            else:
                logger.error("AKShare 调用失败(重试耗尽): %s", e, exc_info=True)
                return pd.DataFrame()


def _is_valid_stock_code(code: str) -> bool:
    """判断是否为有效的 A 股代码（6 位纯数字）。"""
    return bool(code) and len(code) == 6 and code.isdigit()


# ---------------------------------------------------------------------------
# 步骤 1：获取所有 A 股基础信息
# ---------------------------------------------------------------------------

def fetch_all_stocks() -> dict[str, str]:
    """获取所有 A 股代码→名称映射。

    Returns:
        {stock_code: stock_name, ...}
    """
    logger.info("=== 步骤1：获取所有 A 股股票基础信息 ===")
    df = _safe_fetch(ak.stock_info_a_code_name)
    if df.empty:
        logger.error("无法获取股票基础信息，终止")
        return {}

    stock_map: dict[str, str] = {}
    for _, row in df.iterrows():
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        if _is_valid_stock_code(code) and name:
            stock_map[code] = name

    logger.info("获取到 %d 只 A 股股票", len(stock_map))
    return stock_map


# ---------------------------------------------------------------------------
# 步骤 2：获取申万一级行业分类及成分股
# ---------------------------------------------------------------------------

def fetch_industry_constituents() -> dict[str, list[str]]:
    """获取申万一级行业分类及其成分股。

    Returns:
        {industry_code: [stock_code, ...], ...}
    """
    logger.info("=== 步骤2：获取申万一级行业分类及成分股 ===")

    # 2.1 获取所有行业板块名称
    logger.info("获取行业板块列表...")
    df_industries = _safe_fetch(ak.stock_board_industry_name_em)
    if df_industries.empty:
        logger.error("无法获取行业板块列表，终止")
        return {}

    logger.info("AKShare 返回 %d 个行业板块", len(df_industries))
    logger.info("行业板块列名: %s", list(df_industries.columns))

    # 筛选出属于申万一级行业的板块
    # AKShare 返回的列名可能是「板块名称」
    name_col = None
    for col in df_industries.columns:
        if "名称" in str(col) or "name" in str(col).lower():
            name_col = col
            break
    if name_col is None and len(df_industries.columns) >= 2:
        # 尝试第二列（第一列通常是排名/序号）
        name_col = df_industries.columns[1]

    if name_col is None:
        logger.error("无法识别行业名称列，列名: %s", list(df_industries.columns))
        return {}

    industry_constituents: dict[str, list[str]] = {}
    total_industries = 0
    matched_industries = 0

    for _, row in df_industries.iterrows():
        ind_name = str(row.get(name_col, "")).strip()
        if not ind_name:
            continue

        ind_code = INDUSTRY_NAME_TO_CODE.get(ind_name)
        if ind_code is None:
            # 尝试模糊匹配：部分名称包含即可
            continue

        total_industries += 1
        matched_industries += 1
        logger.info("匹配行业: '%s' → industry_code=%s", ind_name, ind_code)

        # 2.2 获取该行业的成分股
        logger.info("获取行业 '%s' 的成分股...", ind_name)
        df_cons = _safe_fetch(ak.stock_board_industry_cons_em, symbol=ind_name)

        codes: list[str] = []
        if not df_cons.empty:
            # 成分股 DataFrame 中，代码列名可能是「代码」
            code_col = None
            for col in df_cons.columns:
                if "代码" in str(col) or "code" in str(col).lower():
                    code_col = col
                    break
            if code_col is None and len(df_cons.columns) >= 2:
                code_col = df_cons.columns[1]

            if code_col:
                for _, cons_row in df_cons.iterrows():
                    code = str(cons_row.get(code_col, "")).strip()
                    if _is_valid_stock_code(code):
                        codes.append(code)

        industry_constituents[ind_code] = codes
        logger.info("行业 '%s' 成分股数量: %d", ind_name, len(codes))

        # 请求间隔，避免被封
        time.sleep(0.3)

    logger.info(
        "行业匹配结果: AKShare返回 %d 个板块, 匹配到 %d 个申万一级行业",
        len(df_industries),
        matched_industries,
    )
    return industry_constituents


# ---------------------------------------------------------------------------
# 步骤 3：确保 t_industry 中有 31 个行业
# ---------------------------------------------------------------------------

async def ensure_industries(session: AsyncSession) -> None:
    """确保 t_industry 表中已有 31 个申万一级行业，缺失则插入。"""
    logger.info("=== 步骤3：检查并补充 t_industry 行业记录 ===")

    # 查询已有的行业
    stmt = select(Industry).where(Industry.level == 1)
    result = await session.execute(stmt)
    existing = {row.industry_code: row for row in result.scalars().all()}
    logger.info("数据库中已有 %d 个一级行业", len(existing))

    # 插入缺失的行业
    added = 0
    for ind_code, ind_name in INDUSTRY_CODE_TO_NAME.items():
        if ind_code in existing:
            continue

        # 从 seed 数据中获取 display_order
        display_order_map = {
            "110000": 1, "220000": 2, "230000": 3, "240000": 4,
            "270000": 5, "280000": 6, "330000": 7, "340000": 8,
            "350000": 9, "360000": 10, "370000": 11, "410000": 12,
            "420000": 13, "430000": 14, "440000": 15, "450000": 16,
            "480000": 17, "490000": 18, "510000": 19, "610000": 20,
            "620000": 21, "630000": 22, "640000": 23, "650000": 24,
            "710000": 25, "720000": 26, "730000": 27, "810000": 28,
            "820000": 29, "830000": 30, "840000": 31,
        }
        industry = Industry(
            industry_code=ind_code,
            name=ind_name,
            level=1,
            parent_code=None,
            display_order=display_order_map.get(ind_code, 0),
        )
        session.add(industry)
        added += 1
        logger.info("新增行业: %s (%s)", ind_name, ind_code)

    if added > 0:
        await session.flush()
        logger.info("新增了 %d 个行业记录", added)
    else:
        logger.info("所有 31 个行业已存在，无需新增")


# ---------------------------------------------------------------------------
# 步骤 4：更新 t_stock 表的 industry_code / industry_name
# ---------------------------------------------------------------------------

async def update_stock_industry_fields(
    session: AsyncSession,
    industry_constituents: dict[str, list[str]],
) -> int:
    """更新 t_stock 表中每只股票的 industry_code 和 industry_name 字段。

    Returns:
        成功更新的股票数量
    """
    logger.info("=== 步骤4：更新 t_stock 行业字段 ===")

    # 构建 code → (industry_code, industry_name) 映射
    stock_industry_map: dict[str, tuple[str, str]] = {}
    for ind_code, stock_codes in industry_constituents.items():
        ind_name = INDUSTRY_CODE_TO_NAME.get(ind_code, "")
        for code in stock_codes:
            stock_industry_map[code] = (ind_code, ind_name)

    logger.info("从行业成分股构建了 %d 条 股票→行业 映射", len(stock_industry_map))

    # 查询数据库中所有股票
    stmt = select(Stock).where(Stock.deleted == "0")
    result = await session.execute(stmt)
    all_stocks = result.scalars().all()
    logger.info("数据库中有 %d 只股票", len(all_stocks))

    updated = 0
    skipped = 0
    for stock in all_stocks:
        mapping = stock_industry_map.get(stock.stock_code)
        if mapping is None:
            skipped += 1
            continue

        ind_code, ind_name = mapping
        # 只在值不同时才更新
        if stock.industry_code != ind_code or stock.industry_name != ind_name:
            stock.industry_code = ind_code
            stock.industry_name = ind_name
            updated += 1

    if updated > 0:
        await session.flush()

    logger.info("更新 t_stock: 更新 %d 只, 无需更新 %d 只", updated, skipped)
    return updated


# ---------------------------------------------------------------------------
# 步骤 5：写入 t_stock_industry 映射
# ---------------------------------------------------------------------------

async def upsert_stock_industry_mappings(
    session: AsyncSession,
    industry_constituents: dict[str, list[str]],
    all_stock_codes_in_db: set[str],
) -> int:
    """确保 t_stock_industry 表中的映射关系存在。

    对于已存在的映射（stock_code + industry_code 唯一键），跳过不重复创建。
    对于缺失的映射，新增记录。

    Returns:
        新增的映射数量
    """
    logger.info("=== 步骤5：写入 t_stock_industry 映射 ===")

    # 查询已有的映射
    stmt = select(StockIndustry.stock_code, StockIndustry.industry_code).where(
        StockIndustry.deleted == "0"
    )
    result = await session.execute(stmt)
    existing_pairs = {(row[0], row[1]) for row in result.all()}
    logger.info("数据库中已有 %d 条映射关系", len(existing_pairs))

    added = 0
    skipped_not_in_db = 0
    for ind_code, stock_codes in industry_constituents.items():
        for code in stock_codes:
            # 只处理数据库中存在的股票
            if code not in all_stock_codes_in_db:
                skipped_not_in_db += 1
                continue

            if (code, ind_code) in existing_pairs:
                continue

            mapping = StockIndustry(
                id=_uuid(),
                stock_code=code,
                industry_code=ind_code,
                is_primary=True,
                classification_source="official",
            )
            session.add(mapping)
            existing_pairs.add((code, ind_code))
            added += 1

    if added > 0:
        await session.flush()

    logger.info(
        "t_stock_industry: 新增 %d 条映射, 不在库中的股票跳过 %d 条",
        added,
        skipped_not_in_db,
    )
    return added


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

async def init_industry_data() -> None:
    """一次性初始化行业数据的主流程。"""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("开始行业数据初始化")
    logger.info("=" * 60)

    # --- 同步部分：从 AKShare 获取数据 ---
    stock_map = fetch_all_stocks()
    if not stock_map:
        logger.error("未获取到股票数据，退出")
        return

    industry_constituents = fetch_industry_constituents()
    if not industry_constituents:
        logger.error("未获取到行业成分股数据，退出")
        return

    # 统计行业成分股总数
    total_constituents = sum(len(v) for v in industry_constituents.values())
    logger.info(
        "行业数据汇总: %d 个行业, %d 条成分股关系",
        len(industry_constituents),
        total_constituents,
    )

    # --- 异步部分：写入数据库 ---
    logger.info("开始写入数据库...")
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # 步骤3：确保行业记录存在
            await ensure_industries(session)

            # 获取数据库中所有有效的股票代码
            stmt = select(Stock.stock_code).where(Stock.deleted == "0")
            result = await session.execute(stmt)
            all_stock_codes_in_db = {row[0] for row in result.all()}
            logger.info("数据库中有效股票数: %d", len(all_stock_codes_in_db))

            # 步骤4：更新 t_stock 行业字段
            await update_stock_industry_fields(session, industry_constituents)

            # 步骤5：写入 t_stock_industry 映射
            await upsert_stock_industry_mappings(
                session, industry_constituents, all_stock_codes_in_db
            )

            # 提交事务
            await session.commit()
            logger.info("数据库事务提交成功")

        except Exception as e:
            await session.rollback()
            logger.error("数据库操作失败，已回滚: %s", e, exc_info=True)
            raise

    await engine.dispose()

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("行业数据初始化完成，总耗时 %.1f 秒", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(init_industry_data())
