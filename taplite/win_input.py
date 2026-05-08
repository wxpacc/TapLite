from __future__ import annotations

from ctypes import Structure, Union, WinDLL, byref, c_int, c_long, c_ulong, c_void_p, sizeof
import ctypes
import sys
from typing import Literal


MouseButton = Literal["left", "right", "middle"]


if sys.platform == "win32":
    user32 = WinDLL("user32", use_last_error=True)
    shell32 = WinDLL("shell32", use_last_error=True)
else:
    user32 = None
    shell32 = None


INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


class MOUSEINPUT(Structure):
    _fields_ = [
        ("dx", c_long),
        ("dy", c_long),
        ("mouseData", c_ulong),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", c_void_p),
    ]


class INPUT_UNION(Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(Structure):
    _fields_ = [("type", c_ulong), ("union", INPUT_UNION)]


BUTTON_FLAGS: dict[MouseButton, tuple[int, int]] = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


def ensure_windows() -> None:
    if sys.platform != "win32" or user32 is None:
        raise RuntimeError("TapLite only supports Windows input APIs.")


def get_cursor_position() -> tuple[int, int]:
    ensure_windows()
    point = POINT()
    if not user32.GetCursorPos(byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(point.x), int(point.y)


def set_cursor_position(x: int, y: int) -> None:
    ensure_windows()
    if not user32.SetCursorPos(int(x), int(y)):
        raise ctypes.WinError(ctypes.get_last_error())


def send_click(button: MouseButton = "left", clicks: int = 1) -> None:
    ensure_windows()
    if button not in BUTTON_FLAGS:
        raise ValueError(f"Unsupported mouse button: {button}")
    if clicks < 1:
        raise ValueError("clicks must be greater than zero")

    down_flag, up_flag = BUTTON_FLAGS[button]
    events: list[INPUT] = []
    for _ in range(clicks):
        events.append(INPUT(INPUT_MOUSE, INPUT_UNION(mi=MOUSEINPUT(0, 0, 0, down_flag, 0, None))))
        events.append(INPUT(INPUT_MOUSE, INPUT_UNION(mi=MOUSEINPUT(0, 0, 0, up_flag, 0, None))))

    array_type = INPUT * len(events)
    sent = user32.SendInput(len(events), array_type(*events), sizeof(INPUT))
    if sent != len(events):
        raise ctypes.WinError(ctypes.get_last_error())


def is_running_as_admin() -> bool:
    if sys.platform != "win32" or shell32 is None:
        return False
    try:
        return bool(shell32.IsUserAnAdmin())
    except OSError:
        return False
