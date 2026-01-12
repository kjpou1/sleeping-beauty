from datetime import date, timedelta
from typing import Optional

from sleeping_beauty.clients.oura_api_client import OuraApiClient
from sleeping_beauty.core.sleep.sleep_day_builder import build_sleep_day_snapshot
from sleeping_beauty.core.sleep.sleep_day_snapshot import SleepDaySnapshot


class SleepDayProvider:
    def __init__(self, client: OuraApiClient):
        self.client = client

    async def get_snapshot(self, target_day: date) -> Optional[SleepDaySnapshot]:
        # -----------------------------
        # Fetch sleep docs (expanded)
        # -----------------------------
        sleep_docs = []
        async for doc in self.client.iter_sleep(
            start_date=target_day - timedelta(days=1),
            end_date=target_day + timedelta(days=1),
        ):
            sleep_docs.append(doc)

        if not sleep_docs:
            return None

        # -----------------------------
        # Daily sleep score
        # -----------------------------
        daily_sleep = None
        async for doc in self.client.iter_daily_sleep_scores(
            start_date=target_day,
            end_date=target_day,
        ):
            daily_sleep = doc

        if not daily_sleep:
            raise RuntimeError("Missing DailySleepScore")

        # -----------------------------
        # Readiness score
        # -----------------------------
        readiness = None
        async for doc in self.client.iter_daily_readiness_scores(
            start_date=target_day,
            end_date=target_day,
        ):
            readiness = doc

        if not readiness:
            raise RuntimeError("Missing DailyReadinessScore")

        # -----------------------------
        # Build snapshot (pure)
        # -----------------------------
        return await build_sleep_day_snapshot(
            target_day=target_day,
            sleep_docs=sleep_docs,
            daily_sleep=daily_sleep,
            readiness=readiness,
        )
