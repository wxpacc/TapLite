from __future__ import annotations

from ctypes import WinDLL, c_void_p
import ctypes
import sys


ERROR_ALREADY_EXISTS = 183


if sys.platform == "win32":
    kernel32 = WinDLL("kernel32", use_last_error=True)
    user32 = WinDLL("user32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = c_void_p
    kernel32.ReleaseMutex.argtypes = [c_void_p]
    kernel32.ReleaseMutex.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    user32.FindWindowW.restype = c_void_p
    user32.ShowWindow.argtypes = [c_void_p, ctypes.c_int]
    user32.ShowWindow.restype = ctypes.c_int
    user32.SetForegroundWindow.argtypes = [c_void_p]
    user32.SetForegroundWindow.restype = ctypes.c_int
else:
    kernel32 = None
    user32 = None


SW_SHOW = 5
SW_RESTORE = 9


class SingleInstance:
    def __init__(self, name: str) -> None:
        self._name = name
        self._handle: c_void_p | None = None
        self.already_running = False

    def acquire(self) -> bool:
        if sys.platform != "win32" or kernel32 is None:
            return True
        handle = kernel32.CreateMutexW(None, 0, self._name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self._handle = c_void_p(handle)
        self.already_running = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
        return not self.already_running

    def release(self) -> None:
        if self._handle is None or kernel32 is None:
            return
        kernel32.CloseHandle(self._handle)
        self._handle = None


def activate_existing_window(window_title: str) -> bool:
    if sys.platform != "win32" or user32 is None:
        return False
    hwnd = user32.FindWindowW(None, window_title)
    if not hwnd:
        return False
    user32.ShowWindow(hwnd, SW_SHOW)
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    return True
