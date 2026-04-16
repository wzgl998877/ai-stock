from enum import Enum


class EventType(str, Enum):
    GEO_POLITICAL = "geopolitical"
    POLICY = "policy"
    EARNINGS = "earnings"
    SUPPLY_CHAIN = "supply_chain"
    OTHER = "other"
