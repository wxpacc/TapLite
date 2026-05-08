from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
from typing import Any


APP_NAME = "TapLite"
SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"
MOUSE_BUTTONS = {"left", "right", "middle"}
CLICK_TYPES = {"single", "double"}
REPEAT_MODES = {"infinite", "count"}
POSITION_MODES = {"current", "fixed"}


@dataclass(slots=True)
class Settings:
    interval_ms: int = 100
    mouse_button: str = "left"
    click_type: str = "single"
    repeat_mode: str = "infinite"
    repeat_count: int = 100
    position_mode: str = "current"
    fixed_x: int = 0
    fixed_y: int = 0
    toggle_hotkey: str = "F6"
    stop_hotkey: str = "F8"


def default_settings() -> Settings:
    return Settings()


def load_settings(path: Path = SETTINGS_FILE) -> Settings:
    if not path.exists():
        return default_settings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_settings()

    defaults = default_settings()
    valid_names = {field.name for field in fields(Settings)}
    filtered: dict[str, Any] = {
        key: value for key, value in data.items() if key in valid_names
    }

    try:
        settings = Settings(**filtered)
    except TypeError:
        return default_settings()

    return Settings(
        interval_ms=_positive_int(settings.interval_ms, defaults.interval_ms),
        mouse_button=_choice(settings.mouse_button, MOUSE_BUTTONS, defaults.mouse_button),
        click_type=_choice(settings.click_type, CLICK_TYPES, defaults.click_type),
        repeat_mode=_choice(settings.repeat_mode, REPEAT_MODES, defaults.repeat_mode),
        repeat_count=_positive_int(settings.repeat_count, defaults.repeat_count),
        position_mode=_choice(settings.position_mode, POSITION_MODES, defaults.position_mode),
        fixed_x=_non_negative_int(settings.fixed_x, defaults.fixed_x),
        fixed_y=_non_negative_int(settings.fixed_y, defaults.fixed_y),
        toggle_hotkey=_non_empty_string(settings.toggle_hotkey, defaults.toggle_hotkey),
        stop_hotkey=_non_empty_string(settings.stop_hotkey, defaults.stop_hotkey),
    )


def _choice(value: Any, allowed: set[str], default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def _positive_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and value > 0 else default


def _non_negative_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and value >= 0 else default


def _non_empty_string(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value.strip() else default


def save_settings(settings: Settings, path: Path = SETTINGS_FILE) -> None:
    path.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
