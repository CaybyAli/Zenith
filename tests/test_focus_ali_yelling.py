from __future__ import annotations

from core.focus_switch_engine import FocusSwitchEngine
from core.gameplay_menu_detector import GameplayDetectionPoint
from core.voice_intensity_analyzer import VoiceIntensity, VoiceIntensityPoint
from models.transcript_result import TranscriptSegment


def test_ali_bruellen_gets_strong_facecam_focus() -> None:
    decisions = FocusSwitchEngine().decide(
        voice_intensity=[
            VoiceIntensityPoint(
                timestamp=0.0,
                intensity=VoiceIntensity.BRUELLEN,
                lufs=-10.0,
                rms_dbfs=-5.0,
                speaker="ali",
            )
        ],
        facial_expressions=[],
        speaker_segments=[
            TranscriptSegment(0.0, 1.0, "nein nein", speaker="ali"),
        ],
        gameplay_points=[
            GameplayDetectionPoint(
                timestamp=0.0,
                is_gameplay=True,
                score=0.8,
                signals={"motion": 0.8},
            )
        ],
        clip_duration=1.0,
    )

    assert decisions[0].focus_target == "facecam"
    assert decisions[0].facecam_zoom >= 1.8
    assert decisions[0].facecam_opacity == 1.0
    assert "ali_voice_intensity_bruellen" in decisions[0].reasoning
