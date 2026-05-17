from __future__ import annotations

from models.dynamic_edit_plan import DynamicEditPlan
from models.reaction_moment import ReactionMoment
from models.zoom_instruction import ZoomInstruction


def main() -> None:
    moment = ReactionMoment(
        moment_id="moment_001",
        job_id="job_dynamic_edit_models_smoke",
        timeline_id="timeline_001",
        segment_id="seg_001",
        start_time=12.0,
        end_time=15.5,
        reaction_kind="hook_reaction",
        intensity=0.88,
        confidence=0.82,
        notes=["strong opening reaction"],
    )

    zoom = ZoomInstruction(
        instruction_id="zoom_001",
        job_id="job_dynamic_edit_models_smoke",
        timeline_id="timeline_001",
        segment_id="seg_001",
        moment_id="moment_001",
        zoom_kind="hook_push",
        focus_kind="facecam",
        intensity=0.84,
        start_time=12.0,
        end_time=14.0,
        notes=["tighten opening emphasis"],
    )

    plan = DynamicEditPlan(
        plan_id="dynamic_plan_001",
        job_id="job_dynamic_edit_models_smoke",
        timeline_id="timeline_001",
        reaction_moments=[moment],
        zoom_instructions=[zoom],
        pacing_hints=[
            {
                "segment_id": "seg_001",
                "hint_kind": "fast_open",
                "strength": 0.80,
                "notes": ["hook should feel immediate"],
            }
        ],
        plan_score=0.83,
        plan_notes=["basic dynamic edit plan smoke"],
    )

    assert moment.duration == 3.5
    assert zoom.duration == 2.0
    assert len(plan.reaction_moments) == 1
    assert len(plan.zoom_instructions) == 1
    assert len(plan.pacing_hints) == 1
    assert plan.plan_score == 0.83

    print("DYNAMIC EDIT MODELS SMOKE TEST PASSED")
    print(
        {
            "reaction_moments": len(plan.reaction_moments),
            "zoom_instructions": len(plan.zoom_instructions),
            "pacing_hints": len(plan.pacing_hints),
            "plan_score": plan.plan_score,
        }
    )


if __name__ == "__main__":
    main()