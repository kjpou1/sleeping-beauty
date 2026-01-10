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

        # -----------------------------
        # Load config
        # -----------------------------
        config = Config()
        if args.config:
            config.load_from_yaml(args.config)

        # -----------------------------
        # Apply CLI overrides to config
        # -----------------------------
        if getattr(args, "log_level", None):
            config.log_level = args.log_level
        elif getattr(args, "debug", False):
            config.debug = True

        # -----------------------------
        # Phase 2: FINAL logging policy
        # -----------------------------
        LoggerManager.apply_config(config)

        # Load config from YAML if provided
        if args.config:
            config.config_path = args.config
            config.load_from_yaml(args.config)

        # Apply CLI overrides if any
        config.apply_cli_overrides(args)

        log.info("🚀 Launching host with arguments")

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
