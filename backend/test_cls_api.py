#!/usr/bin/env python3
"""测试财联社新 API 接口的脚本

用法: python test_cls_api.py

目的:
1. 找到替代 /nodeapi/updateTelegraphList 的新 API
2. 确认是否需要 cookie/session
3. 确认请求格式（GET vs POST，参数结构）
"""

import asyncio
import json
import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.cls.cn/telegraph",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


async def test_session_then_api():
    """先访问主页获取 cookie，再调用 API"""
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        # 第1步: 访问主页拿 cookie
        print("=" * 60)
        print("Step 1: 访问主页获取 cookie...")
        resp = await client.get("https://www.cls.cn/telegraph", headers=HEADERS)
        print(f"  Status: {resp.status_code}")
        print(f"  Cookies: {dict(client.cookies)}")

        # 第2步: 尝试 GET /api/cache (与旧接口结构类似)
        print("\n" + "=" * 60)
        print("Step 2: GET /api/cache?rn=5&lastTime=0&name=telegraph")
        resp = await client.get(
            "https://www.cls.cn/api/cache",
            params={"rn": 5, "lastTime": 0, "name": "telegraph"},
            headers=HEADERS,
        )
        print(f"  Status: {resp.status_code}")
        try:
            data = resp.json()
            print(f"  errno: {data.get('errno')}")
            roll_data = data.get("data", {}).get("roll_data", [])
            print(f"  roll_data count: {len(roll_data)}")
            if roll_data:
                item = roll_data[0]
                print(f"  First item keys: {list(item.keys())}")
                print(f"  First item sample: {json.dumps(item, ensure_ascii=False)[:300]}")
        except Exception as e:
            print(f"  JSON parse error: {e}")
            print(f"  Raw body (first 500): {resp.text[:500]}")

        # 第3步: 尝试 GET /api/cache (refreshTenTelegraph)
        print("\n" + "=" * 60)
        print("Step 3: GET /api/cache?name=refreshTenTelegraph")
        resp = await client.get(
            "https://www.cls.cn/api/cache",
            params={"name": "refreshTenTelegraph"},
            headers=HEADERS,
        )
        print(f"  Status: {resp.status_code}")
        try:
            data = resp.json()
            print(f"  errno: {data.get('errno')}")
            roll_data = data.get("data", {}).get("roll_data", [])
            print(f"  roll_data count: {len(roll_data)}")
        except Exception as e:
            print(f"  JSON parse error: {e}")

        # 第4步: 尝试 POST /api/csw
        print("\n" + "=" * 60)
        print("Step 4: POST /api/csw {lastTime: 0, keyword: '', category: 'telegraph'}")
        resp = await client.post(
            "https://www.cls.cn/api/csw",
            json={"lastTime": 0, "keyword": "", "category": "telegraph"},
            headers=HEADERS,
        )
        print(f"  Status: {resp.status_code}")
        try:
            data = resp.json()
            print(f"  errno/msg: {data.get('errno') or data.get('msg')}")
            telegraph_list = data.get("data", {}).get("list", [])
            total = data.get("data", {}).get("total")
            print(f"  total: {total}")
            print(f"  list count: {len(telegraph_list)}")
            if telegraph_list:
                item = telegraph_list[0]
                print(f"  First item keys: {list(item.keys())}")
                print(f"  First item sample: {json.dumps(item, ensure_ascii=False)[:300]}")
        except Exception as e:
            print(f"  JSON parse error: {e}")
            print(f"  Raw body (first 500): {resp.text[:500]}")

        # 第5步: 尝试 GET /v1/roll/get_roll_list (已知有签名验证)
        print("\n" + "=" * 60)
        print("Step 5: GET /v1/roll/get_roll_list (预期签名失败)")
        resp = await client.get(
            "https://www.cls.cn/v1/roll/get_roll_list",
            params={"refresh_type": 1, "rn": 5, "last_time": 0},
            headers=HEADERS,
        )
        print(f"  Status: {resp.status_code}")
        try:
            data = resp.json()
            print(f"  Response: {json.dumps(data, ensure_ascii=False)}")
        except Exception as e:
            print(f"  JSON parse error: {e}")

        # 第6步: 尝试 POST /api/csw with a recent timestamp
        print("\n" + "=" * 60)
        import time
        recent_time = int(time.time())
        print(f"Step 6: POST /api/csw {{lastTime: {recent_time} (now)}}")
        resp = await client.post(
            "https://www.cls.cn/api/csw",
            json={"lastTime": recent_time, "keyword": "", "category": ""},
            headers=HEADERS,
        )
        print(f"  Status: {resp.status_code}")
        try:
            data = resp.json()
            print(f"  errno/msg: {data.get('errno') or data.get('msg')}")
            telegraph_list = data.get("data", {}).get("list", [])
            print(f"  list count: {len(telegraph_list)}")
            if telegraph_list:
                item = telegraph_list[0]
                print(f"  First item keys: {list(item.keys())}")
                print(f"  First item sample: {json.dumps(item, ensure_ascii=False)[:300]}")
        except Exception as e:
            print(f"  JSON parse error: {e}")


if __name__ == "__main__":
    asyncio.run(test_session_then_api())
