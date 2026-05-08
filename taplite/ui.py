from __future__ import annotations

import queue
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from .clicker import AutoClicker, ClickConfig, ClickEvent
from .hotkeys import HOTKEY_ACTION_STOP, HOTKEY_ACTION_TOGGLE, HotkeyManager, hotkey_to_vk
from .settings import Settings, load_settings, save_settings
from .win_input import get_cursor_position, is_running_as_admin, send_click, set_cursor_position


LOW_INTERVAL_WARNING_MS = 10


class TapLiteApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TapLite")
        self.geometry("500x560")
        self.minsize(440, 500)
        self.resizable(True, True)
        self._configure_style()

        self.settings = load_settings()
        self.event_queue: queue.Queue[ClickEvent] = queue.Queue()
        self.clicker = AutoClicker(send_click, set_cursor_position, self.event_queue)
        self.hotkeys = HotkeyManager(self._on_hotkey)
        self.config_widgets: list[tk.Widget] = []

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
        self.action_text_var = tk.StringVar(value="开始 (F6)")

        self._build_ui()
        self._refresh_running_state()
        self._refresh_enabled_fields()
        self._install_hotkeys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_events)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.configure("TFrame", background="#f7f8fa")
        style.configure("TLabel", background="#f7f8fa", foreground="#1f2937")
        style.configure("Muted.TLabel", foreground="#6b7280")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Value.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TLabelframe", background="#f7f8fa")
        style.configure("TLabelframe.Label", background="#f7f8fa", foreground="#374151")
        style.configure("TButton", padding=(10, 5))
        style.configure("Accent.TButton", padding=(14, 6))

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        shell = ttk.Frame(self, padding=14)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(0, weight=1)

        canvas = tk.Canvas(shell, background="#f7f8fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))

        root = ttk.Frame(canvas)
        content_window = canvas.create_window((0, 0), window=root, anchor="nw")

        def update_scroll_region(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_content_width(event: tk.Event) -> None:
            canvas.itemconfigure(content_window, width=event.width)

        def scroll_content(event: tk.Event) -> None:
            if event.delta:
                canvas.yview_scroll(int(-event.delta / 120), "units")

        root.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_content_width)
        canvas.bind_all("<MouseWheel>", scroll_content)

        header = ttk.Frame(root)
        header.pack(fill="x", padx=(0, 4), pady=(0, 8))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="TapLite", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="状态").grid(row=0, column=1, sticky="e")
        ttk.Label(header, textvariable=self.status_var, style="Value.TLabel").grid(row=0, column=2, sticky="e", padx=(8, 0))
        ttk.Label(header, text="点击").grid(row=1, column=1, sticky="e", pady=(4, 0))
        ttk.Label(header, textvariable=self.count_var, style="Value.TLabel").grid(row=1, column=2, sticky="e", padx=(8, 0), pady=(4, 0))
        ttk.Label(header, textvariable=self.notice_var, style="Muted.TLabel", wraplength=450).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        click = ttk.LabelFrame(root, text="点击", padding=(10, 8))
        click.pack(fill="x", padx=(0, 4), pady=(0, 8))
        for column in range(5):
            click.columnconfigure(column, weight=1)
        self._add_config_widget(ttk.Label(click, text="间隔(ms)")).grid(row=0, column=0, sticky="w")
        self._add_config_widget(ttk.Entry(click, textvariable=self.interval_var, width=9)).grid(row=0, column=1, sticky="w")
        self._add_config_widget(ttk.Radiobutton(click, text="单击", variable=self.click_type_var, value="single")).grid(row=0, column=3, sticky="w")
        self._add_config_widget(ttk.Radiobutton(click, text="双击", variable=self.click_type_var, value="double")).grid(row=0, column=4, sticky="w")
        self._add_config_widget(ttk.Label(click, text="鼠标键")).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self._add_config_widget(ttk.Radiobutton(click, text="左键", variable=self.button_var, value="left")).grid(row=1, column=1, sticky="w", pady=(8, 0))
        self._add_config_widget(ttk.Radiobutton(click, text="右键", variable=self.button_var, value="right")).grid(row=1, column=2, sticky="w", pady=(8, 0))
        self._add_config_widget(ttk.Radiobutton(click, text="中键", variable=self.button_var, value="middle")).grid(row=1, column=3, sticky="w", pady=(8, 0))

        behavior = ttk.Frame(root)
        behavior.pack(fill="x", padx=(0, 4), pady=(0, 8))
        behavior.columnconfigure(0, weight=1)
        behavior.columnconfigure(1, weight=1)

        repeat = ttk.LabelFrame(behavior, text="重复", padding=(10, 8))
        repeat.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._add_config_widget(ttk.Radiobutton(repeat, text="无限循环", variable=self.repeat_mode_var, value="infinite", command=self._refresh_enabled_fields)).grid(row=0, column=0, sticky="w")
        self._add_config_widget(ttk.Radiobutton(repeat, text="指定次数", variable=self.repeat_mode_var, value="count", command=self._refresh_enabled_fields)).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.repeat_count_entry = self._add_config_widget(ttk.Entry(repeat, textvariable=self.repeat_count_var, width=8))
        self.repeat_count_entry.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

        position = ttk.LabelFrame(behavior, text="位置", padding=(10, 8))
        position.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._add_config_widget(ttk.Radiobutton(position, text="当前位置", variable=self.position_mode_var, value="current", command=self._refresh_enabled_fields)).grid(row=0, column=0, columnspan=5, sticky="w")
        self._add_config_widget(ttk.Radiobutton(position, text="固定坐标", variable=self.position_mode_var, value="fixed", command=self._refresh_enabled_fields)).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self._add_config_widget(ttk.Label(position, text="X")).grid(row=1, column=1, sticky="e", padx=(8, 2), pady=(8, 0))
        self.fixed_x_entry = self._add_config_widget(ttk.Entry(position, textvariable=self.fixed_x_var, width=6))
        self.fixed_x_entry.grid(row=1, column=2, sticky="w", pady=(8, 0))
        self._add_config_widget(ttk.Label(position, text="Y")).grid(row=1, column=3, sticky="e", padx=(6, 2), pady=(8, 0))
        self.fixed_y_entry = self._add_config_widget(ttk.Entry(position, textvariable=self.fixed_y_var, width=6))
        self.fixed_y_entry.grid(row=1, column=4, sticky="w", pady=(8, 0))
        self.capture_button = self._add_config_widget(ttk.Button(position, text="读取坐标", command=self._capture_position))
        self.capture_button.grid(row=2, column=0, columnspan=5, sticky="w", pady=(8, 0))

        hotkeys = ttk.LabelFrame(root, text="热键", padding=(10, 8))
        hotkeys.pack(fill="x", padx=(0, 4), pady=(0, 8))
        for column in range(5):
            hotkeys.columnconfigure(column, weight=1)
        ttk.Label(hotkeys, text="开始/停止").grid(row=0, column=0, sticky="w")
        ttk.Entry(hotkeys, textvariable=self.toggle_hotkey_var, width=8).grid(row=0, column=1, sticky="w", padx=(8, 16))
        ttk.Label(hotkeys, text="紧急停止").grid(row=0, column=2, sticky="w")
        ttk.Entry(hotkeys, textvariable=self.stop_hotkey_var, width=8).grid(row=0, column=3, sticky="w", padx=(8, 16))
        ttk.Button(hotkeys, text="应用", command=self._install_hotkeys).grid(row=0, column=4, sticky="e")

        actions = ttk.Frame(shell)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, textvariable=self.action_text_var, style="Accent.TButton", command=self._toggle_clicking).grid(row=0, column=0, sticky="ew")
        ttk.Button(actions, text="停止 (F8)", command=self._stop_clicking).grid(row=0, column=1, sticky="e", padx=(8, 0))

    def _add_config_widget(self, widget: tk.Widget) -> tk.Widget:
        self.config_widgets.append(widget)
        return widget

    def _build_notice(self) -> str:
        if sys.platform != "win32":
            return "此软件使用 Windows 输入 API，当前系统只能查看界面。"
        if not is_running_as_admin():
            return "若目标游戏以管理员权限运行，请也用管理员权限启动 TapLite。"
        return "管理员模式运行中。部分游戏或反作弊可能会屏蔽模拟输入。"

    def _set_config_widgets_state(self, state: str) -> None:
        for widget in self.config_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass

    def _refresh_running_state(self) -> None:
        if self.clicker.is_running:
            self.action_text_var.set("停止 (F6)")
            self._set_config_widgets_state("disabled")
        else:
            self.action_text_var.set("开始 (F6)")
            self._set_config_widgets_state("normal")
            self._refresh_enabled_fields()

    def _refresh_enabled_fields(self) -> None:
        if self.clicker.is_running:
            self.repeat_count_entry.configure(state="disabled")
            self.fixed_x_entry.configure(state="disabled")
            self.fixed_y_entry.configure(state="disabled")
            self.capture_button.configure(state="disabled")
            return

        repeat_state = "normal" if self.repeat_mode_var.get() == "count" else "disabled"
        position_state = "normal" if self.position_mode_var.get() == "fixed" else "disabled"
        self.repeat_count_entry.configure(state=repeat_state)
        self.fixed_x_entry.configure(state=position_state)
        self.fixed_y_entry.configure(state=position_state)
        self.capture_button.configure(state="normal")

    def _capture_position(self) -> None:
        try:
            x, y = get_cursor_position()
        except Exception as exc:
            messagebox.showerror("无法读取坐标", str(exc))
            return
        self.fixed_x_var.set(str(x))
        self.fixed_y_var.set(str(y))
        self.status_var.set(f"已读取坐标 X={x}, Y={y}")

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

    def _confirm_low_interval(self, config: ClickConfig) -> bool:
        if config.interval_ms >= LOW_INTERVAL_WARNING_MS:
            return True
        return messagebox.askyesno(
            "确认高速点击",
            f"当前间隔为 {config.interval_ms} ms，可能导致目标窗口卡顿或难以及时停止。是否继续？",
        )

    def _toggle_clicking(self) -> None:
        if self.clicker.is_running:
            self.clicker.stop()
            self._refresh_running_state()
            return

        config = self._read_config()
        if config is None or not self._confirm_low_interval(config):
            return

        if config.repeat_mode == "infinite":
            self.status_var.set("准备开始，F8 可紧急停止")
        self.clicker.start(config)
        self._refresh_running_state()

    def _stop_clicking(self) -> None:
        self.clicker.stop()
        self._refresh_running_state()

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
            self.status_var.set("运行中，F8 可紧急停止")
            self._refresh_running_state()
        elif event.kind == "clicked":
            self.count_var.set(str(event.count))
        elif event.kind == "stopped":
            self.status_var.set("已停止")
            self.count_var.set(str(event.count))
            self._refresh_running_state()
        elif event.kind == "error":
            self.status_var.set("发生错误")
            self._refresh_running_state()
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
