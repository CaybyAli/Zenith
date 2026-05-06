from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.hard_speech_lock_guard import HardSpeechLockGuard
from core.speech_safe_pacing_guard import SpeechSafePacingGuard
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.round_phase_result import RoundPhase, RoundPhaseResult, RoundPhaseWindow
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


JOB_ID = "job_menu_speech_removal_qa6q"


def _seg(seg_id: str, start: float, end: float, role: str = "bridge") -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{seg_id}",
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.74,
    )


def _state(state_type: str, start: float, end: float) -> GameplayStateWindow:
    return GameplayStateWindow(
        window_id=f"state_{state_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        state_type=state_type,
        score=0.9,
        confidence=0.9,
        motion_score=0.8,
        scene_change_score=0.1,
        visual_activity_score=0.8,
        reason="synthetic qa6q",
    )


def _states(*windows: GameplayStateWindow) -> GameplayStateResult:
    return GameplayStateResult(windows=list(windows))


def _phase(phase: RoundPhase, start: float, end: float) -> RoundPhaseWindow:
    return RoundPhaseWindow(
        start_seconds=start,
        end_seconds=end,
        phase=phase,
        confidence=0.9,
    )


def _phases(*windows: RoundPhaseWindow) -> RoundPhaseResult:
    return RoundPhaseResult(windows=list(windows))


def _audio(role_type: str, start: float, end: float, score: float = 0.85) -> AudioRoleWindow:
    return AudioRoleWindow(
        window_id=f"audio_{role_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        role_type=role_type,
        score=score,
        confidence=score,
        reason="synthetic qa6q",
    )


def _indicator(indicator_type: str, start: float, end: float, score: float = 0.9) -> CutIndicator:
    negative_types = {"menu_or_idle", "low_gameplay_value", "silence_or_dead_air", "round_end_dead_time"}
    return CutIndicator(
        indicator_id=f"ind_{indicator_type}_{start}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=score,
        source="qa6q_smoke",
        reason="synthetic qa6q",
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


def _t(start: float, end: float, text: str = "LEO LEO LEO") -> TranscriptSegment:
    return TranscriptSegment(start_seconds=start, end_seconds=end, text=text, confidence=0.9)


def _assert_timeline_invariants(segments: list[TimelineSegment]) -> None:
    assert [segment.start_time for segment in segments] == sorted(segment.start_time for segment in segments)
    for index in range(len(segments) - 1):
        assert segments[index + 1].start_time >= segments[index].end_time
    for segment in segments:
        if segment.segment_role not in {"hook", "peak", "payoff"}:
            assert segment.duration >= 2.5


def test_menu_speech_block_is_removed_as_whole_block() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("menu_speech", 10.0, 24.0)],
        gameplay_state_result=_states(_state("menu_wait", 10.0, 24.0)),
        round_phase_result=_phases(_phase(RoundPhase.MENU_WAIT, 10.0, 24.0)),
        audio_role_result=AudioRoleResult(windows=[_audio("speech_active", 12.0, 22.0)]),
        transcript_result=_transcript(_t(12.0, 22.0, "alles gut wir warten im menue")),
    )
    assert result == []
    assert summary.boring_wait_removed >= 1
    assert summary.neutral_speech_ignored >= 1


def test_active_gameplay_speech_remains() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("gameplay_speech", 30.0, 42.0)],
        gameplay_state_result=_states(_state("active_gameplay", 30.0, 42.0)),
        audio_role_result=AudioRoleResult(windows=[_audio("speech_active", 32.0, 40.0)]),
        transcript_result=_transcript(_t(32.0, 40.0, "jetzt passiert was im spiel")),
    )
    assert [segment.segment_id for segment in result] == ["gameplay_speech"]
    assert summary.boring_wait_removed == 0


def test_round_start_moves_to_visible_gameplay() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("round_start", 100.0, 132.0)],
        gameplay_state_result=_states(
            _state("menu_wait", 100.0, 116.0),
            _state("active_gameplay", 118.0, 132.0),
        ),
        round_phase_result=_phases(_phase(RoundPhase.COUNTDOWN_KICKOFF, 100.0, 116.0)),
        audio_role_result=AudioRoleResult(windows=[_audio("speech_active", 102.0, 114.0)]),
        transcript_result=_transcript(_t(102.0, 114.0, "wir starten gleich")),
    )
    assert result[0].start_time >= 117.0
    assert summary.round_start_wait_trimmed >= 1


def test_round_end_tension_stays_before_dead_time() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("round_end_tension", 211.0, 220.0)],
        gameplay_state_result=_states(
            _state("high_motion_action", 202.0, 210.0),
            _state("possible_dead_time_after_goal", 211.0, 220.0),
        ),
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("high_action_burst", 202.0, 210.0)]),
    )
    assert result[0].start_time < 211.0
    assert summary.round_end_context_expanded >= 1
    assert summary.round_end_protected >= 1


def test_hard_speech_lock_does_not_restore_menu_sentence() -> None:
    result, summary = HardSpeechLockGuard().apply(
        [_seg("menu_edge", 300.0, 308.0)],
        gameplay_state_result=_states(_state("menu_wait", 300.0, 310.0)),
        transcript_result=_transcript(_t(306.0, 312.0, "alles gut wir warten")),
    )
    assert result[0].end_time == 308.0
    assert summary.word_end_locked == 0
    assert summary.phrase_locked == 0


def test_qa6q_final_invariants() -> None:
    result, _ = SpeechSafePacingGuard().apply(
        [
            _seg("hook", 0.0, 8.0, role="hook"),
            _seg("menu_speech", 10.0, 22.0),
            _seg("round_start", 30.0, 60.0),
            _seg("gameplay", 62.0, 72.0, role="peak"),
            _seg("payoff", 80.0, 88.0, role="payoff"),
        ],
        gameplay_state_result=_states(
            _state("menu_wait", 10.0, 22.0),
            _state("menu_wait", 30.0, 45.0),
            _state("active_gameplay", 47.0, 72.0),
        ),
        audio_role_result=AudioRoleResult(windows=[_audio("speech_active", 12.0, 20.0)]),
        transcript_result=_transcript(_t(12.0, 20.0, "menue satz")),
    )
    assert "menu_speech" not in [segment.segment_id for segment in result]
    _assert_timeline_invariants(result)


def test_menu_speech_removal_qa6q_smoke() -> None:
    test_menu_speech_block_is_removed_as_whole_block()
    test_active_gameplay_speech_remains()
    test_round_start_moves_to_visible_gameplay()
    test_round_end_tension_stays_before_dead_time()
    test_hard_speech_lock_does_not_restore_menu_sentence()
    test_qa6q_final_invariants()
    print("MENU SPEECH REMOVAL QA6Q SMOKE TEST PASSED")


if __name__ == "__main__":
    test_menu_speech_removal_qa6q_smoke()
