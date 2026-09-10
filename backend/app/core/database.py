from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_recycle=1800,        # 每 30 分钟回收连接，避免 MySQL gone away
    pool_size=10,
    max_overflow=20,
    # TCP 建连超时（秒）：aiomysql 透传给 pymysql 的 connect_timeout。
    # 无此项时半开网络下的新建连接会无限等待（2026-09-10 生产事故：手动重算
    # 与定时扫描叠跑、池频繁建连，撞上无响应建连后协程永久悬死）。
    # 只覆盖建连阶段；会话期 IO 的兜底由调用侧 wait_for 看门狗负责。
    connect_args={"connect_timeout": 10},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
