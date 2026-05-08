from pathlib import Path

from taplite.settings import Settings, load_settings, save_settings


def test_load_defaults_when_file_missing(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.json")

    assert settings.interval_ms == 100
    assert settings.toggle_hotkey == "F6"
    assert settings.stop_hotkey == "F8"


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    original = Settings(interval_ms=25, mouse_button="right", fixed_x=10, fixed_y=20)

    save_settings(original, path)
    loaded = load_settings(path)

    assert loaded == original


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
          "position_mode": "window"
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.mouse_button == "left"
    assert loaded.click_type == "single"
    assert loaded.repeat_mode == "infinite"
    assert loaded.position_mode == "current"


def test_load_resets_invalid_number_values(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        """
        {
          "interval_ms": 0,
          "repeat_count": -1,
          "fixed_x": -10,
          "fixed_y": "20"
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.interval_ms == 100
    assert loaded.repeat_count == 100
    assert loaded.fixed_x == 0
    assert loaded.fixed_y == 0


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
          "unknown": true
        }
        """,
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded == Settings(
        interval_ms=25,
        mouse_button="right",
        click_type="double",
        repeat_mode="count",
        repeat_count=5,
        position_mode="fixed",
        fixed_x=10,
        fixed_y=20,
    )
