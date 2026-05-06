"""分时数据客户端及 UseCase 单元测试。

覆盖:
- TencentMinuteClient 解析逻辑（实际格式: "0930 价格 累计成交量 累计成交额"）
- SinaMinuteClient 解析逻辑（实际格式: JSONP 包裹 var data([...])）
- TwelveDataMinuteClient 解析逻辑 + API Key 未配置场景
- MinuteClient 多源 fallback + 缓存逻辑
- MinuteDataUseCase dict -> MinuteQuote 转换
"""

import json
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.market.tencent_client import TencentMinuteClient, _prefix_code
from app.infrastructure.market.sina_client import SinaMinuteClient
from app.infrastructure.market.twelvedata_client import TwelveDataMinuteClient
from app.infrastructure.market.minute_client import MinuteClient
from app.application.use_cases.minute_data import MinuteDataUseCase


# ---------------------------------------------------------------------------
# Helpers: 构造 mock httpx 响应
# ---------------------------------------------------------------------------

def _mock_response(text: str, status_code: int = 200):
    """构造一个 mock httpx.Response。"""
    resp = MagicMock()
    resp.text = text
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


# ===========================================================================
# Test: TencentMinuteClient
# ===========================================================================

class TestTencentMinuteClient:
    """腾讯分时客户端解析测试。"""

    @pytest.mark.anyio
    async def test_minute_data_parsing(self):
        """分时接口正常解析（实际格式: 4字段累计值）。"""
        # 模拟真实数据: "时间 价格 累计成交量(手) 累计成交额(元)"
        # 第一条: 100手成交, 均价=16850000/(100*100)=1685.00
        # 第二条: 累计300手, 均价=50647500/(300*100)=1688.25
        payload = {
            "code": 0,
            "msg": "",
            "data": {
                "sh600519": {
                    "data": {
                        "data": [
                            "0930 1685.00 100 16850000.00",
                            "0931 1686.50 300 50647500.00",
                        ]
                    }
                }
            }
        }
        mock_resp = _mock_response(f"min_data={json.dumps(payload)}")

        client = TencentMinuteClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("600519")

        assert len(result) == 2
        assert result[0]["time"] == "09:30"
        assert result[0]["price"] == 1685.00
        # 增量: 第一条 100, 第二条 300-100=200
        assert result[0]["volume"] == 100.0
        # 均价 = 16850000 / (100 * 100) = 1685.00
        assert result[0]["avg_price"] == 1685.00
        assert result[1]["time"] == "09:31"
        assert result[1]["price"] == 1686.50
        assert result[1]["volume"] == 200.0
        # 均价 = 50647500 / (300 * 100) = 1688.25
        assert result[1]["avg_price"] == 1688.25

    @pytest.mark.anyio
    async def test_error_code_returns_empty(self):
        """腾讯返回错误码时返回空列表。"""
        payload = {"code": 1, "msg": "bad params", "data": {}}
        mock_resp = _mock_response(f"min_data={json.dumps(payload)}")

        client = TencentMinuteClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("600519")

        assert result == []

    @pytest.mark.anyio
    async def test_empty_response_returns_empty_list(self):
        """空响应返回空列表。"""
        mock_resp = _mock_response("min_data=;")

        client = TencentMinuteClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("600519")

        assert result == []


# ===========================================================================
# Test: SinaMinuteClient
# ===========================================================================

class TestSinaMinuteClient:
    """新浪分时客户端解析测试。"""

    @pytest.mark.anyio
    async def test_kline_data_parsing(self):
        """新浪5分钟K线正常解析（实际 JSONP 格式）。"""
        items = [
            {
                "day": "2026-05-06 09:35:00",
                "open": "90.780", "high": "92.780", "low": "90.100",
                "close": "90.530", "volume": "23696832", "amount": "2154781893.36",
            },
            {
                "day": "2026-05-06 09:40:00",
                "open": "90.530", "high": "91.520", "low": "90.500",
                "close": "91.510", "volume": "5172492", "amount": "470324297.35",
            },
        ]
        body = f"/*<script>location.href='//sina.com';</script>*/\nvar data({json.dumps(items)});"
        mock_resp = _mock_response(body)

        client = SinaMinuteClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858")

        assert len(result) == 2
        assert result[0]["time"] == "09:35"
        assert result[0]["price"] == 90.53
        assert result[1]["time"] == "09:40"
        assert result[1]["volume"] == 5172492.0

    @pytest.mark.anyio
    async def test_empty_jsonp_returns_empty(self):
        """JSONP 包含错误时返回空列表。"""
        body = "/*<script>location.href='//sina.com';</script>*/\nvar data({\"__ERROR\":3});"
        mock_resp = _mock_response(body)

        client = SinaMinuteClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858")

        assert result == []


# ===========================================================================
# Test: TwelveDataMinuteClient
# ===========================================================================

class TestTwelveDataMinuteClient:
    """TwelveData 客户端解析测试。"""

    @pytest.mark.anyio
    async def test_returns_empty_when_no_api_key(self):
        """API Key 未配置时返回空列表。"""
        with patch("app.infrastructure.market.twelvedata_client.settings") as mock_settings:
            mock_settings.twelvedata_api_key = ""
            client = TwelveDataMinuteClient()
            result = await client.fetch("600519")
            assert result == []

    @pytest.mark.anyio
    async def test_normal_data_parsing(self):
        """TwelveData 正常解析。"""
        payload = {
            "values": [
                {"datetime": "2025-05-06 14:30:00", "close": "1685.50", "volume": "12345"},
                {"datetime": "2025-05-06 14:25:00", "close": "1684.00", "volume": "10000"},
            ]
        }
        mock_resp = _mock_response(json.dumps(payload))
        mock_resp.json.return_value = payload

        with patch("app.infrastructure.market.twelvedata_client.settings") as mock_settings:
            mock_settings.twelvedata_api_key = "test_key"
            client = TwelveDataMinuteClient()

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_resp
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                result = await client.fetch("600519")

        # reversed 后应按时间正序
        assert len(result) == 2
        assert result[0]["time"] == "14:25"
        assert result[0]["price"] == 1684.00
        assert result[1]["time"] == "14:30"

    @pytest.mark.anyio
    async def test_handles_error_response(self):
        """TwelveData 返回错误时返回空列表。"""
        payload = {"status": "error", "message": "Invalid API Key"}
        mock_resp = _mock_response(json.dumps(payload))
        mock_resp.json.return_value = payload

        with patch("app.infrastructure.market.twelvedata_client.settings") as mock_settings:
            mock_settings.twelvedata_api_key = "bad_key"
            client = TwelveDataMinuteClient()

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_resp
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                result = await client.fetch("600519")

        assert result == []


# ===========================================================================
# Test: MinuteClient (多源聚合 + 缓存)
# ===========================================================================

class TestMinuteClient:
    """分时数据多源聚合客户端测试。"""

    @pytest.mark.anyio
    async def test_returns_cached_data(self):
        """缓存命中时直接返回缓存数据。"""
        cached_data = [{"time": "09:30", "price": 100.0, "volume": 500, "avg_price": 100.0}]
        mock_redis = MagicMock()
        mock_redis.get.return_value = cached_data

        with patch("app.infrastructure.market.minute_client.redis_cache", mock_redis):
            client = MinuteClient()
            result = await client.get_minute_data("600519")

        assert result == cached_data
        mock_redis.get.assert_called_once_with("stock:minute:600519")

    @pytest.mark.anyio
    async def test_fallback_to_second_source(self):
        """第一数据源失败时 fallback 到第二数据源。"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # 缓存未命中

        tencent_data = []  # 腾讯返回空
        sina_data = [{"time": "09:30", "price": 100.0, "volume": 500, "avg_price": 100.0}]

        mock_tencent = AsyncMock()
        mock_tencent.fetch.return_value = tencent_data
        mock_sina = AsyncMock()
        mock_sina.fetch.return_value = sina_data
        mock_twelvedata = AsyncMock()

        with patch("app.infrastructure.market.minute_client.redis_cache", mock_redis):
            client = MinuteClient()
            client._tencent = mock_tencent
            client._sina = mock_sina
            client._twelvedata = mock_twelvedata

            result = await client.get_minute_data("000858")

        assert result == sina_data
        mock_sina.fetch.assert_awaited_once_with("000858")
        mock_twelvedata.fetch.assert_not_awaited()
        # 成功数据应写入缓存
        mock_redis.set.assert_called_once()

    @pytest.mark.anyio
    async def test_all_sources_fail_returns_empty(self):
        """所有数据源失败时返回空列表。"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        mock_tencent = AsyncMock()
        mock_tencent.fetch.side_effect = Exception("网络超时")
        mock_sina = AsyncMock()
        mock_sina.fetch.side_effect = Exception("连接拒绝")
        mock_twelvedata = AsyncMock()
        mock_twelvedata.fetch.return_value = []

        with patch("app.infrastructure.market.minute_client.redis_cache", mock_redis):
            client = MinuteClient()
            client._tencent = mock_tencent
            client._sina = mock_sina
            client._twelvedata = mock_twelvedata

            result = await client.get_minute_data("600519")

        assert result == []
        # 空数据不缓存
        mock_redis.set.assert_not_called()


# ===========================================================================
# Test: MinuteDataUseCase
# ===========================================================================

class TestMinuteDataUseCase:
    """分时数据 UseCase 测试。"""

    @pytest.mark.anyio
    async def test_converts_raw_dict_to_minute_quote(self):
        """正确将原始 dict 转换为 MinuteQuote 实体。"""
        raw_data = [
            {"time": "09:30", "price": 1685.5, "volume": 12345.0, "avg_price": 1684.2},
            {"time": "09:31", "price": 1686.0, "volume": 10000.0, "avg_price": 1685.0},
        ]

        mock_client = AsyncMock()
        mock_client.get_minute_data.return_value = raw_data

        with patch("app.application.use_cases.minute_data.MinuteClient", return_value=mock_client):
            uc = MinuteDataUseCase()
            quotes = await uc.get_minute_data("000858")

        assert len(quotes) == 2
        assert quotes[0].stock_code == "000858"
        assert quotes[0].time == "09:30"
        assert quotes[0].price == Decimal("1685.5")
        assert quotes[0].volume == Decimal("12345.0")
        assert quotes[0].avg_price == Decimal("1684.2")

    @pytest.mark.anyio
    async def test_returns_empty_when_no_data(self):
        """无数据时返回空列表。"""
        mock_client = AsyncMock()
        mock_client.get_minute_data.return_value = []

        with patch("app.application.use_cases.minute_data.MinuteClient", return_value=mock_client):
            uc = MinuteDataUseCase()
            quotes = await uc.get_minute_data("600519")

        assert quotes == []


# ===========================================================================
# Test: 辅助函数
# ===========================================================================

class TestHelperFunctions:
    """辅助函数测试。"""

    def test_prefix_code_shanghai(self):
        """上海代码加 sh 前缀。"""
        assert _prefix_code("600519") == "sh600519"

    def test_prefix_code_shenzhen(self):
        """深圳代码加 sz 前缀。"""
        assert _prefix_code("000858") == "sz000858"

    def test_prefix_code_already_prefixed(self):
        """已有前缀不重复添加。"""
        assert _prefix_code("sh600519") == "sh600519"
        assert _prefix_code("sz000858") == "sz000858"

    def test_prefix_code_3_start(self):
        """3 开头的代码加 sz 前缀。"""
        assert _prefix_code("300001") == "sz300001"
