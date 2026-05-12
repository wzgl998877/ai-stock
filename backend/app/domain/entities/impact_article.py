from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ImpactArticle:
    article_id: Optional[int] = None
    event_id: int = 0
    title: str = ""
    content: Optional[str] = None
    source: str = ""
    url: str = ""
    url_hash: str = ""
    published_at: Optional[datetime] = None
    crawled_at: Optional[datetime] = None
