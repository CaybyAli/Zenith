from __future__ import annotations

from dataclasses import fields

from models.job import Job


BASE_JOB_PAYLOAD = {
    "job_id": "job_block7_job_fields_audit",
    "job_type": "gaming",
    "channel_type": "gaming_main",
    "target_format": "short",
    "target_platforms": ["youtube"],
    "status": "routed",
    "mode": "normal",
    "autopublish_class": "manual_only",
    "confidence_score": 0.0,
    "validator_status": "not_validated",
}


BLOCK7_JOB_FIELDS = [
    "hook_identification_report",
    "hook_identification_status",
    "hook_candidates",
    "hook_selected_candidate",
    "hook_can_apply",
    "hook_can_reorder_timeline",
    "hook_can_render",
    "emotional_arc_report",
    "emotional_arc_status",
    "emotional_arc_points",
    "emotional_arc_can_apply",
    "emotional_arc_can_reorder_timeline",
    "emotional_arc_can_render",
    "dynamic_pacing_report",
    "dynamic_pacing_status",
    "dynamic_pacing_segments",
    "dynamic_pacing_can_apply",
    "dynamic_pacing_can_split_clips",
    "dynamic_pacing_can_merge_clips",
    "dynamic_pacing_can_render",
    "pattern_interrupt_report",
    "pattern_interrupt_status",
    "pattern_interrupt_windows",
    "pattern_interrupt_can_apply",
    "pattern_interrupt_can_insert_zoom",
    "pattern_interrupt_can_insert_text_overlay",
    "pattern_interrupt_can_insert_sfx",
    "pattern_interrupt_can_render",
    "reaction_shot_placement_report",
    "reaction_shot_placement_status",
    "reaction_shot_candidates",
    "reaction_shot_placements",
    "reaction_shot_can_apply",
    "reaction_shot_can_insert_clip",
    "reaction_shot_can_render",
    "but_therefore_story_report",
    "but_therefore_story_status",
    "story_moments",
    "story_transitions",
    "story_can_apply_changes",
    "story_can_remove_and_moments",
    "story_can_render",
    "final_quality_validation_report",
    "final_quality_validation_status",
    "final_quality_checks",
    "final_quality_can_apply_fixes",
    "final_quality_can_render",
    "final_quality_can_execute_timeline",
]


BLOCK7_EXECUTION_FIELDS = [
    "hook_can_apply",
    "hook_can_reorder_timeline",
    "hook_can_render",
    "emotional_arc_can_apply",
    "emotional_arc_can_reorder_timeline",
    "emotional_arc_can_render",
    "dynamic_pacing_can_apply",
    "dynamic_pacing_can_split_clips",
    "dynamic_pacing_can_merge_clips",
    "dynamic_pacing_can_render",
    "pattern_interrupt_can_apply",
    "pattern_interrupt_can_insert_zoom",
    "pattern_interrupt_can_insert_text_overlay",
    "pattern_interrupt_can_insert_sfx",
    "pattern_interrupt_can_render",
    "reaction_shot_can_apply",
    "reaction_shot_can_insert_clip",
    "reaction_shot_can_render",
    "story_can_apply_changes",
    "story_can_remove_and_moments",
    "story_can_render",
    "final_quality_can_apply_fixes",
    "final_quality_can_render",
    "final_quality_can_execute_timeline",
]


def _field_names() -> set[str]:
    return {field.name for field in fields(Job)}


def test_job_model_declares_all_block7_report_and_safety_fields():
    missing = [
        field_name
        for field_name in BLOCK7_JOB_FIELDS
        if field_name not in _field_names()
    ]

    assert missing == []


def test_job_from_dict_loads_all_block7_report_fields():
    payload = dict(BASE_JOB_PAYLOAD)
    payload.update(
        {
            "hook_identification_report": {"status": "hook_candidate_found"},
            "hook_identification_status": "hook_candidate_found",
            "hook_candidates": [{"candidate_id": "hook-1"}],
            "hook_selected_candidate": {"candidate_id": "hook-1"},
            "emotional_arc_report": {"status": "arc_analysis_ready"},
            "emotional_arc_status": "arc_analysis_ready",
            "emotional_arc_points": [{"point_id": "arc-1"}],
            "dynamic_pacing_report": {"status": "pacing_analysis_ready"},
            "dynamic_pacing_status": "pacing_analysis_ready",
            "dynamic_pacing_segments": [{"segment_id": "pace-1"}],
            "pattern_interrupt_report": {"status": "pattern_interrupt_analysis_ready"},
            "pattern_interrupt_status": "pattern_interrupt_analysis_ready",
            "pattern_interrupt_windows": [{"window_id": "pattern-1"}],
            "reaction_shot_placement_report": {"status": "reaction_placement_ready"},
            "reaction_shot_placement_status": "reaction_placement_ready",
            "reaction_shot_candidates": [{"candidate_id": "reaction-1"}],
            "reaction_shot_placements": [{"placement_id": "placement-1"}],
            "but_therefore_story_report": {"status": "story_analysis_ready"},
            "but_therefore_story_status": "story_analysis_ready",
            "story_moments": [{"moment_id": "story-1"}],
            "story_transitions": [{"transition_type": "but"}],
            "final_quality_validation_report": {"status": "final_quality_ready"},
            "final_quality_validation_status": "final_quality_ready",
            "final_quality_checks": [{"check_id": "quality-1"}],
        }
    )

    job = Job.from_dict(payload)

    assert job.hook_identification_report["status"] == "hook_candidate_found"
    assert job.hook_identification_status == "hook_candidate_found"
    assert job.hook_candidates == [{"candidate_id": "hook-1"}]
    assert job.hook_selected_candidate == {"candidate_id": "hook-1"}

    assert job.emotional_arc_report["status"] == "arc_analysis_ready"
    assert job.emotional_arc_status == "arc_analysis_ready"
    assert job.emotional_arc_points == [{"point_id": "arc-1"}]

    assert job.dynamic_pacing_report["status"] == "pacing_analysis_ready"
    assert job.dynamic_pacing_status == "pacing_analysis_ready"
    assert job.dynamic_pacing_segments == [{"segment_id": "pace-1"}]

    assert job.pattern_interrupt_report["status"] == "pattern_interrupt_analysis_ready"
    assert job.pattern_interrupt_status == "pattern_interrupt_analysis_ready"
    assert job.pattern_interrupt_windows == [{"window_id": "pattern-1"}]

    assert job.reaction_shot_placement_report["status"] == "reaction_placement_ready"
    assert job.reaction_shot_placement_status == "reaction_placement_ready"
    assert job.reaction_shot_candidates == [{"candidate_id": "reaction-1"}]
    assert job.reaction_shot_placements == [{"placement_id": "placement-1"}]

    assert job.but_therefore_story_report["status"] == "story_analysis_ready"
    assert job.but_therefore_story_status == "story_analysis_ready"
    assert job.story_moments == [{"moment_id": "story-1"}]
    assert job.story_transitions == [{"transition_type": "but"}]

    assert job.final_quality_validation_report["status"] == "final_quality_ready"
    assert job.final_quality_validation_status == "final_quality_ready"
    assert job.final_quality_checks == [{"check_id": "quality-1"}]


def test_job_defaults_keep_all_block7_render_apply_execution_flags_false():
    job = Job.from_dict(dict(BASE_JOB_PAYLOAD))

    violations = [
        field_name
        for field_name in BLOCK7_EXECUTION_FIELDS
        if getattr(job, field_name) is not False
    ]

    assert violations == []


def test_job_from_dict_preserves_false_for_all_block7_render_apply_execution_flags():
    payload = dict(BASE_JOB_PAYLOAD)
    payload.update({field_name: False for field_name in BLOCK7_EXECUTION_FIELDS})

    job = Job.from_dict(payload)

    violations = [
        field_name
        for field_name in BLOCK7_EXECUTION_FIELDS
        if getattr(job, field_name) is not False
    ]

    assert violations == []


def test_job_from_dict_loads_block7_warning_and_blocking_lists():
    payload = dict(BASE_JOB_PAYLOAD)
    payload.update(
        {
            "hook_blocking_reasons": ["hook_blocked"],
            "hook_warnings": ["hook_warning"],
            "emotional_arc_blocking_reasons": ["arc_blocked"],
            "emotional_arc_warnings": ["arc_warning"],
            "dynamic_pacing_blocking_reasons": ["pacing_blocked"],
            "dynamic_pacing_warnings": ["pacing_warning"],
            "pattern_interrupt_blocking_reasons": ["pattern_blocked"],
            "pattern_interrupt_warnings": ["pattern_warning"],
            "reaction_shot_blocking_reasons": ["reaction_blocked"],
            "reaction_shot_warnings": ["reaction_warning"],
            "story_blocking_reasons": ["story_blocked"],
            "story_warnings": ["story_warning"],
            "final_quality_blocking_reasons": ["quality_blocked"],
            "final_quality_warnings": ["quality_warning"],
        }
    )

    job = Job.from_dict(payload)

    assert job.hook_blocking_reasons == ["hook_blocked"]
    assert job.hook_warnings == ["hook_warning"]
    assert job.emotional_arc_blocking_reasons == ["arc_blocked"]
    assert job.emotional_arc_warnings == ["arc_warning"]
    assert job.dynamic_pacing_blocking_reasons == ["pacing_blocked"]
    assert job.dynamic_pacing_warnings == ["pacing_warning"]
    assert job.pattern_interrupt_blocking_reasons == ["pattern_blocked"]
    assert job.pattern_interrupt_warnings == ["pattern_warning"]
    assert job.reaction_shot_blocking_reasons == ["reaction_blocked"]
    assert job.reaction_shot_warnings == ["reaction_warning"]
    assert job.story_blocking_reasons == ["story_blocked"]
    assert job.story_warnings == ["story_warning"]
    assert job.final_quality_blocking_reasons == ["quality_blocked"]
    assert job.final_quality_warnings == ["quality_warning"]
