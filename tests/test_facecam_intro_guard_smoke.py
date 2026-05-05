from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.facecam_intro_guard import FacecamIntroGuard
from models.edit_timeline import EditTimeline
from models.facecam_reaction_result import FacecamReactionResult, FacecamReactionWindow
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment


JOB_ID = "job_facecam_intro_guard_smoke"
TIMELINE_ID = "timeline_facecam_intro_guard_smoke"


def _segment(
    segment_id: str,
    start_time: float,
    end_time: float,
    role: str,
) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{segment_id}",
        start_time=start_time,
        end_time=end_time,
        segment_role=role,
        selection_score=0.8,
        notes=[],
        source="facecam_intro_guard_smoke",
    )


def _instruction(segment_id: str, layout_kind: str) -> FramingInstruction:
    return FramingInstruction(
        instruction_id=f"frame_{segment_id}",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        segment_id=segment_id,
        focus_kind="facecam" if layout_kind == "facecam_emphasis" else "balanced",
        layout_kind=layout_kind,
        source_aspect_ratio="32:9",
        target_aspect_ratio="16:9",
        crop_window={"x": 0.0, "y": 0.0, "width": 0.5, "height": 1.0},
        notes=[],
        metadata={},
    )


def test_facecam_intro_guard_smoke() -> None:
    hook = _segment("seg_hook_long", 0.0, 14.0, "hook")
    long_no_reaction = _segment("seg_long_no_reaction", 30.0, 39.0, "bridge")
    short_reaction = _segment("seg_short_reaction", 50.0, 53.0, "bridge")
    timeline = EditTimeline(
        timeline_id=TIMELINE_ID,
        job_id=JOB_ID,
        target_duration=26.0,
        selected_segments=[hook, long_no_reaction, short_reaction],
        hook_segment_id=hook.segment_id,
        timeline_score=0.8,
    )
    reframe_plan = ReframePlan(
        plan_id="reframe_facecam_intro_guard_smoke",
        job_id=JOB_ID,
        timeline_id=TIMELINE_ID,
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        secondary_target_aspect_ratio="9:16",
        instructions=[
            _instruction(hook.segment_id, "facecam_emphasis"),
            _instruction(long_no_reaction.segment_id, "facecam_emphasis"),
            _instruction(short_reaction.segment_id, "facecam_emphasis"),
        ],
        plan_notes=[],
        plan_score=0.8,
    )
    reaction_result = FacecamReactionResult(
        windows=[],
        reaction_windows=[
            FacecamReactionWindow(
                start_seconds=50.2,
                end_seconds=52.6,
                reaction_score=0.85,
                motion_score=0.8,
                expression_change_score=0.8,
                label="strong_facecam_reaction",
                reason="synthetic short reaction",
            )
        ],
        average_reaction_score=0.3,
        max_reaction_score=0.85,
    )

    before_layout = reframe_plan.instructions[0].layout_kind
    summary = FacecamIntroGuard().apply(timeline, reframe_plan, reaction_result)
    by_segment = {
        instruction.segment_id: instruction
        for instruction in reframe_plan.instructions
    }

    after_layout = by_segment[hook.segment_id].layout_kind
    long_after_layout = by_segment[long_no_reaction.segment_id].layout_kind
    short_after_layout = by_segment[short_reaction.segment_id].layout_kind

    assert before_layout == "facecam_emphasis"
    assert after_layout in {"balanced_split", "gameplay_crop"}
    assert long_after_layout in {"balanced_split", "gameplay_crop"}
    assert short_after_layout == "facecam_emphasis"

    assert summary.intro_blocked >= 1
    assert summary.converted >= 2
    assert summary.limited >= 2
    assert summary.no_reaction_blocked >= 2
    assert summary.allowed_short_reactions == 1

    assert "intro_facecam_only_blocked" in by_segment[hook.segment_id].notes
    assert "facecam_only_limited" in by_segment[long_no_reaction.segment_id].notes
    assert "facecam_intro_guard_allowed_short_reaction" in by_segment[short_reaction.segment_id].notes

    for segment in timeline.selected_segments:
        assert segment.start_time >= 0.0
        assert segment.end_time > segment.start_time

    print(f"before_layout={before_layout}")
    print(f"after_layout={after_layout}")
    print(f"long_after_layout={long_after_layout}")
    print(f"short_reaction_layout={short_after_layout}")
    print(f"intro_blocked_count={summary.intro_blocked}")
    print(f"converted_count={summary.converted}")
    print(f"short_reaction_allowed={summary.allowed_short_reactions}")
    print("FACECAM INTRO GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    test_facecam_intro_guard_smoke()
