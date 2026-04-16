from enum import Enum


class ReminderStatus(str, Enum):
    PENDING = "pending"
    REMINDED_3DAY = "reminded_3day"
    REMINDED_TODAY = "reminded_today"
    ARCHIVED = "archived"
