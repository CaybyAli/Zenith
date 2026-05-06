from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.sentence_atomicity_guard import SentenceAtomicityGuard
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.round_phase_result import RoundPhase, RoundPhaseResult, RoundPhaseWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


JOB_ID = "job_sentence_atomicity_guard_smoke"


def _seg(seg_id: str, start: float, end: float, role: str = "build") -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{seg_id}",
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.75,
    )


def _sentence(sentence_id: str, start: float, end: float, text: str = "Die Katze findet den Ball gut") -> SentenceItem:
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


def _sentences(*items: SentenceItem) -> SentenceTimelineResult:
    return SentenceTimelineResult(sentences=list(items))


def _transcript(*segments: TranscriptSegment) -> TranscriptResult:
    return TranscriptResult(
        source_path="synthetic.mp4",
        language="de",
        segments=list(segments),
        full_text=" ".join(segment.text for segment in segments),
        engine="synthetic",
    )


def _t(start: float, end: float, text: str = "Die Katze findet den Ball gut") -> TranscriptSegment:
    return TranscriptSegment(start_seconds=start, end_seconds=end, text=text, confidence=0.9)


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
    negative_types = {"menu_or_idle", "low_gameplay_value", "round_end_dead_time", "silence_or_dead_air", "filler_sentence"}
    return CutIndicator(
        indicator_id=f"indicator_{indicator_type}_{start}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=score,
        source="sentence_atomicity_guard_smoke",
        reason="synthetic",
        polarity="negative" if indicator_type in negative_types else "positive",
        channel_scope="all",
    )


def _state(state_type: str, start: float, end: float, score: float = 0.9) -> GameplayStateWindow:
    return GameplayStateWindow(
        window_id=f"state_{state_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        state_type=state_type,
        score=score,
        confidence=score,
        motion_score=0.8 if state_type in {"active_gameplay", "high_motion_action", "possible_goal_or_flash"} else 0.05,
        scene_change_score=0.1,
        visual_activity_score=0.8 if state_type in {"active_gameplay", "high_motion_action", "possible_goal_or_flash"} else 0.05,
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


def _assert_invariants(segments: list[TimelineSegment]) -> None:
    assert [segment.start_time for segment in segments] == sorted(segment.start_time for segment in segments)
    for index in range(len(segments) - 1):
        assert segments[index + 1].start_time >= segments[index].end_time
    for segment in segments:
        if segment.segment_role not in {"hook", "peak", "payoff"}:
            assert segment.duration >= 2.5


def test_partial_sentence_start_fixed_or_removed() -> None:
    result, summary = SentenceAtomicityGuard().apply(
        [_seg("partial_start", 13.5, 20.0)],
        sentence_timeline_result=_sentences(_sentence("s_start", 10.0, 15.0)),
    )
    assert result == [] or result[0].start_time <= 10.0
    assert not result or result[0].start_time != 13.5
    assert summary.sentence_start_fixed + summary.sentence_partial_removed >= 1


def test_partial_sentence_end_fixed_or_removed() -> None:
    result, summary = SentenceAtomicityGuard().apply(
        [_seg("partial_end", 5.0, 13.0)],
        sentence_timeline_result=_sentences(_sentence("s_end", 10.0, 15.0)),
    )
    # R2: segment starts at 5s < FIRST_CONTEXT_PROTECTION (30s) and the trim is large
    # (>1.5s), so the guard keeps the segment as-is (first_context_kept).
    # Accept either old behavior (fixed/removed) or R2 first-context keep.
    kept_by_r2 = summary.first_context_kept >= 1
    fixed_or_removed = (
        result == []
        or result[0].end_time >= 15.0
        or result[0].end_time <= 10.0
    )
    assert fixed_or_removed or kept_by_r2, (
        f"end_time={result[0].end_time if result else 'N/A'} not fixed, removed, or r2-kept"
    )
    assert (
        summary.sentence_end_fixed + summary.sentence_partial_removed + summary.first_context_kept >= 1
    )


def test_secondary_speech_atomicity() -> None:
    result, summary = SentenceAtomicityGuard().apply(
        [_seg("secondary", 32.0, 40.0)],
        audio_role_result=AudioRoleResult(windows=[_audio("secondary_speech_like", 30.0, 35.0)]),
    )
    assert result == [] or result[0].start_time <= 30.0
    assert not result or result[0].start_time != 32.0
    assert summary.secondary_sentence_fixed + summary.secondary_sentence_removed >= 1


def test_micro_segment_removal() -> None:
    result, summary = SentenceAtomicityGuard().apply([_seg("micro", 50.0, 51.0, role="build")])
    assert result == []
    assert summary.micro_segments_removed >= 1


def test_protected_micro_segment_kept() -> None:
    result, summary = SentenceAtomicityGuard().apply(
        [_seg("micro_goal", 60.0, 61.0, role="peak")],
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("goal_or_save_like_flash", 60.0, 61.0)]),
    )
    assert [segment.segment_id for segment in result] == ["micro_goal"]
    assert summary.micro_segments_removed == 0


def test_smart_action_lead_trim() -> None:
    result, summary = SentenceAtomicityGuard().apply(
        [_seg("lead", 100.0, 110.0)],
        gameplay_state_result=_states(
            _state("low_motion_wait", 100.0, 104.0),
            _state("active_gameplay", 105.0, 110.0),
        ),
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("high_action_burst", 105.0, 106.0)]),
    )
    assert 100.0 < result[0].start_time <= 104.2
    assert summary.action_lead_trimmed >= 1


def test_round_start_with_action_protected() -> None:
    result, summary = SentenceAtomicityGuard().apply(
        [_seg("round_action", 120.0, 130.0)],
        gameplay_state_result=_states(
            _state("menu_wait", 120.0, 126.0),
            _state("possible_goal_or_flash", 126.0, 128.0),
        ),
        round_phase_result=_phases(_phase(RoundPhase.COUNTDOWN_KICKOFF, 120.0, 126.0)),
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("goal_or_save_like_flash", 126.0, 127.0)]),
    )
    assert len(result) == 1
    assert 120.0 < result[0].start_time < 126.0
    assert summary.round_start_action_protected >= 1


def test_final_invariants() -> None:
    result, _ = SentenceAtomicityGuard().apply(
        [
            _seg("later", 7.5, 12.0),
            _seg("hook", 0.0, 8.0, role="hook"),
            _seg("short", 12.2, 13.0),
            _seg("payoff", 14.0, 20.0, role="payoff"),
        ]
    )
    _assert_invariants(result)


def test_sentence_atomicity_guard_smoke() -> None:
    test_partial_sentence_start_fixed_or_removed()
    test_partial_sentence_end_fixed_or_removed()
    test_secondary_speech_atomicity()
    test_micro_segment_removal()
    test_protected_micro_segment_kept()
    test_smart_action_lead_trim()
    test_round_start_with_action_protected()
    test_final_invariants()
    print("SENTENCE ATOMICITY GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    test_sentence_atomicity_guard_smoke()
