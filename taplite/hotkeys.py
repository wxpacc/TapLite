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

    def start(self, toggle_hotkey: str, stop_hotkey: str) -> None:
        if sys.platform != "win32" or user32 is None:
            return
        self.stop()
        self._stop_event.clear()
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._message_loop,
            args=(toggle_hotkey, stop_hotkey),
            name="TapLiteHotkeys",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=1)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread_id and user32 is not None:
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=1)
        self._thread = None
        self._thread_id = 0

    def drain(self) -> list[str]:
        actions: list[str] = []
        while True:
            try:
                actions.append(self._events.get_nowait())
            except queue.Empty:
                return actions

    def _message_loop(self, toggle_hotkey: str, stop_hotkey: str) -> None:
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        hotkeys = {
            1: (normalize_hotkey(toggle_hotkey), HOTKEY_ACTION_TOGGLE),
            2: (normalize_hotkey(stop_hotkey), HOTKEY_ACTION_STOP),
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
                        self._callback(action)
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageW(byref(msg))
        except Exception as exc:
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
