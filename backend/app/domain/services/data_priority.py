"""Data source priority service.

When multiple data sources provide data for the same stock,
select the one with highest priority (lowest priority number).
"""

from app.domain.models.stock_data import SourceType
from typing import Optional


# Default priority map (lower = higher priority)
DEFAULT_PRIORITY = {
    SourceType.TUSHARE: 1,
    SourceType.AKSHARE: 2,
    SourceType.BAOSTOCK: 3,
}


def get_highest_priority_source(
    available_sources: list[SourceType] | list[str],
    priority_map: Optional[dict] = None,
) -> Optional[SourceType]:
    """Return the source with the highest priority from available sources.

    Args:
        available_sources: List of available source types.
        priority_map: Optional custom priority map. Uses DEFAULT_PRIORITY if not provided.

    Returns:
        The SourceType with the lowest priority number, or None if no sources available.
    """
    if not available_sources:
        return None

    pmap = priority_map or DEFAULT_PRIORITY

    def _resolve(s):
        if isinstance(s, str):
            try:
                return SourceType(s)
            except ValueError:
                return None
        return s

    resolved = [_resolve(s) for s in available_sources]
    resolved = [s for s in resolved if s is not None]

    if not resolved:
        return None

    return min(resolved, key=lambda s: pmap.get(s, 99))


def merge_by_priority(
    results_by_source: dict[str, list],
    priority_map: Optional[dict] = None,
) -> list:
    """Merge results from multiple sources, prioritized by source priority.

    For each unique record (by code/date), keep the one from the highest
    priority source.

    Args:
        results_by_source: {source_type_name: [records]}
        priority_map: Optional custom priority map.

    Returns:
        Merged list of records.
    """
    pmap = priority_map or DEFAULT_PRIORITY
    merged = {}

    # Sort sources by priority
    sorted_sources = sorted(
        results_by_source.keys(),
        key=lambda s: pmap.get(s, 99),
    )

    for source in sorted_sources:
        records = results_by_source.get(source, [])
        for record in records:
            # Use code or code+date as key for deduplication
            key = record.get("code") or record.get("ts_code", "")
            if key not in merged:
                merged[key] = record

    return list(merged.values())
