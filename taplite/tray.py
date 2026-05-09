from __future__ import annotations

import ctypes
from ctypes import POINTER, Structure, WinDLL, byref, c_int, c_long, c_uint, c_ulong, c_void_p, sizeof
from dataclasses import dataclass
from pathlib import Path
import queue
import sys
import threading

from .settings import PROJECT_ROOT


if sys.platform == "win32":
    user32 = WinDLL("user32", use_last_error=True)
    shell32 = WinDLL("shell32", use_last_error=True)
    kernel32 = WinDLL("kernel32", use_last_error=True)
else:
    user32 = None
    shell32 = None
    kernel32 = None


HWND = c_void_p
HICON = c_void_p
HMENU = c_void_p
HINSTANCE = c_void_p
WPARAM = c_void_p
LPARAM = c_void_p
UINT_PTR = c_void_p
LRESULT = ctypes.c_ssize_t

WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_CLOSE = 0x0010
WM_NULL = 0x0000
WM_APP = 0x8000
WM_TRAYICON = WM_APP + 1
WM_RBUTTONUP = 0x0205
WM_LBUTTONDBLCLK = 0x0203

NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_LEFTALIGN = 0x0000
TPM_BOTTOMALIGN = 0x0020
TPM_RIGHTBUTTON = 0x0002

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040
SM_CXSMICON = 49
SM_CYSMICON = 50
IDI_APPLICATION = 32512
CW_USEDEFAULT = 0x80000000

TRAY_ID = 1
MENU_SHOW = 1001
MENU_TOGGLE = 1002
MENU_EXIT = 1003


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


class MSG(Structure):
    _fields_ = [
        ("hwnd", HWND),
        ("message", c_uint),
        ("wParam", WPARAM),
        ("lParam", LPARAM),
        ("time", c_ulong),
        ("pt", POINT),
    ]


WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, c_uint, WPARAM, LPARAM)


class WNDCLASSW(Structure):
    _fields_ = [
        ("style", c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", c_int),
        ("cbWndExtra", c_int),
        ("hInstance", HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", c_void_p),
        ("hbrBackground", c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
    ]


class NOTIFYICONDATAW(Structure):
    _fields_ = [
        ("cbSize", c_ulong),
        ("hWnd", HWND),
        ("uID", c_uint),
        ("uFlags", c_uint),
        ("uCallbackMessage", c_uint),
        ("hIcon", HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", c_uint),
        ("dwStateMask", c_uint),
        ("szInfo", ctypes.c_wchar * 256),
        ("uTimeoutOrVersion", c_uint),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", c_uint),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", HICON),
    ]


@dataclass(slots=True)
class TrayState:
    window_visible: bool = True
    clicker_running: bool = False


def resolve_app_icon_path(project_root: Path | None = None) -> Path | None:
    root = project_root or PROJECT_ROOT
    candidates = [
        root / "assets" / "TapLite.ico",
        root / "releases" / "TapLite.ico",
        root / "TapLite.ico",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _configure_win32_api() -> None:
    if sys.platform != "win32" or user32 is None or shell32 is None or kernel32 is None:
        return

    user32.DefWindowProcW.argtypes = [HWND, c_uint, WPARAM, LPARAM]
    user32.DefWindowProcW.restype = LRESULT
    user32.RegisterClassW.argtypes = [POINTER(WNDCLASSW)]
    user32.RegisterClassW.restype = ctypes.c_ushort
    user32.CreateWindowExW.argtypes = [
        c_ulong,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        c_ulong,
        c_int,
        c_int,
        c_int,
        c_int,
        HWND,
        HMENU,
        HINSTANCE,
        c_void_p,
    ]
    user32.CreateWindowExW.restype = HWND
    user32.DestroyWindow.argtypes = [HWND]
    user32.DestroyWindow.restype = ctypes.c_int
    user32.PostQuitMessage.argtypes = [c_int]
    user32.PostQuitMessage.restype = None
    user32.GetMessageW.argtypes = [POINTER(MSG), HWND, c_uint, c_uint]
    user32.GetMessageW.restype = c_int
    user32.TranslateMessage.argtypes = [POINTER(MSG)]
    user32.TranslateMessage.restype = ctypes.c_int
    user32.DispatchMessageW.argtypes = [POINTER(MSG)]
    user32.DispatchMessageW.restype = LRESULT
    user32.PostMessageW.argtypes = [HWND, c_uint, WPARAM, LPARAM]
    user32.PostMessageW.restype = ctypes.c_int
    user32.CreatePopupMenu.argtypes = []
    user32.CreatePopupMenu.restype = HMENU
    user32.AppendMenuW.argtypes = [HMENU, c_uint, UINT_PTR, ctypes.c_wchar_p]
    user32.AppendMenuW.restype = ctypes.c_int
    user32.DestroyMenu.argtypes = [HMENU]
    user32.DestroyMenu.restype = ctypes.c_int
    user32.GetCursorPos.argtypes = [POINTER(POINT)]
    user32.GetCursorPos.restype = ctypes.c_int
    user32.SetForegroundWindow.argtypes = [HWND]
    user32.SetForegroundWindow.restype = ctypes.c_int
    user32.TrackPopupMenu.argtypes = [HMENU, c_uint, c_int, c_int, c_int, HWND, c_void_p]
    user32.TrackPopupMenu.restype = ctypes.c_int
    user32.LoadImageW.argtypes = [HINSTANCE, ctypes.c_wchar_p, c_uint, c_int, c_int, c_uint]
    user32.LoadImageW.restype = c_void_p
    user32.LoadIconW.argtypes = [HINSTANCE, c_void_p]
    user32.LoadIconW.restype = HICON
    user32.GetSystemMetrics.argtypes = [c_int]
    user32.GetSystemMetrics.restype = c_int
    user32.DestroyIcon.argtypes = [HICON]
    user32.DestroyIcon.restype = ctypes.c_int

    shell32.Shell_NotifyIconW.argtypes = [c_uint, POINTER(NOTIFYICONDATAW)]
    shell32.Shell_NotifyIconW.restype = ctypes.c_int
    shell32.ExtractIconW.argtypes = [HINSTANCE, ctypes.c_wchar_p, c_uint]
    shell32.ExtractIconW.restype = HICON

    kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel32.GetModuleHandleW.restype = HINSTANCE


_configure_win32_api()


class SystemTrayIcon:
    def __init__(self, tooltip: str = "TapLite") -> None:
        self._tooltip = tooltip
        self._state = TrayState()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._hwnd = HWND()
        self._ready = threading.Event()
        self._stop_requested = threading.Event()
        self._events: queue.Queue[str] = queue.Queue()
        self._class_name = f"TapLiteTrayWindow_{id(self)}"
        self._hicon = HICON()
        self._wnd_proc: WNDPROC | None = None
        self._startup_error: str | None = None

    def start(self) -> bool:
        if sys.platform != "win32" or user32 is None or shell32 is None or kernel32 is None:
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._stop_requested.clear()
        self._ready.clear()
        self._startup_error = None
        self._thread = threading.Thread(target=self._message_loop, name="TapLiteTray", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2)
        return self._startup_error is None and bool(self._hwnd)

    def stop(self) -> None:
        self._stop_requested.set()
        if self._hwnd and user32 is not None:
            user32.PostMessageW(self._hwnd, WM_CLOSE, WPARAM(), LPARAM())
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2)
        self._thread = None

    def update(self, *, window_visible: bool, clicker_running: bool) -> None:
        with self._lock:
            self._state.window_visible = window_visible
            self._state.clicker_running = clicker_running

    def drain_events(self) -> list[str]:
        events: list[str] = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                return events

    def _message_loop(self) -> None:
        assert user32 is not None
        assert kernel32 is not None

        @WNDPROC
        def wnd_proc(hwnd: HWND, message: int, w_param: WPARAM, l_param: LPARAM) -> int:
            if message == WM_COMMAND:
                command = int(w_param or 0) & 0xFFFF
                if command == MENU_SHOW:
                    self._events.put("toggle_window")
                elif command == MENU_TOGGLE:
                    self._events.put("toggle_clicker")
                elif command == MENU_EXIT:
                    self._events.put("exit")
                return 0
            if message == WM_TRAYICON:
                event_code = int(l_param or 0)
                if event_code == WM_RBUTTONUP:
                    self._show_context_menu(hwnd)
                elif event_code == WM_LBUTTONDBLCLK:
                    self._events.put("toggle_window")
                return 0
            if message == WM_CLOSE:
                user32.DestroyWindow(hwnd)
                return 0
            if message == WM_DESTROY:
                self._remove_icon()
                user32.PostQuitMessage(0)
                return 0
            return int(user32.DefWindowProcW(hwnd, message, w_param, l_param))

        self._wnd_proc = wnd_proc

        try:
            instance = kernel32.GetModuleHandleW(None)
            window_class = WNDCLASSW()
            window_class.lpfnWndProc = self._wnd_proc
            window_class.hInstance = instance
            window_class.lpszClassName = self._class_name

            atom = user32.RegisterClassW(byref(window_class))
            if not atom:
                raise ctypes.WinError(ctypes.get_last_error())

            hwnd = user32.CreateWindowExW(
                0,
                self._class_name,
                self._class_name,
                0,
                CW_USEDEFAULT,
                CW_USEDEFAULT,
                0,
                0,
                None,
                None,
                instance,
                None,
            )
            if not hwnd:
                raise ctypes.WinError(ctypes.get_last_error())

            self._hwnd = hwnd
            self._hicon = HICON(self._load_icon_handle())
            self._add_icon()
            self._ready.set()

            msg = MSG()
            while not self._stop_requested.is_set():
                result = user32.GetMessageW(byref(msg), None, 0, 0)
                if result in (0, -1):
                    break
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageW(byref(msg))
        except Exception as exc:
            self._startup_error = str(exc)
            self._events.put(str(exc))
            self._ready.set()
        finally:
            self._hwnd = HWND()
            if self._hicon and user32 is not None:
                user32.DestroyIcon(self._hicon)
            self._hicon = HICON()

    def _load_icon_handle(self) -> int:
        assert user32 is not None
        assert shell32 is not None

        icon_path = resolve_app_icon_path()
        if icon_path is not None:
            width = user32.GetSystemMetrics(SM_CXSMICON)
            height = user32.GetSystemMetrics(SM_CYSMICON)
            handle = user32.LoadImageW(
                None,
                str(icon_path),
                IMAGE_ICON,
                width,
                height,
                LR_LOADFROMFILE | LR_DEFAULTSIZE,
            )
            if handle:
                return self._handle_to_int(handle)

        if getattr(sys, "frozen", False):
            extracted = shell32.ExtractIconW(None, sys.executable, 0)
            if extracted:
                return self._handle_to_int(extracted)

        default_icon = user32.LoadIconW(None, c_void_p(IDI_APPLICATION))
        return self._handle_to_int(default_icon)

    @staticmethod
    def _handle_to_int(handle: object) -> int:
        if isinstance(handle, int):
            return handle
        value = getattr(handle, "value", None)
        return int(value or 0)

    def _notify_data(self) -> NOTIFYICONDATAW:
        data = NOTIFYICONDATAW()
        data.cbSize = sizeof(NOTIFYICONDATAW)
        data.hWnd = self._hwnd
        data.uID = TRAY_ID
        data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        data.uCallbackMessage = WM_TRAYICON
        data.hIcon = self._hicon
        data.szTip = self._tooltip
        return data

    def _add_icon(self) -> None:
        assert shell32 is not None
        data = self._notify_data()
        if not shell32.Shell_NotifyIconW(NIM_ADD, byref(data)):
            raise ctypes.WinError(ctypes.get_last_error())

    def _remove_icon(self) -> None:
        if shell32 is None or not self._hwnd:
            return
        data = self._notify_data()
        shell32.Shell_NotifyIconW(NIM_DELETE, byref(data))

    def _show_context_menu(self, hwnd: HWND) -> None:
        assert user32 is not None

        menu = user32.CreatePopupMenu()
        if not menu:
            return

        try:
            with self._lock:
                state = TrayState(
                    window_visible=self._state.window_visible,
                    clicker_running=self._state.clicker_running,
                )

            show_label = "显示窗口" if not state.window_visible else "隐藏窗口"
            toggle_label = "停止连点" if state.clicker_running else "开始连点"
            user32.AppendMenuW(menu, MF_STRING, UINT_PTR(MENU_SHOW), show_label)
            user32.AppendMenuW(menu, MF_STRING, UINT_PTR(MENU_TOGGLE), toggle_label)
            user32.AppendMenuW(menu, MF_SEPARATOR, UINT_PTR(0), None)
            user32.AppendMenuW(menu, MF_STRING, UINT_PTR(MENU_EXIT), "退出")

            point = POINT()
            user32.GetCursorPos(byref(point))
            user32.SetForegroundWindow(hwnd)
            user32.TrackPopupMenu(
                menu,
                TPM_LEFTALIGN | TPM_BOTTOMALIGN | TPM_RIGHTBUTTON,
                point.x,
                point.y,
                0,
                hwnd,
                None,
            )
            user32.PostMessageW(hwnd, WM_NULL, WPARAM(), LPARAM())
        finally:
            user32.DestroyMenu(menu)
