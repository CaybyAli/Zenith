from __future__ import annotations

from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan


def main() -> None:
    instruction_1 = FramingInstruction(
        instruction_id="frame_001",
        job_id="job_reframe_models_smoke",
        timeline_id="timeline_reframe_001",
        segment_id="seg_001",
        focus_kind="facecam",
        layout_kind="facecam_emphasis",
        source_aspect_ratio="32:9",
        target_aspect_ratio="16:9",
        crop_window={
            "x": 0.05,
            "y": 0.10,
            "width": 0.55,
            "height": 0.80,
        },
        notes=["hook segment should emphasize reaction"],
        metadata={"role": "hook"},
    )

    instruction_2 = FramingInstruction(
        instruction_id="frame_002",
        job_id="job_reframe_models_smoke",
        timeline_id="timeline_reframe_001",
        segment_id="seg_002",
        focus_kind="gameplay",
        layout_kind="gameplay_crop",
        source_aspect_ratio="32:9",
        target_aspect_ratio="16:9",
        crop_window={
            "x": 0.20,
            "y": 0.08,
            "width": 0.60,
            "height": 0.84,
        },
        notes=["peak segment should prioritize gameplay"],
        metadata={"role": "peak"},
    )

    plan = ReframePlan(
        plan_id="reframe_plan_001",
        job_id="job_reframe_models_smoke",
        timeline_id="timeline_reframe_001",
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        secondary_target_aspect_ratio="9:16",
        instructions=[instruction_1, instruction_2],
        plan_notes=["basic reframing domain smoke test"],
        plan_score=0.82,
    )

    assert len(plan.instructions) == 2
    assert plan.instructions[0].focus_kind == "facecam"
    assert plan.instructions[1].focus_kind == "gameplay"
    assert plan.primary_target_aspect_ratio == "16:9"
    assert plan.secondary_target_aspect_ratio == "9:16"
    assert plan.plan_score == 0.82

    print("REFRAME MODELS SMOKE TEST PASSED")
    print(
        {
            "instructions": len(plan.instructions),
            "primary_target": plan.primary_target_aspect_ratio,
            "secondary_target": plan.secondary_target_aspect_ratio,
            "plan_score": plan.plan_score,
        }
    )


if __name__ == "__main__":
    main()