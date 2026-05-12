from taplite.clicker import ClickPoint
from taplite.ui import CaptureRequest, apply_capture_request, compute_capture_card_position


def test_apply_capture_request_for_single_point() -> None:
    result = apply_capture_request(CaptureRequest(kind="single"), 120, 340)

    assert result.fixed_position == (120, 340)
    assert result.point is None
    assert result.status_message == "已读取坐标 X=120, Y=340"


def test_apply_capture_request_for_multi_point() -> None:
    result = apply_capture_request(CaptureRequest(kind="multi", wait_ms=180), 45, 78)

    assert result.fixed_position is None
    assert result.point == ClickPoint(x=45, y=78, wait_ms=180)
    assert result.status_message == "已添加点 X=45, Y=78"


def test_apply_capture_request_keeps_negative_coordinates() -> None:
    result = apply_capture_request(CaptureRequest(kind="single"), -320, 120)

    assert result.fixed_position == (-320, 120)


def test_compute_capture_card_position_offsets_near_cursor() -> None:
    x, y = compute_capture_card_position(
        cursor_x=100,
        cursor_y=120,
        card_width=160,
        card_height=90,
        screen_x=0,
        screen_y=0,
        screen_width=1920,
        screen_height=1080,
    )

    assert x == 118
    assert y == 142


def test_compute_capture_card_position_clamps_to_virtual_screen_bounds() -> None:
    x, y = compute_capture_card_position(
        cursor_x=-1900,
        cursor_y=1060,
        card_width=160,
        card_height=90,
        screen_x=-1920,
        screen_y=0,
        screen_width=3840,
        screen_height=1080,
    )

    assert x == -1882
    assert y == 982
