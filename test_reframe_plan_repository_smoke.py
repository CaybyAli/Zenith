from __future__ import annotations

import os
import shutil

from core.reframe_plan_repository import ReframePlanRepository
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan


def main() -> None:
    test_dir = os.path.join("tmp", "reframe_plan_repository_smoke")
    export_path = os.path.join(test_dir, "export")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    instruction_1 = FramingInstruction(
        instruction_id="frame_repo_001",
        job_id="job_reframe_repo_smoke",
        timeline_id="timeline_repo_001",
        segment_id="seg_repo_001",
        focus_kind="facecam",
        layout_kind="facecam_emphasis",
        source_aspect_ratio="32:9",
        target_aspect_ratio="16:9",
        crop_window={"x": 0.02, "y": 0.08, "width": 0.42, "height": 0.84},
        notes=["repo hook framing"],
        metadata={"role": "hook"},
    )

    instruction_2 = FramingInstruction(
        instruction_id="frame_repo_002",
        job_id="job_reframe_repo_smoke",
        timeline_id="timeline_repo_001",
        segment_id="seg_repo_002",
        focus_kind="gameplay",
        layout_kind="gameplay_crop",
        source_aspect_ratio="32:9",
        target_aspect_ratio="16:9",
        crop_window={"x": 0.18, "y": 0.06, "width": 0.64, "height": 0.88},
        notes=["repo peak framing"],
        metadata={"role": "peak"},
    )

    plan = ReframePlan(
        plan_id="reframe_repo_001",
        job_id="job_reframe_repo_smoke",
        timeline_id="timeline_repo_001",
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        secondary_target_aspect_ratio="9:16",
        instructions=[instruction_1, instruction_2],
        plan_notes=["repository smoke test"],
        plan_score=0.88,
    )

    repo = ReframePlanRepository()
    saved_path = repo.save_plan(export_path, plan)
    loaded = repo.load_plan(export_path)

    assert os.path.exists(saved_path)
    assert loaded is not None
    assert loaded.plan_id == plan.plan_id
    assert loaded.timeline_id == plan.timeline_id
    assert len(loaded.instructions) == 2
    assert loaded.instructions[0].focus_kind == "facecam"
    assert loaded.instructions[1].focus_kind == "gameplay"
    assert loaded.primary_target_aspect_ratio == "16:9"
    assert loaded.secondary_target_aspect_ratio == "9:16"

    print("REFRAME PLAN REPOSITORY SMOKE TEST PASSED")
    print(
        {
            "saved_path": saved_path,
            "instructions": len(loaded.instructions),
            "plan_score": loaded.plan_score,
            "primary_target": loaded.primary_target_aspect_ratio,
        }
    )


if __name__ == "__main__":
    main()