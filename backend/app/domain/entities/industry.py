from dataclasses import dataclass
from typing import Optional


@dataclass
class Industry:
    industry_code: str
    name: str
    level: int  # 1=一级, 2=二级, 3=三级
    parent_code: Optional[str] = None
    display_order: int = 0
