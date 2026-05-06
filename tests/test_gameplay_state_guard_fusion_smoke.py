from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.facecam_zoom_smoothness_guard import FacecamZoomSmoothnessGuard
from core.final_cut_seam_guard import FinalCutSeamGuard
from core.pre_action_context_guard import PreActionContextGuard
from core.round_wait_deadtime_guard import RoundWaitDeadtimeGuard
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment
from models.zoom_instruction import ZoomInstruction


JOB_ID = "job_gameplay_state_guard_fusion_smoke"
TIMELINE_ID = "timeline_gameplay_state_guard_fusion_smoke"


def _seg(seg_id: str, start: float, end: float, role: str = "bridge") -> TimelineSegment:
    return TimelineSegment(
        segment_id=seg_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{seg_id}",
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.75,
    )


def _state(state_type: str, start: float, end: float, score: float = 0.8) -> GameplayStateWindow:
    return GameplayStateWindow(
        window_id=f"state_{state_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        state_type=state_type,
        score=score,
        confidence=0.8,
        motion_score=0.1,
        scene_change_score=0.1,
        visual_activity_score=0.1,
        reason="synthetic state",
    )


def _states(*windows: GameplayStateWindow) -> GameplayStateResult:
    return GameplayStateResult(windows=list(windows))


def _audio(role_type: str, start: float, end: float, score: float = 0.85) -> AudioRoleWindow:
    return AudioRoleWindow(
        window_id=f"audio_{role_type}_{start}",
        start_seconds=start,
        end_seconds=end,
        role_type=role_type,
        score=score,
        confidence=0.85,
        reason="synthetic audio",
    )


def _indicator(indicator_type: str, start: float, end: float, polarity: str = "positive") -> CutIndicator:
    return CutIndicator(
        indicator_id=f"ind_{indicator_type}_{start}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=0.9,
        confidence=0.85,
        source="gameplay_state_guard_fusion_smoke",
        reason="synthetic indicator",
        polarity=polarity,
        channel_scope="all",
    )


def _timeline(segment: TimelineSegment) -> EditTimeline:
    return EditTimeline(
        timeline_id=TIMELINE_ID,
        job_id=JOB_ID,
        target_duration=segment.duration,
        selected_segments=[segment],
        peak_segment_ids=[segment.segment_id] if segment.segment_role == "peak" else [],
        timeline_score=0.9,
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


def test_round_wait_removes_menu_dominant_bridge() -> None:
    segment = _seg("wait_menu", 0.0, 10.0)
    result, summary = RoundWaitDeadtimeGuard().apply(
        [segment],
        gameplay_state_result=_states(_state("menu_wait", 0.0, 6.0)),
    )
    assert result == []
    assert summary.gameplay_state_removed == 1


def test_round_wait_protects_action_state_bridge() -> None:
    segment = _seg("action_bridge", 20.0, 30.0)
    result, summary = RoundWaitDeadtimeGuard().apply(
        [segment],
        gameplay_state_result=_states(
            _state("menu_wait", 20.0, 26.0),
            _state("high_motion_action", 24.0, 28.0),
        ),
    )
    assert [item.segment_id for item in result] == ["action_bridge"]
    assert summary.protected_by_action_state == 1
    assert summary.gameplay_state_removed == 0


def test_round_wait_trims_bad_wait_edge() -> None:
    segment = _seg("trim_wait", 40.0, 50.0)
    result, summary = RoundWaitDeadtimeGuard().apply(
        [segment],
        gameplay_state_result=_states(_state("low_motion_wait", 40.0, 44.0)),
    )
    assert len(result) == 1
    assert result[0].start_time == 44.0
    assert summary.gameplay_state_trimmed == 1


def test_pre_action_goal_state_backfills_three_seconds() -> None:
    segment = _seg("goal_context", 70.5, 76.0)
    result, summary = PreActionContextGuard().apply(
        [segment],
        gameplay_state_result=_states(_state("possible_goal_or_flash", 70.0, 70.5)),
    )
    assert result[0].start_time == 67.0
    assert summary.gameplay_state_backfilled == 1
    assert summary.goal_state_backfilled == 1


def test_pre_action_blocks_backfill_in_menu_wait() -> None:
    segment = _seg("blocked_context", 90.5, 96.0)
    result, summary = PreActionContextGuard().apply(
        [segment],
        gameplay_state_result=_states(
            _state("menu_wait", 87.0, 90.0),
            _state("possible_goal_or_flash", 90.0, 90.5),
        ),
    )
    assert result[0].start_time == 90.5
    assert summary.skipped_state_silence == 1


def test_facecam_zoom_removes_zoom_in_menu_wait() -> None:
    segment = _seg("seg_zoom", 100.0, 110.0, role="peak")
    plan = DynamicEditPlan(
        plan_id="plan_menu_zoom",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        zoom_instructions=[_zoom("zoom_menu", 102.0, 106.0, 0.9)],
    )
    summary = FacecamZoomSmoothnessGuard().apply(
        _timeline(segment),
        plan,
        gameplay_state_result=_states(_state("menu_wait", 102.0, 106.0)),
    )
    assert plan.zoom_instructions == []
    assert summary.state_zoom_removed == 1


def test_facecam_zoom_protects_shout_action_zoom() -> None:
    segment = _seg("seg_zoom", 120.0, 130.0, role="peak")
    plan = DynamicEditPlan(
        plan_id="plan_action_zoom",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        zoom_instructions=[_zoom("zoom_action", 122.0, 125.0, 0.8)],
    )
    summary = FacecamZoomSmoothnessGuard().apply(
        _timeline(segment),
        plan,
        audio_role_result=AudioRoleResult(windows=[_audio("shout_like_audio", 122.0, 125.0)]),
        gameplay_state_result=_states(_state("high_motion_action", 122.0, 125.0)),
    )
    assert [zoom.instruction_id for zoom in plan.zoom_instructions] == ["zoom_action"]
    assert summary.state_zoom_protected == 1


def test_facecam_zoom_drops_segment_edge_zoom() -> None:
    segment = _seg("seg_zoom", 140.0, 150.0, role="peak")
    plan = DynamicEditPlan(
        plan_id="plan_edge_zoom",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        zoom_instructions=[_zoom("zoom_edge", 140.2, 143.0, 0.9)],
    )
    summary = FacecamZoomSmoothnessGuard().apply(_timeline(segment), plan)
    assert plan.zoom_instructions == []
    assert summary.zoom_edge_hard_dropped == 1


def test_seam_guard_protects_speech_end_with_action_state() -> None:
    segment = _seg("seam_action", 160.0, 166.0)
    transcript = TranscriptResult(
        source_path="synthetic.mp4",
        language="de",
        full_text="leo",
        engine="synthetic",
        segments=[TranscriptSegment(165.0, 174.0, "LEO")],
    )
    result, summary = FinalCutSeamGuard().apply(
        [segment],
        transcript_result=transcript,
        cut_indicator_result=CutIndicatorResult(indicators=[_indicator("shout_like_audio", 165.5, 166.5)]),
        gameplay_state_result=_states(_state("high_motion_action", 165.5, 167.0)),
    )
    assert len(result) == 1
    assert result[0].end_time > 166.0
    assert summary.seam_state_protected >= 1
    assert summary.speech_end_trimmed_back == 0


def test_final_invariants_after_state_guards() -> None:
    segments = [
        _seg("hook", 0.0, 5.0, role="hook"),
        _seg("remove_wait", 5.2, 15.2, role="bridge"),
        _seg("action", 16.0, 22.0, role="build"),
    ]
    states = _states(
        _state("menu_wait", 5.2, 12.0),
        _state("high_motion_action", 16.0, 20.0),
    )
    round_wait_result, _ = RoundWaitDeadtimeGuard().apply(segments, gameplay_state_result=states)
    pre_action_result, _ = PreActionContextGuard().apply(round_wait_result, gameplay_state_result=states)

    starts = [segment.start_time for segment in pre_action_result]
    assert starts == sorted(starts)
    for index in range(len(pre_action_result) - 1):
        assert pre_action_result[index + 1].start_time >= pre_action_result[index].end_time
    for segment in pre_action_result:
        if segment.segment_role not in {"hook", "peak", "payoff"}:
            assert segment.duration >= 2.5


def test_gameplay_state_guard_fusion_smoke() -> None:
    test_round_wait_removes_menu_dominant_bridge()
    test_round_wait_protects_action_state_bridge()
    test_round_wait_trims_bad_wait_edge()
    test_pre_action_goal_state_backfills_three_seconds()
    test_pre_action_blocks_backfill_in_menu_wait()
    test_facecam_zoom_removes_zoom_in_menu_wait()
    test_facecam_zoom_protects_shout_action_zoom()
    test_facecam_zoom_drops_segment_edge_zoom()
    test_seam_guard_protects_speech_end_with_action_state()
    test_final_invariants_after_state_guards()
    print("GAMEPLAY STATE GUARD FUSION SMOKE TEST PASSED")


if __name__ == "__main__":
    test_gameplay_state_guard_fusion_smoke()
