from datetime import date, timedelta

from sleeping_beauty.config.config import Config
from sleeping_beauty.logsys.logger_manager import LoggerManager
from sleeping_beauty.models.sleep_context import SleepContext

logger = LoggerManager.get_logger(__name__)


class SleepContextBuilder:
    """
    Builds a SleepContext from Config.

    Assumes:
    - CLI-level validation has already enforced argument exclusivity
    - Required selectors (--view or --start-date) are present

    Owns:
    - intent resolution (view vs date)
    - calendar-based date expansion
    """

    def build(self) -> SleepContext:
        config = Config()
        view = config.sleep_view
        start_raw = config.sleep_start_date
        end_raw = config.sleep_end_date
        divider = getattr(config, "sleep_divider", False)

        # -------------------------------------------------
        # Determine mode (CLI guarantees validity)
        # -------------------------------------------------
        mode = "view" if view is not None else "date"

        today = date.today()

        # -------------------------------------------------
        # Resolve date range
        # -------------------------------------------------
        if mode == "view":
            if view == "today":
                start = end = today

            elif view == "yesterday":
                start = end = today - timedelta(days=1)

            elif view == "week":
                start = today - timedelta(days=today.weekday())  # Monday
                end = start + timedelta(days=6)  # Sunday

            elif view == "month":
                start = today.replace(day=1)
                if start.month == 12:
                    end = start.replace(year=start.year + 1, month=1) - timedelta(
                        days=1
                    )
                else:
                    end = start.replace(month=start.month + 1) - timedelta(days=1)

            else:
                # Programmer/config error
                raise ValueError(f"Unsupported sleep view: {view}")

        else:
            start = date.fromisoformat(start_raw)
            end = date.fromisoformat(end_raw) if end_raw else start

            if start > end:
                raise ValueError("start_date cannot be after end_date")

        logger.debug(
            f"SleepContext resolved: mode={mode}, start={start}, end={end}, divider={divider}"
        )

        return SleepContext(
            mode=mode,
            view=view,
            start_date=start,
            end_date=end,
            divider=divider,
        )
