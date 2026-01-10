import os


def _parse_env_bool(key: str, default: bool = True) -> bool:
    """Parse environment variable as a boolean."""
    val = os.getenv(key)
    if val is None:
        return default

    val = val.strip().lower()
    if val in {"true", "1", "yes", "on"}:
        return True
    if val in {"false", "0", "no", "off"}:
        return False

    raise ValueError(f"Invalid boolean value for {key}: {val}")
