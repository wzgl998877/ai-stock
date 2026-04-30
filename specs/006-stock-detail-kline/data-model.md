# Data Model: 股票详情页与行情数据展示

**Feature**: 006-stock-detail-kline
**Date**: 2026-04-30

---

## 1. Entity Overview

```text
+----------------+        +------------------+        +------------------+
|     Stock      |<------>|  IndustryStock   |<------|    Industry      |
|  (已有,扩展)    |        |   (新增)          |        |   (已有)         |
+----------------+        +------------------+        +------------------+
       ^
       |
       | 1:N
       v
+----------------+        +------------------+        +------------------+
| WatchlistItem  |------->| WatchlistGroup   |<------|      User        |
|   (新增)        |        |   (新增)          |        |   (已有)         |
+----------------+        +------------------+        +------------------+
       ^
       |
       | N:1
       v
+----------------+        +------------------+        +------------------+
|ArticleStockRel |<------>|     Article      |        |  StockIndicator  |
|   (新增)        |        |   (已有)         |        |   (新增)          |
+----------------+        +------------------+        +------------------+
```

---

## 2. Domain Entities

### 2.1 Stock (已有, 需扩展)

```python
@dataclass
class Stock:
    stock_code: str          # PK, 如 "300750"
    name: str                # 如 "宁德时代"
    exchange: str            # SH / SZ / BJ
    full_name: Optional[str] = None
    list_date: Optional[date] = None
    is_active: bool = True
    # 新增字段 ↓
    industry_code: Optional[str] = None   # 申万一级行业代码
    industry_name: Optional[str] = None   # 申万一级行业名称
    total_market_cap: Optional[Decimal] = None   # 总市值(亿元)
    float_market_cap: Optional[Decimal] = None   # 流通市值(亿元)
```

### 2.2 Industry (已有)

```python
@dataclass
class Industry:
    industry_code: str       # PK, 如 "480000"
    name: str                # 如 "电力设备"
    level: int               # 1=一级, 2=二级, 3=三级
    parent_code: Optional[str] = None
    display_order: int = 0
```

### 2.3 IndustryStock (新增)

```python
@dataclass
class IndustryStock:
    id: Optional[int] = None
    industry_code: str       # FK -> Industry.industry_code
    stock_code: str          # FK -> Stock.stock_code
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
```

### 2.4 WatchlistGroup (新增)

```python
@dataclass
class WatchlistGroup:
    id: Optional[int] = None
    user_id: str             # FK -> User.id
    name: str                # 分组名称, max 10 chars
    display_order: int = 0   # 排序
    is_default: bool = False # 是否系统默认分组
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
```

### 2.5 WatchlistItem (新增)

```python
@dataclass
class WatchlistItem:
    id: Optional[int] = None
    group_id: int            # FK -> WatchlistGroup.id
    stock_code: str          # FK -> Stock.stock_code
    stock_name: str          # 冗余, 避免join
    add_time: Optional[datetime] = None
    create_time: Optional[datetime] = None
```

### 2.6 ArticleStockRelation (新增)

```python
@dataclass
class ArticleStockRelation:
    id: Optional[int] = None
    article_id: int          # FK -> Article.id
    stock_code: str          # FK -> Stock.stock_code
    stock_name: str          # 冗余
    create_time: Optional[datetime] = None
```

### 2.7 StockIndicator (新增)

```python
@dataclass
class StockIndicator:
    """技术指标计算结果缓存"""
    id: Optional[int] = None
    stock_code: str
    trade_date: date
    period: str              # daily/weekly/monthly

    # MACD
    macd_dif: Optional[Decimal] = None
    macd_dea: Optional[Decimal] = None
    macd_bar: Optional[Decimal] = None

    # KDJ
    kdj_k: Optional[Decimal] = None
    kdj_d: Optional[Decimal] = None
    kdj_j: Optional[Decimal] = None

    # MA (冗余存储, 也可前端计算)
    ma5: Optional[Decimal] = None
    ma10: Optional[Decimal] = None
    ma20: Optional[Decimal] = None

    data_source: str = ""
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
```

### 2.8 MinuteQuote (新增 - 仅Redis缓存, 不持久化)

```python
@dataclass
class MinuteQuote:
    """分时数据, 仅Redis缓存, 不入MySQL"""
    stock_code: str
    trade_time: datetime     # 精确到分钟
    price: Decimal
    volume: Decimal
    avg_price: Optional[Decimal] = None
    # 缓存TTL: 15分钟(交易时段) / 收盘后清空
```

---

## 3. Database Schema (Alembic Migration)

### Migration: add_market_data_module2_tables

```python
"""add market data module 2 tables

Revision ID: xxxxxxxx
Revises: a1b2c3d4e5f6
Create Date: 2026-04-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DECIMAL


def upgrade():
    # --- 扩展 t_stock ---
    op.add_column('t_stock', sa.Column('industry_code', sa.String(10), nullable=True))
    op.add_column('t_stock', sa.Column('industry_name', sa.String(50), nullable=True))
    op.add_column('t_stock', sa.Column('total_market_cap', DECIMAL(18, 2), nullable=True))
    op.add_column('t_stock', sa.Column('float_market_cap', DECIMAL(18, 2), nullable=True))
    op.create_index('idx_industry_code', 't_stock', ['industry_code'])

    # --- 创建 t_industry_stock ---
    op.create_table(
        't_industry_stock',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('industry_code', sa.String(10), nullable=False),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('create_time', sa.DateTime, nullable=False),
        sa.Column('update_time', sa.DateTime, nullable=False),
        sa.UniqueConstraint('industry_code', 'stock_code', name='uk_industry_stock'),
        sa.Index('idx_industry_code', 'industry_code'),
        sa.Index('idx_stock_code', 'stock_code'),
    )

    # --- 创建 t_watchlist_group ---
    op.create_table(
        't_watchlist_group',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(64), nullable=False),
        sa.Column('name', sa.String(10), nullable=False),
        sa.Column('display_order', sa.Integer, nullable=False, default=0),
        sa.Column('is_default', sa.Boolean, nullable=False, default=False),
        sa.Column('create_time', sa.DateTime, nullable=False),
        sa.Column('update_time', sa.DateTime, nullable=False),
        sa.Index('idx_user_id', 'user_id'),
    )

    # --- 创建 t_watchlist_item ---
    op.create_table(
        't_watchlist_item',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('group_id', sa.Integer, nullable=False),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('stock_name', sa.String(50), nullable=False),
        sa.Column('add_time', sa.DateTime, nullable=False),
        sa.Column('create_time', sa.DateTime, nullable=False),
        sa.UniqueConstraint('group_id', 'stock_code', name='uk_group_stock'),
        sa.Index('idx_group_id', 'group_id'),
        sa.Index('idx_stock_code', 'stock_code'),
    )

    # --- 创建 t_article_stock_relation ---
    op.create_table(
        't_article_stock_relation',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('article_id', sa.Integer, nullable=False),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('stock_name', sa.String(50), nullable=False),
        sa.Column('create_time', sa.DateTime, nullable=False),
        sa.UniqueConstraint('article_id', 'stock_code', name='uk_article_stock'),
        sa.Index('idx_article_id', 'article_id'),
        sa.Index('idx_stock_code', 'stock_code'),
    )

    # --- 创建 t_stock_indicator ---
    op.create_table(
        't_stock_indicator',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('trade_date', sa.Date, nullable=False),
        sa.Column('period', sa.String(10), nullable=False, default='daily'),
        sa.Column('macd_dif', DECIMAL(12, 4), nullable=True),
        sa.Column('macd_dea', DECIMAL(12, 4), nullable=True),
        sa.Column('macd_bar', DECIMAL(12, 4), nullable=True),
        sa.Column('kdj_k', DECIMAL(8, 4), nullable=True),
        sa.Column('kdj_d', DECIMAL(8, 4), nullable=True),
        sa.Column('kdj_j', DECIMAL(8, 4), nullable=True),
        sa.Column('ma5', DECIMAL(12, 3), nullable=True),
        sa.Column('ma10', DECIMAL(12, 3), nullable=True),
        sa.Column('ma20', DECIMAL(12, 3), nullable=True),
        sa.Column('data_source', sa.String(20), nullable=False),
        sa.Column('create_time', sa.DateTime, nullable=False),
        sa.Column('update_time', sa.DateTime, nullable=False),
        sa.UniqueConstraint('stock_code', 'trade_date', 'period', name='uk_stock_indicator'),
        sa.Index('idx_stock_date', 'stock_code', 'trade_date'),
    )

    # --- 扩展 t_market_quote (添加PE/PB) ---
    op.add_column('t_market_quote', sa.Column('pe_ttm', DECIMAL(10, 2), nullable=True))
    op.add_column('t_market_quote', sa.Column('pb', DECIMAL(10, 2), nullable=True))


def downgrade():
    op.drop_column('t_market_quote', 'pb')
    op.drop_column('t_market_quote', 'pe_ttm')
    op.drop_table('t_stock_indicator')
    op.drop_table('t_article_stock_relation')
    op.drop_table('t_watchlist_item')
    op.drop_table('t_watchlist_group')
    op.drop_table('t_industry_stock')
    op.drop_index('idx_industry_code', 't_stock')
    op.drop_column('t_stock', 'float_market_cap')
    op.drop_column('t_stock', 'total_market_cap')
    op.drop_column('t_stock', 'industry_name')
    op.drop_column('t_stock', 'industry_code')
```

---

## 4. Repository Interface Design

### 4.1 WatchlistRepository (Domain)

```python
class WatchlistRepository(ABC):
    @abstractmethod
    async def get_groups(self, user_id: str) -> List[WatchlistGroup]: ...

    @abstractmethod
    async def create_group(self, group: WatchlistGroup) -> WatchlistGroup: ...

    @abstractmethod
    async def update_group(self, group: WatchlistGroup) -> WatchlistGroup: ...

    @abstractmethod
    async def delete_group(self, group_id: int) -> None: ...

    @abstractmethod
    async def get_items(self, group_id: int) -> List[WatchlistItem]: ...

    @abstractmethod
    async def add_item(self, item: WatchlistItem) -> WatchlistItem: ...

    @abstractmethod
    async def remove_item(self, group_id: int, stock_code: str) -> None: ...

    @abstractmethod
    async def get_user_watchlists(self, user_id: str) -> Dict[str, List[Dict]]: ...
```

### 4.2 IndustryRepository (Domain) - 扩展已有

```python
class IndustryRepository(ABC):
    # 已有: get_all, get_by_code 等

    # 新增:
    @abstractmethod
    async def get_stocks_by_industry(self, industry_code: str) -> List[StockBasicInfo]: ...

    @abstractmethod
    async def get_industry_overview(self, industry_code: str) -> Dict: ...
```

### 4.3 ArticleStockRelationRepository (Domain)

```python
class ArticleStockRelationRepository(ABC):
    @abstractmethod
    async def create(self, relation: ArticleStockRelation) -> ArticleStockRelation: ...

    @abstractmethod
    async def get_by_stock(self, stock_code: str, limit: int = 50) -> List[ArticleStockRelation]: ...

    @abstractmethod
    async def get_by_article(self, article_id: int) -> List[ArticleStockRelation]: ...

    @abstractmethod
    async def delete_by_article(self, article_id: int) -> None: ...
```

### 4.4 StockIndicatorRepository (Domain)

```python
class StockIndicatorRepository(ABC):
    @abstractmethod
    async def get_indicators(self, stock_code: str, period: str,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> List[StockIndicator]: ...

    @abstractmethod
    async def upsert_batch(self, indicators: List[StockIndicator]) -> None: ...
```

---

## 5. Validation Rules

### 5.1 WatchlistGroup
- `name`: 必填, 1-10个字符
- 每用户最多10个分组（含默认3个）
- 默认分组（is_default=true）不允许删除
- `display_order`: >= 0

### 5.2 WatchlistItem
- `group_id` + `stock_code`: 唯一
- 每组最多100只股票
- `stock_code`: 必须是有效的A股代码（6位数字）

### 5.3 ArticleStockRelation
- `article_id` + `stock_code`: 唯一
- `stock_code`: 6位数字
- 保存文章时从正文自动提取

### 5.4 StockIndicator
- `stock_code` + `trade_date` + `period`: 唯一
- `period`: 只能是 daily/weekly/monthly
- 计算结果须与主流平台（同花顺）误差 < 0.1%

---

## 6. State Transitions

### 6.1 同步任务状态机 (已有, 扩展)

```
PENDING -> RUNNING -> COMPLETED
                  -> FAILED
```

新增数据同步类型: `market_quote`, `daily_quote`, `financial`, `industry_mapping`

### 6.2 自选股分组生命周期

```
创建: 用户主动创建 / 系统默认初始化
修改: 重命名 / 调整排序
删除: 仅自定义分组可删除; 删除时组内股票移入"观察股"
```
