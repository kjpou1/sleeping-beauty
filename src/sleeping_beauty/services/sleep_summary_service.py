from pathlib import Path

from sleeping_beauty.clients.oura_api_client import OuraApiClient
from sleeping_beauty.config.config import Config
from sleeping_beauty.logsys.logger_manager import LoggerManager
from sleeping_beauty.models.sleep_context import SleepContext
from sleeping_beauty.oura.auth.domain.auth_preflight_result import AuthPreflightReport
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
        # Placeholder for future implementation
        # -------------------------------------------------
        logger.debug("Sleep summary execution scaffold reached.")
        logger.info("Sleep summary logic not yet implemented.")
