from __future__ import annotations

import os
import shutil

from core.edit_timeline_repository import EditTimelineRepository
from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment


def main() -> None:
    test_dir = os.path.join("tmp", "edit_timeline_repository_smoke")
    export_path = os.path.join(test_dir, "export")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    segment_1 = TimelineSegment(
        segment_id="seg_repo_001",
        job_id="job_edit_timeline_repository_smoke",
        candidate_id="cand_repo_001",
        start_time=12.0,
        end_time=30.0,
        segment_role="hook",
        selection_score=0.89,
        notes=["repo hook"],
        source="test",
    )

    segment_2 = TimelineSegment(
        segment_id="seg_repo_002",
        job_id="job_edit_timeline_repository_smoke",
        candidate_id="cand_repo_002",
        start_time=55.0,
        end_time=81.0,
        segment_role="peak",
        selection_score=0.91,
        notes=["repo peak"],
        source="test",
    )

    timeline = EditTimeline(
        timeline_id="timeline_repo_001",
        job_id="job_edit_timeline_repository_smoke",
        target_duration=420.0,
        selected_segments=[segment_1, segment_2],
        hook_segment_id=segment_1.segment_id,
        peak_segment_ids=[segment_2.segment_id],
        payoff_segment_id=segment_2.segment_id,
        timeline_score=0.90,
        timeline_notes=["repository smoke test"],
    )

    repo = EditTimelineRepository()
    saved_path = repo.save_timeline(export_path, timeline)
    loaded = repo.load_timeline(export_path)

    assert os.path.exists(saved_path)
    assert loaded is not None
    assert loaded.timeline_id == timeline.timeline_id
    assert loaded.job_id == timeline.job_id
    assert len(loaded.selected_segments) == 2
    assert loaded.hook_segment_id == "seg_repo_001"
    assert loaded.peak_segment_ids == ["seg_repo_002"]
    assert loaded.payoff_segment_id == "seg_repo_002"
    assert loaded.total_selected_duration == 44.0

    print("EDIT TIMELINE REPOSITORY SMOKE TEST PASSED")
    print(
        {
            "saved_path": saved_path,
            "segments": len(loaded.selected_segments),
            "timeline_score": loaded.timeline_score,
            "total_selected_duration": loaded.total_selected_duration,
        }
    )


if __name__ == "__main__":
    main()