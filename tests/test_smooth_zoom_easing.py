from __future__ import annotations

from core.smooth_zoom_engine import ease_in_out_cubic, ease_out_quad, easing_value


def test_ease_in_out_cubic_endpoints_and_midpoint() -> None:
    assert ease_in_out_cubic(0.0) == 0.0
    assert ease_in_out_cubic(1.0) == 1.0
    assert ease_in_out_cubic(0.5) == 0.5


def test_ease_out_quad_is_monotonic() -> None:
    values = [ease_out_quad(step / 10.0) for step in range(11)]

    assert values[0] == 0.0
    assert values[-1] == 1.0
    assert values == sorted(values)
    assert values[5] > 0.5


def test_easing_value_clamps_progress() -> None:
    assert easing_value("linear", -2.0) == 0.0
    assert easing_value("linear", 2.0) == 1.0
    assert easing_value("ease_out_quad", 2.0) == 1.0
