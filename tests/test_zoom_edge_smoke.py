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


JOB_ID = "job_zoom_edge_smoke"
TIMELINE_ID = "timeline_zoom_edge_smoke"


def _segment() -> TimelineSegment:
    return TimelineSegment(
        segment_id="seg_zoom_edge",
        job_id=JOB_ID,
        candidate_id="cand_zoom_edge",
        start_time=10.0,
        end_time=20.0,
        segment_role="peak",
        selection_score=0.9,
    )


def _zoom(zoom_id: str, start: float, end: float) -> ZoomInstruction:
    return ZoomInstruction(
        instruction_id=zoom_id,
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        segment_id="seg_zoom_edge",
        moment_id=f"moment_{zoom_id}",
        zoom_kind="punch_in_facecam",
        focus_kind="facecam",
        intensity=0.9,
        start_time=start,
        end_time=end,
    )


def test_zoom_edge_smoke() -> None:
    segment = _segment()
    timeline = EditTimeline(
        timeline_id=TIMELINE_ID,
        job_id=JOB_ID,
        target_duration=segment.duration,
        selected_segments=[segment],
        peak_segment_ids=[segment.segment_id],
        timeline_score=0.9,
    )
    plan = DynamicEditPlan(
        plan_id="dynamic_zoom_edge_smoke",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        zoom_instructions=[
            _zoom("drop_start_edge", 10.2, 12.0),
            _zoom("keep_middle_a", 12.0, 14.0),
            _zoom("keep_middle_b", 15.0, 17.0),
            _zoom("drop_end_edge", 18.4, 19.5),
        ],
    )

    summary = FacecamZoomSmoothnessGuard().apply(timeline, plan)
    remaining = [zoom.instruction_id for zoom in plan.zoom_instructions]

    assert remaining == ["keep_middle_a", "keep_middle_b"]
    assert summary.edge_blocked == 2
    assert summary.removed == 2
    print("ZOOM EDGE SMOKE TEST PASSED")


if __name__ == "__main__":
    test_zoom_edge_smoke()
