from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.hard_speech_lock_guard import HardSpeechLockGuard
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


JOB_ID = "job_hard_speech_lock_smoke"


def _seg(seg_id: str, start: float, end: float, role: str = "build", score: float = 0.7) -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{seg_id}",
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=score,
    )


def _transcript(*segments: TranscriptSegment) -> TranscriptResult:
    return TranscriptResult(
        source_path="synthetic.mp4",
        language="de",
        segments=list(segments),
        full_text=" ".join(segment.text for segment in segments),
        engine="synthetic",
    )


def _t(start: float, end: float, text: str = "speech") -> TranscriptSegment:
    return TranscriptSegment(start_seconds=start, end_seconds=end, text=text)


def _sentence(sentence_id: str, start: float, end: float, text: str = "sentence") -> SentenceItem:
    return SentenceItem(
        sentence_id=sentence_id,
        text=text,
        start_seconds=start,
        end_seconds=end,
        duration_seconds=round(end - start, 3),
        score=0.75,
        confidence=0.9,
        sentence_kind="normal",
    )


def _sentences(*sentences: SentenceItem) -> SentenceTimelineResult:
    return SentenceTimelineResult(sentences=list(sentences))


def _audio(role_type: str, start: float, end: float, score: float = 0.85) -> AudioRoleWindow:
    return AudioRoleWindow(
        window_id=f"audio_{role_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        role_type=role_type,
        score=score,
        confidence=0.85,
        reason="synthetic",
    )


def _indicator(indicator_type: str, start: float, end: float, score: float = 0.9) -> CutIndicator:
    return CutIndicator(
        indicator_id=f"ind_{indicator_type}_{start}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=0.85,
        source="hard_speech_lock_smoke",
        reason="synthetic",
        polarity="positive",
        channel_scope="all",
    )


def _state(state_type: str, start: float, end: float) -> GameplayStateWindow:
    return GameplayStateWindow(
        window_id=f"state_{state_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        state_type=state_type,
        score=0.85,
        confidence=0.85,
        motion_score=0.8,
        scene_change_score=0.2,
        visual_activity_score=0.8,
        reason="synthetic",
    )


def test_word_end_cut_extends_or_trims_cleanly() -> None:
    result, summary = HardSpeechLockGuard().apply(
        [_seg("word_end", 8.0, 15.0)],
        transcript_result=_transcript(_t(10.0, 17.0, "jeden tag fuer fuenf stu")),
    )
    assert len(result) == 1
    assert result[0].end_time != 15.0
    assert not (10.0 < result[0].end_time < 17.0)
    assert result[0].end_time >= 17.35 or result[0].end_time <= 9.8
    assert summary.word_end_locked + summary.word_end_trimmed_back >= 1


def test_word_start_cut_pulls_back() -> None:
    result, summary = HardSpeechLockGuard().apply(
        [_seg("word_start", 21.0, 30.0)],
        transcript_result=_transcript(_t(20.0, 24.0, "nils spricht hier")),
    )
    assert result[0].start_time <= 19.75
    assert summary.word_start_locked >= 1


def test_sentence_end_cut_extends_or_trims_cleanly() -> None:
    result, summary = HardSpeechLockGuard().apply(
        [_seg("sentence_end", 35.0, 44.0)],
        sentence_timeline_result=_sentences(_sentence("s1", 40.0, 48.0, "ganzer satz")),
    )
    assert result[0].end_time != 44.0
    assert not (40.0 < result[0].end_time < 48.0)
    assert result[0].end_time >= 48.45 or result[0].end_time <= 39.8
    assert summary.sentence_end_locked + summary.sentence_end_trimmed_back >= 1


def test_phrase_lock_keeps_alles_gut() -> None:
    result, summary = HardSpeechLockGuard().apply(
        [_seg("phrase", 95.0, 102.0)],
        transcript_result=_transcript(_t(100.0, 104.0, "alles gut alles gut")),
    )
    assert result[0].end_time >= 104.5
    assert summary.phrase_locked >= 1


def test_shout_lock_holds_postroll() -> None:
    result, summary = HardSpeechLockGuard().apply(
        [_seg("shout", 60.0, 71.0, role="peak")],
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("shout_like_audio", 70.0, 72.0)]),
    )
    assert result[0].end_time >= 72.7
    assert summary.shout_locked >= 1


def test_secondary_speech_lock_holds_postroll() -> None:
    result, summary = HardSpeechLockGuard().apply(
        [_seg("secondary", 80.0, 92.0)],
        audio_role_result=AudioRoleResult(windows=[_audio("secondary_speech_like", 90.0, 94.0)]),
    )
    assert result[0].end_time >= 94.35
    assert summary.secondary_end_locked >= 1


def test_micro_cut_killer_closes_speech_gap() -> None:
    result, summary = HardSpeechLockGuard().apply(
        [_seg("a", 0.0, 10.0, role="hook"), _seg("b", 11.0, 20.0, role="build")],
        transcript_result=_transcript(_t(9.5, 12.0, "same sentence keeps going")),
    )
    assert summary.micro_fixed > 0
    assert len(result) in {1, 2}
    if len(result) == 2:
        assert result[1].start_time - result[0].end_time <= 0.001


def test_short_useless_build_removed() -> None:
    result, summary = HardSpeechLockGuard().apply([_seg("short", 30.0, 32.0, role="build")])
    assert result == []
    assert summary.short_useless_removed >= 1


def test_action_preroll_moves_start_back() -> None:
    result, summary = HardSpeechLockGuard().apply(
        [_seg("action", 51.0, 60.0, role="peak")],
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("high_action_burst", 50.0, 55.0)]),
    )
    assert result[0].start_time <= 50.0
    assert summary.action_preroll_locked >= 1


def test_final_invariants() -> None:
    segments = [
        _seg("hook", 0.0, 8.0, role="hook"),
        _seg("overlap", 7.5, 12.0, role="build"),
        _seg("short_useless", 13.0, 14.0, role="bridge"),
        _seg("peak", 15.0, 22.0, role="peak"),
    ]
    result, _ = HardSpeechLockGuard().apply(
        segments,
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("goal_or_save_like_flash", 15.0, 17.0)]),
        gameplay_state_result=GameplayStateResult(windows=[_state("possible_goal_or_flash", 15.0, 17.0)]),
    )
    assert [segment.start_time for segment in result] == sorted(segment.start_time for segment in result)
    for index in range(len(result) - 1):
        assert result[index + 1].start_time >= result[index].end_time
    for segment in result:
        if segment.segment_role not in {"hook", "peak", "payoff"}:
            assert segment.duration >= 2.5


def test_hard_speech_lock_guard_smoke() -> None:
    test_word_end_cut_extends_or_trims_cleanly()
    test_word_start_cut_pulls_back()
    test_sentence_end_cut_extends_or_trims_cleanly()
    test_phrase_lock_keeps_alles_gut()
    test_shout_lock_holds_postroll()
    test_secondary_speech_lock_holds_postroll()
    test_micro_cut_killer_closes_speech_gap()
    test_short_useless_build_removed()
    test_action_preroll_moves_start_back()
    test_final_invariants()
    print("HARD SPEECH LOCK GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    test_hard_speech_lock_guard_smoke()
