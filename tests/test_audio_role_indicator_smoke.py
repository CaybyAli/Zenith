from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.audio_role_indicator_builder import AudioRoleIndicatorBuilder
from core.cut_indicator_builder import CutIndicatorBuilder
from models.edit_signal import EditSignal
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.transcript_result import TranscriptResult, TranscriptSegment


JOB_ID = "job_audio_role_indicator_smoke"


def _signal(signal_id: str, signal_type: str, start: float, end: float, strength: float) -> EditSignal:
    return EditSignal(
        signal_id=signal_id,
        job_id=JOB_ID,
        start_time=start,
        end_time=end,
        signal_type=signal_type,
        strength=strength,
        confidence=0.82,
        source="audio_role_smoke",
    )


def _transcript() -> TranscriptResult:
    return TranscriptResult(
        source_path="audio_role_smoke.mp4",
        language="de",
        segments=[
            TranscriptSegment(1.0, 2.4, "okay haha", confidence=0.9),
            TranscriptSegment(4.0, 5.3, "Alter was war das!", confidence=0.91),
            TranscriptSegment(8.0, 8.8, "komm mit", confidence=0.82),
        ],
        full_text="okay haha Alter was war das! komm mit",
        engine="smoke-transcript",
    )


def _sentence_timeline() -> SentenceTimelineResult:
    return SentenceTimelineResult(
        sentences=[
            SentenceItem(
                sentence_id="sentence_laugh",
                text="okay haha",
                start_seconds=1.0,
                end_seconds=2.4,
                duration_seconds=1.4,
                score=0.35,
                confidence=0.9,
                sentence_kind="normal",
                source_segment_ids=["segment_000000"],
            ),
            SentenceItem(
                sentence_id="sentence_shout",
                text="Alter was war das!",
                start_seconds=4.0,
                end_seconds=5.3,
                duration_seconds=1.3,
                score=0.74,
                confidence=0.91,
                sentence_kind="exclamation",
                source_segment_ids=["segment_000001"],
            ),
            SentenceItem(
                sentence_id="sentence_short",
                text="komm mit",
                start_seconds=8.0,
                end_seconds=8.8,
                duration_seconds=0.8,
                score=0.45,
                confidence=0.82,
                sentence_kind="normal",
                source_segment_ids=["segment_000002"],
            ),
        ],
        engine="sentence-timeline-builder-v1",
    )


def test_empty_inputs_do_not_crash() -> None:
    result = AudioRoleIndicatorBuilder().build()

    assert result.windows == []
    assert result.role_counts == {}
    assert result.skipped_reason == "no audio role windows"


def test_audio_role_indicator_smoke() -> None:
    edit_signals = [
        _signal("sig_laugh_activity", "audio_activity", 1.0, 2.2, 0.55),
        _signal("sig_shout_peak_a", "audio_peak", 4.0, 4.7, 0.92),
        _signal("sig_shout_activity", "audio_activity", 4.6, 5.1, 0.60),
        _signal("sig_shout_peak_b", "audio_peak", 5.0, 5.6, 0.88),
        _signal("sig_secondary_activity", "audio_activity", 8.0, 8.8, 0.58),
        _signal("sig_game_peak", "audio_peak", 12.0, 13.0, 0.78),
        _signal("sig_silence", "silence_zone", 15.0, 19.0, 0.10),
    ]

    result = AudioRoleIndicatorBuilder().build(
        edit_signals=edit_signals,
        transcript_result=_transcript(),
        sentence_timeline_result=_sentence_timeline(),
        channel_type="gaming_main",
    )

    role_counts = result.role_counts
    role_types = [window.role_type for window in result.windows]

    assert role_counts["speech_active"] == 3
    assert role_counts["laugh_like_audio"] >= 1
    assert role_counts["shout_like_audio"] >= 1
    assert role_counts["group_reaction_like"] >= 1
    assert role_counts["secondary_speech_like"] >= 1
    assert role_counts["game_audio_peak"] >= 1
    assert role_counts["silence_or_dead_air"] >= 1
    assert role_counts["speech_cut_risk_audio"] == 6

    payload = result.to_dict()
    assert payload["engine"] == AudioRoleIndicatorBuilder.engine
    assert payload["role_counts"] == role_counts
    assert payload["windows"]

    indicator_result = CutIndicatorBuilder().build(
        audio_role_result=result,
        channel_type="gaming_main",
    )
    indicator_types = [indicator.indicator_type for indicator in indicator_result.indicators]
    assert "speech_active" in indicator_types
    assert "silence_or_dead_air" in indicator_types
    assert "game_audio_peak" in indicator_types
    assert any(
        indicator.indicator_type == "silence_or_dead_air" and indicator.polarity == "negative"
        for indicator in indicator_result.indicators
    )

    print("AUDIO ROLE INDICATOR SMOKE TEST PASSED")
    print(f"total_windows={len(result.windows)}")
    print(f"role_counts={role_counts}")
    print(f"indicator_types={sorted(set(indicator_types))}")
    print(f"role_types={sorted(set(role_types))}")


if __name__ == "__main__":
    test_empty_inputs_do_not_crash()
    test_audio_role_indicator_smoke()
