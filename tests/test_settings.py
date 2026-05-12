from pathlib import Path

from taplite.clicker import ClickPoint
from taplite import settings as settings_module
from taplite.settings import Settings, load_settings, save_settings


def test_load_defaults_when_file_missing(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.json")

    assert settings.interval_ms == 100
    assert settings.toggle_hotkey == "F6"
    assert settings.stop_hotkey == "F8"
    assert settings.click_mode == "single_point"
    assert settings.click_points == []
    assert settings.show_running_overlay is True


def test_save_creates_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "data" / "settings.json"

    save_settings(Settings(interval_ms=42), path)

    assert path.exists()
    assert load_settings(path).interval_ms == 42


def test_load_migrates_legacy_settings_file(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path
    settings_file = project_root / "data" / "settings.json"
    legacy_file = project_root / "settings.json"
    legacy_file.write_text('{"interval_ms": 42}', encoding="utf-8")

    monkeypatch.setattr(settings_module, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(settings_module, "DATA_DIR", project_root / "data")
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(settings_module, "LEGACY_SETTINGS_FILE", legacy_file)

    loaded = load_settings()

    assert loaded.interval_ms == 42
    assert settings_file.exists()
    assert not legacy_file.exists()
    assert load_settings(settings_file).interval_ms == 42


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    original = Settings(
        interval_ms=25,
        mouse_button="right",
        fixed_x=10,
        fixed_y=20,
        click_mode="multi_point",
        click_points=[ClickPoint(1, 2, 3)],
        random_interval_enabled=True,
        random_interval_min_ms=20,
        random_interval_max_ms=30,
        random_offset_enabled=True,
        random_offset_px=2,
        start_delay_seconds=3,
        run_limit_seconds=60,
        show_running_overlay=False,
        presets={"test": {"interval_ms": 50}},
    )

    save_settings(original, path)
    loaded = load_settings(path)

    assert loaded.interval_ms == original.interval_ms
    assert loaded.mouse_button == original.mouse_button
    assert loaded.click_mode == original.click_mode
    assert loaded.click_points == original.click_points
    assert loaded.random_interval_enabled is True
    assert loaded.random_interval_min_ms == 20
    assert loaded.random_interval_max_ms == 30
    assert loaded.random_offset_enabled is True
    assert loaded.random_offset_px == 2
    assert loaded.start_delay_seconds == 3
    assert loaded.run_limit_seconds == 60
    assert loaded.show_running_overlay is False
    assert loaded.presets is not None
    assert loaded.presets["test"]["interval_ms"] == 50


def test_load_ignores_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"interval_ms": 33, "unknown": true}', encoding="utf-8")

    loaded = load_settings(path)

    assert loaded.interval_ms == 33


def test_load_resets_invalid_choice_values(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        """
        {
          "mouse_button": "side",
          "click_type": "triple",
          "repeat_mode": "forever",
          "position_mode": "window",
          "click_mode": "macro"
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.mouse_button == "left"
    assert loaded.click_type == "single"
    assert loaded.repeat_mode == "infinite"
    assert loaded.position_mode == "current"
    assert loaded.click_mode == "single_point"


def test_load_resets_invalid_number_values(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        """
        {
          "interval_ms": 0,
          "repeat_count": -1,
          "fixed_x": -10,
          "fixed_y": "20",
          "random_interval_min_ms": 50,
          "random_interval_max_ms": 10,
          "random_offset_px": -2,
          "start_delay_seconds": 2,
          "run_limit_seconds": -1,
          "show_running_overlay": "yes"
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.interval_ms == 100
    assert loaded.repeat_count == 100
    assert loaded.fixed_x == -10
    assert loaded.fixed_y == 0
    assert loaded.random_interval_min_ms == 100
    assert loaded.random_interval_max_ms == 150
    assert loaded.random_offset_px == 0
    assert loaded.start_delay_seconds == 0
    assert loaded.run_limit_seconds == 0
    assert loaded.show_running_overlay is True


def test_load_validates_click_points(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        """
        {
          "click_points": [
            {"x": 1, "y": 2, "wait_ms": 3},
            {"x": -1, "y": 2},
            {"x": 3, "y": "bad"}
          ]
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.click_points == [ClickPoint(1, 2, 3), ClickPoint(-1, 2, 0)]


def test_load_keeps_valid_values_when_unknown_keys_exist(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        """
        {
          "interval_ms": 25,
          "mouse_button": "right",
          "click_type": "double",
          "repeat_mode": "count",
          "repeat_count": 5,
          "position_mode": "fixed",
          "fixed_x": 10,
          "fixed_y": 20,
          "click_mode": "multi_point",
          "click_points": [{"x": 10, "y": 20, "wait_ms": 5}],
          "random_interval_enabled": true,
          "random_interval_min_ms": 25,
          "random_interval_max_ms": 40,
          "random_offset_enabled": true,
          "random_offset_px": 3,
          "start_delay_seconds": 5,
          "run_limit_seconds": 90,
          "show_running_overlay": false,
          "unknown": true
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.interval_ms == 25
    assert loaded.mouse_button == "right"
    assert loaded.click_type == "double"
    assert loaded.repeat_mode == "count"
    assert loaded.repeat_count == 5
    assert loaded.position_mode == "fixed"
    assert loaded.fixed_x == 10
    assert loaded.fixed_y == 20
    assert loaded.click_mode == "multi_point"
    assert loaded.click_points == [ClickPoint(10, 20, 5)]
    assert loaded.random_interval_enabled is True
    assert loaded.random_interval_min_ms == 25
    assert loaded.random_interval_max_ms == 40
    assert loaded.random_offset_enabled is True
    assert loaded.random_offset_px == 3
    assert loaded.start_delay_seconds == 5
    assert loaded.run_limit_seconds == 90
    assert loaded.show_running_overlay is False


def test_presets_keep_running_overlay_flag(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        """
        {
          "presets": {
            "overlay-off": {
              "interval_ms": 25,
              "show_running_overlay": false
            }
          }
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.presets is not None
    assert loaded.presets["overlay-off"]["show_running_overlay"] is False


def test_load_resets_invalid_hotkeys_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        """
        {
          "toggle_hotkey": "Ctrl+F6",
          "stop_hotkey": "BadKey"
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.toggle_hotkey == "F6"
    assert loaded.stop_hotkey == "F8"


def test_load_resets_duplicate_hotkeys_to_distinct_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        """
        {
          "toggle_hotkey": "F6",
          "stop_hotkey": "f6"
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.toggle_hotkey == "F6"
    assert loaded.stop_hotkey == "F8"


def test_load_keeps_negative_click_point_coordinates(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        """
        {
          "click_points": [
            {"x": -100, "y": 220, "wait_ms": 3}
          ]
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.click_points == [ClickPoint(-100, 220, 3)]
