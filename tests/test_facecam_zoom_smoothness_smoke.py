from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.facecam_zoom_smoothness_guard import FacecamZoomSmoothnessGuard
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment
from models.zoom_instruction import ZoomInstruction


JOB_ID = "job_facecam_zoom_smoothness_smoke"
TIMELINE_ID = "timeline_facecam_zoom_smoothness_smoke"


def _segment(start: float = 10.0, end: float = 20.0) -> TimelineSegment:
    return TimelineSegment(
        segment_id="seg_zoom",
        job_id=JOB_ID,
        candidate_id="cand_zoom",
        start_time=start,
        end_time=end,
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


def _indicator(indicator_type: str, start: float, end: float, score: float = 0.85) -> CutIndicator:
    return CutIndicator(
        indicator_id=f"ind_{indicator_type}_{start}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=0.85,
        source="facecam_zoom_smoothness_smoke",
        reason="synthetic",
        polarity="positive",
        channel_scope="all",
    )


def test_facecam_zoom_smoothness_smoke() -> None:
    segment = _segment(10.0, 20.0)
    plan = DynamicEditPlan(
        plan_id="dynamic_facecam_zoom_smoothness_smoke",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        zoom_instructions=[
            _zoom("zoom_start_edge", 10.1, 12.1),
            _zoom("zoom_end_edge", 17.8, 19.8),
            _zoom("zoom_short", 13.0, 13.8, intensity=0.75),
            _zoom("zoom_strong", 14.0, 15.4),
            _zoom("zoom_weak", 15.8, 17.2, intensity=0.55),
        ],
    )

    summary = FacecamZoomSmoothnessGuard().apply(_timeline(segment), plan)
    by_id = {zoom.instruction_id: zoom for zoom in plan.zoom_instructions}

    assert "zoom_start_edge" not in by_id
    assert "zoom_end_edge" not in by_id
    assert "zoom_short" not in by_id
    assert "zoom_weak" not in by_id
    assert "zoom_strong" in by_id

    assert summary.edge_blocked >= 2
    assert summary.short_removed >= 1
    assert summary.weak_reaction_removed >= 1

    for zoom in plan.zoom_instructions:
        assert zoom.start_time >= segment.start_time
        assert zoom.end_time <= segment.end_time
        assert zoom.start_time >= 0.0
        assert zoom.end_time > zoom.start_time
        assert zoom.duration >= 1.4 or zoom.intensity >= 0.85

    print("FACECAM ZOOM SMOOTHNESS SMOKE TEST PASSED")


def test_zoom_without_speech_or_reaction_removed() -> None:
    segment = _segment()
    plan = DynamicEditPlan(
        plan_id="dynamic_silence_zoom_smoke",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        zoom_instructions=[_zoom("zoom_silence", 12.0, 14.0, intensity=0.9)],
    )
    audio = AudioRoleResult(windows=[_audio("silence_or_dead_air", 12.0, 14.0)])

    summary = FacecamZoomSmoothnessGuard().apply(_timeline(segment), plan, audio_role_result=audio)
    assert plan.zoom_instructions == []
    assert summary.silence_removed == 1
    print("FACECAM ZOOM SILENCE REMOVAL PASSED")


def test_zoom_after_goal_tail_trimmed() -> None:
    segment = _segment(10.0, 25.0)
    plan = DynamicEditPlan(
        plan_id="dynamic_tail_zoom_smoke",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        zoom_instructions=[_zoom("zoom_goal_tail", 16.0, 21.0, intensity=0.9)],
    )
    audio = AudioRoleResult(windows=[_audio("shout_like_audio", 16.0, 17.0)])
    indicators = CutIndicatorResult(indicators=[_indicator("goal_or_save_like_flash", 16.0, 17.0)])

    summary = FacecamZoomSmoothnessGuard().apply(
        _timeline(segment),
        plan,
        audio_role_result=audio,
        cut_indicator_result=indicators,
    )
    assert len(plan.zoom_instructions) == 1
    assert plan.zoom_instructions[0].end_time <= 18.2
    assert summary.tail_trimmed == 1
    print("FACECAM ZOOM TAIL TRIM PASSED")


def test_close_zooms_are_deconflicted() -> None:
    segment = _segment(10.0, 25.0)
    plan = DynamicEditPlan(
        plan_id="dynamic_buffer_zoom_smoke",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        zoom_instructions=[
            _zoom("zoom_close_strong", 14.0, 15.6, intensity=0.86),
            _zoom("zoom_close_weak", 16.0, 17.6, intensity=0.74),
        ],
    )
    audio = AudioRoleResult(windows=[_audio("speech_active", 14.0, 17.6)])

    summary = FacecamZoomSmoothnessGuard().apply(_timeline(segment), plan, audio_role_result=audio)
    assert [zoom.instruction_id for zoom in plan.zoom_instructions] == ["zoom_close_strong"]
    assert summary.smooth_buffer_removed == 1
    print("FACECAM ZOOM SMOOTH BUFFER PASSED")


if __name__ == "__main__":
    test_facecam_zoom_smoothness_smoke()
    test_zoom_without_speech_or_reaction_removed()
    test_zoom_after_goal_tail_trimmed()
    test_close_zooms_are_deconflicted()
