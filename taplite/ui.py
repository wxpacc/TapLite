from __future__ import annotations

from dataclasses import dataclass
import queue
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable, Literal

from .clicker import AutoClicker, ClickConfig, ClickEvent, ClickPoint
from .hotkeys import HOTKEY_ACTION_STOP, HOTKEY_ACTION_TOGGLE, HotkeyManager, hotkey_to_vk
from .settings import Settings, load_settings, save_settings, settings_to_preset, sanitize_settings
from .tray import SystemTrayIcon, resolve_app_icon_path
from .win_input import get_cursor_position, is_running_as_admin, send_click, set_cursor_position


LOW_INTERVAL_WARNING_MS = 10
OVERLAY_MARGIN_PX = 18
CAPTURE_CARD_OFFSET_X = 18
CAPTURE_CARD_OFFSET_Y = 22


def compute_capture_card_position(
    cursor_x: int,
    cursor_y: int,
    card_width: int,
    card_height: int,
    screen_width: int,
    screen_height: int,
    offset_x: int = CAPTURE_CARD_OFFSET_X,
    offset_y: int = CAPTURE_CARD_OFFSET_Y,
) -> tuple[int, int]:
    x = cursor_x + offset_x
    y = cursor_y + offset_y
    max_x = max(screen_width - card_width - 8, 0)
    max_y = max(screen_height - card_height - 8, 0)
    return max(min(x, max_x), 0), max(min(y, max_y), 0)


CaptureKind = Literal["single", "multi"]


@dataclass(slots=True)
class CaptureRequest:
    kind: CaptureKind
    wait_ms: int = 0


@dataclass(slots=True)
class CaptureApplyResult:
    fixed_position: tuple[int, int] | None = None
    point: ClickPoint | None = None
    status_message: str = ""


def apply_capture_request(request: CaptureRequest, x: int, y: int) -> CaptureApplyResult:
    if request.kind == "single":
        return CaptureApplyResult(
            fixed_position=(x, y),
            status_message=f"已读取坐标 X={x}, Y={y}",
        )
    return CaptureApplyResult(
        point=ClickPoint(x=x, y=y, wait_ms=max(request.wait_ms, 0)),
        status_message=f"已添加点 X={x}, Y={y}",
    )


class RunningOverlay:
    def __init__(self, owner: tk.Tk) -> None:
        self._owner = owner
        self._window = tk.Toplevel(owner)
        self._window.withdraw()
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.configure(background="#dbe4f0")

        shell = tk.Frame(
            self._window,
            bg="#f8fafc",
            bd=1,
            highlightthickness=1,
            highlightbackground="#dbe4f0",
            padx=14,
            pady=12,
        )
        shell.pack()

        self._title_label = tk.Label(
            shell,
            text="正在连点",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        self._title_label.pack(anchor="w")
        self._hint_label = tk.Label(
            shell,
            text="按 F8 停止",
            bg="#f8fafc",
            fg="#475569",
            font=("Segoe UI", 9),
            anchor="w",
        )
        self._hint_label.pack(anchor="w", pady=(4, 0))

        self._owner.bind("<Configure>", self._on_owner_configure, add="+")

    @property
    def visible(self) -> bool:
        return self._window.state() != "withdrawn"

    def show(self, title: str, hint: str) -> None:
        self._title_label.configure(text=title)
        self._hint_label.configure(text=hint)
        self._window.update_idletasks()
        self._reposition()
        self._window.deiconify()
        self._window.lift()

    def hide(self) -> None:
        self._window.withdraw()

    def destroy(self) -> None:
        self._window.destroy()

    def _on_owner_configure(self, _event: tk.Event) -> None:
        if self.visible:
            self._reposition()

    def _reposition(self) -> None:
        self._window.update_idletasks()
        width = self._window.winfo_reqwidth()
        height = self._window.winfo_reqheight()
        screen_width = self._owner.winfo_screenwidth()
        screen_height = self._owner.winfo_screenheight()
        x = max(screen_width - width - OVERLAY_MARGIN_PX, 0)
        y = max(screen_height - height - OVERLAY_MARGIN_PX, 0)
        self._window.geometry(f"+{x}+{y}")


class PointCaptureOverlay:
    def __init__(
        self,
        owner: tk.Tk,
        on_confirm: Callable[[int, int], None],
        on_cancel: Callable[[], None],
    ) -> None:
        self._owner = owner
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel
        self._visible = False
        self._poll_after_id: str | None = None
        self._current_position = (0, 0)

        self._window = tk.Toplevel(owner)
        self._window.withdraw()
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.configure(bg="#0f172a", cursor="crosshair")
        try:
            self._window.attributes("-alpha", 0.08)
        except tk.TclError:
            pass

        self._window.bind("<Button-1>", self._confirm)
        self._window.bind("<Button-3>", self._cancel)
        self._window.bind("<Escape>", self._cancel)

        self._card = tk.Toplevel(owner)
        self._card.withdraw()
        self._card.overrideredirect(True)
        self._card.attributes("-topmost", True)
        self._card.configure(bg="#dbe4f0")

        shell = tk.Frame(
            self._card,
            bg="#f8fafc",
            bd=1,
            highlightthickness=1,
            highlightbackground="#dbe4f0",
            padx=14,
            pady=12,
        )
        shell.pack()
        self._title_label = tk.Label(
            shell,
            text="取点中",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self._title_label.pack(anchor="w")
        self._coords_label = tk.Label(
            shell,
            text="X=0, Y=0",
            bg="#f8fafc",
            fg="#1f2937",
            font=("Consolas", 10),
            anchor="w",
        )
        self._coords_label.pack(anchor="w", pady=(4, 0))
        self._hint_label = tk.Label(
            shell,
            text="左键确认，右键或 Esc 取消",
            bg="#f8fafc",
            fg="#475569",
            font=("Segoe UI", 9),
            anchor="w",
        )
        self._hint_label.pack(anchor="w", pady=(4, 0))

    @property
    def visible(self) -> bool:
        return self._visible

    def show(self, title: str) -> None:
        screen_width = self._owner.winfo_screenwidth()
        screen_height = self._owner.winfo_screenheight()
        self._title_label.configure(text=title)
        self._window.geometry(f"{screen_width}x{screen_height}+0+0")
        self._window.deiconify()
        self._window.lift()
        self._card.deiconify()
        self._card.lift()
        self._visible = True
        self._window.focus_force()
        self._schedule_poll()

    def hide(self) -> None:
        self._visible = False
        if self._poll_after_id is not None:
            self._owner.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        self._window.withdraw()
        self._card.withdraw()

    def destroy(self) -> None:
        self.hide()
        self._card.destroy()
        self._window.destroy()

    def _schedule_poll(self) -> None:
        self._poll_after_id = self._owner.after(30, self._poll_cursor)

    def _poll_cursor(self) -> None:
        if not self._visible:
            self._poll_after_id = None
            return
        try:
            x, y = get_cursor_position()
        except Exception:
            self.hide()
            self._on_cancel()
            return
        self._current_position = (x, y)
        self._coords_label.configure(text=f"X={x}, Y={y}")
        self._card.update_idletasks()
        card_width = self._card.winfo_reqwidth()
        card_height = self._card.winfo_reqheight()
        card_x, card_y = compute_capture_card_position(
            x,
            y,
            card_width,
            card_height,
            self._owner.winfo_screenwidth(),
            self._owner.winfo_screenheight(),
        )
        self._card.geometry(f"+{card_x}+{card_y}")
        self._schedule_poll()

    def _confirm(self, event: tk.Event) -> None:
        if not self._visible:
            return
        x = int(getattr(event, "x_root", self._current_position[0]))
        y = int(getattr(event, "y_root", self._current_position[1]))
        self.hide()
        self._on_confirm(x, y)

    def _cancel(self, _event: tk.Event | None = None) -> None:
        if not self._visible:
            return
        self.hide()
        self._on_cancel()


class TapLiteApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TapLite")
        self.geometry("620x680")
        self.minsize(560, 560)
        self.resizable(True, True)
        self._configure_app_icon()
        self._configure_style()

        self.settings = load_settings()
        self.event_queue: queue.Queue[ClickEvent] = queue.Queue()
        self.clicker = AutoClicker(send_click, set_cursor_position, self.event_queue)
        self.hotkeys = HotkeyManager(self._on_hotkey)
        self.config_widgets: list[tk.Widget] = []
        self._overlay_title: str | None = None
        self._capture_request: CaptureRequest | None = None
        self._capture_overlay_was_visible = False
        self._exiting = False
        self._tray_message_shown = False
        self._tray_available = False

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
        self.click_mode_var = tk.StringVar(value=self.settings.click_mode)
        self.random_interval_var = tk.BooleanVar(value=self.settings.random_interval_enabled)
        self.random_interval_min_var = tk.StringVar(value=str(self.settings.random_interval_min_ms))
        self.random_interval_max_var = tk.StringVar(value=str(self.settings.random_interval_max_ms))
        self.random_offset_var = tk.BooleanVar(value=self.settings.random_offset_enabled)
        self.random_offset_px_var = tk.StringVar(value=str(self.settings.random_offset_px))
        self.start_delay_var = tk.StringVar(value=str(self.settings.start_delay_seconds))
        self.run_limit_var = tk.BooleanVar(value=self.settings.run_limit_seconds > 0)
        self.run_limit_seconds_var = tk.StringVar(value=str(self.settings.run_limit_seconds or 60))
        self.show_running_overlay_var = tk.BooleanVar(value=self.settings.show_running_overlay)
        self.preset_name_var = tk.StringVar()
        self.status_var = tk.StringVar(value="就绪")
        self.count_var = tk.StringVar(value="0")
        self.notice_var = tk.StringVar(value=self._build_notice())
        self.action_text_var = tk.StringVar()
        self.running_overlay = RunningOverlay(self)
        self.capture_overlay = PointCaptureOverlay(self, self._handle_capture_confirm, self._handle_capture_cancel)
        self.tray_icon = self._build_tray_icon()

        self._build_ui()
        self._load_points(self.settings.click_points or [])
        self._refresh_running_state()
        self._refresh_enabled_fields()
        self._refresh_preset_names()
        self._install_hotkeys()
        if self.tray_icon is not None:
            self._tray_available = self.tray_icon.start()
            if self._tray_available:
                self._sync_tray_state()
            else:
                self.status_var.set("托盘初始化失败，关闭窗口将直接退出。")
        self.protocol("WM_DELETE_WINDOW", self._on_close_requested)
        self.after(100, self._poll_events)

    def _configure_app_icon(self) -> None:
        icon_path = resolve_app_icon_path()
        if icon_path is None:
            return
        try:
            self.iconbitmap(default=str(icon_path))
        except tk.TclError:
            return

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

    def _build_tray_icon(self) -> SystemTrayIcon | None:
        if sys.platform != "win32":
            return None
        return SystemTrayIcon()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        shell = ttk.Frame(self, padding=14)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        self._build_header(shell)

        notebook = ttk.Notebook(shell)
        notebook.grid(row=1, column=0, sticky="nsew")
        notebook.add(self._build_basic_tab(notebook), text="基础")
        notebook.add(self._build_points_tab(notebook), text="多点")
        notebook.add(self._build_advanced_tab(notebook), text="高级")
        notebook.add(self._build_presets_tab(notebook), text="预设")

        actions = ttk.Frame(shell)
        actions.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)
        ttk.Button(
            actions,
            textvariable=self.action_text_var,
            style="Accent.TButton",
            command=self._toggle_clicking,
        ).grid(row=0, column=0, sticky="ew")
        self.stop_button = ttk.Button(actions, command=self._stop_clicking)
        self.stop_button.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self._refresh_hotkey_labels()

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="TapLite", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="状态").grid(row=0, column=1, sticky="e")
        ttk.Label(header, textvariable=self.status_var, style="Value.TLabel").grid(
            row=0,
            column=2,
            sticky="e",
            padx=(8, 0),
        )
        ttk.Label(header, text="点击").grid(row=1, column=1, sticky="e", pady=(4, 0))
        ttk.Label(header, textvariable=self.count_var, style="Value.TLabel").grid(
            row=1,
            column=2,
            sticky="e",
            padx=(8, 0),
            pady=(4, 0),
        )
        ttk.Label(header, textvariable=self.notice_var, style="Muted.TLabel", wraplength=560).grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(6, 0),
        )

    def _build_basic_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(parent, padding=12)
        for column in range(4):
            tab.columnconfigure(column, weight=1)

        mode = ttk.LabelFrame(tab, text="点击模式", padding=10)
        mode.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        self._add_config_widget(
            ttk.Radiobutton(
                mode,
                text="单点",
                variable=self.click_mode_var,
                value="single_point",
                command=self._refresh_enabled_fields,
            )
        ).grid(row=0, column=0, sticky="w")
        self._add_config_widget(
            ttk.Radiobutton(
                mode,
                text="多点",
                variable=self.click_mode_var,
                value="multi_point",
                command=self._refresh_enabled_fields,
            )
        ).grid(row=0, column=1, sticky="w", padx=(16, 0))

        click = ttk.LabelFrame(tab, text="点击设置", padding=10)
        click.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        for column in range(6):
            click.columnconfigure(column, weight=1)
        self._add_config_widget(ttk.Label(click, text="间隔(ms)")).grid(row=0, column=0, sticky="w")
        self._add_config_widget(ttk.Entry(click, textvariable=self.interval_var, width=9)).grid(
            row=0,
            column=1,
            sticky="w",
        )
        self._add_config_widget(
            ttk.Radiobutton(click, text="单击", variable=self.click_type_var, value="single")
        ).grid(row=0, column=2, sticky="w")
        self._add_config_widget(
            ttk.Radiobutton(click, text="双击", variable=self.click_type_var, value="double")
        ).grid(row=0, column=3, sticky="w")
        self._add_config_widget(
            ttk.Radiobutton(click, text="左键", variable=self.button_var, value="left")
        ).grid(row=1, column=1, sticky="w", pady=(8, 0))
        self._add_config_widget(
            ttk.Radiobutton(click, text="右键", variable=self.button_var, value="right")
        ).grid(row=1, column=2, sticky="w", pady=(8, 0))
        self._add_config_widget(
            ttk.Radiobutton(click, text="中键", variable=self.button_var, value="middle")
        ).grid(row=1, column=3, sticky="w", pady=(8, 0))

        repeat = ttk.LabelFrame(tab, text="重复", padding=10)
        repeat.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 6))
        self._add_config_widget(
            ttk.Radiobutton(
                repeat,
                text="无限循环",
                variable=self.repeat_mode_var,
                value="infinite",
                command=self._refresh_enabled_fields,
            )
        ).grid(row=0, column=0, sticky="w")
        self._add_config_widget(
            ttk.Radiobutton(
                repeat,
                text="指定次数/轮数",
                variable=self.repeat_mode_var,
                value="count",
                command=self._refresh_enabled_fields,
            )
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.repeat_count_entry = self._add_config_widget(
            ttk.Entry(repeat, textvariable=self.repeat_count_var, width=8)
        )
        self.repeat_count_entry.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

        position = ttk.LabelFrame(tab, text="单点位置", padding=10)
        position.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(6, 0))
        self._add_config_widget(
            ttk.Radiobutton(
                position,
                text="当前位置",
                variable=self.position_mode_var,
                value="current",
                command=self._refresh_enabled_fields,
            )
        ).grid(row=0, column=0, columnspan=5, sticky="w")
        self._add_config_widget(
            ttk.Radiobutton(
                position,
                text="固定坐标",
                variable=self.position_mode_var,
                value="fixed",
                command=self._refresh_enabled_fields,
            )
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self._add_config_widget(ttk.Label(position, text="X")).grid(
            row=1,
            column=1,
            sticky="e",
            padx=(8, 2),
            pady=(8, 0),
        )
        self.fixed_x_entry = self._add_config_widget(
            ttk.Entry(position, textvariable=self.fixed_x_var, width=6)
        )
        self.fixed_x_entry.grid(row=1, column=2, sticky="w", pady=(8, 0))
        self._add_config_widget(ttk.Label(position, text="Y")).grid(
            row=1,
            column=3,
            sticky="e",
            padx=(6, 2),
            pady=(8, 0),
        )
        self.fixed_y_entry = self._add_config_widget(
            ttk.Entry(position, textvariable=self.fixed_y_var, width=6)
        )
        self.fixed_y_entry.grid(row=1, column=4, sticky="w", pady=(8, 0))
        self.capture_button = self._add_config_widget(
            ttk.Button(position, text="读取坐标", command=self._capture_position)
        )
        self.capture_button.grid(row=2, column=0, columnspan=5, sticky="w", pady=(8, 0))
        return tab

    def _build_points_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(parent, padding=12)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        self.points_tree = ttk.Treeview(tab, columns=("x", "y", "wait"), show="headings", height=8)
        self.points_tree.heading("x", text="X")
        self.points_tree.heading("y", text="Y")
        self.points_tree.heading("wait", text="等待(ms)")
        self.points_tree.column("x", width=80, anchor="center")
        self.points_tree.column("y", width=80, anchor="center")
        self.points_tree.column("wait", width=90, anchor="center")
        self.points_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.points_tree.yview)
        self.points_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        buttons = ttk.Frame(tab)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for index, (text, command) in enumerate(
            (
                ("添加位置", self._add_current_point),
                ("编辑", self._edit_selected_point),
                ("删除", self._delete_selected_point),
                ("上移", lambda: self._move_selected_point(-1)),
                ("下移", lambda: self._move_selected_point(1)),
            )
        ):
            button = self._add_config_widget(ttk.Button(buttons, text=text, command=command))
            button.grid(row=0, column=index, padx=(0, 8))
        return tab

    def _build_advanced_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(parent, padding=12)

        random_frame = ttk.LabelFrame(tab, text="随机化", padding=10)
        random_frame.pack(fill="x", pady=(0, 10))
        self._add_config_widget(
            ttk.Checkbutton(
                random_frame,
                text="随机间隔",
                variable=self.random_interval_var,
                command=self._refresh_enabled_fields,
            )
        ).grid(row=0, column=0, sticky="w")
        self.random_min_entry = self._add_config_widget(
            ttk.Entry(random_frame, textvariable=self.random_interval_min_var, width=8)
        )
        self.random_min_entry.grid(row=0, column=1, padx=(8, 2))
        ttk.Label(random_frame, text="-").grid(row=0, column=2)
        self.random_max_entry = self._add_config_widget(
            ttk.Entry(random_frame, textvariable=self.random_interval_max_var, width=8)
        )
        self.random_max_entry.grid(row=0, column=3, padx=(2, 4))
        ttk.Label(random_frame, text="ms").grid(row=0, column=4, sticky="w")
        self._add_config_widget(
            ttk.Checkbutton(
                random_frame,
                text="随机坐标偏移",
                variable=self.random_offset_var,
                command=self._refresh_enabled_fields,
            )
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.random_offset_entry = self._add_config_widget(
            ttk.Entry(random_frame, textvariable=self.random_offset_px_var, width=8)
        )
        self.random_offset_entry.grid(row=1, column=1, sticky="w", padx=(8, 2), pady=(8, 0))
        ttk.Label(random_frame, text="px").grid(row=1, column=2, sticky="w", pady=(8, 0))

        run_frame = ttk.LabelFrame(tab, text="运行控制", padding=10)
        run_frame.pack(fill="x")
        self._add_config_widget(ttk.Label(run_frame, text="启动倒计时")).grid(row=0, column=0, sticky="w")
        self.start_delay_combo = self._add_config_widget(
            ttk.Combobox(
                run_frame,
                textvariable=self.start_delay_var,
                values=("0", "1", "3", "5"),
                state="readonly",
                width=8,
            )
        )
        self.start_delay_combo.grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Label(run_frame, text="秒").grid(row=0, column=2, sticky="w", padx=(4, 0))
        self._add_config_widget(
            ttk.Checkbutton(
                run_frame,
                text="运行时限",
                variable=self.run_limit_var,
                command=self._refresh_enabled_fields,
            )
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.run_limit_entry = self._add_config_widget(
            ttk.Entry(run_frame, textvariable=self.run_limit_seconds_var, width=8)
        )
        self.run_limit_entry.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Label(run_frame, text="秒").grid(row=1, column=2, sticky="w", padx=(4, 0), pady=(8, 0))

        hotkeys = ttk.LabelFrame(tab, text="热键", padding=10)
        hotkeys.pack(fill="x", pady=(10, 0))
        ttk.Label(hotkeys, text="开始/停止").grid(row=0, column=0, sticky="w")
        ttk.Entry(hotkeys, textvariable=self.toggle_hotkey_var, width=8).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(8, 16),
        )
        ttk.Label(hotkeys, text="紧急停止").grid(row=0, column=2, sticky="w")
        ttk.Entry(hotkeys, textvariable=self.stop_hotkey_var, width=8).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(8, 16),
        )
        ttk.Button(hotkeys, text="应用", command=self._install_hotkeys).grid(row=0, column=4, sticky="e")

        overlay = ttk.LabelFrame(tab, text="提示", padding=10)
        overlay.pack(fill="x", pady=(10, 0))
        self._add_config_widget(
            ttk.Checkbutton(
                overlay,
                text="运行时显示右下角提示",
                variable=self.show_running_overlay_var,
                command=self._on_overlay_toggle,
            )
        ).grid(row=0, column=0, sticky="w")

        tray_frame = ttk.LabelFrame(tab, text="后台运行", padding=10)
        tray_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(
            tray_frame,
            text="关闭窗口后保留在系统托盘，可从托盘恢复、开始/停止和退出。",
            style="Muted.TLabel",
            wraplength=520,
        ).grid(row=0, column=0, sticky="w")
        return tab

    def _build_presets_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(parent, padding=12)
        tab.columnconfigure(1, weight=1)
        ttk.Label(tab, text="预设名称").grid(row=0, column=0, sticky="w")
        self.preset_combo = ttk.Combobox(tab, textvariable=self.preset_name_var, values=(), width=28)
        self.preset_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Button(tab, text="保存预设", command=self._save_preset).grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Button(tab, text="载入预设", command=self._load_preset).grid(
            row=1,
            column=1,
            sticky="w",
            padx=(8, 0),
            pady=(10, 0),
        )
        ttk.Button(tab, text="删除预设", command=self._delete_preset).grid(
            row=1,
            column=2,
            sticky="w",
            padx=(8, 0),
            pady=(10, 0),
        )
        ttk.Label(
            tab,
            text="预设仅保存在本机 data/settings.json，不会进入版本控制。",
            style="Muted.TLabel",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 0))
        return tab

    def _add_config_widget(self, widget: tk.Widget) -> tk.Widget:
        self.config_widgets.append(widget)
        return widget

    def _build_notice(self) -> str:
        if sys.platform != "win32":
            return "此软件使用 Windows 输入 API，当前系统只能查看界面。"
        if not is_running_as_admin():
            return "若目标游戏以管理员权限运行，请也用管理员权限启动 TapLite。"
        return "管理员模式运行中。部分游戏或反作弊可能会屏蔽模拟输入。"

    def _refresh_hotkey_labels(self) -> None:
        toggle_hotkey = self.toggle_hotkey_var.get().strip().upper() or "F6"
        stop_hotkey = self.stop_hotkey_var.get().strip().upper() or "F8"
        self.stop_button.configure(text=f"停止 ({stop_hotkey})")
        if self.clicker.is_running:
            self.action_text_var.set(f"停止 ({toggle_hotkey})")
        else:
            self.action_text_var.set(f"开始 ({toggle_hotkey})")

    def _set_config_widgets_state(self, state: str) -> None:
        for widget in self.config_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass

    def _refresh_running_state(self) -> None:
        self._refresh_hotkey_labels()
        if self.clicker.is_running:
            self._set_config_widgets_state("disabled")
        else:
            self._set_config_widgets_state("normal")
            self._refresh_enabled_fields()
            self._hide_overlay()
        self._sync_tray_state()

    def _refresh_enabled_fields(self) -> None:
        if self.clicker.is_running:
            return
        repeat_state = "normal" if self.repeat_mode_var.get() == "count" else "disabled"
        fixed_state = (
            "normal"
            if self.position_mode_var.get() == "fixed" and self.click_mode_var.get() == "single_point"
            else "disabled"
        )
        self.repeat_count_entry.configure(state=repeat_state)
        self.fixed_x_entry.configure(state=fixed_state)
        self.fixed_y_entry.configure(state=fixed_state)
        self.capture_button.configure(
            state="normal" if self.click_mode_var.get() == "single_point" else "disabled"
        )
        self.random_min_entry.configure(state="normal" if self.random_interval_var.get() else "disabled")
        self.random_max_entry.configure(state="normal" if self.random_interval_var.get() else "disabled")
        self.random_offset_entry.configure(state="normal" if self.random_offset_var.get() else "disabled")
        self.run_limit_entry.configure(state="normal" if self.run_limit_var.get() else "disabled")

    def _load_points(self, points: list[ClickPoint]) -> None:
        for item in self.points_tree.get_children():
            self.points_tree.delete(item)
        for point in points:
            self.points_tree.insert("", "end", values=(point.x, point.y, point.wait_ms))

    def _read_points(self) -> list[ClickPoint]:
        points: list[ClickPoint] = []
        for item in self.points_tree.get_children():
            x, y, wait_ms = self.points_tree.item(item, "values")
            points.append(ClickPoint(int(x), int(y), int(wait_ms)))
        return points

    def _add_current_point(self) -> None:
        wait_ms = self._read_default_point_wait()
        if wait_ms is None:
            return
        self._start_capture_mode(CaptureRequest(kind="multi", wait_ms=wait_ms))

    def _selected_point(self) -> str | None:
        selection = self.points_tree.selection()
        if not selection:
            messagebox.showinfo("请选择点位", "请先选择一个多点列表项。")
            return None
        return selection[0]

    def _edit_selected_point(self) -> None:
        item = self._selected_point()
        if item is None:
            return
        x, y, wait_ms = self.points_tree.item(item, "values")
        new_x = simpledialog.askinteger("编辑 X", "X 坐标", initialvalue=int(x), minvalue=0, parent=self)
        if new_x is None:
            return
        new_y = simpledialog.askinteger("编辑 Y", "Y 坐标", initialvalue=int(y), minvalue=0, parent=self)
        if new_y is None:
            return
        new_wait = simpledialog.askinteger(
            "编辑等待",
            "等待毫秒，0 表示使用全局间隔",
            initialvalue=int(wait_ms),
            minvalue=0,
            parent=self,
        )
        if new_wait is None:
            return
        self.points_tree.item(item, values=(new_x, new_y, new_wait))

    def _delete_selected_point(self) -> None:
        item = self._selected_point()
        if item:
            self.points_tree.delete(item)

    def _move_selected_point(self, offset: int) -> None:
        item = self._selected_point()
        if item is None:
            return
        siblings = list(self.points_tree.get_children())
        index = siblings.index(item)
        new_index = index + offset
        if 0 <= new_index < len(siblings):
            self.points_tree.move(item, "", new_index)

    def _capture_position(self) -> None:
        self._start_capture_mode(CaptureRequest(kind="single"))

    def _read_default_point_wait(self) -> int | None:
        try:
            interval_ms = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror("输入错误", "点击间隔必须是整数。")
            return None
        if interval_ms < 1:
            messagebox.showerror("输入错误", "点击间隔必须大于 0。")
            return None
        return interval_ms

    def _start_capture_mode(self, request: CaptureRequest) -> None:
        if sys.platform != "win32":
            messagebox.showerror("当前平台不支持", "取点模式仅支持 Windows。")
            return
        self._stop_capture_mode(update_status=False)
        self._capture_request = request
        self._capture_overlay_was_visible = bool(self._overlay_title and self.show_running_overlay_var.get())
        self.running_overlay.hide()
        title = "读取坐标" if request.kind == "single" else "添加位置"
        self.capture_overlay.show(title)
        self.status_var.set("取点中，左键确认，右键或 Esc 取消。")

    def _stop_capture_mode(self, *, update_status: bool) -> None:
        self._capture_request = None
        if self.capture_overlay.visible:
            self.capture_overlay.hide()
        if self._capture_overlay_was_visible and self._overlay_title:
            self.running_overlay.show(self._overlay_title, self._stop_hint_text())
        self._capture_overlay_was_visible = False
        if update_status and not self.clicker.is_running:
            self.status_var.set("已取消取点")

    def _handle_capture_confirm(self, x: int, y: int) -> None:
        request = self._capture_request
        self._capture_request = None
        if self._capture_overlay_was_visible and self._overlay_title:
            self.running_overlay.show(self._overlay_title, self._stop_hint_text())
        self._capture_overlay_was_visible = False
        if request is None:
            return
        result = apply_capture_request(request, max(x, 0), max(y, 0))
        if result.fixed_position is not None:
            fixed_x, fixed_y = result.fixed_position
            self.fixed_x_var.set(str(fixed_x))
            self.fixed_y_var.set(str(fixed_y))
            self.position_mode_var.set("fixed")
            self.click_mode_var.set("single_point")
            self._refresh_enabled_fields()
        if result.point is not None:
            point = result.point
            self.points_tree.insert("", "end", values=(point.x, point.y, point.wait_ms))
        self.status_var.set(result.status_message)
        self.bell()

    def _handle_capture_cancel(self) -> None:
        self._stop_capture_mode(update_status=True)

    def _read_config(self) -> ClickConfig | None:
        try:
            interval_ms = int(self.interval_var.get())
            repeat_count = int(self.repeat_count_var.get())
            fixed_x = int(self.fixed_x_var.get())
            fixed_y = int(self.fixed_y_var.get())
            random_min = int(self.random_interval_min_var.get())
            random_max = int(self.random_interval_max_var.get())
            random_offset = int(self.random_offset_px_var.get())
            start_delay = int(self.start_delay_var.get())
            run_limit = int(self.run_limit_seconds_var.get()) if self.run_limit_var.get() else 0
        except ValueError:
            messagebox.showerror("输入错误", "间隔、次数、坐标和高级参数必须是整数。")
            return None

        if interval_ms < 1 or repeat_count < 1:
            messagebox.showerror("输入错误", "点击间隔和指定次数必须大于 0。")
            return None
        if fixed_x < 0 or fixed_y < 0 or random_offset < 0:
            messagebox.showerror("输入错误", "坐标和随机偏移必须是非负整数。")
            return None
        if random_min < 1 or random_max < random_min:
            messagebox.showerror("输入错误", "随机间隔范围必须有效。")
            return None
        if run_limit < 0:
            messagebox.showerror("输入错误", "运行时限必须是非负整数。")
            return None

        points = self._read_points()
        if self.click_mode_var.get() == "multi_point" and not points:
            messagebox.showerror("输入错误", "多点模式至少需要一个点位。")
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
            click_mode=self.click_mode_var.get(),  # type: ignore[arg-type]
            click_points=points,
            random_interval_enabled=self.random_interval_var.get(),
            random_interval_min_ms=random_min,
            random_interval_max_ms=random_max,
            random_offset_enabled=self.random_offset_var.get(),
            random_offset_px=random_offset,
            start_delay_seconds=start_delay,
            run_limit_seconds=run_limit,
        )

    def _confirm_low_interval(self, config: ClickConfig) -> bool:
        interval_ms = config.random_interval_min_ms if config.random_interval_enabled else config.interval_ms
        if interval_ms >= LOW_INTERVAL_WARNING_MS:
            return True
        return messagebox.askyesno(
            "确认高速点击",
            f"当前最小间隔为 {interval_ms} ms，可能导致目标窗口卡顿或难以及时停止。是否继续？",
        )

    def _toggle_clicking(self) -> None:
        self._stop_capture_mode(update_status=False)
        if self.clicker.is_running:
            self.clicker.stop()
            self._refresh_running_state()
            return
        config = self._read_config()
        if config is None or not self._confirm_low_interval(config):
            return
        if config.repeat_mode == "infinite":
            self.status_var.set(f"准备开始，{self._stop_hint_text()}。")
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
        self._refresh_hotkey_labels()
        if self._overlay_title:
            self._show_overlay(self._overlay_title)

    def _on_overlay_toggle(self) -> None:
        if self._capture_request is not None:
            return
        if self.show_running_overlay_var.get() and self._overlay_title:
            self.running_overlay.show(self._overlay_title, self._stop_hint_text())
        else:
            self.running_overlay.hide()

    def _stop_hint_text(self) -> str:
        stop_hotkey = self.stop_hotkey_var.get().strip().upper() or "F8"
        return f"按 {stop_hotkey} 停止"

    def _show_overlay(self, title: str) -> None:
        self._overlay_title = title
        if self.show_running_overlay_var.get() and self._capture_request is None:
            self.running_overlay.show(title, self._stop_hint_text())

    def _hide_overlay(self) -> None:
        self._overlay_title = None
        self.running_overlay.hide()

    def _toggle_window_visibility(self) -> None:
        if not self.winfo_viewable():
            self._show_window()
        else:
            self._hide_to_tray()

    def _show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()
        self._sync_tray_state()

    def _hide_to_tray(self) -> None:
        if not self._tray_available or self.tray_icon is None:
            self._close_app()
            return
        self.withdraw()
        self._sync_tray_state()
        if not self._tray_message_shown:
            self.status_var.set("已最小化到系统托盘")
            self._tray_message_shown = True

    def _exit_from_tray(self) -> None:
        self._exiting = True
        self._close_app()

    def _sync_tray_state(self) -> None:
        if not self._tray_available or self.tray_icon is None:
            return
        self.tray_icon.update(
            window_visible=bool(self.winfo_viewable()),
            clicker_running=self.clicker.is_running,
        )

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

        if self.tray_icon is not None:
            for event in self.tray_icon.drain_events():
                if event == "toggle_window":
                    self._toggle_window_visibility()
                elif event == "toggle_clicker":
                    self._toggle_clicking()
                elif event == "exit":
                    self._exit_from_tray()
                elif event:
                    self._tray_available = False
                    self.status_var.set(f"托盘初始化失败：{event}")

        self.after(100, self._poll_events)

    def _handle_click_event(self, event: ClickEvent) -> None:
        if event.kind == "countdown":
            message = f"{event.message} 秒后开始"
            self.status_var.set(message)
            self._show_overlay(message)
        elif event.kind == "started":
            self._stop_capture_mode(update_status=False)
            self.status_var.set(f"运行中，{self._stop_hint_text()}。")
            self._refresh_running_state()
            self._show_overlay("正在连点")
        elif event.kind == "clicked":
            self.count_var.set(str(event.count))
        elif event.kind == "limit_reached":
            self.status_var.set("已达到运行时限")
            self._hide_overlay()
        elif event.kind == "stopped":
            if self.status_var.get() != "已达到运行时限":
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
            click_mode=config.click_mode,
            click_points=config.click_points or [],
            random_interval_enabled=config.random_interval_enabled,
            random_interval_min_ms=config.random_interval_min_ms,
            random_interval_max_ms=config.random_interval_max_ms,
            random_offset_enabled=config.random_offset_enabled,
            random_offset_px=config.random_offset_px,
            start_delay_seconds=config.start_delay_seconds,
            run_limit_seconds=config.run_limit_seconds,
            show_running_overlay=self.show_running_overlay_var.get(),
            presets=self.settings.presets or {},
        )

    def _apply_settings(self, settings: Settings) -> None:
        self.interval_var.set(str(settings.interval_ms))
        self.button_var.set(settings.mouse_button)
        self.click_type_var.set(settings.click_type)
        self.repeat_mode_var.set(settings.repeat_mode)
        self.repeat_count_var.set(str(settings.repeat_count))
        self.position_mode_var.set(settings.position_mode)
        self.fixed_x_var.set(str(settings.fixed_x))
        self.fixed_y_var.set(str(settings.fixed_y))
        self.toggle_hotkey_var.set(settings.toggle_hotkey)
        self.stop_hotkey_var.set(settings.stop_hotkey)
        self.click_mode_var.set(settings.click_mode)
        self.random_interval_var.set(settings.random_interval_enabled)
        self.random_interval_min_var.set(str(settings.random_interval_min_ms))
        self.random_interval_max_var.set(str(settings.random_interval_max_ms))
        self.random_offset_var.set(settings.random_offset_enabled)
        self.random_offset_px_var.set(str(settings.random_offset_px))
        self.start_delay_var.set(str(settings.start_delay_seconds))
        self.run_limit_var.set(settings.run_limit_seconds > 0)
        self.run_limit_seconds_var.set(str(settings.run_limit_seconds or 60))
        self.show_running_overlay_var.set(settings.show_running_overlay)
        self._load_points(settings.click_points or [])
        self._refresh_hotkey_labels()
        self._refresh_enabled_fields()
        self._on_overlay_toggle()

    def _refresh_preset_names(self) -> None:
        names = sorted((self.settings.presets or {}).keys())
        self.preset_combo.configure(values=names)
        if names and not self.preset_name_var.get():
            self.preset_name_var.set(names[0])

    def _save_preset(self) -> None:
        name = self.preset_name_var.get().strip()
        if not name:
            messagebox.showerror("预设名称为空", "请输入预设名称。")
            return
        settings = self._collect_settings()
        presets = dict(settings.presets or {})
        presets[name] = settings_to_preset(settings)
        settings.presets = presets
        self.settings = settings
        save_settings(settings)
        self._refresh_preset_names()
        self.status_var.set(f"已保存预设：{name}")

    def _load_preset(self) -> None:
        name = self.preset_name_var.get().strip()
        preset = (self.settings.presets or {}).get(name)
        if not preset:
            messagebox.showerror("预设不存在", "请选择已有预设。")
            return
        loaded = sanitize_settings(preset)
        loaded.presets = self.settings.presets or {}
        self._apply_settings(loaded)
        self.status_var.set(f"已载入预设：{name}")

    def _delete_preset(self) -> None:
        name = self.preset_name_var.get().strip()
        presets = dict(self.settings.presets or {})
        if name not in presets:
            messagebox.showerror("预设不存在", "请选择已有预设。")
            return
        presets.pop(name)
        self.settings.presets = presets
        save_settings(self.settings)
        self.preset_name_var.set("")
        self._refresh_preset_names()
        self.status_var.set(f"已删除预设：{name}")

    def _on_close_requested(self) -> None:
        self._stop_capture_mode(update_status=False)
        if self._exiting:
            self._close_app()
            return
        if not self._tray_available or self.tray_icon is None:
            self._close_app()
            return
        self._hide_to_tray()

    def _close_app(self) -> None:
        self._exiting = True
        self._stop_capture_mode(update_status=False)
        self.clicker.stop()
        self.clicker.wait(timeout=1)
        self.hotkeys.stop()
        if self.tray_icon is not None:
            self.tray_icon.stop()
        self._hide_overlay()
        save_settings(self._collect_settings())
        self.capture_overlay.destroy()
        self.running_overlay.destroy()
        self.destroy()


def main() -> None:
    app = TapLiteApp()
    app.mainloop()
