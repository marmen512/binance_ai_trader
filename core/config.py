from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.exceptions import ConfigError


@dataclass(frozen=True)
class AppConfig:
    env: str
    log_level: str
    log_dir: Path
    log_file: str
    json_log_file: str
    console_log_format: str
    enable_json_file_log: bool


def _require_str(obj: dict[str, Any], key: str) -> str:
    val = obj.get(key)
    if not isinstance(val, str) or not val.strip():
        raise ConfigError(f"Invalid or missing config value: {key}")
    return val


def _get_str(obj: dict[str, Any], key: str, default: str) -> str:
    val = obj.get(key, default)
    if val is None:
        return default
    if not isinstance(val, str):
        raise ConfigError(f"Invalid config value (expected string): {key}")
    return val


def _get_bool(obj: dict[str, Any], key: str, default: bool) -> bool:
    val = obj.get(key, default)
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    raise ConfigError(f"Invalid config value (expected bool): {key}")


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as e:
        raise ConfigError(
            "PyYAML is not installed. Install it (e.g. `pip install PyYAML`) to use YAML config."
        ) from e

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise ConfigError(f"Failed to parse YAML config: {path}") from e

    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a YAML mapping")

    app = raw.get("app")
    if not isinstance(app, dict):
        raise ConfigError("Missing 'app' section in config")

    env = _require_str(app, "env")
    log_level = _require_str(app, "log_level")

    log_dir_raw = _require_str(app, "log_dir")
    log_dir = Path(log_dir_raw).expanduser()

    log_file = _require_str(app, "log_file")

    json_log_file = _get_str(app, "json_log_file", default="app.json.log")
    console_log_format = _get_str(app, "console_log_format", default="text")
    enable_json_file_log = _get_bool(app, "enable_json_file_log", default=True)

    return AppConfig(
        env=env,
        log_level=log_level,
        log_dir=log_dir,
        log_file=log_file,
        json_log_file=json_log_file,
        console_log_format=console_log_format,
        enable_json_file_log=enable_json_file_log,
    )
