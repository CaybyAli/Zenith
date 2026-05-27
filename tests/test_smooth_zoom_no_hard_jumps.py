from __future__ import annotations

from core.smooth_zoom_engine import SmoothZoomEngine, ZoomCurve, ZoomKeyframe


def test_enforce_no_hard_jumps_moves_too_close_keyframes() -> None:
    engine = SmoothZoomEngine()
    curve = ZoomCurve(
        [
            ZoomKeyframe(0.0, 1.0, "balanced", "linear"),
            ZoomKeyframe(0.2, 2.0, "facecam", "ease_out_quad"),
        ]
    )

    smoothed = engine.enforce_no_hard_jumps(curve)

    assert engine.find_hard_jumps(smoothed) == []
    assert smoothed.keyframes[1].timestamp >= 0.5


def test_built_curve_has_no_adjacent_hard_jumps() -> None:
    engine = SmoothZoomEngine()
    curve = engine.build_curve_from_triggers(
        voice_intensity=[],
        facial_expressions=[],
        speaker_segments=[],
        gameplay_points=[],
        clip_duration=3.0,
    )

    assert engine.find_hard_jumps(curve) == []
