from __future__ import annotations

import os
import shutil

from core.dynamic_edit_plan_repository import DynamicEditPlanRepository
from models.dynamic_edit_plan import DynamicEditPlan
from models.reaction_moment import ReactionMoment
from models.zoom_instruction import ZoomInstruction


def main() -> None:
    test_dir = os.path.join("tmp", "dynamic_edit_plan_repository_smoke")
    export_path = os.path.join(test_dir, "export")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    moment = ReactionMoment(
        moment_id="moment_repo_001",
        job_id="job_dynamic_edit_repo_smoke",
        timeline_id="timeline_repo_001",
        segment_id="seg_repo_001",
        start_time=12.0,
        end_time=15.0,
        reaction_kind="hook_reaction",
        intensity=0.88,
        confidence=0.84,
        notes=["repo moment"],
    )

    zoom = ZoomInstruction(
        instruction_id="zoom_repo_001",
        job_id="job_dynamic_edit_repo_smoke",
        timeline_id="timeline_repo_001",
        segment_id="seg_repo_001",
        moment_id="moment_repo_001",
        zoom_kind="hook_push",
        focus_kind="facecam",
        intensity=0.86,
        start_time=12.0,
        end_time=14.0,
        notes=["repo zoom"],
    )

    plan = DynamicEditPlan(
        plan_id="dynamic_repo_001",
        job_id="job_dynamic_edit_repo_smoke",
        timeline_id="timeline_repo_001",
        reaction_moments=[moment],
        zoom_instructions=[zoom],
        pacing_hints=[
            {
                "segment_id": "seg_repo_001",
                "hint_kind": "fast_open",
                "strength": 0.81,
                "notes": ["repo pacing"],
            }
        ],
        plan_score=0.85,
        plan_notes=["repository smoke test"],
    )

    repo = DynamicEditPlanRepository()
    saved_path = repo.save_plan(export_path, plan)
    loaded = repo.load_plan(export_path)

    assert os.path.exists(saved_path)
    assert loaded is not None
    assert loaded.plan_id == plan.plan_id
    assert loaded.timeline_id == plan.timeline_id
    assert len(loaded.reaction_moments) == 1
    assert len(loaded.zoom_instructions) == 1
    assert len(loaded.pacing_hints) == 1
    assert loaded.plan_score == 0.85

    print("DYNAMIC EDIT PLAN REPOSITORY SMOKE TEST PASSED")
    print(
        {
            "saved_path": saved_path,
            "reaction_moments": len(loaded.reaction_moments),
            "zoom_instructions": len(loaded.zoom_instructions),
            "pacing_hints": len(loaded.pacing_hints),
            "plan_score": loaded.plan_score,
        }
    )


if __name__ == "__main__":
    main()