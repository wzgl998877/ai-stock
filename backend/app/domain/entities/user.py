from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    user_id: str
    user_account: str
    password: str
    user_name: Optional[str] = None
    email: Optional[str] = None
    nick_name: Optional[str] = None
    icon_url: Optional[str] = None
    gender: Optional[str] = None  # '0'=未知, '1'=男, '2'=女
    mobile: Optional[str] = None
    user_type: Optional[str] = None  # '0'=普通, '1'=管理员
    status: str = "0"  # '0'=正常, '1'=停用
    last_login: Optional[datetime] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    deleted: str = "0"
