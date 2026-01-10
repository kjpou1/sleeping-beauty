from argparse import ArgumentParser

from sleeping_beauty.logging.logger_manager import LoggerManager


class LoggingArgumentParser(ArgumentParser):
    """
    Custom ArgumentParser that logs errors instead of printing to stderr.
    """

    def error(self, message: str):
        logger = LoggerManager.get_logger(__name__)
        logger.error("Argument parsing error: {}", message)
        self.print_help()
        raise SystemExit(2)
