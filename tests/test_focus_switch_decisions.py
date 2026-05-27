from __future__ import annotations

from core.facial_expression_analyzer import FacialExpression, FacialExpressionPoint
from core.focus_switch_engine import FocusSwitchEngine
from core.gameplay_menu_detector import GameplayDetectionPoint
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


def _gameplay(timestamp: float, score: float) -> GameplayDetectionPoint:
    return GameplayDetectionPoint(
        timestamp=timestamp,
        is_gameplay=score > 0.5,
        score=score,
        signals={"motion": score},
    )


def test_focus_switch_priority_tree_covers_drop_facecam_balanced_and_gameplay() -> None:
    decisions = FocusSwitchEngine().decide(
        voice_intensity=[
            _voice(1.0, VoiceIntensity.SCHREIEN),
            _voice(2.0, VoiceIntensity.NORMAL),
            _voice(3.0, VoiceIntensity.NORMAL),
        ],
        facial_expressions=[],
        speaker_segments=[
            TranscriptSegment(1.0, 2.0, "laut", speaker="ali"),
            TranscriptSegment(2.0, 3.0, "ich rede", speaker="friend"),
            TranscriptSegment(3.0, 4.0, "boah krass", speaker="friend"),
        ],
        gameplay_points=[
            _gameplay(0.0, 0.2),
            _gameplay(1.0, 0.9),
            _gameplay(2.0, 0.8),
            _gameplay(3.0, 0.8),
        ],
    )

    by_time = {decision.timestamp: decision for decision in decisions}
    assert by_time[0.0].focus_target == "drop"
    assert by_time[1.0].focus_target == "facecam"
    assert by_time[1.0].facecam_zoom >= 1.5
    assert by_time[2.0].focus_target == "balanced"
    assert by_time[2.0].facecam_opacity == 0.7
    assert by_time[3.0].focus_target == "gameplay"
    assert by_time[3.0].gameplay_zoom >= 1.3


def test_focus_expression_drives_facecam_when_ali_speaks() -> None:
    decisions = FocusSwitchEngine().decide(
        voice_intensity=[_voice(0.0, VoiceIntensity.NORMAL)],
        facial_expressions=[
            FacialExpressionPoint(
                timestamp=0.0,
                expressions=[FacialExpression.SURPRISE],
                confidence_by_expression={FacialExpression.SURPRISE: 0.91},
            )
        ],
        speaker_segments=[
            TranscriptSegment(0.0, 1.0, "oh", speaker="ali"),
        ],
        gameplay_points=[_gameplay(0.0, 0.9)],
        clip_duration=1.0,
    )

    assert decisions[0].focus_target == "facecam"
    assert decisions[0].facecam_zoom == 2.5
    assert decisions[0].confidence >= 0.9


def test_focus_summary_counts_targets() -> None:
    engine = FocusSwitchEngine()
    decisions = engine.decide(
        voice_intensity=[],
        facial_expressions=[],
        speaker_segments=[],
        gameplay_points=[_gameplay(0.0, 0.9), _gameplay(1.0, 0.9)],
        clip_duration=2.0,
    )

    summary = engine.summarize(decisions)

    assert summary["decision_count"] == 2
    assert summary["focus_counts"]["gameplay"] == 2
