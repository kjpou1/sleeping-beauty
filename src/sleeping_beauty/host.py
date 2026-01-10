import asyncio
import sys

from sleeping_beauty.config.config import Config
from sleeping_beauty.exception import CustomException
from sleeping_beauty.logging.logger_manager import LoggerManager
from sleeping_beauty.models.command_line_args import CommandLineArgs

logging = LoggerManager.get_logger(__name__)


class Host:
    """
    Host class to manage the execution of the main application.

    This class handles initialization with command-line arguments and
    configuration, and runs the main asynchronous functionality.
    """

    def __init__(self, args: CommandLineArgs):
        self.args = args
        self.config = Config()

        # Load config from YAML if provided
        if args.config:
            self.config.config_path = args.config
            self.config.load_from_yaml(args.config)

        # Apply CLI overrides if any
        self.config.apply_cli_overrides(args)

    # -----------------------------------------------------
    def run(self):
        return asyncio.run(self.run_async())

    async def run_async(self):
        """
        Dispatch the correct pipeline based on the CLI subcommand.
        """
        try:
            logging.info("🚀 Starting host operations.")

            if self.args.command == "hic-svnt":
                self.run_hic_svnt()
            else:
                logging.error(f"❌ Unknown subcommand: {self.args.command}")
                raise ValueError("Please specify a valid subcommand: 'hic-svnt'.")

        except CustomException as e:
            logging.error("🔥 A custom error occurred: %s", e)
            raise
        except Exception as e:
            logging.error("💥 An unexpected error occurred: %s", e)
            raise
        finally:
            logging.info("✅ Shutting down host gracefully.")

    # -----------------------------------------------------
    def run_hic_svnt(self):
        """
        Runs the Hic Svnt.
        """
        logging.info("🧭 Hic svnt: entering uncharted operational territory.")
