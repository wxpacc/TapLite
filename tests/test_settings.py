from pathlib import Path

from taplite.clicker import ClickPoint
from taplite.settings import Settings, load_settings, save_settings


def test_load_defaults_when_file_missing(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.json")

    assert settings.interval_ms == 100
    assert settings.toggle_hotkey == "F6"
    assert settings.stop_hotkey == "F8"
    assert settings.click_mode == "single_point"
    assert settings.click_points == []


def test_save_creates_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "data" / "settings.json"

    save_settings(Settings(interval_ms=42), path)

    assert path.exists()
    assert load_settings(path).interval_ms == 42


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
          "run_limit_seconds": -1
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.interval_ms == 100
    assert loaded.repeat_count == 100
    assert loaded.fixed_x == 0
    assert loaded.fixed_y == 0
    assert loaded.random_interval_min_ms == 100
    assert loaded.random_interval_max_ms == 150
    assert loaded.random_offset_px == 0
    assert loaded.start_delay_seconds == 0
    assert loaded.run_limit_seconds == 0


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

    assert loaded.click_points == [ClickPoint(1, 2, 3)]


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
