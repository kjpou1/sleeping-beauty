"""
Launch the asynchronous system.

This script initializes the application by parsing command-line arguments,
creating a Host instance, and launching its main logic asynchronously.
"""

import asyncio

from sleeping_beauty.config.config import Config
from sleeping_beauty.logsys.logger_manager import LoggerManager
from sleeping_beauty.runtime.command_line import CommandLine

# Phase 1: bootstrap logging ASAP
LoggerManager.bootstrap()
log = LoggerManager.get_logger(__name__)

from sleeping_beauty.host import Host


async def launch_async():
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

        log.info("🚀 Launching host with arguments")

        instance = Host(args)
        await instance.run_async()

    except KeyboardInterrupt:
        log.info("Execution interrupted by user.")
    except Exception:
        log.exception("Unexpected error occurred")
        raise


def launch():
    asyncio.run(launch_async())


if __name__ == "__main__":
    asyncio.run(launch_async())
