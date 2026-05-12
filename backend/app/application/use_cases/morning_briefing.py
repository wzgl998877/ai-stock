"""晨报用例"""

from app.domain.repositories.morning_briefing_repo import MorningBriefingRepository


class MorningBriefingUseCase:
    def __init__(self, briefing_repo: MorningBriefingRepository):
        self.briefing_repo = briefing_repo

    async def get_today(self, user_id: str):
        return await self.briefing_repo.get_today(user_id)

    async def get_history(self, user_id: str, days: int = 7):
        return await self.briefing_repo.list_history(user_id, days)
