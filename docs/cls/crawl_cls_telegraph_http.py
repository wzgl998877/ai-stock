#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社电报抓取（纯 HTTP，无需 Playwright / 浏览器）

通过财联社 Web 端签名规则请求 /v1/roll/get_roll_list 接口：
  sign = MD5( SHA1(按 key 排序序列化后的参数字符串) )

依赖:
    pip install httpx   # 或仅用标准库 urllib（默认）

用法:
    python scripts/crawl_cls_telegraph_http.py
    python scripts/crawl_cls_telegraph_http.py -o output/cls_telegraph.json
    python scripts/crawl_cls_telegraph_http.py --max-items 50
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import httpx

    _USE_HTTPX = True
except ImportError:
    import urllib.error
    import urllib.parse
    import urllib.request

    _USE_HTTPX = False

API_ROLL_LIST = "https://www.cls.cn/v1/roll/get_roll_list"
TELEGRAPH_URL = "https://www.cls.cn/telegraph"
MAX_RN_PER_REQUEST = 50  # 接口实测 rn>50 返回空列表
DEFAULT_APP = "CailianpressWeb"
DEFAULT_OS = "web"
DEFAULT_SV = "8.7.9"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class TelegraphItem:
    id: int
    title: str
    content: str
    brief: str
    published_at: str
    ctime: int
    level: str
    reading_num: int
    url: str
    source: str = "cls"

    @classmethod
    def from_roll(cls, raw: dict[str, Any]) -> TelegraphItem:
        ctime = int(raw.get("ctime") or 0)
        dt = datetime.fromtimestamp(ctime) if ctime else None
        published = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""
        item_id = int(raw.get("id") or 0)
        title = (raw.get("title") or "").strip()
        brief = (raw.get("brief") or raw.get("content") or "").strip()
        content = (raw.get("content") or brief).strip()
        detail_url = f"https://www.cls.cn/detail/{item_id}" if item_id else TELEGRAPH_URL
        return cls(
            id=item_id,
            title=title or brief[:80],
            content=content,
            brief=brief,
            published_at=published,
            ctime=ctime,
            level=str(raw.get("level") or ""),
            reading_num=int(raw.get("reading_num") or 0),
            url=detail_url,
        )


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _serialize_param(key: str, value: Any) -> str | None:
    """与财联社前端 sign 模块一致的参数序列化。"""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return f"{key}={_stringify(value)}"
    if isinstance(value, list):
        if not value:
            return f"{key}[]"
        parts = [_serialize_param(f"{key}[{i}]", item) for i, item in enumerate(value)]
        return "&".join(p for p in parts if p)
    if isinstance(value, dict):
        parts = []
        for k in sorted(value.keys()):
            part = _serialize_param(f"{key}[{k}]", value[k])
            if part:
                parts.append(part)
        return "&".join(parts)
    return f"{key}={_stringify(value)}"


def build_query_string(params: dict[str, Any]) -> str:
    parts = []
    for key in sorted(params.keys()):
        part = _serialize_param(key, params[key])
        if part:
            parts.append(part)
    return "&".join(parts)


def compute_sign(params: dict[str, Any]) -> str:
    """
    财联社 sign 算法（自 wwwjs.cls.cn _app bundle 逆向）:
    query_string = serialize(sorted params without sign)
    sign = MD5( SHA1(query_string).hexdigest() )
    """
    qs = build_query_string(params)
    sha1_hex = hashlib.sha1(qs.encode("utf-8")).hexdigest()
    return hashlib.md5(sha1_hex.encode("utf-8")).hexdigest()


def _parse_response(body: dict[str, Any]) -> list[dict[str, Any]]:
    errno = body.get("errno")
    if errno not in (0, "0", None):
        msg = body.get("msg") or body.get("message") or "unknown"
        raise RuntimeError(f"API 错误 errno={errno} msg={msg}")
    roll = (body.get("data") or {}).get("roll_data")
    if roll is None:
        return []
    if not isinstance(roll, list):
        raise RuntimeError("roll_data 格式异常")
    return roll


def _request_roll_list(params: dict[str, Any], timeout: float = 15.0) -> dict[str, Any]:
    """请求 /v1/roll/get_roll_list（电报列表官方接口）。"""
    payload = dict(params)
    payload.setdefault("app", DEFAULT_APP)
    payload.setdefault("os", DEFAULT_OS)
    payload.setdefault("sv", DEFAULT_SV)
    payload.setdefault("category", "telegraph")
    payload["sign"] = compute_sign(payload)

    headers = {
        "User-Agent": DEFAULT_UA,
        "Referer": TELEGRAPH_URL,
        "Accept": "application/json",
    }

    if _USE_HTTPX:
        with httpx.Client(timeout=timeout, headers=headers) as client:
            resp = client.get(API_ROLL_LIST, params=payload)
            resp.raise_for_status()
            return resp.json()

    qs = urllib.parse.urlencode(payload)
    url = f"{API_ROLL_LIST}?{qs}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}") from e


def fetch_telegraph(max_items: int = 20) -> list[TelegraphItem]:
    """
    拉取财联社电报（/v1/roll/get_roll_list）。

    - 首次: refresh_type=1, last_time=当前时间戳, rn<=50
    - 翻页: last_time=本批最后一条的 ctime（与官网下拉逻辑一致）
    """
    import time

    merged: dict[int, dict[str, Any]] = {}
    last_time = int(time.time())

    while len(merged) < max_items:
        need = max_items - len(merged)
        rn = min(need, MAX_RN_PER_REQUEST)

        body = _request_roll_list(
            {
                "refresh_type": 1,
                "rn": rn,
                "last_time": last_time,
            }
        )
        batch = _parse_response(body)
        if not batch:
            break

        added = 0
        for raw in batch:
            rid = int(raw.get("id") or 0)
            if rid and rid not in merged:
                merged[rid] = raw
                added += 1

        if added == 0:
            break

        # 下一页：取本批最后一条的时间戳（官网 Q.current = roll_data[last].ctime）
        last_time = int(batch[-1].get("ctime") or last_time)

    items = [TelegraphItem.from_roll(r) for r in merged.values()]
    items.sort(key=lambda x: x.ctime, reverse=True)
    return items[:max_items]


def save_json(items: list[TelegraphItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "cls",
        "method": "http",
        "url": TELEGRAPH_URL,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(items),
        "items": [asdict(x) for x in items],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def print_preview(items: list[TelegraphItem], limit: int = 5) -> None:
    print(f"\n共抓取 {len(items)} 条电报（HTTP）\n")
    for i, item in enumerate(items[:limit], 1):
        print(f"[{i}] {item.published_at} | {item.level} | 阅读 {item.reading_num}")
        text = item.brief or item.content
        print(f"    {text[:120]}{'...' if len(text) > 120 else ''}")
        print(f"    {item.url}\n")
    if len(items) > limit:
        print(f"... 另有 {len(items) - limit} 条，见输出文件")


def main() -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="财联社电报抓取（纯 HTTP）")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output/cls_telegraph_http.json"),
        help="JSON 输出路径",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=20,
        help="最多抓取条数（默认 20，可分页拉取更多）",
    )
    args = parser.parse_args()

    try:
        items = fetch_telegraph(max_items=args.max_items)
    except Exception as e:
        print(f"抓取失败: {e}", file=sys.stderr)
        print(
            "若签名失效，可能是财联社升级了算法，可暂时改用 scripts/crawl_cls_telegraph.py",
            file=sys.stderr,
        )
        return 1

    if not items:
        print("未获取到数据", file=sys.stderr)
        return 1

    save_json(items, args.output)
    print_preview(items)
    print(f"已保存: {args.output.resolve()}")
    if not _USE_HTTPX:
        print("提示: pip install httpx 可获得更好的连接池与超时控制（当前使用标准库）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
