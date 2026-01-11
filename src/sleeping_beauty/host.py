import asyncio
import sys

from sleeping_beauty.config.config import Config
from sleeping_beauty.logsys.logger_manager import LoggerManager
from sleeping_beauty.models.command_line_args import CommandLineArgs
from sleeping_beauty.services.auth_service import AuthService
from sleeping_beauty.services.sleep_service import SleepService

logger = LoggerManager.get_logger(__name__)


class Host:
    """
    Host class to manage the execution of the main application.

    This class handles initialization with command-line arguments and
    configuration, and runs the main asynchronous functionality.
    """

    def __init__(self, args: CommandLineArgs):
        self.args = args

    # -----------------------------------------------------
    def run(self):
        return asyncio.run(self.run_async())

    async def run_async(self):
        """
        Dispatch the correct pipeline based on the CLI subcommand.
        """
        try:
            logger.info("🚀 Starting host operations.")

            if self.args.command == "auth":
                await self.run_auth()
            elif self.args.command == "sleep":
                await self.run_sleep()
            else:
                logger.error(f"❌ Unknown subcommand: {self.args.command}")
                raise ValueError("Please specify a valid subcommand: 'auth', 'sleep'.")

        finally:
            logger.info("✅ Shutting down host gracefully.")

    # -----------------------------------------------------
    async def run_auth(self):
        """
        Runs the Auth service.
        """
        auth_service = AuthService()
        auth_service.run(self.args.subcommand)

    # -----------------------------------------------------
    async def run_sleep(self):
        """
        Dispatch sleep-related subcommands.
        """
        if self.args.subcommand == "summary":
            service = SleepService()
            await service.run(self.args.subcommand)

        else:
            logger.error(f"❌ Unknown sleep subcommand: {self.args.subcommand}")
            raise ValueError("Please specify a valid sleep subcommand: 'summary'.")
