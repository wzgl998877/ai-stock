"""依赖注入 — 当前用户解析"""

from dataclasses import dataclass

from fastapi import Depends, Request


@dataclass
class CurrentUser:
    """当前请求用户信息"""
    user_id: str
    user_account: str
    user_name: str


def get_current_user(request: Request) -> CurrentUser:
    """从请求头解析当前用户，未携带时回退为 default（过渡兼容）"""
    user_id = request.headers.get("X-User-Id", "default")
    user_account = request.headers.get("X-User-Account", "default")
    user_name = request.headers.get("X-User-Name", "默认用户")
    return CurrentUser(user_id=user_id, user_account=user_account, user_name=user_name)
