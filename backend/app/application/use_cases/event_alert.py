"""预警管理用例"""

from app.domain.repositories.user_alert_repo import UserAlertRepository


class EventAlertUseCase:
    def __init__(self, alert_repo: UserAlertRepository):
        self.alert_repo = alert_repo

    async def get_unread_alerts(self, user_id: str, limit: int = 10):
        return await self.alert_repo.get_unread_by_user(user_id, limit)

    async def get_unread_count(self, user_id: str) -> int:
        return await self.alert_repo.count_unread(user_id)
