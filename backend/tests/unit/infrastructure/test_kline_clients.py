"""K线数据客户端单元测试。

覆盖:
- TencentKlineClient 解析逻辑（周K/月K/日K）
- SinaKlineClient 解析逻辑（JSONP 包裹）
- DailyKlineClient 多源 fallback 逻辑
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.market.tencent_kline_client import TencentKlineClient
from app.infrastructure.market.sina_kline_client import SinaKlineClient
from app.infrastructure.market.daily_kline_client import DailyKlineClient


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
# Test: TencentKlineClient
# ===========================================================================

class TestTencentKlineClient:
    """腾讯K线客户端解析测试。"""

    @pytest.mark.anyio
    async def test_weekly_kline_parsing(self):
        """周K数据正常解析。"""
        # 模拟真实数据: 腾讯返回 kline_weekqfq=... 前缀
        # 字段顺序: [date, open, close, low, high, volume]
        payload = {
            "code": 0,
            "msg": "",
            "data": {
                "sz000858": {
                    "qfqweek": [
                        ["2026-04-27", "148.50", "151.20", "147.80", "152.00", "12345678"],
                        ["2026-04-20", "145.00", "149.00", "144.50", "150.00", "9876543"],
                    ]
                }
            }
        }
        mock_resp = _mock_response(f"kline_weekqfq={json.dumps(payload)}")

        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "weekly")

        assert len(result) == 2
        assert result[0]["trade_date"] == "2026-04-27"
        assert result[0]["open"] == 148.50
        assert result[0]["close"] == 151.20
        assert result[0]["low"] == 147.80
        assert result[0]["high"] == 152.00
        assert result[0]["volume"] == 12345678.0
        assert result[0]["amount"] is None  # 腾讯不返回成交额

    @pytest.mark.anyio
    async def test_monthly_kline_parsing(self):
        """月K数据正常解析。"""
        payload = {
            "code": 0,
            "msg": "",
            "data": {
                "sz000858": {
                    "qfqmonth": [
                        ["2026-04-01", "140.00", "152.00", "138.00", "155.00", "45678901"],
                    ]
                }
            }
        }
        mock_resp = _mock_response(f"kline_monthqfq={json.dumps(payload)}")

        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "monthly")

        assert len(result) == 1
        assert result[0]["trade_date"] == "2026-04-01"
        assert result[0]["open"] == 140.00

    @pytest.mark.anyio
    async def test_daily_kline_parsing(self):
        """日K数据正常解析（使用 qfqday 字段）。"""
        payload = {
            "code": 0,
            "msg": "",
            "data": {
                "sh600519": {
                    "qfqday": [
                        ["2026-05-06", "1680.00", "1685.50", "1678.00", "1690.00", "54321"],
                    ]
                }
            }
        }
        mock_resp = _mock_response(f"kline_dayqfq={json.dumps(payload)}")

        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("600519", "daily")

        assert len(result) == 1
        assert result[0]["trade_date"] == "2026-05-06"

    @pytest.mark.anyio
    async def test_m30_kline_parsing(self):
        """m30 分钟线解析（mkline 接口；时间戳 202608251500 → 区间结束时刻）。"""
        payload = {
            "code": 0,
            "msg": "",
            "data": {
                "sz002940": {
                    "m30": [
                        ["202608251430", "25.54", "25.75", "25.90", "25.54", "10754.00"],
                        ["202608251500", "25.75", "25.82", "25.88", "25.75", "10574.00"],
                    ]
                }
            }
        }
        mock_resp = _mock_response(json.dumps(payload))

        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("002940", "m30")

        assert len(result) == 2
        first = result[0]
        assert first["trade_date"] == "2026-08-25 14:30:00"  # 与新浪 m30 口径一致
        assert first["open"] == 25.54 and first["close"] == 25.75
        assert first["high"] == 25.90 and first["low"] == 25.54  # 注意 close 在 high 前
        assert result[1]["trade_date"] == "2026-08-25 15:00:00"

    @pytest.mark.anyio
    async def test_m30_empty_returns_empty(self):
        """m30 无数据返回空列表（降级方判定"真无数据"的依据）。"""
        payload = {"code": 0, "msg": "", "data": {"sz002940": {}}}
        mock_resp = _mock_response(json.dumps(payload))

        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("002940", "m30")

        assert result == []

    @pytest.mark.anyio
    async def test_empty_response_returns_empty(self):
        """空数据返回空列表。"""
        payload = {"code": 0, "msg": "", "data": {"sz000858": {}}}
        mock_resp = _mock_response(f"kline_weekqfq={json.dumps(payload)}")

        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "weekly")

        assert result == []

    @pytest.mark.anyio
    async def test_network_error_returns_empty(self):
        """网络异常返回空列表。"""
        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("连接超时")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "weekly")

        assert result == []

    @pytest.mark.anyio
    async def test_daily_url_param_six_segments(self):
        """日K URL param 必须是六段（code,type,start,end,count,fq）。

        五段格式（start/end 只留一个空位）被腾讯接口判 "param error"——
        2026-08-27 日线降级全量失败事故根因。
        """
        payload = {
            "code": 0, "msg": "",
            "data": {"sz000858": {"qfqday": [
                ["2026-08-26", "73.00", "74.00", "74.20", "72.80", "12345.00"],
            ]}},
        }
        mock_resp = _mock_response(f"kline_dayqfq={json.dumps(payload)}")

        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await client.fetch("000858", "daily", count=20)

            url = mock_client.get.call_args.args[0]
            assert "param=sz000858,day,,,20,qfq" in url

    @pytest.mark.anyio
    async def test_param_error_data_list_returns_empty(self):
        """腾讯返回 "param error"（data 为列表）时返回空，不抛 'list' has no 'get'。"""
        mock_resp = _mock_response('kline_dayqfq={"code":0,"msg":"param error","data":[]}')

        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "daily", count=20)

        assert result == []

    @pytest.mark.anyio
    async def test_m30_param_error_data_list_returns_empty(self):
        """m30 错误响应（data 为列表）同样防御，返回空。"""
        mock_resp = _mock_response('{"code":0,"msg":"param error","data":[]}')

        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "m30", count=20)

        assert result == []

    @pytest.mark.anyio
    async def test_malformed_row_skipped(self):
        """字段不足的行被跳过。"""
        payload = {
            "code": 0,
            "msg": "",
            "data": {
                "sz000858": {
                    "qfqweek": [
                        ["2026-04-27", "148.50"],  # 字段不足
                        ["2026-04-20", "145.00", "149.00", "144.50", "150.00", "9876543"],
                    ]
                }
            }
        }
        mock_resp = _mock_response(f"kline_weekqfq={json.dumps(payload)}")

        client = TencentKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "weekly")

        assert len(result) == 1
        assert result[0]["trade_date"] == "2026-04-20"


# ===========================================================================
# Test: SinaKlineClient
# ===========================================================================

class TestSinaKlineClient:
    """新浪K线客户端解析测试。"""

    @pytest.mark.anyio
    async def test_weekly_kline_parsing(self):
        """周K数据正常解析（JSONP 格式）。"""
        items = [
            {
                "day": "2026-04-27 00:00:00",
                "open": "148.50", "high": "152.00", "low": "147.80",
                "close": "151.20", "volume": "12345678", "amount": "1850000000.50",
            },
            {
                "day": "2026-04-20 00:00:00",
                "open": "145.00", "high": "150.00", "low": "144.50",
                "close": "149.00", "volume": "9876543", "amount": "1460000000.00",
            },
        ]
        body = f"/*<script>location.href='//sina.com';</script>*/\nvar data({json.dumps(items)});"
        mock_resp = _mock_response(body)

        client = SinaKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "weekly")

        assert len(result) == 2
        assert result[0]["trade_date"] == "2026-04-27"
        assert result[0]["open"] == 148.50
        assert result[0]["high"] == 152.00
        assert result[0]["low"] == 147.80
        assert result[0]["close"] == 151.20
        assert result[0]["volume"] == 12345678.0
        assert result[0]["amount"] == 1850000000.50

    @pytest.mark.anyio
    async def test_monthly_kline_parsing(self):
        """月K数据正常解析。"""
        items = [
            {
                "day": "2026-04-01 00:00:00",
                "open": "140.00", "high": "155.00", "low": "138.00",
                "close": "152.00", "volume": "45678901", "amount": "6800000000.00",
            },
        ]
        body = f"var data({json.dumps(items)});"
        mock_resp = _mock_response(body)

        client = SinaKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "monthly")

        assert len(result) == 1
        assert result[0]["trade_date"] == "2026-04-01"
        assert result[0]["amount"] == 6800000000.00

    @pytest.mark.anyio
    async def test_empty_jsonp_returns_empty(self):
        """JSONP 包含非列表数据时返回空。"""
        body = "var data({\"error\": 1});"
        mock_resp = _mock_response(body)

        client = SinaKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "weekly")

        assert result == []

    @pytest.mark.anyio
    async def test_network_error_returns_empty(self):
        """网络异常返回空列表。"""
        client = SinaKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("连接超时")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "monthly")

        assert result == []

    @pytest.mark.anyio
    async def test_date_only_format(self):
        """日期只有日期部分（无时间）时也能正常解析。"""
        items = [
            {
                "day": "2026-04-27",
                "open": "148.50", "high": "152.00", "low": "147.80",
                "close": "151.20", "volume": "12345678", "amount": "1850000000.00",
            },
        ]
        body = f"var data({json.dumps(items)});"
        mock_resp = _mock_response(body)

        client = SinaKlineClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await client.fetch("000858", "weekly")

        assert len(result) == 1
        assert result[0]["trade_date"] == "2026-04-27"


# ===========================================================================
# Test: DailyKlineClient (多源聚合)
# ===========================================================================

class TestDailyKlineClient:
    """K线多源聚合客户端测试。"""

    @pytest.mark.anyio
    async def test_tencent_first_success(self):
        """腾讯成功时直接返回。"""
        tencent_data = [
            {"trade_date": "2026-04-27", "open": 148.5, "close": 151.2,
             "low": 147.8, "high": 152.0, "volume": 12345.0, "amount": None},
        ]

        mock_tencent = AsyncMock()
        mock_tencent.fetch.return_value = tencent_data
        mock_sina = AsyncMock()

        client = DailyKlineClient()
        client._tencent = mock_tencent
        client._sina = mock_sina

        result = await client.fetch("000858", "weekly")

        assert result == tencent_data
        mock_tencent.fetch.assert_awaited_once_with("000858", "weekly")
        mock_sina.fetch.assert_not_awaited()

    @pytest.mark.anyio
    async def test_fallback_to_sina_when_tencent_empty(self):
        """腾讯返回空时 fallback 到新浪。"""
        sina_data = [
            {"trade_date": "2026-04-27", "open": 148.5, "close": 151.2,
             "low": 147.8, "high": 152.0, "volume": 12345.0, "amount": 1850000.0},
        ]

        mock_tencent = AsyncMock()
        mock_tencent.fetch.return_value = []
        mock_sina = AsyncMock()
        mock_sina.fetch.return_value = sina_data

        client = DailyKlineClient()
        client._tencent = mock_tencent
        client._sina = mock_sina

        result = await client.fetch("000858", "monthly")

        assert result == sina_data
        mock_sina.fetch.assert_awaited_once_with("000858", "monthly")

    @pytest.mark.anyio
    async def test_fallback_to_sina_when_tencent_fails(self):
        """腾讯异常时 fallback 到新浪。"""
        sina_data = [
            {"trade_date": "2026-04-27", "open": 148.5, "close": 151.2,
             "low": 147.8, "high": 152.0, "volume": 12345.0, "amount": 1850000.0},
        ]

        mock_tencent = AsyncMock()
        mock_tencent.fetch.side_effect = Exception("超时")
        mock_sina = AsyncMock()
        mock_sina.fetch.return_value = sina_data

        client = DailyKlineClient()
        client._tencent = mock_tencent
        client._sina = mock_sina

        result = await client.fetch("000858", "weekly")

        assert result == sina_data

    @pytest.mark.anyio
    async def test_all_sources_fail_returns_empty(self):
        """所有数据源失败时返回空列表。"""
        mock_tencent = AsyncMock()
        mock_tencent.fetch.side_effect = Exception("超时")
        mock_sina = AsyncMock()
        mock_sina.fetch.return_value = []

        client = DailyKlineClient()
        client._tencent = mock_tencent
        client._sina = mock_sina

        result = await client.fetch("000858", "weekly")

        assert result == []
