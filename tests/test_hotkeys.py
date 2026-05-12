import pytest

from taplite.hotkeys import hotkey_to_vk, normalize_hotkey, HotkeyManager


def test_normalize_hotkey() -> None:
    assert normalize_hotkey(" f6 ") == "F6"


def test_hotkey_to_vk_supports_defaults() -> None:
    assert hotkey_to_vk("F6") == 0x75
    assert hotkey_to_vk("F8") == 0x77


def test_hotkey_to_vk_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        hotkey_to_vk("Ctrl+F6")


def test_start_returns_none_for_non_windows(monkeypatch) -> None:
    monkeypatch.setattr("taplite.hotkeys.sys.platform", "linux")
    manager = HotkeyManager(lambda _action: None)

    assert manager.start("F6", "F8") is None


def test_start_does_not_stop_existing_hotkeys_when_probe_fails(monkeypatch) -> None:
    manager = HotkeyManager(lambda _action: None)
    stop_calls: list[bool] = []

    monkeypatch.setattr(manager, "_probe_hotkeys_available", lambda _hotkeys: "busy")
    monkeypatch.setattr(manager, "stop", lambda: stop_calls.append(True))

    error = manager.start("F6", "F8")

    assert error == "busy"
    assert stop_calls == []


def test_start_allows_swapping_current_hotkeys_without_probe(monkeypatch) -> None:
    manager = HotkeyManager(lambda _action: None)
    manager._current_hotkeys = ("F6", "F8")

    monkeypatch.setattr("taplite.hotkeys.sys.platform", "win32")
    monkeypatch.setattr("taplite.hotkeys.user32", object())
    monkeypatch.setattr(manager, "_probe_hotkeys_available", lambda _hotkeys: pytest.fail("probe should not run"))
    monkeypatch.setattr(manager, "stop", lambda: None)
    monkeypatch.setattr(manager._ready, "wait", lambda timeout=None: True)

    class FakeThread:
        def __init__(self, **_kwargs) -> None:
            pass

        def start(self) -> None:
            return None

        def is_alive(self) -> bool:
            return False

    monkeypatch.setattr("taplite.hotkeys.threading.Thread", FakeThread)

    error = manager.start("F8", "F6")

    assert error is None
    assert manager._current_hotkeys == ("F8", "F6")
