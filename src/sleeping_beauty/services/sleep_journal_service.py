"""
Sleep Journal Service

CLI-facing service responsible for rendering descriptive, journal-style
sleep entries.

Architecture:
- This service performs orchestration only (CLI flow, iteration, rendering).
- All backend data access is delegated to SleepDayProvider.
- All domain construction logic lives in pure builder functions.
- The service consumes a SleepDaySnapshot DTO and renders it.

Design guarantees:
- No raw API calls outside the provider
- No business logic in rendering
- No formatting logic in providers
- Snapshots are backend-agnostic and reusable

The journal differs from the summary in *presentation only*:
- Narrative-friendly
- Observational
- No aggregation or interpretation
"""

from datetime import date, timedelta
from typing import Optional

from sleeping_beauty.clients.oura_api_client import OuraApiClient
from sleeping_beauty.clients.oura_errors import OuraAuthError
from sleeping_beauty.config.config import Config
from sleeping_beauty.core.sleep.sleep_day_provider import SleepDayProvider
from sleeping_beauty.core.sleep.sleep_day_snapshot import SleepDaySnapshot
from sleeping_beauty.logsys.logger_manager import LoggerManager
from sleeping_beauty.models.sleep_context import SleepContext
from sleeping_beauty.oura.auth.domain.auth_preflight_result import AuthPreflightReport
from sleeping_beauty.oura.auth.domain.exceptions import LoginRequiredError
from sleeping_beauty.oura.auth.oura_auth import OuraAuth

logger = LoggerManager.get_logger(__name__)


class SleepJournalService:
    """
    CLI-facing service for rendering sleep journal entries.

    Responsibilities:
    - Validate authentication and API reachability
    - Iterate over a resolved date range
    - Request SleepDaySnapshot objects from SleepDayProvider
    - Render snapshots in a descriptive, journal-style format

    Non-responsibilities:
    - Does NOT fetch raw API data directly
    - Does NOT perform sleep selection logic
    - Does NOT construct domain objects
    - Does NOT interpret or score sleep

    This service is intentionally thin and stateless.
    """

    def __init__(self):
        logger.debug("Initializing SleepJournalService")
        self.config = Config()

        # -------------------------------------------------
        # Authentication preflight (IDENTICAL to summary)
        # -------------------------------------------------
        oura_auth = OuraAuth.from_config()
        preflight: AuthPreflightReport = oura_auth.preflight_check()

        if preflight.ok:
            logger.debug("\n" + "\n".join(preflight.messages))
        else:
            logger.error("\n" + "\n".join(preflight.messages))
            raise RuntimeError("Oura authentication preflight failed")

        # -------------------------------------------------
        # API client + provider wiring
        # -------------------------------------------------
        token_provider = oura_auth.get_access_token
        self.client = OuraApiClient(token_provider=token_provider)
        self.provider = SleepDayProvider(self.client)

        logger.debug("SleepJournalService initialized successfully")

    async def run(self, sleep_context: SleepContext) -> None:
        """
        Execute the sleep journal command.

        Flow:
        1. Validate authentication and API access
        2. Iterate day-by-day over the resolved date range
        3. Request a SleepDaySnapshot for each day
        4. Render a journal entry to stdout

        Processing is intentionally day-by-day to allow:
        - streaming output
        - partial failures
        - chronological journaling
        """
        logger.info(f"🛏️ SleepJournalService invoked: {sleep_context}")

        try:
            current = sleep_context.start_date
            end = sleep_context.end_date

            while current <= end:
                await self._render_day(current)

                if sleep_context.divider and current < end:
                    print("\n" + "─" * 28 + "\n")

                current += timedelta(days=1)

        except (LoginRequiredError, OuraAuthError):
            logger.error(
                "Oura authentication required.\n"
                "Run `sleeping-beauty auth login` and try again."
            )
            return  # graceful exit

    async def _render_day(self, target_day: date) -> None:
        """
        Fetch and render a single day's sleep journal entry.

        This method:
        - Requests a fully-built SleepDaySnapshot from the provider
        - Performs no business logic
        - Emits a placeholder entry if no data exists
        """

        snapshot: Optional[SleepDaySnapshot] = await self.provider.get_snapshot(
            target_day
        )

        if snapshot:
            self._render_snapshot(snapshot)
        else:
            self._render_missing_day(target_day)

    # -------------------------------------------------
    # Rendering (journal-style)
    # -------------------------------------------------

    def _render_snapshot(self, s: SleepDaySnapshot) -> None:
        """
        Render a SleepDaySnapshot as a descriptive journal entry.

        This output is intentionally observational and narrative-friendly.
        No interpretation or aggregation is introduced here.
        """

        print(
            f"""🛏️ Sleep Journal — {s.day:%A, %b %-d, %Y}

    Night window:
    {s.night_start:%a %b %-d %H:%M} → {s.night_end:%a %b %-d %H:%M}

    Sleep observed:
    • Core overnight sleep: {self._seconds_to_hm(s.core_sleep_seconds)}
    • Supplemental sleep: {self._seconds_to_hm(s.supplemental_sleep_seconds)}
    • Total sleep (24h): {self._seconds_to_hm(s.total_sleep_24h_seconds)}

    Sleep process:
    • Sleep efficiency: {s.efficiency_pct} %
    • Time in bed: {self._seconds_to_hm(s.time_in_bed_seconds)}
    • Sleep latency: {self._seconds_to_minutes(s.latency_seconds)} min

    Sleep structure:
    • REM: {self._seconds_to_hm(s.rem_seconds)} ({s.rem_pct}%)
    • Deep: {self._seconds_to_hm(s.deep_seconds)} ({s.deep_pct}%)

    Physiology:
    • Average HR: {s.avg_hr:.0f} bpm
    • Lowest HR: {s.min_hr} bpm
    • Average HRV: {s.avg_hrv} ms

    Contextual scores:
    • Sleep score: {s.sleep_score}
    • Timing: {s.timing_label}
    • Readiness score: {s.readiness_score}

    ────────────────────────────

    Nocturnal Bathroom
    • Bathroom trips: 0 / 1 / 2+
    • If ≥1:
    – Woke to pee / peed after waking / unclear
    – Return to sleep: yes / no / partial

    ────────────────────────────

    Subjective Feedback (free format)
    [Write anything relevant: how you felt on waking, heat/cold, grogginess, pain,
    meds taken or skipped, alcohol/food, stress, noise, frustration with the wearable,
    thoughts on waking, etc. No rules.]
    """
        )

    def _render_missing_day(self, day: date) -> None:
        """
        Render an explicit journal entry for days with no sleep data.
        """

        print(
            f"""🛏️ Sleep Journal — {day:%A, %b %-d, %Y}

No sleep data available for this day.
"""
        )

    # -------------------------------------------------
    # Presentation helpers (IDENTICAL to summary)
    # -------------------------------------------------

    def _seconds_to_hm(self, seconds: Optional[int]) -> str:
        if not seconds or seconds <= 0:
            return "0h 00m"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m:02d}m"

    # -------------------------------------------------
    # Presentation helpers (rendering concerns only)
    # -------------------------------------------------

    def _seconds_to_hm(self, seconds: Optional[int]) -> str:
        if not seconds or seconds <= 0:
            return "0h 00m"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m:02d}m"

    def _seconds_to_minutes(self, seconds: Optional[int]) -> str:
        if seconds is None:
            return "n/a"
        return f"{seconds // 60}"
