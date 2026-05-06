from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.speech_safe_pacing_guard import MIN_FINAL_GAP_SECONDS, SpeechSafePacingGuard
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.round_phase_result import RoundPhase, RoundPhaseResult, RoundPhaseWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


JOB_ID = "job_speech_safe_pacing_smoke"


def _seg(seg_id: str, start: float, end: float, role: str = "bridge", score: float = 0.72) -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{seg_id}",
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=score,
    )


def _state(state_type: str, start: float, end: float, score: float = 0.85) -> GameplayStateWindow:
    return GameplayStateWindow(
        window_id=f"state_{state_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        state_type=state_type,
        score=score,
        confidence=0.85,
        motion_score=0.7,
        scene_change_score=0.2,
        visual_activity_score=0.7,
        reason="synthetic",
    )


def _states(*windows: GameplayStateWindow) -> GameplayStateResult:
    return GameplayStateResult(windows=list(windows))


def _phase(phase: RoundPhase, start: float, end: float, confidence: float = 0.85) -> RoundPhaseWindow:
    return RoundPhaseWindow(
        start_seconds=start,
        end_seconds=end,
        phase=phase,
        confidence=confidence,
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
        reason="synthetic",
    )


def _indicator(indicator_type: str, start: float, end: float, score: float = 0.9) -> CutIndicator:
    return CutIndicator(
        indicator_id=f"ind_{indicator_type}_{start}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=score,
        source="speech_safe_pacing_smoke",
        reason="synthetic",
        polarity="positive" if indicator_type not in {"silence_or_dead_air", "low_gameplay_value", "filler_sentence", "menu_or_idle"} else "negative",
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


def _t(start: float, end: float, text: str, confidence: float | None = None) -> TranscriptSegment:
    return TranscriptSegment(start_seconds=start, end_seconds=end, text=text, confidence=confidence)


def _sentence(sentence_id: str, start: float, end: float, text: str, score: float = 0.75) -> SentenceItem:
    return SentenceItem(
        sentence_id=sentence_id,
        text=text,
        start_seconds=start,
        end_seconds=end,
        duration_seconds=round(end - start, 3),
        score=score,
        confidence=score,
        sentence_kind="normal",
    )


def _sentences(*items: SentenceItem) -> SentenceTimelineResult:
    return SentenceTimelineResult(sentences=list(items))


def test_micro_gap_with_speech_or_action_is_closed() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("a", 0.0, 10.0, role="hook"), _seg("b", 10.5, 20.0)],
        audio_role_result=AudioRoleResult(windows=[_audio("speech_active", 9.8, 11.0)]),
    )
    assert summary.micro_gaps_closed >= 1
    assert result[1].start_time - result[0].end_time <= 0.001


def test_micro_gap_without_content_is_spaced_or_safe() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("a", 0.0, 10.0, role="hook"), _seg("b", 10.5, 20.0)],
    )
    gap = result[1].start_time - result[0].end_time
    assert summary.micro_gaps_spaced >= 0
    assert gap >= MIN_FINAL_GAP_SECONDS


def test_boring_wait_without_important_speech_removed() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("boring", 30.0, 40.0)],
        gameplay_state_result=_states(_state("low_motion_wait", 30.0, 40.0)),
        audio_role_result=AudioRoleResult(windows=[_audio("silence_or_dead_air", 30.0, 40.0)]),
    )
    assert result == []
    assert summary.boring_wait_removed >= 1


def test_neutral_speech_does_not_protect_wait() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("neutral_wait", 50.0, 65.0)],
        gameplay_state_result=_states(_state("menu_wait", 50.0, 65.0)),
        audio_role_result=AudioRoleResult(windows=[_audio("speech_active", 52.0, 60.0)]),
    )
    assert "neutral_wait" not in [segment.segment_id for segment in result]
    assert summary.neutral_speech_ignored >= 1


def test_important_speech_protects_wait() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("important_wait", 70.0, 80.0)],
        gameplay_state_result=_states(_state("low_motion_wait", 70.0, 80.0)),
        transcript_result=_transcript(_t(70.0, 80.0, "LEO LEO LEO")),
    )
    assert [segment.segment_id for segment in result] == ["important_wait"]
    assert summary.boring_wait_removed == 0


def test_round_end_tension_is_expanded_and_protected() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("round_end", 101.0, 108.0, role="build")],
        gameplay_state_result=_states(
            _state("high_motion_action", 90.0, 95.0),
            _state("round_end", 96.0, 108.0),
        ),
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("high_action_burst", 90.0, 95.0)]),
    )
    assert result[0].start_time < 101.0
    assert summary.round_end_context_expanded >= 1
    assert summary.round_end_protected >= 1


def test_round_start_wait_is_trimmed() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("round_start", 120.0, 145.0, role="bridge")],
        gameplay_state_result=_states(
            _state("menu_wait", 120.0, 135.0),
            _state("active_gameplay", 136.0, 145.0),
        ),
        round_phase_result=_phases(_phase(RoundPhase.COUNTDOWN_KICKOFF, 120.0, 135.0)),
    )
    assert result[0].start_time >= 135.0
    assert summary.round_start_wait_trimmed >= 1


def test_action_context_backfill() -> None:
    result, summary = SpeechSafePacingGuard().apply(
        [_seg("action", 200.0, 210.0, role="peak")],
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("high_action_burst", 199.5, 201.0)]),
    )
    assert result[0].start_time < 200.0
    assert summary.action_context_expanded >= 1


def test_final_invariants() -> None:
    result, _ = SpeechSafePacingGuard().apply(
        [
            _seg("hook", 0.0, 8.0, role="hook"),
            _seg("overlap", 7.5, 12.0, role="build"),
            _seg("short_wait", 12.2, 13.0, role="bridge"),
            _seg("payoff", 14.0, 20.0, role="payoff"),
        ],
        gameplay_state_result=_states(_state("low_motion_wait", 12.2, 13.0)),
    )
    starts = [segment.start_time for segment in result]
    assert starts == sorted(starts)
    for index in range(len(result) - 1):
        assert result[index + 1].start_time >= result[index].end_time
    for segment in result:
        if segment.segment_role not in {"hook", "peak", "payoff"}:
            assert segment.duration >= 2.5


def test_speech_safe_pacing_guard_smoke() -> None:
    test_micro_gap_with_speech_or_action_is_closed()
    test_micro_gap_without_content_is_spaced_or_safe()
    test_boring_wait_without_important_speech_removed()
    test_neutral_speech_does_not_protect_wait()
    test_important_speech_protects_wait()
    test_round_end_tension_is_expanded_and_protected()
    test_round_start_wait_is_trimmed()
    test_action_context_backfill()
    test_final_invariants()
    print("SPEECH SAFE PACING GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    test_speech_safe_pacing_guard_smoke()
