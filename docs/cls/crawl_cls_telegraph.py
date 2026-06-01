#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社电报抓取脚本

通过 Playwright 打开 https://www.cls.cn/telegraph ，拦截站内已签名的
/api/cache 接口，解析 roll_data 列表并保存为 JSON。

依赖（与 Crawl4AI 相同，需已安装浏览器）:
    pip install playwright
    python -m playwright install chromium

用法:
    python scripts/crawl_cls_telegraph.py
    python scripts/crawl_cls_telegraph.py -o output/cls_telegraph.json
    python scripts/crawl_cls_telegraph.py --max-items 40
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import Page, Response, async_playwright

TELEGRAPH_URL = "https://www.cls.cn/telegraph"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class TelegraphItem:
    """统一后的电报条目"""

    id: int
    title: str
    content: str
    brief: str
    published_at: str  # 北京时间字符串
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
        # 详情页（部分条目有独立 id）
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


def _parse_roll_response(body: dict[str, Any]) -> list[dict[str, Any]]:
    errno = body.get("errno")
    if errno not in (0, "0", None):
        msg = body.get("msg") or body.get("message") or "unknown error"
        raise RuntimeError(f"财联社 API 返回错误: errno={errno} msg={msg}")
    data = body.get("data") or {}
    roll = data.get("roll_data")
    if roll is None:
        return []
    if not isinstance(roll, list):
        raise RuntimeError("roll_data 格式异常")
    return roll


def _merge_items(
    existing: list[TelegraphItem], new_raw: list[dict[str, Any]]
) -> list[TelegraphItem]:
    seen = {x.id for x in existing}
    out = list(existing)
    for raw in new_raw:
        item = TelegraphItem.from_roll(raw)
        if item.id and item.id not in seen:
            seen.add(item.id)
            out.append(item)
    return out


async def _collect_from_responses(
    page: Page, timeout_ms: int = 90_000
) -> list[dict[str, Any]]:
    """监听页面请求，汇总 telegraph / telegraphList 的 roll_data。"""
    batches: list[list[dict[str, Any]]] = []

    async def on_response(response: Response) -> None:
        url = response.url
        if "/api/cache" not in url:
            return
        if "telegraph" not in url:
            return
        if response.status != 200:
            return
        try:
            body = await response.json()
        except Exception:
            return
        try:
            roll = _parse_roll_response(body)
        except RuntimeError:
            return
        if roll:
            batches.append(roll)

    page.on("response", on_response)
    try:
        await page.goto(
            TELEGRAPH_URL,
            wait_until="domcontentloaded",
            timeout=timeout_ms,
        )
        # 等待首屏接口；若需更多，滚动触发 telegraphList
        await asyncio.sleep(2.5)
    finally:
        page.remove_listener("response", on_response)

    merged: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for batch in batches:
        for raw in batch:
            rid = int(raw.get("id") or 0)
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                merged.append(raw)
    return merged


async def _scroll_load_more(page: Page, rounds: int = 3) -> None:
    """向下滚动，触发加载更多（telegraphList）。"""
    for _ in range(rounds):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)


async def fetch_telegraph(
    max_items: int = 20,
    headless: bool = True,
    scroll_more: bool = True,
) -> list[TelegraphItem]:
    """
    抓取财联社电报。

    Args:
        max_items: 最多保留条数（去重后按时间新→旧）
        headless: 是否无头浏览器
        scroll_more: 是否滚动加载更多
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=DEFAULT_UA, locale="zh-CN")
        page = await context.new_page()

        all_raw: list[dict[str, Any]] = []

        if scroll_more and max_items > 20:
            batches_collected: list[list[dict[str, Any]]] = []

            async def on_response(response: Response) -> None:
                url = response.url
                if "/api/cache" not in url or "telegraph" not in url:
                    return
                if response.status != 200:
                    return
                try:
                    body = await response.json()
                    roll = _parse_roll_response(body)
                except Exception:
                    return
                if roll:
                    batches_collected.append(roll)

            page.on("response", on_response)
            await page.goto(
                TELEGRAPH_URL, wait_until="domcontentloaded", timeout=90_000
            )
            await asyncio.sleep(2)
            while len({int(r.get("id") or 0) for b in batches_collected for r in b}) < max_items:
                await _scroll_load_more(page, rounds=1)
                await asyncio.sleep(1)
                if len(batches_collected) > 10:
                    break
            page.remove_listener("response", on_response)

            seen: set[int] = set()
            for batch in batches_collected:
                for raw in batch:
                    rid = int(raw.get("id") or 0)
                    if rid and rid not in seen:
                        seen.add(rid)
                        all_raw.append(raw)
        else:
            all_raw = await _collect_from_responses(page)

        await browser.close()

    items = [TelegraphItem.from_roll(r) for r in all_raw]
    items.sort(key=lambda x: x.ctime, reverse=True)
    return items[:max_items]


def save_json(items: list[TelegraphItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "cls",
        "url": TELEGRAPH_URL,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(items),
        "items": [asdict(x) for x in items],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def print_preview(items: list[TelegraphItem], limit: int = 5) -> None:
    print(f"\n共抓取 {len(items)} 条电报\n")
    for i, item in enumerate(items[:limit], 1):
        print(f"[{i}] {item.published_at} | {item.level} | 阅读 {item.reading_num}")
        text = item.brief or item.content
        print(f"    {text[:120]}{'...' if len(text) > 120 else ''}")
        print(f"    {item.url}\n")
    if len(items) > limit:
        print(f"... 另有 {len(items) - limit} 条，见输出文件")


def main() -> int:
    # Windows 控制台 UTF-8
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="财联社电报抓取")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output/cls_telegraph.json"),
        help="JSON 输出路径（默认 output/cls_telegraph.json）",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=20,
        help="最多抓取条数（默认 20；>20 时会滚动加载更多）",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="显示浏览器窗口（调试用）",
    )
    parser.add_argument(
        "--no-scroll",
        action="store_true",
        help="不滚动，仅首屏约 20 条",
    )
    args = parser.parse_args()

    try:
        items = asyncio.run(
            fetch_telegraph(
                max_items=args.max_items,
                headless=not args.no_headless,
                scroll_more=not args.no_scroll,
            )
        )
    except Exception as e:
        print(f"抓取失败: {e}", file=sys.stderr)
        print(
            "提示: 请先执行 python -m playwright install chromium",
            file=sys.stderr,
        )
        return 1

    if not items:
        print("未获取到电报数据，请检查网络或稍后重试。", file=sys.stderr)
        return 1

    save_json(items, args.output)
    print_preview(items)
    print(f"已保存: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
