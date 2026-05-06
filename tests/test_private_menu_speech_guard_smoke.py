from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.private_menu_speech_guard import PrivateMenuSpeechGuard
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.round_phase_result import RoundPhase, RoundPhaseResult, RoundPhaseWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


JOB_ID = "job_private_menu_speech_guard_smoke"


def _seg(seg_id: str, start: float, end: float, role: str = "bridge") -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{seg_id}",
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.75,
    )


def _state(state_type: str, start: float, end: float, score: float = 0.9) -> GameplayStateWindow:
    return GameplayStateWindow(
        window_id=f"state_{state_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        state_type=state_type,
        score=score,
        confidence=score,
        motion_score=0.8 if state_type in {"active_gameplay", "high_motion_action"} else 0.04,
        scene_change_score=0.1,
        visual_activity_score=0.8 if state_type in {"active_gameplay", "high_motion_action"} else 0.04,
        reason="synthetic",
    )


def _states(*windows: GameplayStateWindow) -> GameplayStateResult:
    return GameplayStateResult(windows=list(windows))


def _phase(phase: RoundPhase, start: float, end: float, confidence: float = 0.9) -> RoundPhaseWindow:
    return RoundPhaseWindow(
        start_seconds=start,
        end_seconds=end,
        phase=phase,
        confidence=confidence,
    )


def _phases(*windows: RoundPhaseWindow) -> RoundPhaseResult:
    return RoundPhaseResult(windows=list(windows))


def _audio(role_type: str, start: float, end: float, score: float = 0.9) -> AudioRoleWindow:
    return AudioRoleWindow(
        window_id=f"audio_{role_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        role_type=role_type,
        score=score,
        confidence=score,
        reason="synthetic",
    )


def _indicator(indicator_type: str, start: float, end: float, score: float = 0.9) -> CutIndicator:
    negative_types = {"menu_or_idle", "low_gameplay_value", "round_end_dead_time", "silence_or_dead_air"}
    return CutIndicator(
        indicator_id=f"indicator_{indicator_type}_{start}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=score,
        source="private_menu_speech_guard_smoke",
        reason="synthetic",
        polarity="negative" if indicator_type in negative_types else "positive",
        channel_scope="all",
    )


def _transcript(*segments: TranscriptSegment) -> TranscriptResult:
    return TranscriptResult(
        source_path="synthetic.mp4",
        language="de",
        segments=list(segments),
        full_text=" ".join(segment.text for segment in segments),
        engine="synthetic",
    )


def _t(start: float, end: float, text: str = "privates menue gespraech") -> TranscriptSegment:
    return TranscriptSegment(start_seconds=start, end_seconds=end, text=text, confidence=0.9)


def _sentence(sentence_id: str, start: float, end: float, text: str = "privater satz") -> SentenceItem:
    return SentenceItem(
        sentence_id=sentence_id,
        text=text,
        start_seconds=start,
        end_seconds=end,
        duration_seconds=round(end - start, 3),
        score=0.8,
        confidence=0.9,
        sentence_kind="normal",
    )


def _sentences(*sentences: SentenceItem) -> SentenceTimelineResult:
    return SentenceTimelineResult(sentences=list(sentences))


def _assert_invariants(segments: list[TimelineSegment]) -> None:
    assert [segment.start_time for segment in segments] == sorted(segment.start_time for segment in segments)
    for index in range(len(segments) - 1):
        assert segments[index + 1].start_time >= segments[index].end_time
    for segment in segments:
        if segment.segment_role not in {"hook", "peak", "payoff"}:
            assert segment.duration >= 2.5


def test_menu_speech_removed() -> None:
    result, summary = PrivateMenuSpeechGuard().apply(
        [_seg("menu_speech", 80.0, 110.0)],
        gameplay_state_result=_states(
            _state("menu_wait", 80.0, 95.0),
            _state("low_motion_wait", 95.0, 110.0),
        ),
        audio_role_result=AudioRoleResult(windows=[_audio("speech_active", 82.0, 108.0)]),
        transcript_result=_transcript(_t(82.0, 108.0)),
        sentence_timeline_result=_sentences(_sentence("s_menu", 82.0, 108.0)),
    )
    assert result == []
    assert summary.removed == 1
    assert summary.menu_sentences_removed >= 1


def test_active_gameplay_speech_kept() -> None:
    result, summary = PrivateMenuSpeechGuard().apply(
        [_seg("active_speech", 20.0, 35.0)],
        gameplay_state_result=_states(
            _state("active_gameplay", 20.0, 35.0),
            _state("high_motion_action", 23.0, 30.0),
        ),
        audio_role_result=AudioRoleResult(windows=[_audio("speech_active", 22.0, 32.0)]),
        transcript_result=_transcript(_t(22.0, 32.0, "gameplay call")),
    )
    assert [segment.segment_id for segment in result] == ["active_speech"]
    assert summary.active_speech_kept == 1


def test_true_round_start_shifted() -> None:
    result, summary = PrivateMenuSpeechGuard().apply(
        [_seg("round_start", 100.0, 130.0)],
        gameplay_state_result=_states(
            _state("menu_wait", 100.0, 112.0),
            _state("active_gameplay", 113.0, 130.0),
        ),
        round_phase_result=_phases(_phase(RoundPhase.COUNTDOWN_KICKOFF, 100.0, 112.0)),
        audio_role_result=AudioRoleResult(windows=[_audio("speech_active", 101.0, 111.0)]),
        transcript_result=_transcript(_t(101.0, 111.0, "gleich geht es los")),
    )
    assert result[0].start_time >= 113.0
    assert summary.round_start_shifted == 1


def test_menu_sentence_does_not_protect() -> None:
    result, summary = PrivateMenuSpeechGuard().apply(
        [_seg("menu_sentence", 88.0, 102.0)],
        gameplay_state_result=_states(_state("menu_wait", 88.0, 102.0)),
        audio_role_result=AudioRoleResult(windows=[_audio("secondary_speech_like", 90.0, 100.0)]),
        sentence_timeline_result=_sentences(_sentence("s_private", 90.0, 100.0)),
    )
    assert result == []
    assert summary.removed == 1
    assert summary.menu_sentences_removed >= 1


def test_round_end_tension_protected_and_menu_tail_trimmed() -> None:
    result, summary = PrivateMenuSpeechGuard().apply(
        [_seg("round_end_tension", 60.0, 85.0)],
        gameplay_state_result=_states(
            _state("high_motion_action", 60.0, 65.0),
            _state("round_end", 66.0, 70.0),
            _state("menu_wait", 70.0, 85.0),
        ),
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("high_action_burst", 60.0, 65.0)]),
        audio_role_result=AudioRoleResult(windows=[_audio("speech_active", 72.0, 84.0)]),
    )
    assert len(result) == 1
    assert result[0].start_time == 60.0
    assert result[0].end_time == 70.0
    assert summary.round_end_protected >= 1
    assert summary.trimmed >= 1


def test_no_overlaps_or_backjumps() -> None:
    result, summary = PrivateMenuSpeechGuard().apply(
        [
            _seg("later", 14.0, 20.0),
            _seg("hook", 0.0, 8.0, role="hook"),
            _seg("middle", 10.0, 15.0),
        ]
    )
    assert summary.overlap_fixed >= 1
    _assert_invariants(result)


def test_private_menu_speech_guard_smoke() -> None:
    test_menu_speech_removed()
    test_active_gameplay_speech_kept()
    test_true_round_start_shifted()
    test_menu_sentence_does_not_protect()
    test_round_end_tension_protected_and_menu_tail_trimmed()
    test_no_overlaps_or_backjumps()
    print("PRIVATE MENU SPEECH GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    test_private_menu_speech_guard_smoke()
