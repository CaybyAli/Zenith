from types import SimpleNamespace

from core.final_quality_validator_runner import run_final_quality_validator
from models.job import Job


def _job(**overrides):
    data = {
        "job_id": "runner-final-quality-job",
        "review_timeline_plan_items": [
            {
                "item_id": "clip-1",
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "duration_seconds": 5.0,
                "label": "gameplay",
            }
        ],
        "hook_selected_candidate": {"hook_score": 0.91},
        "hook_identification_report": {
            "status": "hook_identification_ready",
            "candidates": [{"hook_score": 0.91}],
        },
        "emotional_arc_report": {
            "status": "arc_analysis_ready",
            "average_deviation": 0.10,
        },
        "dynamic_pacing_report": {
            "status": "pacing_analysis_ready",
            "monotony_score": 0.20,
            "breathing_room_score": 0.80,
        },
        "pattern_interrupt_report": {
            "status": "pattern_interrupt_analysis_ready",
            "monotony_risk": False,
        },
        "pattern_interrupt_windows": [{"start_seconds": 1.0, "end_seconds": 1.3}],
        "reaction_shot_placement_report": {
            "status": "reaction_placement_ready",
            "placeholder_count": 0,
        },
        "reaction_shot_placements": [{"start_seconds": 2.0, "end_seconds": 2.5}],
        "but_therefore_story_report": {
            "status": "story_analysis_ready",
            "but_therefore_ratio": 0.80,
        },
        "timeline_safety_validator_report": {
            "status": "timeline_safety_ready",
            "can_render": False,
            "can_execute_timeline": False,
        },
        "continuity_check_report": {
            "sentence_boundary_violation": False,
            "block_override": False,
        },
        "sentence_boundary_report": {
            "sentence_boundary_violation": False,
            "cut_mid_sentence": False,
            "cut_mid_word": False,
        },
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_final_quality_runner_writes_job_fields():
    job = _job()

    report = run_final_quality_validator(job)

    assert report["status"] == "final_quality_ready"
    assert job.final_quality_validation_status == "final_quality_ready"
    assert job.final_quality_validation_report["status"] == "final_quality_ready"
    assert job.final_quality_validator["status"] == "final_quality_ready"
    assert isinstance(job.final_quality_checks, list)
    assert isinstance(job.final_quality_suggestions, list)
    assert job.final_quality_passed_count > 0
    assert job.final_quality_warning_count == 0
    assert job.final_quality_blocking_count == 0
    assert job.final_quality_review_required is True
    assert job.final_quality_recommendation == "review_final_quality"


def test_final_quality_runner_forces_all_dangerous_flags_false():
    job = _job(
        can_render=True,
        can_apply_fixes=True,
        can_execute_timeline=True,
        can_reorder_timeline=True,
        can_trim=True,
        can_extend=True,
        can_insert_effects=True,
    )

    report = run_final_quality_validator(job)

    assert report["status"] == "final_quality_blocked"
    assert job.final_quality_can_apply_fixes is False
    assert job.final_quality_can_render is False
    assert job.final_quality_can_execute_timeline is False
    assert job.final_quality_can_reorder_timeline is False
    assert job.final_quality_can_trim is False
    assert job.final_quality_can_extend is False
    assert job.final_quality_can_insert_effects is False
    assert report["can_apply_fixes"] is False
    assert report["can_render"] is False
    assert report["can_execute_timeline"] is False
    assert report["can_reorder_timeline"] is False
    assert report["can_trim"] is False
    assert report["can_extend"] is False
    assert report["can_insert_effects"] is False


def test_job_from_dict_loads_final_quality_fields_and_keeps_safety_false():
    loaded = Job.from_dict(
        {
            "job_id": "job-from-dict-final-quality",
            "job_type": "gaming",
            "channel_type": "gaming_main",
            "target_format": "short",
            "status": "routed",
            "mode": "normal",
            "autopublish_class": "manual_only",
            "validator_status": "not_validated",
            "final_quality_validation_report": {
                "status": "final_quality_ready_with_warnings",
                "checks": [{"check_id": "hook_present"}],
            },
            "final_quality_validator": {"status": "final_quality_ready_with_warnings"},
            "final_quality_validation_status": "final_quality_ready_with_warnings",
            "final_quality_checks": [{"check_id": "hook_present"}],
            "final_quality_suggestions": [{"suggestion_id": "s1"}],
            "final_quality_audio_score": 0.7,
            "final_quality_video_score": 0.8,
            "final_quality_story_score": 0.9,
            "final_quality_pacing_score": 0.6,
            "final_quality_safety_score": 1.0,
            "final_quality_overall_score": 0.8,
            "final_quality_passed_count": 10,
            "final_quality_warning_count": 2,
            "final_quality_blocking_count": 0,
            "final_quality_review_required": True,
            "final_quality_can_apply_fixes": True,
            "final_quality_can_render": True,
            "final_quality_can_execute_timeline": True,
            "final_quality_can_reorder_timeline": True,
            "final_quality_can_trim": True,
            "final_quality_can_extend": True,
            "final_quality_can_insert_effects": True,
            "final_quality_blocking_reasons": [],
            "final_quality_warnings": ["weak hook"],
            "final_quality_recommendation": "review_final_quality",
        }
    )

    assert loaded.final_quality_validation_status == "final_quality_ready_with_warnings"
    assert loaded.final_quality_validation_report["status"] == "final_quality_ready_with_warnings"
    assert loaded.final_quality_checks == [{"check_id": "hook_present"}]
    assert loaded.final_quality_suggestions == [{"suggestion_id": "s1"}]
    assert loaded.final_quality_audio_score == 0.7
    assert loaded.final_quality_video_score == 0.8
    assert loaded.final_quality_story_score == 0.9
    assert loaded.final_quality_pacing_score == 0.6
    assert loaded.final_quality_safety_score == 1.0
    assert loaded.final_quality_overall_score == 0.8
    assert loaded.final_quality_passed_count == 10
    assert loaded.final_quality_warning_count == 2
    assert loaded.final_quality_blocking_count == 0
    assert loaded.final_quality_review_required is True
    assert loaded.final_quality_can_apply_fixes is False
    assert loaded.final_quality_can_render is False
    assert loaded.final_quality_can_execute_timeline is False
    assert loaded.final_quality_can_reorder_timeline is False
    assert loaded.final_quality_can_trim is False
    assert loaded.final_quality_can_extend is False
    assert loaded.final_quality_can_insert_effects is False
