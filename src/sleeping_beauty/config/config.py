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
        self._oura_scopes: list[str] = ["daily", "personal"]  # safe default

        self._sleep_view: Optional[str] = None
        self._start_date: Optional[str] = None
        self._end_date: Optional[str] = None

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

        if _was_explicit(args, "scopes"):
            print(f"[Config] Overriding Oura scopes from CLI: {args.scopes}")
            self._oura_scopes = args.scopes

        if _was_explicit(args, "redirect_uri"):
            print(
                f"[Config] Overriding Oura redirect_uri from CLI: {args.redirect_uri}"
            )
            self._oura_redirect_uri = args.redirect_uri

        # --------------------------------------------
        # Sleep overrides
        # --------------------------------------------
        if _was_explicit(args, "view"):
            print(f"[Config] Overriding sleep.view from CLI: {args.view}")
            self.sleep_view = args.view

        if _was_explicit(args, "start_date"):
            print(f"[Config] Overriding sleep.start_date from CLI: {args.start_date}")
            self.start_date = args.start_date

        if _was_explicit(args, "end_date"):
            print(f"[Config] Overriding sleep.end_date from CLI: {args.end_date}")
            self.end_date = args.end_date

    def _load_sleep_section(self, data: dict) -> None:
        if not data:
            return

        sleep_cfg = data.get("sleep", {})

        if not sleep_cfg:
            return

        if "view" in sleep_cfg:
            print(
                f"[Config] Overriding 'view': "
                f"{self._sleep_view} → {sleep_cfg.get("view")}"
            )
            self.sleep_view = sleep_cfg.get("view")

        if "start_date" in sleep_cfg:
            print(
                f"[Config] Overriding 'sleep.start_date': "
                f"{self._start_date} → {sleep_cfg.get('start_date')}"
            )
            self.start_date = sleep_cfg.get("start_date")

        if "end_date" in sleep_cfg:
            print(
                f"[Config] Overriding 'sleep.end_date': "
                f"{self._end_date} → {sleep_cfg.get('end_date')}"
            )
            self.end_date = sleep_cfg.get("end_date")

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

        if "scopes" in oura_cfg:
            scopes = oura_cfg["scopes"]
            if not isinstance(scopes, list) or not all(
                isinstance(s, str) for s in scopes
            ):
                raise ValueError("auth.oura.scopes must be a list of strings")
            self._oura_scopes = scopes

        if "redirect_uri" in oura_cfg:
            uri = oura_cfg["redirect_uri"]
            if uri is not None and not isinstance(uri, str):
                raise ValueError("auth.oura.redirect_uri must be a string or null")
            self._oura_redirect_uri = uri

        self._load_sleep_section(data)

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

    @property
    def oura_scopes(self) -> set[str]:
        """
        Oura OAuth scopes (human-facing, e.g. {'daily', 'personal'}).

        Precedence:
        1. YAML config
        2. CLI override
        3. Defaults
        """
        return set(self._oura_scopes)

    @property
    def oura_redirect_uri(self) -> str:
        """
        Oura OAuth redirect URI.

        Precedence:
        1. YAML config
        2. Environment variable OURA_REDIRECT_URI
        3. Default localhost callback
        """
        return (
            self._oura_redirect_uri
            or os.getenv("OURA_REDIRECT_URI")
            or "http://localhost:8400/callback"
        )

    # --------------------------------------------
    # Sleep: view
    # --------------------------------------------
    @property
    def sleep_view(self) -> Optional[str]:
        """
        Calendar-based sleep view.
        Expected values: today, yesterday, week, month.
        """
        return self._sleep_view

    @sleep_view.setter
    def sleep_view(self, value: Optional[str]) -> None:
        """
        Set sleep view.

        No validation here; validation is handled
        by the sleep service layer.
        """
        self._sleep_view = value

    # --------------------------------------------
    # start_date
    # --------------------------------------------
    @property
    def start_date(self) -> Optional[str]:
        """
        start date (YYYY-MM-DD).
        """
        return self._start_date

    @start_date.setter
    def start_date(self, value: Optional[str]) -> None:
        self._start_date = value

    # --------------------------------------------
    # end_date
    # --------------------------------------------
    @property
    def end_date(self) -> Optional[str]:
        """
        Sleep summary end date (YYYY-MM-DD).
        """
        return self._end_date

    @end_date.setter
    def end_date(self, value: Optional[str]) -> None:
        self._end_date = value

    def print_config_info(self):
        print("=" * 50)
        print("📂 Configuration")
        print("-" * 50)
        print(f"{'Configuration file:':25} {self.config_path}")
        print("-" * 50)
        print("🔐 Auth / Oura")
        print("-" * 50)
        print(f"{'Token path:':25} {self.oura_token_path}")
        print(f"{'Client ID set:':25} {bool(self.oura_client_id)}")
        print(f"{'Client Secret set:':25} {bool(self.oura_client_secret)}")
        print(f"{'Redirect URI:':25} {self.oura_redirect_uri}")
        print(f"{'Scopes:':25} {sorted(self.oura_scopes)}")

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
