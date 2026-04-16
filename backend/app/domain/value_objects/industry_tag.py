from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class IndustryTag:
    """行业标签值对象（用于 DTO 传递，非持久化）"""
    code: str
    name: str
    chain_level: Optional[int] = None
