from sleeping_beauty.logsys.logger_manager import LoggerManager
from sleeping_beauty.models.sleep_context import SleepContext
from sleeping_beauty.services.sleep.sleep_context_builder import SleepContextBuilder
from sleeping_beauty.services.sleep_summary_service import SleepSummaryService

logger = LoggerManager.get_logger(__name__)


class SleepService:
    """
    Service responsible for routing sleep-related subcommands
    to their respective handlers.
    """

    def __init__(self):
        logger.debug("Initializing SleepService")

    async def run(self, subcommand: str) -> None:
        """
        Dispatch sleep subcommands.

        Parameters
        ----------
        subcommand : str
            The sleep subcommand to execute (e.g. 'summary').
        """
        logger.info(f"🛌 SleepService received subcommand: {subcommand}")

        sleep_context: SleepContext = SleepContextBuilder().build()

        if subcommand == "summary":
            service = SleepSummaryService()
            await service.run(sleep_context)

        else:
            logger.error(f"❌ Unknown sleep subcommand: {subcommand}")
            raise ValueError("Unsupported sleep subcommand. Valid option: 'summary'.")
