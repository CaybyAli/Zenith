from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.round_phase_detector import RoundPhaseDetector
from models.analysis_result import AnalysisResult
from models.edit_signal import EditSignal
from models.gameplay_vision_result import GameplayVisionResult, GameplayVisionWindow
from models.job import Job
from models.round_phase_result import RoundPhase
from models.transcript_result import TranscriptResult, TranscriptSegment
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


JOB_ID = "job_round_phase_detector_smoke"


def _job() -> Job:
    return Job(
        job_id=JOB_ID,
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=[],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.9,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/round_phase_detector_smoke.mp4",
    )


def _analysis() -> AnalysisResult:
    return AnalysisResult(
        job_id=JOB_ID,
        duration_seconds=30.0,
        file_size_bytes=123456,
        usable_for_shorts=True,
        usable_for_longform=True,
        analysis_confidence=0.9,
        notes=[],
    )


def _signal(signal_type: str, start: float, end: float, strength: float) -> EditSignal:
    return EditSignal(
        signal_id=f"{signal_type}_{start}",
        job_id=JOB_ID,
        start_time=start,
        end_time=end,
        signal_type=signal_type,
        strength=strength,
        confidence=0.9,
        tags=[],
        source="round_phase_smoke",
        notes=[],
    )


def _vision() -> GameplayVisionResult:
    windows: list[GameplayVisionWindow] = []
    for second in range(0, 10):
        windows.append(GameplayVisionWindow(second, second + 1, 0.32, 0.28, 0.05, "active", "active round"))
    for second in range(10, 13):
        windows.append(GameplayVisionWindow(second, second + 1, 0.04, 0.03, 0.02, "dead", "round end"))
    for second in range(13, 25):
        windows.append(GameplayVisionWindow(second, second + 1, 0.02, 0.01, 0.01, "menu", "menu wait"))
    for second in range(25, 30):
        windows.append(GameplayVisionWindow(second, second + 1, 0.10, 0.10, 0.04, "kickoff", "countdown"))
    return GameplayVisionResult(
        windows=windows,
        action_windows=windows[:10],
        average_action_score=0.12,
        max_action_score=0.28,
    )


def _transcript() -> TranscriptResult:
    return TranscriptResult(
        source_path="round_phase_detector_smoke.mp4",
        language="de",
        full_text="drei zwei eins los",
        engine="smoke",
        segments=[
            TranscriptSegment(25.0, 29.0, "drei zwei eins los"),
        ],
    )


def test_round_phase_detector_smoke() -> None:
    result = RoundPhaseDetector().detect(
        job=_job(),
        analysis_result=_analysis(),
        edit_signals=[
            _signal("audio_activity", 0.0, 10.0, 0.75),
            _signal("low_motion_zone", 10.0, 25.0, 0.8),
            _signal("silence_zone", 13.0, 25.0, 0.9),
            _signal("audio_peak", 28.5, 29.5, 0.8),
        ],
        transcript_result=_transcript(),
        gameplay_vision_result=_vision(),
    )

    phases = {window.phase: window for window in result.windows}
    assert RoundPhase.ACTIVE_ROUND in phases
    assert RoundPhase.ROUND_END in phases
    assert RoundPhase.MENU_WAIT in phases
    assert RoundPhase.COUNTDOWN_KICKOFF in phases
    assert phases[RoundPhase.ACTIVE_ROUND].confidence > 0.5
    assert phases[RoundPhase.ROUND_END].confidence > 0.5
    assert phases[RoundPhase.MENU_WAIT].confidence > 0.5
    assert phases[RoundPhase.COUNTDOWN_KICKOFF].confidence > 0.5
    assert phases[RoundPhase.ROUND_END].start_seconds == 10.0
    assert phases[RoundPhase.MENU_WAIT].start_seconds == 13.0
    assert phases[RoundPhase.COUNTDOWN_KICKOFF].start_seconds == 25.0

    print("ROUND PHASE DETECTOR SMOKE TEST PASSED")


if __name__ == "__main__":
    test_round_phase_detector_smoke()
