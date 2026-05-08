import pytest

from taplite.hotkeys import hotkey_to_vk, normalize_hotkey


def test_normalize_hotkey() -> None:
    assert normalize_hotkey(" f6 ") == "F6"


def test_hotkey_to_vk_supports_defaults() -> None:
    assert hotkey_to_vk("F6") == 0x75
    assert hotkey_to_vk("F8") == 0x77


def test_hotkey_to_vk_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        hotkey_to_vk("Ctrl+F6")
