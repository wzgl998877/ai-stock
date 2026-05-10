"""搜索引擎抽象基类 — Key 轮询 + 错误计数 + 模板方法"""

import asyncio
import itertools
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.domain.value_objects.search_result import SearchResponse

logger = logging.getLogger(__name__)


class BaseSearchProvider(ABC):
    """搜索引擎基类。

    - 多 Key 轮询（itertools.cycle）+ 错误跳过
    - 模板方法：search() → _execute_search() → _do_search()
    """

    _ERROR_THRESHOLD = 3  # 单 Key 连续错误上限

    def __init__(self, api_keys: List[str], name: str):
        self._api_keys = api_keys
        self._name = name
        self._key_cycle = itertools.cycle(api_keys) if api_keys else None
        self._key_usage: Dict[str, int] = {k: 0 for k in api_keys}
        self._key_errors: Dict[str, int] = {k: 0 for k in api_keys}
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_available(self) -> bool:
        return bool(self._api_keys)

    # ------------------------------------------------------------------
    # Key 管理
    # ------------------------------------------------------------------

    async def _get_next_key(self) -> Optional[str]:
        async with self._lock:
            if not self._key_cycle:
                return None
            for _ in range(len(self._api_keys)):
                key = next(self._key_cycle)
                if self._key_errors.get(key, 0) < self._ERROR_THRESHOLD:
                    return key
            # 所有 Key 都超限 → 重置错误计数
            logger.warning("[%s] 所有 API Key 错误计数超限，重置", self._name)
            self._key_errors = {k: 0 for k in self._api_keys}
            return self._api_keys[0] if self._api_keys else None

    async def _record_success(self, key: str) -> None:
        async with self._lock:
            self._key_usage[key] = self._key_usage.get(key, 0) + 1
            if key in self._key_errors and self._key_errors[key] > 0:
                self._key_errors[key] -= 1

    async def _record_error(self, key: str) -> None:
        async with self._lock:
            self._key_errors[key] = self._key_errors.get(key, 0) + 1
            err_count = self._key_errors[key]
        logger.warning("[%s] Key %s... 错误计数: %d", self._name, key[:8], err_count)

    # ------------------------------------------------------------------
    # 模板方法
    # ------------------------------------------------------------------

    @abstractmethod
    async def _do_search(
        self,
        query: str,
        max_results: int,
        days: int,
        api_key: str,
        **kwargs: Any,
    ) -> SearchResponse:
        """子类实现具体搜索逻辑。"""

    async def _execute_search(
        self,
        query: str,
        max_results: int,
        days: int,
        **kwargs: Any,
    ) -> SearchResponse:
        """共享流程：取 Key → 计时 → 调用子类 → 记录成功/失败。"""
        api_key = await self._get_next_key()
        if api_key is None:
            return SearchResponse(
                query=query, provider=self._name, success=False,
                error_message="无可用 API Key",
            )
        start = time.monotonic()
        try:
            response = await self._do_search(query, max_results, days, api_key, **kwargs)
            response.search_time = time.monotonic() - start
            await self._record_success(api_key)
            return response
        except Exception as e:
            await self._record_error(api_key)
            logger.error("[%s] 搜索异常: %s", self._name, e, exc_info=True)
            return SearchResponse(
                query=query, provider=self._name, success=False,
                error_message=str(e),
            )

    async def search(
        self,
        query: str,
        max_results: int = 5,
        days: int = 7,
        **kwargs: Any,
    ) -> SearchResponse:
        """公开搜索入口。"""
        if not self.is_available:
            return SearchResponse(
                query=query, provider=self._name, success=False,
                error_message="引擎不可用",
            )
        return await self._execute_search(query, max_results, days, **kwargs)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            parsed = urlparse(url)
            return parsed.netloc or url
        except Exception:
            return url
