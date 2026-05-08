import queue
import time

from taplite.clicker import AutoClicker, ClickConfig, ClickEvent, ClickPoint


def make_config(**overrides: object) -> ClickConfig:
    data = {
        "interval_ms": 1,
        "mouse_button": "left",
        "click_type": "single",
        "repeat_mode": "count",
        "repeat_count": 3,
        "position_mode": "current",
        "fixed_x": 0,
        "fixed_y": 0,
    }
    data.update(overrides)
    return ClickConfig(**data)  # type: ignore[arg-type]


def test_clicker_stops_after_repeat_count() -> None:
    calls: list[tuple[str, int]] = []
    events: queue.Queue[ClickEvent] = queue.Queue()
    clicker = AutoClicker(lambda button, clicks: calls.append((button, clicks)), lambda x, y: None, events)

    assert clicker.start(make_config(repeat_count=3))
    clicker.wait(timeout=1)

    assert calls == [("left", 1), ("left", 1), ("left", 1)]
    assert not clicker.is_running
    assert clicker.count == 3


def test_clicker_moves_for_fixed_position() -> None:
    moves: list[tuple[int, int]] = []
    clicker = AutoClicker(lambda _button, _clicks: None, lambda x, y: moves.append((x, y)))

    clicker.start(make_config(position_mode="fixed", fixed_x=12, fixed_y=34, repeat_count=2))
    clicker.wait(timeout=1)

    assert moves == [(12, 34), (12, 34)]


def test_clicker_toggle_stops_running_loop() -> None:
    calls: list[tuple[str, int]] = []
    clicker = AutoClicker(lambda button, clicks: calls.append((button, clicks)), lambda x, y: None)
    config = make_config(repeat_mode="infinite", interval_ms=5)

    clicker.toggle(config)
    time.sleep(0.03)
    clicker.toggle(config)
    clicker.wait(timeout=1)

    assert calls
    assert not clicker.is_running


def test_double_click_sends_two_clicks_per_action() -> None:
    calls: list[tuple[str, int]] = []
    clicker = AutoClicker(lambda button, clicks: calls.append((button, clicks)), lambda x, y: None)

    clicker.start(make_config(click_type="double", repeat_count=1))
    clicker.wait(timeout=1)

    assert calls == [("left", 2)]


def test_multi_point_clicks_in_order_for_repeat_rounds() -> None:
    moves: list[tuple[int, int]] = []
    calls: list[tuple[str, int]] = []
    clicker = AutoClicker(
        lambda button, clicks: calls.append((button, clicks)),
        lambda x, y: moves.append((x, y)),
    )

    clicker.start(
        make_config(
            click_mode="multi_point",
            click_points=[ClickPoint(10, 20, 1), ClickPoint(30, 40, 1)],
            repeat_count=2,
        )
    )
    clicker.wait(timeout=1)

    assert moves == [(10, 20), (30, 40), (10, 20), (30, 40)]
    assert calls == [("left", 1), ("left", 1), ("left", 1), ("left", 1)]
    assert clicker.count == 4


def test_random_offset_is_applied_within_configured_range() -> None:
    moves: list[tuple[int, int]] = []
    offsets = iter([2, -1])
    clicker = AutoClicker(
        lambda _button, _clicks: None,
        lambda x, y: moves.append((x, y)),
        random_int=lambda _low, _high: next(offsets),
    )

    clicker.start(
        make_config(
            position_mode="fixed",
            fixed_x=10,
            fixed_y=20,
            repeat_count=1,
            random_offset_enabled=True,
            random_offset_px=3,
        )
    )
    clicker.wait(timeout=1)

    assert moves == [(12, 19)]


def test_random_interval_uses_configured_range() -> None:
    requested_ranges: list[tuple[int, int]] = []

    def random_int(low: int, high: int) -> int:
        requested_ranges.append((low, high))
        return 1

    clicker = AutoClicker(lambda _button, _clicks: None, lambda _x, _y: None, random_int=random_int)

    clicker.start(
        make_config(
            repeat_count=1,
            random_interval_enabled=True,
            random_interval_min_ms=25,
            random_interval_max_ms=40,
        )
    )
    clicker.wait(timeout=1)

    assert requested_ranges == [(25, 40)]


def test_run_limit_stops_infinite_loop() -> None:
    calls: list[tuple[str, int]] = []
    clicker = AutoClicker(lambda button, clicks: calls.append((button, clicks)), lambda _x, _y: None)

    clicker.start(make_config(repeat_mode="infinite", interval_ms=5, run_limit_seconds=1))
    clicker.wait(timeout=2)

    assert calls
    assert not clicker.is_running


def test_start_delay_emits_countdown_before_clicking() -> None:
    events: queue.Queue[ClickEvent] = queue.Queue()
    clicker = AutoClicker(lambda _button, _clicks: None, lambda _x, _y: None, events)

    clicker.start(make_config(start_delay_seconds=1, repeat_count=1))
    clicker.wait(timeout=2)

    kinds = [events.get_nowait().kind for _ in range(events.qsize())]
    assert kinds[0] == "countdown"
    assert "started" in kinds
