import asyncio
import sys

from sleeping_beauty.config.config import Config
from sleeping_beauty.logging.logger_manager import LoggerManager
from sleeping_beauty.models.command_line_args import CommandLineArgs

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

            if self.args.command == "hic-svnt":
                self.run_hic_svnt()
            else:
                logger.error(f"❌ Unknown subcommand: {self.args.command}")
                raise ValueError("Please specify a valid subcommand: 'hic-svnt'.")

        finally:
            logger.info("✅ Shutting down host gracefully.")

    # -----------------------------------------------------
    def run_hic_svnt(self):
        """
        Runs the Hic Svnt.
        """
        logger.exception("Something failed")
        logger.debug("🧭 DEBUG - Hic svnt: entering uncharted operational territory.")
        logger.info("🧭 Hic svnt: entering uncharted operational territory.")
        logger.warning(
            "🧭 WARNING - Hic svnt: entering uncharted operational territory."
        )
        logger.error("🧭 ERROR - Hic svnt: entering uncharted operational territory.")
        logger.critical(
            "🧭 CRITICAL - Hic svnt: entering uncharted operational territory."
        )
