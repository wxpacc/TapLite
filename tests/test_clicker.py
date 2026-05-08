import queue
import time

from taplite.clicker import AutoClicker, ClickConfig, ClickEvent


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
