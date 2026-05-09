from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
import sys
from typing import Any

from .clicker import ClickPoint


APP_NAME = "TapLite"
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"
LEGACY_SETTINGS_FILE = PROJECT_ROOT / "settings.json"

MOUSE_BUTTONS = {"left", "right", "middle"}
CLICK_TYPES = {"single", "double"}
REPEAT_MODES = {"infinite", "count"}
POSITION_MODES = {"current", "fixed"}
CLICK_MODES = {"single_point", "multi_point"}
START_DELAYS = {0, 1, 3, 5}


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
    click_mode: str = "single_point"
    click_points: list[ClickPoint] | None = None
    random_interval_enabled: bool = False
    random_interval_min_ms: int = 100
    random_interval_max_ms: int = 150
    random_offset_enabled: bool = False
    random_offset_px: int = 0
    start_delay_seconds: int = 0
    run_limit_seconds: int = 0
    show_running_overlay: bool = True
    presets: dict[str, dict[str, Any]] | None = None


def default_settings() -> Settings:
    return Settings(click_points=[], presets={})


def load_settings(path: Path | None = None) -> Settings:
    path = path or SETTINGS_FILE
    source_path = path
    if path == SETTINGS_FILE and not source_path.exists() and LEGACY_SETTINGS_FILE.exists():
        source_path = LEGACY_SETTINGS_FILE

    if not source_path.exists():
        return default_settings()

    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_settings()

    if not isinstance(data, dict):
        return default_settings()

    settings = sanitize_settings(data)
    if source_path == LEGACY_SETTINGS_FILE and path == SETTINGS_FILE:
        _migrate_legacy_settings(settings)
    return settings


def save_settings(settings: Settings, path: Path | None = None) -> None:
    path = path or SETTINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _migrate_legacy_settings(settings: Settings) -> None:
    try:
        save_settings(settings, SETTINGS_FILE)
        LEGACY_SETTINGS_FILE.unlink(missing_ok=True)
    except OSError:
        return


def sanitize_settings(data: dict[str, Any]) -> Settings:
    defaults = default_settings()
    valid_names = {field.name for field in fields(Settings)}
    filtered = {key: value for key, value in data.items() if key in valid_names}

    min_interval = _positive_int(
        filtered.get("random_interval_min_ms"),
        defaults.random_interval_min_ms,
    )
    max_interval = _positive_int(
        filtered.get("random_interval_max_ms"),
        defaults.random_interval_max_ms,
    )
    if min_interval > max_interval:
        min_interval = defaults.random_interval_min_ms
        max_interval = defaults.random_interval_max_ms

    return Settings(
        interval_ms=_positive_int(filtered.get("interval_ms"), defaults.interval_ms),
        mouse_button=_choice(filtered.get("mouse_button"), MOUSE_BUTTONS, defaults.mouse_button),
        click_type=_choice(filtered.get("click_type"), CLICK_TYPES, defaults.click_type),
        repeat_mode=_choice(filtered.get("repeat_mode"), REPEAT_MODES, defaults.repeat_mode),
        repeat_count=_positive_int(filtered.get("repeat_count"), defaults.repeat_count),
        position_mode=_choice(filtered.get("position_mode"), POSITION_MODES, defaults.position_mode),
        fixed_x=_non_negative_int(filtered.get("fixed_x"), defaults.fixed_x),
        fixed_y=_non_negative_int(filtered.get("fixed_y"), defaults.fixed_y),
        toggle_hotkey=_non_empty_string(filtered.get("toggle_hotkey"), defaults.toggle_hotkey),
        stop_hotkey=_non_empty_string(filtered.get("stop_hotkey"), defaults.stop_hotkey),
        click_mode=_choice(filtered.get("click_mode"), CLICK_MODES, defaults.click_mode),
        click_points=_click_points(filtered.get("click_points")),
        random_interval_enabled=_bool(filtered.get("random_interval_enabled"), defaults.random_interval_enabled),
        random_interval_min_ms=min_interval,
        random_interval_max_ms=max_interval,
        random_offset_enabled=_bool(filtered.get("random_offset_enabled"), defaults.random_offset_enabled),
        random_offset_px=_non_negative_int(filtered.get("random_offset_px"), defaults.random_offset_px),
        start_delay_seconds=_start_delay(filtered.get("start_delay_seconds"), defaults.start_delay_seconds),
        run_limit_seconds=_non_negative_int(filtered.get("run_limit_seconds"), defaults.run_limit_seconds),
        show_running_overlay=_bool(filtered.get("show_running_overlay"), defaults.show_running_overlay),
        presets=_presets(filtered.get("presets")),
    )


def settings_to_preset(settings: Settings) -> dict[str, Any]:
    data = asdict(settings)
    data.pop("presets", None)
    return data


def _choice(value: Any, allowed: set[str], default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def _positive_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and value > 0 else default


def _non_negative_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and value >= 0 else default


def _non_empty_string(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value.strip() else default


def _bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _start_delay(value: Any, default: int) -> int:
    return value if isinstance(value, int) and value in START_DELAYS else default


def _click_points(value: Any) -> list[ClickPoint]:
    if not isinstance(value, list):
        return []

    points: list[ClickPoint] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        x = item.get("x")
        y = item.get("y")
        wait_ms = item.get("wait_ms", 0)
        if not isinstance(x, int) or not isinstance(y, int):
            continue
        if x < 0 or y < 0:
            continue
        points.append(ClickPoint(x=x, y=y, wait_ms=_non_negative_int(wait_ms, 0)))
    return points


def _presets(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}

    presets: dict[str, dict[str, Any]] = {}
    for name, preset_data in value.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(preset_data, dict):
            continue
        presets[name.strip()] = settings_to_preset(sanitize_settings(preset_data))
    return presets
