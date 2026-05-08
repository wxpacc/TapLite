from __future__ import annotations

from dataclasses import dataclass
import queue
import threading
import time
from typing import Callable, Literal

from .win_input import MouseButton


ClickType = Literal["single", "double"]
RepeatMode = Literal["infinite", "count"]
PositionMode = Literal["current", "fixed"]


@dataclass(slots=True)
class ClickConfig:
    interval_ms: int
    mouse_button: MouseButton
    click_type: ClickType
    repeat_mode: RepeatMode
    repeat_count: int
    position_mode: PositionMode
    fixed_x: int
    fixed_y: int


@dataclass(slots=True)
class ClickEvent:
    kind: str
    count: int = 0
    message: str = ""


ClickFunc = Callable[[MouseButton, int], None]
MoveFunc = Callable[[int, int], None]


class AutoClicker:
    def __init__(
        self,
        click_func: ClickFunc,
        move_func: MoveFunc,
        event_queue: queue.Queue[ClickEvent] | None = None,
    ) -> None:
        self._click_func = click_func
        self._move_func = move_func
        self.events = event_queue or queue.Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._count = 0

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    def start(self, config: ClickConfig) -> bool:
        with self._lock:
            if self.is_running:
                return False
            self._count = 0
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                args=(config,),
                name="TapLiteClicker",
                daemon=True,
            )
            self._thread.start()
            return True

    def stop(self) -> None:
        self._stop_event.set()

    def toggle(self, config: ClickConfig) -> None:
        if self.is_running:
            self.stop()
            return
        self.start(config)

    def wait(self, timeout: float | None = None) -> None:
        thread = self._thread
        if thread:
            thread.join(timeout)

    def _run(self, config: ClickConfig) -> None:
        self.events.put(ClickEvent("started", 0))
        clicks_per_action = 2 if config.click_type == "double" else 1
        target_count = config.repeat_count if config.repeat_mode == "count" else None
        interval_seconds = max(config.interval_ms, 1) / 1000

        try:
            while not self._stop_event.is_set():
                with self._lock:
                    if target_count is not None and self._count >= target_count:
                        break

                if config.position_mode == "fixed":
                    self._move_func(config.fixed_x, config.fixed_y)

                self._click_func(config.mouse_button, clicks_per_action)

                with self._lock:
                    self._count += 1
                    count = self._count
                self.events.put(ClickEvent("clicked", count))

                if target_count is not None and count >= target_count:
                    break

                if self._stop_event.wait(interval_seconds):
                    break
        except Exception as exc:  # pragma: no cover - message is surfaced in UI.
            self.events.put(ClickEvent("error", self.count, str(exc)))
        finally:
            self._stop_event.set()
            self.events.put(ClickEvent("stopped", self.count))
