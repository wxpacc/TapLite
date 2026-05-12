from __future__ import annotations

from ctypes import Structure, WinDLL, byref, c_int, c_long, c_uint, c_ulong, c_void_p
import ctypes
import queue
import sys
import threading
from typing import Callable


HOTKEY_ACTION_TOGGLE = "toggle"
HOTKEY_ACTION_STOP = "stop"
WM_HOTKEY = 0x0312


if sys.platform == "win32":
    user32 = WinDLL("user32", use_last_error=True)
else:
    user32 = None


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


class MSG(Structure):
    _fields_ = [
        ("hwnd", c_void_p),
        ("message", c_uint),
        ("wParam", c_void_p),
        ("lParam", c_void_p),
        ("time", c_ulong),
        ("pt", POINT),
    ]


KEY_CODES: dict[str, int] = {
    **{f"F{number}": 0x6F + number for number in range(1, 13)},
    "ESC": 0x1B,
    "SPACE": 0x20,
    "PAUSE": 0x13,
}


class HotkeyManager:
    def __init__(self, callback: Callable[[str], None]) -> None:
        self._callback = callback
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._events: queue.Queue[str] = queue.Queue()
        self._registered_ids: list[int] = []
        self._thread_id = 0
        self._current_hotkeys: tuple[str, str] | None = None
        self._startup_error: str | None = None

    def start(self, toggle_hotkey: str, stop_hotkey: str) -> str | None:
        if sys.platform != "win32" or user32 is None:
            return None
        requested = (normalize_hotkey(toggle_hotkey), normalize_hotkey(stop_hotkey))
        if self._thread and self._thread.is_alive() and requested == self._current_hotkeys:
            return None
        if not self._is_only_remapping_current_hotkeys(requested):
            error = self._probe_hotkeys_available(requested)
            if error is not None:
                return error
        self.stop()
        self._stop_event.clear()
        self._ready.clear()
        self._startup_error = None
        self._thread = threading.Thread(
            target=self._message_loop,
            args=(requested,),
            name="TapLiteHotkeys",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=1)
        if self._startup_error is not None:
            return self._startup_error
        self._current_hotkeys = requested
        return None

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread_id and user32 is not None:
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=1)
        self._thread = None
        self._thread_id = 0
        self._current_hotkeys = None

    def drain(self) -> list[str]:
        actions: list[str] = []
        while True:
            try:
                actions.append(self._events.get_nowait())
            except queue.Empty:
                return actions

    def _is_only_remapping_current_hotkeys(self, requested: tuple[str, str]) -> bool:
        current = self._current_hotkeys
        if current is None or requested == current:
            return False
        return set(requested) == set(current)

    def _probe_hotkeys_available(self, hotkeys: tuple[str, str]) -> str | None:
        assert user32 is not None
        registered_ids: list[int] = []
        try:
            for hotkey_id, hotkey in enumerate(hotkeys, start=101):
                vk = hotkey_to_vk(hotkey)
                if not user32.RegisterHotKey(None, hotkey_id, 0, vk):
                    raise ctypes.WinError(ctypes.get_last_error())
                registered_ids.append(hotkey_id)
            return None
        except Exception as exc:
            return str(exc)
        finally:
            for hotkey_id in registered_ids:
                user32.UnregisterHotKey(None, hotkey_id)

    def _message_loop(self, hotkeys_requested: tuple[str, str]) -> None:
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        hotkeys = {
            1: (hotkeys_requested[0], HOTKEY_ACTION_TOGGLE),
            2: (hotkeys_requested[1], HOTKEY_ACTION_STOP),
        }
        try:
            for hotkey_id, (hotkey, _) in hotkeys.items():
                vk = hotkey_to_vk(hotkey)
                if not user32.RegisterHotKey(None, hotkey_id, 0, vk):
                    raise ctypes.WinError(ctypes.get_last_error())
                self._registered_ids.append(hotkey_id)

            self._ready.set()
            msg = MSG()
            while not self._stop_event.is_set():
                result = user32.GetMessageW(byref(msg), None, 0, 0)
                if result in (0, -1):
                    break
                if msg.message == WM_HOTKEY:
                    action = hotkeys.get(int(msg.wParam), ("", ""))[1]
                    if action:
                        self._events.put(action)
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageW(byref(msg))
        except Exception as exc:
            self._startup_error = str(exc)
            self._events.put(f"error:{exc}")
            self._ready.set()
        finally:
            for hotkey_id in self._registered_ids:
                user32.UnregisterHotKey(None, hotkey_id)
            self._registered_ids.clear()


def normalize_hotkey(value: str) -> str:
    return value.strip().upper()


def hotkey_to_vk(value: str) -> int:
    hotkey = normalize_hotkey(value)
    if hotkey not in KEY_CODES:
        raise ValueError(f"Unsupported hotkey: {value}")
    return KEY_CODES[hotkey]
