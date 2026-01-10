"""
Launch the asynchronous system.

This script initializes the application by parsing command-line arguments,
creating a Host instance, and launching its main logic asynchronously.
"""

import asyncio
import logging

from sleeping_beauty.config.config import Config
from sleeping_beauty.logging.logger_manager import LoggerManager
from sleeping_beauty.runtime.command_line import CommandLine

# Phase 1: bootstrap logging ASAP
LoggerManager.bootstrap()
log = LoggerManager.get_logger(__name__)

from sleeping_beauty.host import Host


async def launch_async():
    """
    Main asynchronous launch point.

    Parses command-line arguments, initializes the Host instance, and
    launches the main logic asynchronously.
    """
    try:
        args = CommandLine.parse_arguments()

        log.info(
            "Launching host with arguments",
            extra={"args": args},
        )

        LoggerManager.initialize_from_args(args, log_dir=Config().LOG_DIR)
        # if args.debug:
        #     LoggerManager.set_log_level(logging.DEBUG)

        # LoggerManager.configure_file_logging(Config().LOG_DIR)

        # Create an instance of Host with parsed arguments
        instance = Host(args)

        # Launch the async main function with the parsed arguments
        await instance.run_async()
    except ValueError as e:
        log.error(f"ValueError: {e}")
    except KeyboardInterrupt:
        log.info("Execution interrupted by user.")
    except Exception as e:
        log.error(f"Unexpected error occurred: {e}")


def launch():
    asyncio.run(launch_async())


if __name__ == "__main__":
    asyncio.run(launch_async())
