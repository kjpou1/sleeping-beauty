from datetime import date, timedelta
from pathlib import Path

from sleeping_beauty.clients.oura_api_client import OuraApiClient
from sleeping_beauty.clients.oura_errors import OuraAuthError
from sleeping_beauty.config.config import Config
from sleeping_beauty.logsys.logger_manager import LoggerManager
from sleeping_beauty.models.sleep_context import SleepContext
from sleeping_beauty.oura.auth.domain.auth_preflight_result import AuthPreflightReport
from sleeping_beauty.oura.auth.domain.exceptions import LoginRequiredError
from sleeping_beauty.oura.auth.oura_auth import OuraAuth
from sleeping_beauty.oura.auth.storage.file_storage import FileTokenStorage

logger = LoggerManager.get_logger(__name__)


class SleepSummaryService:
    """
    Service responsible for handling sleep summary commands.

    This is a scaffold only.
    Business logic (validation, date resolution, API access, rendering)
    will be implemented incrementally.
    """

    def __init__(self):
        logger.debug("Initializing SleepSummaryService")
        self.config = Config()

        # -------------------------------------------------
        # Oura authentication + client initialization
        # -------------------------------------------------
        storage = FileTokenStorage(path=Path(self.config.oura_token_path).expanduser())

        oura_auth = OuraAuth.from_config()
        preflight: AuthPreflightReport = oura_auth.preflight_check()

        if preflight.ok:
            logger.debug("\n" + "\n".join(preflight.messages))
        else:
            logger.error("\n" + "\n".join(preflight.messages))
            raise RuntimeError("Oura authentication preflight failed")

        # -------------------------------------------------
        # Oura API client
        # -------------------------------------------------
        token_provider = oura_auth.get_access_token  # callable, not invoked
        self.client = OuraApiClient(token_provider=token_provider)

        logger.debug("OuraApiClient initialized successfully")

    async def run(self, sleep_context: SleepContext) -> None:
        """
        Entry point for sleep summary execution.

        Parameters
        ----------
        subcommand : str
            The sleep subcommand to execute (expected: 'summary').
        """
        logger.info(f"🛏️ SleepSummaryService invoked: {sleep_context}")

        # -------------------------------------------------
        # Auth + API reachability test (INTENTIONAL)
        # -------------------------------------------------
        try:
            # We do NOT consume results yet.
            # This is just to validate authentication + API access.
            # async for _ in self.client.iter_sleep(
            #     start_date=sleep_context.start_date,
            #     end_date=sleep_context.end_date,
            # ):
            #     break  # one item is enough to prove access

            current = sleep_context.start_date
            end = sleep_context.end_date

            while current <= end:
                await self._summarize_day(current)

                if sleep_context.divider and current < end:
                    print("\n" + "─" * 28 + "\n")

                current += timedelta(days=1)

        except (LoginRequiredError, OuraAuthError):
            logger.error(
                "Oura authentication required.\n"
                "Run `sleeping-beauty auth login` and try again."
            )
            return  # 👈 graceful exit

        # -------------------------------------------------
        # Placeholder for future implementation
        # -------------------------------------------------
        logger.debug("Sleep summary execution scaffold reached.")
        logger.info("Sleep summary logic not yet implemented.")

    def _print_day_header(self, day: date) -> None:
        night_start = day - timedelta(days=1)

        print(f"🛏️ Sleep Summary — {day.isoformat()}")
        print(
            f"Night: "
            f"{night_start.strftime('%b %d').lstrip('0')} "
            f"→ "
            f"{day.strftime('%b %d').lstrip('0')}"
        )

    async def _summarize_day(self, target_day: date) -> None:
        # -------------------------------------------------
        # 1. Fetch sleep docs (expanded window)
        # -------------------------------------------------
        sleep_docs = []
        async for doc in self.client.iter_sleep(
            start_date=target_day - timedelta(days=1),
            end_date=target_day + timedelta(days=1),
        ):
            sleep_docs.append(doc)

        if not sleep_docs:
            logger.warning(f"No sleep data for {target_day}")
            return

        # -------------------------------------------------
        # 2. Core sleep
        # -------------------------------------------------
        core_sleep = self._select_core_sleep(sleep_docs, target_day)

        # -------------------------------------------------
        # 3. Daily sleep score
        # -------------------------------------------------
        daily_sleep_docs = []
        async for doc in self.client.iter_daily_sleep_scores(
            start_date=target_day,
            end_date=target_day,
        ):
            daily_sleep_docs.append(doc)

        if len(daily_sleep_docs) != 1:
            raise RuntimeError("Expected exactly one DailySleepScore")

        daily_sleep = daily_sleep_docs[0]

        # -------------------------------------------------
        # 4. Readiness score
        # -------------------------------------------------
        readiness_docs = []
        async for doc in self.client.iter_daily_readiness_scores(
            start_date=target_day,
            end_date=target_day,
        ):
            readiness_docs.append(doc)

        if len(readiness_docs) != 1:
            raise RuntimeError("Expected exactly one DailyReadinessScore")

        readiness = readiness_docs[0]

        # -------------------------------------------------
        # 5. Supplemental sleep
        # -------------------------------------------------
        _, supplemental_seconds = self._compute_supplemental_sleep(
            sleep_docs, core_sleep, target_day
        )

        total_24h_seconds = core_sleep.total_sleep_duration + supplemental_seconds

        # -------------------------------------------------
        # 6. Derived metrics
        # -------------------------------------------------
        rem_pct = (
            round(100 * core_sleep.rem_sleep_duration / core_sleep.total_sleep_duration)
            if core_sleep.rem_sleep_duration and core_sleep.total_sleep_duration
            else "n/a"
        )

        deep_pct = (
            round(
                100 * core_sleep.deep_sleep_duration / core_sleep.total_sleep_duration
            )
            if core_sleep.deep_sleep_duration and core_sleep.total_sleep_duration
            else "n/a"
        )

        timing_label = (
            "Optimal" if daily_sleep.timing >= 90 else f"{daily_sleep.timing}/100"
        )

        # -------------------------------------------------
        # 7. Output (CANONICAL)
        # -------------------------------------------------
        print(
            f"""🛏️ Sleep Summary — {core_sleep.day}
    Night: {core_sleep.bedtime_start.strftime("%b %d")} → {core_sleep.bedtime_end.strftime("%b %d")}

    Core overnight sleep:
    Total sleep: {self._seconds_to_hm(core_sleep.total_sleep_duration)}
    Sleep efficiency: {core_sleep.efficiency} %

    Supplemental sleep (naps):
    Total: {self._seconds_to_hm(supplemental_seconds)}

    Total sleep (24h): {self._seconds_to_hm(total_24h_seconds)}

    ────────────────────────────

    Time in bed: {self._seconds_to_hm(core_sleep.time_in_bed)}
    Latency: {self._seconds_to_minutes(core_sleep.latency)} min

    REM sleep: {self._seconds_to_hm(core_sleep.rem_sleep_duration)} ({rem_pct}%)
    Deep sleep: {self._seconds_to_hm(core_sleep.deep_sleep_duration)} ({deep_pct}%)

    Average HR: {core_sleep.average_heart_rate:.0f} bpm
    Lowest HR: {core_sleep.lowest_heart_rate} bpm
    Average HRV: {core_sleep.average_hrv} ms

    Sleep score: {daily_sleep.score}
    Timing: {timing_label}
    Readiness score: {readiness.score}
    """.strip()
        )

    # ================================================================
    # Helpers (local, private)
    # ================================================================

    def _seconds_to_hm(self, seconds: int | None) -> str:
        if not seconds or seconds <= 0:
            return "0h 00m"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m:02d}m"

    def _seconds_to_minutes(self, seconds: int | None) -> str:
        if seconds is None:
            return "n/a"
        return f"{seconds // 60}"

    def _is_night_sleep(self, doc) -> bool:
        start = doc.bedtime_start.timetz()
        return start >= time(18, 0) or start <= time(12, 0)

    def _select_core_sleep(self, sleep_docs, target_day: date):
        ending_today = [d for d in sleep_docs if d.day == target_day]
        if not ending_today:
            raise RuntimeError(f"No sleep episodes ending on {target_day}")

        long_sleeps = [d for d in ending_today if d.type == "long_sleep"]
        if long_sleeps:
            return max(long_sleeps, key=lambda d: d.total_sleep_duration)

        night_sleeps = [d for d in ending_today if self._is_night_sleep(d)]
        if night_sleeps:
            return max(night_sleeps, key=lambda d: d.total_sleep_duration)

        return max(ending_today, key=lambda d: d.total_sleep_duration)

    def _compute_supplemental_sleep(
        self,
        sleep_docs,
        core_sleep,
        target_day: date,
    ):
        supplemental = [
            d
            for d in sleep_docs
            if (
                d.day == target_day
                and d.id != core_sleep.id
                and (d.total_sleep_duration or 0) > 0
            )
        ]
        total_seconds = sum(d.total_sleep_duration for d in supplemental)
        return supplemental, total_seconds
