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
