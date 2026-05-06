from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.facecam_zoom_smoothness_guard import FacecamZoomSmoothnessGuard
from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment
from models.zoom_instruction import ZoomInstruction


JOB_ID = "job_facecam_zoom_smoothness_smoke"
TIMELINE_ID = "timeline_facecam_zoom_smoothness_smoke"


def _segment() -> TimelineSegment:
    return TimelineSegment(
        segment_id="seg_zoom",
        job_id=JOB_ID,
        candidate_id="cand_zoom",
        start_time=10.0,
        end_time=20.0,
        segment_role="peak",
        selection_score=0.9,
    )


def _zoom(zoom_id: str, start: float, end: float, intensity: float = 0.85) -> ZoomInstruction:
    return ZoomInstruction(
        instruction_id=zoom_id,
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        segment_id="seg_zoom",
        moment_id=f"moment_{zoom_id}",
        zoom_kind="punch_in_facecam",
        focus_kind="facecam",
        intensity=intensity,
        start_time=start,
        end_time=end,
    )


def _timeline(segment: TimelineSegment) -> EditTimeline:
    return EditTimeline(
        timeline_id=TIMELINE_ID,
        job_id=JOB_ID,
        target_duration=segment.duration,
        selected_segments=[segment],
        peak_segment_ids=[segment.segment_id],
        timeline_score=0.9,
    )


def test_facecam_zoom_smoothness_smoke() -> None:
    segment = _segment()
    plan = DynamicEditPlan(
        plan_id="dynamic_facecam_zoom_smoothness_smoke",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        zoom_instructions=[
            _zoom("zoom_start_edge", 10.1, 12.1),
            _zoom("zoom_end_edge", 17.8, 19.8),
            _zoom("zoom_short", 13.0, 13.8),
            _zoom("zoom_strong", 14.0, 15.4),
            _zoom("zoom_weak", 15.8, 17.2, intensity=0.55),
        ],
    )

    summary = FacecamZoomSmoothnessGuard().apply(_timeline(segment), plan)
    by_id = {zoom.instruction_id: zoom for zoom in plan.zoom_instructions}

    assert "zoom_start_edge" in by_id
    assert by_id["zoom_start_edge"].start_time >= segment.start_time + 0.6
    assert "zoom_end_edge" in by_id
    assert by_id["zoom_end_edge"].end_time <= segment.end_time - 0.6
    assert "zoom_short" not in by_id
    assert "zoom_weak" not in by_id
    assert "zoom_strong" in by_id

    assert summary.shifted >= 2
    assert summary.short_removed >= 1
    assert summary.weak_reaction_removed >= 1

    for zoom in plan.zoom_instructions:
        assert zoom.start_time >= segment.start_time
        assert zoom.end_time <= segment.end_time
        assert zoom.start_time >= 0.0
        assert zoom.end_time > zoom.start_time
        assert zoom.duration >= 1.2

    print("FACECAM ZOOM SMOOTHNESS SMOKE TEST PASSED")


if __name__ == "__main__":
    test_facecam_zoom_smoothness_smoke()
