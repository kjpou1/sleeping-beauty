import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger


class LoggerManager:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_JSON = os.getenv("LOG_JSON", "false").lower() == "true"

    _bootstrapped = False
    _console_sink_id: Optional[int] = None
    _file_sink_id: Optional[int] = None
    _file_log_path: Optional[Path] = None

    # ---------- Formatter ----------

    @classmethod
    def _formatter(cls, record):
        try:
            relpath = Path(record["file"].path).relative_to(Path.cwd())
        except ValueError:
            relpath = record["file"].path

        time = record["time"].strftime("%Y-%m-%d %H:%M:%S")
        level = record["level"].name
        path = f"{relpath}:{record['line']}"
        message = record["message"]

        if cls.LOG_JSON:
            import json

            return (
                json.dumps(
                    {
                        "time": time,
                        "level": level,
                        "path": path,
                        "message": message,
                    }
                )
                + "\n"
            )

        return (
            f"<green>[ {time} ]</green> "
            f"<level>{level}</level> "
            f"<cyan>[{path}]</cyan> - {message}\n"
        )

    # ---------- Phase 1: bootstrap ----------

    @classmethod
    def bootstrap(cls):
        if cls._bootstrapped:
            return

        logger.remove()

        cls._console_sink_id = logger.add(
            sys.stdout,
            level=cls.LOG_LEVEL,
            format=cls._formatter,
            enqueue=True,
            colorize=True,
        )

        cls._bootstrapped = True

    # ---------- Phase 2: file logging ----------

    @classmethod
    def configure_file_logging(cls, log_dir: str):
        if not cls._bootstrapped:
            raise RuntimeError(
                "LoggerManager.bootstrap() must be called before configure_file_logging()"
            )

        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        if cls._file_sink_id is not None:
            logger.remove(cls._file_sink_id)

        cls._file_log_path = log_dir / f"{datetime.now():%m_%d_%Y_%H_%M_%S}.log"

        cls._file_sink_id = logger.add(
            cls._file_log_path,
            level=cls.LOG_LEVEL,
            format=cls._formatter,
            colorize=False,
            rotation="5 MB",
            retention=5,
            enqueue=True,
        )

    # ---------- Logger access ----------

    @classmethod
    def get_logger(cls, name: Optional[str] = None):
        if not cls._bootstrapped:
            raise RuntimeError(
                "LoggerManager.bootstrap() must be called before get_logger()"
            )
        return logger.bind(logger=name) if name else logger

    # ---------- Dynamic config ----------

    @classmethod
    def set_log_level(cls, level: str):
        cls.LOG_LEVEL = level.upper()

        # Recreate console sink
        if cls._console_sink_id is not None:
            logger.remove(cls._console_sink_id)
            cls._console_sink_id = logger.add(
                sys.stdout,
                level=cls.LOG_LEVEL,
                format=cls._formatter,
                enqueue=True,
            )

        # Recreate file sink (if enabled)
        if cls._file_sink_id is not None and cls._file_log_path is not None:
            logger.remove(cls._file_sink_id)
            cls._file_sink_id = logger.add(
                cls._file_log_path,
                level=cls.LOG_LEVEL,
                format=cls._formatter,
                rotation="5 MB",
                retention=5,
                enqueue=True,
            )

    @classmethod
    def initialize_from_args(cls, args, log_dir: str | None = None):
        """
        Apply CLI-driven logging configuration.

        Assumes LoggerManager.bootstrap() has already been called.
        Intended to be called once arguments and config are known.
        """
        if not cls._bootstrapped:
            raise RuntimeError(
                "LoggerManager.bootstrap() must be called before initialize_from_args()"
            )

        if getattr(args, "debug", False):
            cls.set_log_level("DEBUG")
            logger.debug("🔧 Debug logging enabled via CLI flag.")
        else:
            cls.set_log_level(cls.LOG_LEVEL)

        if log_dir:
            cls.configure_file_logging(log_dir)

    @classmethod
    def apply_config(cls, config):
        if not cls._bootstrapped:
            raise RuntimeError("LoggerManager.bootstrap() must be called first")

        cls.set_log_level(config.log_level)

        if hasattr(config, "LOG_DIR"):
            cls.configure_file_logging(config.LOG_DIR)
