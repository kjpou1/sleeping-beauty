"""
Sleep Summary Service

CLI-facing service responsible for rendering human-readable sleep summaries.

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

This structure allows reuse across:
- sleep summary
- sleep journal
- sleep export
- LLM analysis pipelines
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from sleeping_beauty.clients.oura_api_client import OuraApiClient
from sleeping_beauty.clients.oura_errors import OuraAuthError
from sleeping_beauty.config.config import Config
from sleeping_beauty.core.sleep.sleep_day_provider import SleepDayProvider
from sleeping_beauty.core.sleep.sleep_day_snapshot import SleepDaySnapshot
from sleeping_beauty.core.sleep.sleep_stage import SleepStage
from sleeping_beauty.logsys.logger_manager import LoggerManager
from sleeping_beauty.models.sleep_context import SleepContext
from sleeping_beauty.oura.auth.domain.auth_preflight_result import AuthPreflightReport
from sleeping_beauty.oura.auth.domain.exceptions import LoginRequiredError
from sleeping_beauty.oura.auth.oura_auth import OuraAuth

logger = LoggerManager.get_logger(__name__)


class SleepSummaryService:
    """
    CLI-facing service for rendering daily sleep summaries.

    Responsibilities:
    - Validate authentication and API reachability
    - Iterate over a resolved date range
    - Request SleepDaySnapshot objects from SleepDayProvider
    - Render snapshots to stdout

    Non-responsibilities:
    - Does NOT fetch raw API data directly
    - Does NOT perform sleep selection logic
    - Does NOT construct domain objects

    This service is intentionally thin and stateless.
    """

    def __init__(self):
        logger.debug("Initializing SleepSummaryService")
        self.config = Config()

        # -------------------------------------------------
        # Authentication preflight
        # -------------------------------------------------
        # Validates:
        # - token presence
        # - token refreshability
        # - local credential storage
        #
        # NOTE:
        # Authentication is explicit by design.
        # The user must run `sleeping-beauty auth login`.
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
        # The service never calls the API directly.
        # All backend access flows through SleepDayProvider.
        token_provider = oura_auth.get_access_token
        self.client = OuraApiClient(token_provider=token_provider)
        self.provider = SleepDayProvider(self.client)

        logger.debug("SleepSummaryService initialized successfully")

    async def run(self, sleep_context: SleepContext) -> None:
        """
        Execute the sleep summary command.

        Flow:
        1. Validate authentication and API access
        2. Iterate day-by-day over the resolved date range
        3. Request a SleepDaySnapshot for each day
        4. Render the snapshot to stdout

        Processing is intentionally day-by-day to allow:
        - streaming output
        - partial failures
        - easier debugging
        """
        logger.info(f"🛏️ SleepSummaryService invoked: {sleep_context}")

        try:
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
            return  # graceful exit

    async def _summarize_day(self, target_day: date) -> None:
        """
        Fetch and render a single day's sleep snapshot.

        This method:
        - Requests a fully-built SleepDaySnapshot from the provider
        - Performs no business logic
        - Skips rendering if no data exists for the day
        """

        snapshot: Optional[SleepDaySnapshot] = await self.provider.get_snapshot(
            target_day
        )

        if snapshot:
            self._render_snapshot(snapshot)

    def _render_snapshot(self, s: SleepDaySnapshot) -> None:
        awake_block = self._render_awake_periods(s)

        supplemental_episode_block = ""
        if s.supplemental_episodes:
            supplemental_episode_block = "\n" + self._render_supplemental_episodes(s)

        print(
            f"""🛏️ Sleep Summary — {s.day:%A, %b %-d, %Y}\n
    Night: {s.night_start:%a %b %-d} → {s.night_end:%a %b %-d}

    Core overnight sleep:
    Total sleep: {self._seconds_to_hm(s.core_sleep_seconds)} ({self._format_time_range(s.night_start, s.night_end)})
    Sleep efficiency: {s.efficiency_pct} %

    Supplemental sleep (naps): {self._seconds_to_hm(s.supplemental_sleep_seconds)}{supplemental_episode_block}

    Total sleep (24h): {self._seconds_to_hm(s.total_sleep_24h_seconds)}

    ────────────────────────────

    Time in bed: {self._seconds_to_hm(s.time_in_bed_seconds)}
    Latency: {self._seconds_to_minutes(s.latency_seconds)} min

    REM sleep: {self._seconds_to_hm(s.rem_seconds)} ({s.rem_pct}%)
    Deep sleep: {self._seconds_to_hm(s.deep_seconds)} ({s.deep_pct}%)

{awake_block.rstrip()}

    Average HR: {s.avg_hr:.0f} bpm
    Lowest HR: {s.min_hr} bpm
    Average HRV: {s.avg_hrv} ms

    Sleep score: {s.sleep_score}
    Timing: {s.timing_label}
    Readiness score: {s.readiness_score}
"""
        )

    def _format_time_range(self, start, end) -> str:
        return f"{start:%H:%M} - {end:%H:%M}"

    # -------------------------------------------------
    # Presentation helpers (rendering concerns only)
    # -------------------------------------------------

    def _render_supplemental_episodes(self, s: SleepDaySnapshot) -> str:
        """
        Render supplemental (nap) episodes as bullet lines only.

        Assumes:
        - Total duration is already rendered elsewhere
        """
        if not s.supplemental_episodes:
            return ""

        lines = []
        for ep in s.supplemental_episodes:
            duration_min = ep.duration_seconds // 60
            lines.append(f"\t• {ep.start:%H:%M}–{ep.end:%H:%M} ({duration_min}m)")

        return "\n".join(lines)

    def _render_awake_periods(self, s: SleepDaySnapshot, max_entries: int = 3) -> str:
        """
        Render a compact list of awake periods from the sleep timeline.

        Rules:
        - Uses snapshot.timeline only
        - Shows wall-clock times + duration
        - No inference, no aggregation beyond formatting
        """
        if not s.timeline:
            return ""

        awake_segments = [
            seg for seg in s.timeline.segments if seg.stage == SleepStage.AWAKE
        ]

        if not awake_segments:
            return "    Awake periods: none\n"

        lines = ["    Awake periods:"]

        for seg in awake_segments[:max_entries]:
            duration_min = int((seg.end - seg.start).total_seconds() // 60)
            lines.append(f"      • {seg.start:%H:%M}–{seg.end:%H:%M} ({duration_min}m)")

        remaining = len(awake_segments) - max_entries
        if remaining > 0:
            lines.append(f"      • +{remaining} more")

        return "\n".join(lines) + "\n"

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
