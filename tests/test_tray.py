from pathlib import Path

from taplite.tray import resolve_app_icon_path


def test_resolve_app_icon_path_prefers_assets_directory(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    expected = assets / "TapLite.ico"
    expected.write_bytes(b"ico")

    assert resolve_app_icon_path(tmp_path) == expected


def test_resolve_app_icon_path_falls_back_to_releases_directory(tmp_path: Path) -> None:
    releases = tmp_path / "releases"
    releases.mkdir()
    expected = releases / "TapLite.ico"
    expected.write_bytes(b"ico")

    assert resolve_app_icon_path(tmp_path) == expected


def test_resolve_app_icon_path_falls_back_to_project_root(tmp_path: Path) -> None:
    expected = tmp_path / "TapLite.ico"
    expected.write_bytes(b"ico")

    assert resolve_app_icon_path(tmp_path) == expected


def test_resolve_app_icon_path_returns_none_when_missing(tmp_path: Path) -> None:
    assert resolve_app_icon_path(tmp_path) is None
