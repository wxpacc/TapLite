from __future__ import annotations

from dataclasses import dataclass
import queue
import random
import threading
import time
from typing import Callable, Literal

from .win_input import MouseButton


ClickType = Literal["single", "double"]
RepeatMode = Literal["infinite", "count"]
PositionMode = Literal["current", "fixed"]
ClickMode = Literal["single_point", "multi_point"]


@dataclass(slots=True)
class ClickPoint:
    x: int
    y: int
    wait_ms: int = 0


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
    click_mode: ClickMode = "single_point"
    click_points: list[ClickPoint] | None = None
    random_interval_enabled: bool = False
    random_interval_min_ms: int = 100
    random_interval_max_ms: int = 150
    random_offset_enabled: bool = False
    random_offset_px: int = 0
    start_delay_seconds: int = 0
    run_limit_seconds: int = 0


@dataclass(slots=True)
class ClickEvent:
    kind: str
    count: int = 0
    message: str = ""


ClickFunc = Callable[[MouseButton, int], None]
MoveFunc = Callable[[int, int], None]
RandomIntFunc = Callable[[int, int], int]


class AutoClicker:
    def __init__(
        self,
        click_func: ClickFunc,
        move_func: MoveFunc,
        event_queue: queue.Queue[ClickEvent] | None = None,
        random_int: RandomIntFunc | None = None,
    ) -> None:
        self._click_func = click_func
        self._move_func = move_func
        self._random_int = random_int or random.randint
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
        clicks_per_action = 2 if config.click_type == "double" else 1
        target_rounds = config.repeat_count if config.repeat_mode == "count" else None
        started_at = 0.0

        try:
            if self._wait_for_start_delay(config.start_delay_seconds):
                return

            started_at = time.monotonic()
            self.events.put(ClickEvent("started", 0))

            completed_rounds = 0
            while not self._stop_event.is_set():
                if target_rounds is not None and completed_rounds >= target_rounds:
                    break
                if self._is_run_limit_reached(config, started_at):
                    self.events.put(ClickEvent("limit_reached", self.count))
                    break

                for point in self._iter_points(config):
                    if self._stop_event.is_set() or self._is_run_limit_reached(config, started_at):
                        if self._is_run_limit_reached(config, started_at):
                            self.events.put(ClickEvent("limit_reached", self.count))
                        break

                    self._move_if_needed(config, point)
                    self._click_func(config.mouse_button, clicks_per_action)

                    with self._lock:
                        self._count += 1
                        count = self._count
                    self.events.put(ClickEvent("clicked", count))

                    if self._wait_between_clicks(config, point):
                        break

                completed_rounds += 1
        except Exception as exc:  # pragma: no cover - message is surfaced in UI.
            self.events.put(ClickEvent("error", self.count, str(exc)))
        finally:
            self._stop_event.set()
            self.events.put(ClickEvent("stopped", self.count))

    def _wait_for_start_delay(self, seconds: int) -> bool:
        for remaining in range(max(seconds, 0), 0, -1):
            self.events.put(ClickEvent("countdown", self.count, str(remaining)))
            if self._stop_event.wait(1):
                return True
        return False

    def _iter_points(self, config: ClickConfig) -> list[ClickPoint]:
        if config.click_mode == "multi_point" and config.click_points:
            return config.click_points
        return [ClickPoint(config.fixed_x, config.fixed_y, config.interval_ms)]

    def _move_if_needed(self, config: ClickConfig, point: ClickPoint) -> None:
        if config.click_mode == "single_point" and config.position_mode == "current":
            return

        x, y = point.x, point.y
        if config.random_offset_enabled and config.random_offset_px > 0:
            offset = config.random_offset_px
            x += self._random_int(-offset, offset)
            y += self._random_int(-offset, offset)
        self._move_func(max(x, 0), max(y, 0))

    def _wait_between_clicks(self, config: ClickConfig, point: ClickPoint) -> bool:
        wait_ms = point.wait_ms or config.interval_ms
        if config.random_interval_enabled:
            wait_ms = self._random_int(
                config.random_interval_min_ms,
                config.random_interval_max_ms,
            )
        return self._stop_event.wait(max(wait_ms, 1) / 1000)

    def _is_run_limit_reached(self, config: ClickConfig, started_at: float) -> bool:
        return bool(
            config.run_limit_seconds > 0
            and started_at > 0
            and time.monotonic() - started_at >= config.run_limit_seconds
        )
