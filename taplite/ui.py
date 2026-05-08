from __future__ import annotations

import queue
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from .clicker import AutoClicker, ClickConfig, ClickEvent
from .hotkeys import HOTKEY_ACTION_STOP, HOTKEY_ACTION_TOGGLE, HotkeyManager, hotkey_to_vk
from .settings import Settings, load_settings, save_settings
from .win_input import get_cursor_position, is_running_as_admin, send_click, set_cursor_position


BUTTON_LABELS = {"left": "左键", "right": "右键", "middle": "中键"}
CLICK_TYPE_LABELS = {"single": "单击", "double": "双击"}
REPEAT_LABELS = {"infinite": "无限循环", "count": "指定次数"}
POSITION_LABELS = {"current": "当前位置", "fixed": "固定坐标"}


class TapLiteApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TapLite")
        self.geometry("420x470")
        self.resizable(False, False)

        self.settings = load_settings()
        self.event_queue: queue.Queue[ClickEvent] = queue.Queue()
        self.clicker = AutoClicker(send_click, set_cursor_position, self.event_queue)
        self.hotkeys = HotkeyManager(self._on_hotkey)

        self.interval_var = tk.StringVar(value=str(self.settings.interval_ms))
        self.button_var = tk.StringVar(value=self.settings.mouse_button)
        self.click_type_var = tk.StringVar(value=self.settings.click_type)
        self.repeat_mode_var = tk.StringVar(value=self.settings.repeat_mode)
        self.repeat_count_var = tk.StringVar(value=str(self.settings.repeat_count))
        self.position_mode_var = tk.StringVar(value=self.settings.position_mode)
        self.fixed_x_var = tk.StringVar(value=str(self.settings.fixed_x))
        self.fixed_y_var = tk.StringVar(value=str(self.settings.fixed_y))
        self.toggle_hotkey_var = tk.StringVar(value=self.settings.toggle_hotkey)
        self.stop_hotkey_var = tk.StringVar(value=self.settings.stop_hotkey)
        self.status_var = tk.StringVar(value="就绪")
        self.count_var = tk.StringVar(value="0")
        self.notice_var = tk.StringVar(value=self._build_notice())

        self._build_ui()
        self._refresh_enabled_fields()
        self._install_hotkeys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_events)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text="TapLite", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(header, textvariable=self.notice_var, wraplength=380).pack(anchor="w", pady=(4, 12))

        status = ttk.LabelFrame(root, text="状态", padding=10)
        status.pack(fill="x", pady=(0, 10))
        ttk.Label(status, text="运行状态").grid(row=0, column=0, sticky="w")
        ttk.Label(status, textvariable=self.status_var).grid(row=0, column=1, sticky="e")
        ttk.Label(status, text="已点击").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(status, textvariable=self.count_var).grid(row=1, column=1, sticky="e", pady=(6, 0))
        status.columnconfigure(1, weight=1)

        click = ttk.LabelFrame(root, text="点击设置", padding=10)
        click.pack(fill="x", pady=(0, 10))
        ttk.Label(click, text="间隔(ms)").grid(row=0, column=0, sticky="w")
        ttk.Entry(click, textvariable=self.interval_var, width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(click, text="鼠标键").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(click, textvariable=self.button_var, values=list(BUTTON_LABELS), state="readonly", width=10).grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Label(click, text="点击类型").grid(row=1, column=2, sticky="w", padx=(20, 0), pady=(8, 0))
        ttk.Combobox(click, textvariable=self.click_type_var, values=list(CLICK_TYPE_LABELS), state="readonly", width=10).grid(row=1, column=3, sticky="w", pady=(8, 0))

        repeat = ttk.LabelFrame(root, text="重复", padding=10)
        repeat.pack(fill="x", pady=(0, 10))
        ttk.Radiobutton(repeat, text="无限循环", variable=self.repeat_mode_var, value="infinite", command=self._refresh_enabled_fields).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(repeat, text="指定次数", variable=self.repeat_mode_var, value="count", command=self._refresh_enabled_fields).grid(row=0, column=1, sticky="w")
        self.repeat_count_entry = ttk.Entry(repeat, textvariable=self.repeat_count_var, width=10)
        self.repeat_count_entry.grid(row=0, column=2, sticky="w", padx=(12, 0))

        position = ttk.LabelFrame(root, text="位置", padding=10)
        position.pack(fill="x", pady=(0, 10))
        ttk.Radiobutton(position, text="跟随当前位置", variable=self.position_mode_var, value="current", command=self._refresh_enabled_fields).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(position, text="固定坐标", variable=self.position_mode_var, value="fixed", command=self._refresh_enabled_fields).grid(row=0, column=1, sticky="w")
        self.fixed_x_entry = ttk.Entry(position, textvariable=self.fixed_x_var, width=8)
        self.fixed_y_entry = ttk.Entry(position, textvariable=self.fixed_y_var, width=8)
        self.fixed_x_entry.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.fixed_y_entry.grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Button(position, text="读取当前坐标", command=self._capture_position).grid(row=1, column=2, sticky="w", pady=(8, 0))

        hotkeys = ttk.LabelFrame(root, text="热键", padding=10)
        hotkeys.pack(fill="x", pady=(0, 10))
        ttk.Label(hotkeys, text="开始/停止").grid(row=0, column=0, sticky="w")
        ttk.Entry(hotkeys, textvariable=self.toggle_hotkey_var, width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(hotkeys, text="紧急停止").grid(row=0, column=2, sticky="w", padx=(20, 0))
        ttk.Entry(hotkeys, textvariable=self.stop_hotkey_var, width=10).grid(row=0, column=3, sticky="w")
        ttk.Button(hotkeys, text="应用热键", command=self._install_hotkeys).grid(row=1, column=0, sticky="w", pady=(8, 0))

        actions = ttk.Frame(root)
        actions.pack(fill="x")
        ttk.Button(actions, text="开始/停止 (F6)", command=self._toggle_clicking).pack(side="left")
        ttk.Button(actions, text="停止 (F8)", command=self._stop_clicking).pack(side="left", padx=(8, 0))

    def _build_notice(self) -> str:
        if sys.platform != "win32":
            return "此软件使用 Windows 输入 API，当前系统只能查看界面。"
        if not is_running_as_admin():
            return "若目标游戏以管理员权限运行，请也用管理员权限启动 TapLite。"
        return "管理员模式运行中。部分游戏或反作弊可能会屏蔽模拟输入。"

    def _refresh_enabled_fields(self) -> None:
        repeat_state = "normal" if self.repeat_mode_var.get() == "count" else "disabled"
        position_state = "normal" if self.position_mode_var.get() == "fixed" else "disabled"
        self.repeat_count_entry.configure(state=repeat_state)
        self.fixed_x_entry.configure(state=position_state)
        self.fixed_y_entry.configure(state=position_state)

    def _capture_position(self) -> None:
        try:
            x, y = get_cursor_position()
        except Exception as exc:
            messagebox.showerror("无法读取坐标", str(exc))
            return
        self.fixed_x_var.set(str(x))
        self.fixed_y_var.set(str(y))

    def _read_config(self) -> ClickConfig | None:
        try:
            interval_ms = int(self.interval_var.get())
            repeat_count = int(self.repeat_count_var.get())
            fixed_x = int(self.fixed_x_var.get())
            fixed_y = int(self.fixed_y_var.get())
        except ValueError:
            messagebox.showerror("输入错误", "间隔、次数和坐标必须是整数。")
            return None

        if interval_ms < 1:
            messagebox.showerror("输入错误", "点击间隔至少为 1 ms。")
            return None
        if repeat_count < 1:
            messagebox.showerror("输入错误", "指定次数必须大于 0。")
            return None
        if fixed_x < 0 or fixed_y < 0:
            messagebox.showerror("输入错误", "固定坐标必须是非负整数。")
            return None

        return ClickConfig(
            interval_ms=interval_ms,
            mouse_button=self.button_var.get(),  # type: ignore[arg-type]
            click_type=self.click_type_var.get(),  # type: ignore[arg-type]
            repeat_mode=self.repeat_mode_var.get(),  # type: ignore[arg-type]
            repeat_count=repeat_count,
            position_mode=self.position_mode_var.get(),  # type: ignore[arg-type]
            fixed_x=fixed_x,
            fixed_y=fixed_y,
        )

    def _toggle_clicking(self) -> None:
        config = self._read_config()
        if config is None:
            return
        self.clicker.toggle(config)

    def _stop_clicking(self) -> None:
        self.clicker.stop()

    def _on_hotkey(self, action: str) -> None:
        if action == HOTKEY_ACTION_TOGGLE:
            self.after(0, self._toggle_clicking)
        elif action == HOTKEY_ACTION_STOP:
            self.after(0, self._stop_clicking)

    def _install_hotkeys(self) -> None:
        try:
            hotkey_to_vk(self.toggle_hotkey_var.get())
            hotkey_to_vk(self.stop_hotkey_var.get())
        except ValueError as exc:
            messagebox.showerror("热键错误", f"{exc}\n当前支持 F1-F12、Esc、Space、Pause。")
            return
        self.hotkeys.start(self.toggle_hotkey_var.get(), self.stop_hotkey_var.get())

    def _poll_events(self) -> None:
        while True:
            try:
                event = self.event_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_click_event(event)

        for action in self.hotkeys.drain():
            if action.startswith("error:"):
                self.status_var.set(f"热键注册失败：{action[6:]}")

        self.after(100, self._poll_events)

    def _handle_click_event(self, event: ClickEvent) -> None:
        if event.kind == "started":
            self.status_var.set("运行中")
        elif event.kind == "clicked":
            self.count_var.set(str(event.count))
        elif event.kind == "stopped":
            self.status_var.set("已停止")
            self.count_var.set(str(event.count))
        elif event.kind == "error":
            self.status_var.set("发生错误")
            messagebox.showerror("点击失败", event.message)

    def _collect_settings(self) -> Settings:
        config = self._read_config()
        if config is None:
            return self.settings
        return Settings(
            interval_ms=config.interval_ms,
            mouse_button=config.mouse_button,
            click_type=config.click_type,
            repeat_mode=config.repeat_mode,
            repeat_count=config.repeat_count,
            position_mode=config.position_mode,
            fixed_x=config.fixed_x,
            fixed_y=config.fixed_y,
            toggle_hotkey=self.toggle_hotkey_var.get().strip().upper(),
            stop_hotkey=self.stop_hotkey_var.get().strip().upper(),
        )

    def _on_close(self) -> None:
        self.clicker.stop()
        self.clicker.wait(timeout=1)
        self.hotkeys.stop()
        save_settings(self._collect_settings())
        self.destroy()


def main() -> None:
    app = TapLiteApp()
    app.mainloop()
