from types import SimpleNamespace

from core.final_quality_validator import validate_final_quality


def _base_job(**overrides):
    data = {
        "job_id": "job-final-quality-smoke",
        "review_timeline_plan_items": [
            {
                "item_id": "clip-1",
                "start_seconds": 0.0,
                "end_seconds": 4.0,
                "duration_seconds": 4.0,
                "label": "gameplay",
            },
            {
                "item_id": "clip-2",
                "start_seconds": 4.0,
                "end_seconds": 9.0,
                "duration_seconds": 5.0,
                "label": "gameplay",
            },
        ],
        "hook_selected_candidate": {"hook_score": 0.90},
        "hook_identification_report": {
            "status": "hook_identification_ready",
            "candidates": [{"hook_score": 0.90}],
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
        "pattern_interrupt_windows": [
            {"start_seconds": 2.0, "end_seconds": 2.5}
        ],
        "reaction_shot_placement_report": {
            "status": "reaction_placement_ready",
            "placeholder_count": 0,
        },
        "reaction_shot_placements": [
            {"start_seconds": 3.0, "end_seconds": 3.5}
        ],
        "but_therefore_story_report": {
            "status": "story_analysis_ready",
            "but_therefore_ratio": 0.80,
        },
        "story_transitions": [
            {"transition_type": "but"},
            {"transition_type": "therefore"},
            {"transition_type": "and"},
        ],
        "timeline_safety_validator_report": {
            "status": "timeline_safety_ready",
            "can_render": False,
            "can_execute_timeline": False,
            "censor_protection_missing": False,
            "protected_item_danger": False,
            "continuity_block_override": False,
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
        "silence_segments": [
            {"start_seconds": 1.0, "end_seconds": 1.2, "duration_seconds": 0.2}
        ],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _check(report, check_id):
    for item in report.checks:
        if item.check_id == check_id:
            return item
    raise AssertionError(f"check missing: {check_id}")


def test_final_quality_validator_generates_review_only_report_from_block6_and_block7_data():
    report = validate_final_quality(_base_job())

    assert report.status == "final_quality_ready"
    assert report.total_checks >= 15
    assert report.blocking_count == 0
    assert report.review_required is True
    assert report.can_apply_fixes is False
    assert report.can_render is False
    assert report.can_execute_timeline is False
    assert report.can_reorder_timeline is False
    assert report.can_trim is False
    assert report.can_extend is False
    assert report.can_insert_effects is False
    assert report.metadata["phase"] == "2B-43"
    assert report.metadata["review_only"] is True
    assert report.metadata["media_unchanged"] is True


def test_hook_missing_creates_warning():
    report = validate_final_quality(
        _base_job(
            hook_selected_candidate=None,
            hook_identification_report={"status": "hook_identification_ready", "candidates": []},
            hook_candidates=[],
        )
    )

    check = _check(report, "hook_present")
    assert check.status == "warning"
    assert check.review_required is True
    assert report.status == "final_quality_ready_with_warnings"


def test_hook_score_below_080_warns_and_strong_score_passes():
    weak_report = validate_final_quality(
        _base_job(hook_selected_candidate={"hook_score": 0.50})
    )
    weak_check = _check(weak_report, "hook_score_strong")
    assert weak_check.status == "warning"

    strong_report = validate_final_quality(
        _base_job(hook_selected_candidate={"hook_score": 0.85})
    )
    strong_check = _check(strong_report, "hook_score_strong")
    assert strong_check.status == "passed"


def test_emotional_arc_deviation_above_020_warns():
    report = validate_final_quality(
        _base_job(emotional_arc_report={"status": "arc_analysis_ready", "average_deviation": 0.35})
    )

    check = _check(report, "emotional_arc_deviation")
    assert check.status == "warning"
    assert report.status == "final_quality_ready_with_warnings"


def test_pattern_interrupt_missing_or_monotony_risk_warns():
    report = validate_final_quality(
        _base_job(
            pattern_interrupt_report={"status": "pattern_interrupt_ready_with_warnings", "monotony_risk": True},
            pattern_interrupt_windows=[],
        )
    )

    check = _check(report, "pattern_interrupts_present")
    assert check.status == "warning"


def test_reaction_placeholder_warns():
    report = validate_final_quality(
        _base_job(
            reaction_shot_placement_report={
                "status": "reaction_placement_ready_with_warnings",
                "placeholder_count": 2,
            },
            reaction_shot_placements=[],
        )
    )

    check = _check(report, "reaction_shots_reviewed")
    assert check.status == "warning"


def test_but_therefore_ratio_below_060_warns():
    report = validate_final_quality(
        _base_job(but_therefore_story_report={"status": "story_analysis_ready", "but_therefore_ratio": 0.30})
    )

    check = _check(report, "but_therefore_ratio")
    assert check.status == "warning"


def test_pacing_monotone_and_missing_breathing_room_warn():
    report = validate_final_quality(
        _base_job(
            dynamic_pacing_report={
                "status": "pacing_analysis_ready_with_warnings",
                "monotony_score": 0.80,
                "missing_breathing_room": True,
                "breathing_room_score": 0.20,
            }
        )
    )

    assert _check(report, "pacing_not_monotone").status == "warning"
    assert _check(report, "breathing_room_present").status == "warning"


def test_safety_blockers_block_final_quality():
    report = validate_final_quality(
        _base_job(
            timeline_safety_validator_report={
                "status": "blocked",
                "can_render": False,
                "can_execute_timeline": False,
                "censor_protection_missing": True,
                "protected_item_danger": True,
                "continuity_block_override": True,
            },
            continuity_check_report={
                "sentence_boundary_violation": True,
                "block_override": True,
            },
        )
    )

    assert report.status == "final_quality_blocked"
    assert _check(report, "block6_safety_not_overridden").status == "blocked"
    assert _check(report, "no_censor_loss").status == "blocked"
    assert _check(report, "no_protected_loss").status == "blocked"
    assert _check(report, "no_continuity_block_override").status == "blocked"
    assert _check(report, "no_sentence_boundary_violation").status == "blocked"


def test_render_and_execution_flags_block_but_output_flags_stay_false():
    report = validate_final_quality(
        _base_job(
            can_render=True,
            can_apply_fixes=True,
            can_execute_timeline=True,
            can_reorder_timeline=True,
            can_trim=True,
            can_extend=True,
            can_insert_effects=True,
        )
    )

    assert report.status == "final_quality_blocked"
    assert _check(report, "no_render_permission").status == "blocked"
    assert _check(report, "no_execution_permission").status == "blocked"
    assert report.can_apply_fixes is False
    assert report.can_render is False
    assert report.can_execute_timeline is False
    assert report.can_reorder_timeline is False
    assert report.can_trim is False
    assert report.can_extend is False
    assert report.can_insert_effects is False


def test_short_clip_loading_screen_and_long_silence_warn_only():
    report = validate_final_quality(
        _base_job(
            review_timeline_plan_items=[
                {
                    "item_id": "tiny",
                    "start_seconds": 0.0,
                    "end_seconds": 0.2,
                    "duration_seconds": 0.2,
                    "label": "gameplay",
                },
                {
                    "item_id": "loading",
                    "start_seconds": 0.2,
                    "end_seconds": 4.0,
                    "duration_seconds": 3.8,
                    "label": "loading_screen",
                },
            ],
            silence_segments=[
                {"start_seconds": 5.0, "end_seconds": 5.8, "duration_seconds": 0.8}
            ],
        )
    )

    assert _check(report, "no_short_clips").status == "warning"
    assert _check(report, "no_long_loading_screen").status == "warning"
    assert _check(report, "no_long_silence").status == "warning"
    assert report.status == "final_quality_ready_with_warnings"
