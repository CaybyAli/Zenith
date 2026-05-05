from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.cut_indicator_builder import CutIndicatorBuilder
from models.edit_signal import EditSignal
from models.edit_timeline import EditTimeline
from models.energy_curve_result import EnergyCurvePoint, EnergyCurveResult
from models.facecam_reaction_result import FacecamReactionResult, FacecamReactionWindow
from models.gameplay_vision_result import GameplayVisionResult, GameplayVisionWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


JOB_ID = "job_cut_indicator_builder_smoke"


def _signal(signal_type: str, start: float, end: float, strength: float) -> EditSignal:
    return EditSignal(
        signal_id=f"sig_{signal_type}",
        job_id=JOB_ID,
        start_time=start,
        end_time=end,
        signal_type=signal_type,
        strength=strength,
        confidence=0.8,
        tags=["mid_zone"],
        source="smoke",
        notes=[f"{signal_type} note"],
    )


def _transcript() -> TranscriptResult:
    return TranscriptResult(
        source_path="smoke.mp4",
        language="de",
        segments=[
            TranscriptSegment(1.0, 2.5, "Ja!", confidence=0.91),
            TranscriptSegment(3.0, 6.0, "Das ist ein normaler Satz mit Kontext.", confidence=0.87),
        ],
        full_text="Ja! Das ist ein normaler Satz mit Kontext.",
        engine="smoke-transcript",
    )


def _energy() -> EnergyCurveResult:
    peak = EnergyCurvePoint(
        point_id="energy_peak_1",
        job_id=JOB_ID,
        start_seconds=5.0,
        end_seconds=10.0,
        energy_score=0.8,
        signal_count=2,
        dominant_signals=["audio_peak"],
    )
    activity = EnergyCurvePoint(
        point_id="energy_activity_1",
        job_id=JOB_ID,
        start_seconds=10.0,
        end_seconds=15.0,
        energy_score=0.4,
        signal_count=1,
        dominant_signals=["motion_activity"],
    )
    return EnergyCurveResult(
        curve_id="curve_smoke",
        job_id=JOB_ID,
        points=[peak, activity],
        peak_points=[peak],
        average_energy=0.6,
        max_energy=0.8,
    )


def _vision() -> GameplayVisionResult:
    action = GameplayVisionWindow(
        start_seconds=12.0,
        end_seconds=13.0,
        motion_score=0.7,
        action_score=0.82,
        scene_change_score=0.3,
        label="action_candidate",
        reason="action smoke",
    )
    scene = GameplayVisionWindow(
        start_seconds=20.0,
        end_seconds=21.0,
        motion_score=0.5,
        action_score=0.4,
        scene_change_score=0.72,
        label="scene_change",
        reason="scene smoke",
    )
    return GameplayVisionResult(
        windows=[action, scene],
        action_windows=[action, scene],
        average_action_score=0.61,
        max_action_score=0.82,
    )


def _facecam() -> FacecamReactionResult:
    reaction = FacecamReactionWindow(
        start_seconds=14.0,
        end_seconds=15.0,
        reaction_score=0.77,
        motion_score=0.6,
        expression_change_score=0.4,
        label="facecam_reaction",
        reason="reaction smoke",
    )
    return FacecamReactionResult(
        windows=[reaction],
        reaction_windows=[reaction],
        average_reaction_score=0.77,
        max_reaction_score=0.77,
    )


def _timeline() -> EditTimeline:
    segment = TimelineSegment(
        segment_id="seg_smoke",
        job_id=JOB_ID,
        candidate_id="cand_smoke",
        start_time=30.0,
        end_time=40.0,
        segment_role="peak",
        selection_score=0.86,
        notes=["energy_boost"],
    )
    return EditTimeline(
        timeline_id="timeline_smoke",
        job_id=JOB_ID,
        target_duration=60.0,
        selected_segments=[segment],
        timeline_score=0.86,
    )


def _sentence_timeline() -> SentenceTimelineResult:
    return SentenceTimelineResult(
        sentences=[
            SentenceItem(
                sentence_id="sentence_hook",
                text="Wir waren komplett tot, aber dann kam Nils mit dem Save!",
                start_seconds=1.0,
                end_seconds=4.0,
                duration_seconds=3.0,
                score=0.86,
                confidence=0.9,
                sentence_kind="hook",
                source_segment_ids=["segment_000000", "segment_000001"],
                metadata={"word_count": 10},
            ),
            SentenceItem(
                sentence_id="sentence_filler",
                text="okay ja ähm",
                start_seconds=5.0,
                end_seconds=6.0,
                duration_seconds=1.0,
                score=0.18,
                confidence=0.8,
                sentence_kind="filler",
                source_segment_ids=["segment_000002"],
                metadata={"word_count": 3},
            ),
        ],
        engine="sentence-timeline-builder-v1",
    )


def test_empty_inputs_do_not_crash() -> None:
    result = CutIndicatorBuilder().build()

    assert result.indicators == []
    assert result.positive_count == 0
    assert result.negative_count == 0
    assert result.neutral_count == 0
    assert result.skipped_reason == "no indicators"


def test_builder_maps_existing_signals_to_cut_indicators() -> None:
    result = CutIndicatorBuilder().build(
        edit_signals=[
            _signal("audio_peak", 0.0, 1.0, 0.9),
            _signal("silence_zone", 2.0, 3.0, 0.1),
            _signal("low_motion_zone", 4.0, 5.0, 0.2),
        ],
        transcript_result=_transcript(),
        sentence_timeline_result=_sentence_timeline(),
        energy_curve_result=_energy(),
        gameplay_vision_result=_vision(),
        facecam_reaction_result=_facecam(),
        edit_timeline=_timeline(),
        channel_type="gaming_main",
    )

    by_type = {indicator.indicator_type: indicator for indicator in result.indicators}
    indicator_types = [indicator.indicator_type for indicator in result.indicators]

    assert by_type["audio_peak"].polarity == "positive"
    assert by_type["silence"].polarity == "negative"
    assert by_type["low_motion"].polarity == "negative"
    assert "speech_segment" in indicator_types
    assert by_type["speech_segment"].metadata["text_preview"]
    assert by_type["speech_segment"].start_seconds >= 0.0
    assert by_type["speech_segment"].end_seconds >= by_type["speech_segment"].start_seconds
    assert "energy_peak" in indicator_types
    assert 0.0 <= by_type["energy_peak"].score <= 1.0
    assert "gameplay_action" in indicator_types
    assert "facecam_reaction" in indicator_types
    assert "selected_segment" in indicator_types
    assert "hook_sentence" in indicator_types
    assert "filler_sentence" in indicator_types
    assert by_type["hook_sentence"].polarity == "positive"
    assert by_type["filler_sentence"].polarity == "negative"

    assert result.positive_count > 0
    assert result.negative_count > 0
    assert result.neutral_count > 0

    payload = result.to_dict()
    assert payload["engine"] == CutIndicatorBuilder.engine
    assert payload["indicators"]
    assert payload["positive_count"] == result.positive_count
    assert payload["negative_count"] == result.negative_count
    assert payload["neutral_count"] == result.neutral_count

    print("CUT INDICATOR BUILDER SMOKE TEST PASSED")
    print(f"total_indicators={len(result.indicators)}")
    print(f"positive_count={result.positive_count}")
    print(f"negative_count={result.negative_count}")
    print(f"neutral_count={result.neutral_count}")
    print(f"indicator_types={sorted(set(indicator_types))}")


if __name__ == "__main__":
    test_empty_inputs_do_not_crash()
    test_builder_maps_existing_signals_to_cut_indicators()
