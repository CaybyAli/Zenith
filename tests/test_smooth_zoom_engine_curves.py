from __future__ import annotations

from core.facial_expression_analyzer import FacialExpression, FacialExpressionPoint
from core.gameplay_menu_detector import GameplayDetectionPoint
from core.smooth_zoom_engine import SmoothZoomEngine, ZoomCurve, ZoomKeyframe
from core.voice_intensity_analyzer import VoiceIntensity, VoiceIntensityPoint
from models.transcript_result import TranscriptSegment


def _voice(timestamp: float, intensity: VoiceIntensity) -> VoiceIntensityPoint:
    return VoiceIntensityPoint(
        timestamp=timestamp,
        intensity=intensity,
        lufs=-12.0,
        rms_dbfs=-7.0,
        speaker="ali",
    )


def _expression(
    timestamp: float,
    expression: FacialExpression,
    confidence: float = 1.0,
) -> FacialExpressionPoint:
    return FacialExpressionPoint(
        timestamp=timestamp,
        expressions=[expression],
        confidence_by_expression={expression: confidence},
    )


def _gameplay(timestamp: float, score: float = 0.9) -> GameplayDetectionPoint:
    return GameplayDetectionPoint(
        timestamp=timestamp,
        is_gameplay=score > 0.5,
        score=score,
        signals={"motion": score, "audio_activity": 0.0},
    )


def test_voice_intensity_builds_facecam_zoom_levels() -> None:
    curve = SmoothZoomEngine().build_curve_from_triggers(
        voice_intensity=[
            _voice(0.0, VoiceIntensity.NORMAL),
            _voice(1.0, VoiceIntensity.LEISE_ERHOEHT),
            _voice(2.0, VoiceIntensity.SCHREIEN),
            _voice(3.0, VoiceIntensity.BRUELLEN),
        ],
        facial_expressions=[],
        speaker_segments=[],
        gameplay_points=[_gameplay(i) for i in range(5)],
        clip_duration=5.0,
    )

    assert curve.max_zoom >= 1.8
    assert "facecam" in curve.targets
    assert curve.interpolate(2.0)[0] >= 1.4


def test_expression_trigger_can_override_voice_zoom() -> None:
    curve = SmoothZoomEngine().build_curve_from_triggers(
        voice_intensity=[_voice(1.0, VoiceIntensity.LEISE_ERHOEHT)],
        facial_expressions=[_expression(1.0, FacialExpression.SURPRISE, 1.0)],
        speaker_segments=[],
        gameplay_points=[_gameplay(1.0)],
        clip_duration=3.0,
    )

    assert curve.max_zoom >= 2.4
    assert curve.interpolate(1.0)[1] == "facecam"


def test_friend_reaction_targets_gameplay_zoom() -> None:
    curve = SmoothZoomEngine().build_curve_from_triggers(
        voice_intensity=[],
        facial_expressions=[],
        speaker_segments=[
            TranscriptSegment(
                start_seconds=1.0,
                end_seconds=2.0,
                text="boah was war das haha",
                speaker="friend",
                audio_track="discord",
            )
        ],
        gameplay_points=[_gameplay(1.0, 0.8)],
        clip_duration=4.0,
    )

    gameplay_frames = [keyframe for keyframe in curve.keyframes if keyframe.target == "gameplay"]
    assert gameplay_frames
    assert max(keyframe.zoom_factor for keyframe in gameplay_frames) >= 1.3


def test_to_ffmpeg_filter_contains_dynamic_crop_expression() -> None:
    curve = ZoomCurve(
        [
            ZoomKeyframe(0.0, 1.0, "balanced", "linear"),
            ZoomKeyframe(1.0, 1.5, "facecam", "ease_in_out_cubic"),
            ZoomKeyframe(2.0, 1.0, "balanced", "ease_out_quad"),
        ]
    )

    filter_text = SmoothZoomEngine().to_ffmpeg_filter(curve, fps=60)

    assert "crop=" in filter_text
    assert "between(t,0.000,1.000)" in filter_text
    assert "fps=60" in filter_text
