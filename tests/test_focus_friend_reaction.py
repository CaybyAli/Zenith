from __future__ import annotations

from core.focus_switch_engine import FocusSwitchEngine
from core.gameplay_menu_detector import GameplayDetectionPoint
from models.transcript_result import TranscriptSegment


def _gameplay(timestamp: float) -> GameplayDetectionPoint:
    return GameplayDetectionPoint(
        timestamp=timestamp,
        is_gameplay=True,
        score=0.8,
        signals={"motion": 0.8},
    )


def test_friend_reaction_keyword_uses_real_german_gaming_vocab() -> None:
    decisions = FocusSwitchEngine().decide(
        voice_intensity=[],
        facial_expressions=[],
        speaker_segments=[
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=1.0,
                text="diggah wallah was war das hahaha",
                speaker="friend",
                audio_track="discord",
            )
        ],
        gameplay_points=[_gameplay(0.0)],
        clip_duration=1.0,
    )

    assert decisions[0].focus_target == "gameplay"
    assert decisions[0].gameplay_zoom == 1.3
    assert decisions[0].facecam_opacity == 0.3
    assert decisions[0].confidence > 0.6
    assert "friend_keyword" in decisions[0].reasoning


def test_short_negative_keyword_matches_token_not_substring() -> None:
    decisions = FocusSwitchEngine().decide(
        voice_intensity=[],
        facial_expressions=[],
        speaker_segments=[
            TranscriptSegment(0.0, 1.0, "nervig gespielt", speaker="friend"),
        ],
        gameplay_points=[_gameplay(0.0)],
        clip_duration=1.0,
    )

    assert decisions[0].focus_target == "balanced"
    assert decisions[0].reasoning == "friend_speaking_no_keyword"
