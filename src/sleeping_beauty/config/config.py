import json
import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from sleeping_beauty.models.singleton import SingletonMeta
from sleeping_beauty.utils.arg_utils import was_explicit as _was_explicit
from sleeping_beauty.utils.env_utils import _parse_env_bool
from sleeping_beauty.utils.path_utils import ensure_all_dirs_exist, get_project_root


class Config(metaclass=SingletonMeta):
    _is_initialized = False
    ALLOWED_CATEGORICAL_ENCODINGS = ["ohe", "label"]

    def __init__(self):
        if Config._is_initialized:
            return

        load_dotenv()

        self._log_level = os.getenv("LOG_LEVEL", "INFO")
        self._debug = os.getenv("DEBUG", False)
        self.PROJECT_ROOT = get_project_root()

        # === Artifacts (auto-created if missing) ===
        base_dir_env = os.getenv("BASE_DIR", "artifacts")
        self.BASE_DIR = (
            base_dir_env
            if os.path.isabs(base_dir_env)
            else os.path.join(self.PROJECT_ROOT, base_dir_env)
        )

        self.LOG_DIR = os.path.join(self.BASE_DIR, "logs")

        # === Auth / Oura ===
        self._oura_client_id = None
        self._oura_client_secret = None
        self._oura_token_path = Path("~/.sleeping_beauty/oura_token.json").expanduser()

        Config._is_initialized = True

    def _ensure_directories_exist(self):
        ensure_all_dirs_exist(
            [
                self.LOG_DIR,
            ]
        )

    def apply_cli_overrides(self, args):
        if _was_explicit(args, "debug"):
            print(f"[Config] Overriding 'debug' from CLI: {args.debug}")
            self.debug = args.debug

    def load_from_yaml(self, path: str):
        """
        Override config values from a YAML config file.
        Logs changes to config values.
        """
        if not os.path.exists(path):
            print(f"[Config] YAML config file not found: {path}")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        print(f"[Config] Loaded YAML config: {path}")

        # --- Logging level (explicit policy) ---
        logging_cfg = data.get("logging", {})
        if "level" in logging_cfg:
            self.log_level = logging_cfg["level"]

        # --- Debug flag (convenience) ---
        if "debug" in data:
            self.debug = data["debug"]

        # --- Auth / Oura ---
        auth_cfg = data.get("auth", {})
        oura_cfg = auth_cfg.get("oura", {})

        if "client_id" in oura_cfg:
            self._oura_client_id = oura_cfg["client_id"]

        if "client_secret" in oura_cfg:
            self._oura_client_secret = oura_cfg["client_secret"]

        if "token_path" in oura_cfg:
            self.oura_token_path = oura_cfg["token_path"]

    @property
    def config_path(self):
        return self._config_path

    @config_path.setter
    def config_path(self, value):
        if not isinstance(value, str):
            raise ValueError("config_path must be a string.")
        self._config_path = value

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError("debug must be a boolean")

        if self._debug != value:
            print(f"[Config] Setting 'debug': {self._debug} → {value}")

        self._debug = value

        # Optional convenience behavior
        if value:
            self._log_level = "DEBUG"

    @property
    def log_level(self) -> str:
        return self._log_level

    @log_level.setter
    def log_level(self, value: str):
        if not isinstance(value, str):
            raise ValueError("log_level must be a string")

        value = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if value not in allowed:
            raise ValueError(f"Invalid log level: {value}")

        if self._log_level != value:
            print(f"[Config] Setting 'log_level': {self._log_level} → {value}")

        self._log_level = value

    @property
    def oura_client_id(self) -> str:
        """
        Oura OAuth client ID.

        Precedence:
          1. YAML config
          2. Environment variable OURA_CLIENT_ID
        """
        return self._oura_client_id or os.getenv("OURA_CLIENT_ID", "")

    @property
    def oura_client_secret(self) -> str:
        """
        Oura OAuth client secret.

        Precedence:
          1. YAML config
          2. Environment variable OURA_CLIENT_SECRET
        """
        return self._oura_client_secret or os.getenv("OURA_CLIENT_SECRET", "")

    @property
    def oura_token_path(self) -> Path:
        """
        Filesystem path where Oura OAuth tokens are stored.
        """
        return self._oura_token_path

    @oura_token_path.setter
    def oura_token_path(self, value: str | Path):
        if not value:
            raise ValueError("oura_token_path cannot be empty")

        path = Path(value).expanduser()
        self._oura_token_path = path

    def print_config_info(self):
        print("=" * 50)
        print("📂 Configuration")
        print("-" * 50)
        print("-" * 50)
        print("🔐 Auth / Oura")
        print("-" * 50)
        print(f"{'Token path:':25} {self.oura_token_path}")
        print(f"{'Client ID set:':25} {bool(self.oura_client_id)}")
        print(f"{'Client Secret set:':25} {bool(self.oura_client_secret)}")

        # print(f"{'Datasets/raw dir:':25} {self.DATASETS_RAW_DIR}")
        # print(f"{'Datasets/processed dir:':25} {self.DATASETS_PROCESSED_DIR}")
        # print(f"{'Artifacts/raw dir:':25} {self.RAW_DATA_DIR}")
        # print(f"{'Artifacts/processed dir:':25} {self.PROCESSED_DATA_DIR}")
        # print(f"{'Features dir:':25} {self.FEATURES_DATA_DIR}")
        # print("-" * 50)
        # print("📄 Ingestion Data Sources")
        # print("-" * 50)
        # print(f"{'Data files dir:':25} {self.DATA_FILES_DIR}")
        # print(f"{'Symbol data CSV:':25} {self.symbol_data_path}")
        # print("=" * 50)
        # print("🤖 Model Paths")
        # print("-" * 50)
        # print(f"{'Mode:':25} {self.mode}")
        # print(f"{'Model config:':25} {self.model_config_path}")
        # # print(f"{'Model file:':25} {self.model_file_path}")
        # print(f"{'Session Encoder:':25} {self.session_encoder_model_path}")
        # print("-" * 50)
        # print("⚙️  Flags")
        # print("-" * 50)
        # print(f"{'Deterministic:':25} {self.deterministic}")
        # print(f"{'Save report:':25} {self.save_report}")

    def _resolve_path(self, val: Optional[str]) -> Optional[str]:
        if not val:
            return None
        if os.path.isabs(val):
            return val
        # Tier 1: try resolving relative to BASE_DIR
        base_resolved = os.path.join(self.BASE_DIR, val)
        if os.path.exists(base_resolved):
            print(f"[Config] Resolved (BASE_DIR): {val} → {base_resolved}")
            return base_resolved
        # Tier 2: try resolving relative to PROJECT_ROOT
        root_resolved = os.path.join(self.PROJECT_ROOT, val)
        if os.path.exists(root_resolved):
            print(f"[Config] Resolved (PROJECT_ROOT): {val} → {root_resolved}")
            return root_resolved
        # Fallback: assume BASE_DIR anyway
        fallback = base_resolved
        print(f"[Config] Resolved (fallback to BASE_DIR): {val} → {fallback}")
        return fallback

    @classmethod
    def initialize(cls):
        if not cls._is_initialized:
            cls()

    @classmethod
    def is_initialized(cls):
        return cls._is_initialized

    @classmethod
    def reset(cls):
        cls._is_initialized = False
        cls._instances = {}
