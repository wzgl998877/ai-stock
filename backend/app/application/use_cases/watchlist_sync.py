"""WatchlistSyncUseCase — 自选股按分组批量同步编排用例。

职责仅限于「收集选中分组的去重股票代码」（用请求级 session）；
真正的拉取与落库在 ``app.application.sync.watchlist_batch_sync`` 的后台任务里，
用独立 session 完成，避免持有跨请求的 session。
"""

from __future__ import annotations

import logging

from app.domain.repositories.watchlist_repo import WatchlistRepository

logger = logging.getLogger(__name__)


class WatchlistSyncUseCase:
    """自选股批量同步用例：解析选中的自选分组 → 去重股票代码集合。"""

    def __init__(self, watchlist_repo: WatchlistRepository):
        self.watchlist_repo = watchlist_repo

    async def collect_unique_codes(self, user_id: str, group_ids: list[int]) -> list[str]:
        """收集选中分组内的股票代码，跨分组去重。

        不复用 ``get_all_items_by_user``（那是「用户全部分组」并集），
        这里只取用户勾选的分组子集。

        Args:
            user_id: 当前用户 ID（保留参数，便于后续做分组归属校验）。
            group_ids: 用户勾选的分组 ID 列表。

        Returns:
            去重后的股票代码列表（升序）。空 ``stock_code`` 的脏数据会被过滤。
        """
        codes: set[str] = set()
        for gid in group_ids:
            items = await self.watchlist_repo.get_items(gid)
            for it in items:
                if it.stock_code:
                    codes.add(it.stock_code)
        return sorted(codes)
