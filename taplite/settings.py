from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
from typing import Any


APP_NAME = "TapLite"
SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"


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

    valid_names = {field.name for field in fields(Settings)}
    filtered: dict[str, Any] = {
        key: value for key, value in data.items() if key in valid_names
    }

    try:
        return Settings(**filtered)
    except TypeError:
        return default_settings()


def save_settings(settings: Settings, path: Path = SETTINGS_FILE) -> None:
    path.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
