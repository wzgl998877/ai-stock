"""初始化 t_industry 表 — 31 个申万一级行业"""
import asyncio
import sys
import os

# 添加 backend 根目录到 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("错误: 未找到 DATABASE_URL 环境变量")
    sys.exit(1)

INDUSTRIES = [
    ('110000', '农林牧渔', 1, None, 1),
    ('220000', '基础化工', 1, None, 2),
    ('230000', '钢铁', 1, None, 3),
    ('240000', '有色金属', 1, None, 4),
    ('270000', '电子', 1, None, 5),
    ('280000', '汽车', 1, None, 6),
    ('330000', '家用电器', 1, None, 7),
    ('340000', '食品饮料', 1, None, 8),
    ('350000', '纺织服装', 1, None, 9),
    ('360000', '轻工制造', 1, None, 10),
    ('370000', '医药生物', 1, None, 11),
    ('410000', '公用事业', 1, None, 12),
    ('420000', '交通运输', 1, None, 13),
    ('430000', '房地产', 1, None, 14),
    ('440000', '商贸零售', 1, None, 15),
    ('450000', '社会服务', 1, None, 16),
    ('480000', '银行', 1, None, 17),
    ('490000', '非银金融', 1, None, 18),
    ('510000', '综合', 1, None, 19),
    ('610000', '建筑材料', 1, None, 20),
    ('620000', '建筑装饰', 1, None, 21),
    ('630000', '电力设备', 1, None, 22),
    ('640000', '机械设备', 1, None, 23),
    ('650000', '国防军工', 1, None, 24),
    ('710000', '计算机', 1, None, 25),
    ('720000', '传媒', 1, None, 26),
    ('730000', '通信', 1, None, 27),
    ('810000', '煤炭', 1, None, 28),
    ('820000', '石油石化', 1, None, 29),
    ('830000', '环保', 1, None, 30),
    ('840000', '美容护理', 1, None, 31),
]


async def init():
    print(f"连接数据库: {DATABASE_URL.split('://')[0]}://***@{DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else ''}")

    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

    async with engine.connect() as conn:
        # 先检查现有数据
        result = await conn.execute(text('SELECT COUNT(*) FROM t_industry WHERE deleted="0"'))
        cnt = result.scalar()
        print(f"现有行业数据: {cnt} 条")

        if cnt > 0:
            print("已有数据，跳过初始化")
            await engine.dispose()
            return

        # 逐条插入行业数据
        for code, name, level, parent, order_ in INDUSTRIES:
            await conn.execute(
                text("""
                    INSERT INTO t_industry (industry_code, name, level, parent_code, display_order, create_time, update_time, deleted)
                    VALUES (:code, :name, :level, :parent, :order_, NOW(), NOW(), '0')
                    ON DUPLICATE KEY UPDATE name=VALUES(name), level=VALUES(level), display_order=VALUES(display_order)
                """),
                {
                    "code": code,
                    "name": name,
                    "level": level,
                    "parent": parent,
                    "order_": order_,
                },
            )

        await conn.commit()

        # 验证
        result = await conn.execute(text('SELECT industry_code, name FROM t_industry WHERE deleted="0" ORDER BY display_order'))
        rows = result.fetchall()
        print(f"\n初始化完成，共插入 {len(rows)} 条行业数据:")
        for r in rows:
            print(f"  {r[0]} - {r[1]}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init())
