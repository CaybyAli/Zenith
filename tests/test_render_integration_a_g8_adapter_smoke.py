from __future__ import annotations

import json

from core.g8_render_timeline_adapter import (
    build_edit_timeline_from_g8_plan,
    compare_timeline_to_g8_plan,
)


def test_g8_render_timeline_adapter_preserves_exact_segments(tmp_path):
    plan_path = tmp_path / "sample_g8_timeline_plan.json"
    plan = {
        "plan_id": "g8_plan_test",
        "label": "adapter_test",
        "status": "planned",
        "duration_contract": {
            "planned_output_duration_seconds": 12.5,
        },
        "anti_overcut_audit": {
            "fail_count": 0,
        },
        "timeline_segments": [
            {
                "segment_id": "g8_seg_001",
                "block_id": "g8_block_001",
                "start_seconds": 10.0,
                "end_seconds": 15.5,
                "state": "active_play",
                "keep_decision": "keep_active",
            },
            {
                "segment_id": "g8_seg_002",
                "block_id": "g8_block_002",
                "start_seconds": 30.0,
                "end_seconds": 37.0,
                "state": "active_play",
                "keep_decision": "keep_active",
            },
        ],
    }
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    timeline = build_edit_timeline_from_g8_plan(
        job_id="job_adapter_test",
        plan_path=plan_path,
    )

    assert timeline.target_duration == 12.5
    assert timeline.total_selected_duration == 12.5
    assert [s.segment_id for s in timeline.selected_segments] == ["g8_seg_001", "g8_seg_002"]
    assert [(s.start_time, s.end_time) for s in timeline.selected_segments] == [(10.0, 15.5), (30.0, 37.0)]
    assert all(s.source == "g8_timeline_plan" for s in timeline.selected_segments)

    comparison = compare_timeline_to_g8_plan(timeline=timeline, plan_data=plan)
    assert comparison["deviation_count"] == 0
    assert comparison["anti_overcut_preserved"] is True
