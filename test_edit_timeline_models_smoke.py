from __future__ import annotations

from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment


def main() -> None:
    segment_1 = TimelineSegment(
        segment_id="seg_001",
        job_id="job_timeline_models_smoke",
        candidate_id="cand_001",
        start_time=10.0,
        end_time=24.0,
        segment_role="hook",
        selection_score=0.91,
        notes=["strong opener"],
        source="timeline_builder",
    )

    segment_2 = TimelineSegment(
        segment_id="seg_002",
        job_id="job_timeline_models_smoke",
        candidate_id="cand_002",
        start_time=45.0,
        end_time=63.0,
        segment_role="peak",
        selection_score=0.88,
        notes=["high intensity"],
        source="timeline_builder",
    )

    timeline = EditTimeline(
        timeline_id="timeline_001",
        job_id="job_timeline_models_smoke",
        target_duration=600.0,
        selected_segments=[segment_1, segment_2],
        hook_segment_id=segment_1.segment_id,
        peak_segment_ids=[segment_2.segment_id],
        payoff_segment_id=segment_2.segment_id,
        timeline_score=0.86,
        timeline_notes=["basic longform structure created"],
    )

    assert segment_1.duration == 14.0
    assert segment_2.duration == 18.0
    assert timeline.total_selected_duration == 32.0
    assert timeline.hook_segment_id == "seg_001"
    assert timeline.peak_segment_ids == ["seg_002"]
    assert timeline.payoff_segment_id == "seg_002"

    print("EDIT TIMELINE MODELS SMOKE TEST PASSED")
    print(
        {
            "segments": len(timeline.selected_segments),
            "total_selected_duration": timeline.total_selected_duration,
            "timeline_score": timeline.timeline_score,
        }
    )


if __name__ == "__main__":
    main()