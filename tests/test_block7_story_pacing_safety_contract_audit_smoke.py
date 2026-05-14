from __future__ import annotations

from types import SimpleNamespace

from core.final_quality_validator import validate_final_quality


def _base_job(**overrides):
    data = {
        "job_id": "job-block7-safety-contract",
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
        "hook_selected_candidate": {"hook_score": 0.92},
        "hook_candidates": [{"hook_score": 0.92}],
        "hook_identification_report": {
            "status": "hook_identification_ready",
            "candidates": [{"hook_score": 0.92}],
        },
        "emotional_arc_report": {
            "status": "arc_analysis_ready",
            "average_deviation": 0.08,
        },
        "emotional_arc_points": [
            {"timestamp_seconds": 0.0, "energy_score": 0.8},
            {"timestamp_seconds": 4.0, "energy_score": 0.6},
            {"timestamp_seconds": 8.0, "energy_score": 0.9},
        ],
        "dynamic_pacing_report": {
            "status": "pacing_analysis_ready",
            "monotony_score": 0.20,
            "monotony_risk": False,
            "missing_breathing_room": False,
            "breathing_room_score": 0.85,
        },
        "dynamic_pacing_segments": [
            {"start_seconds": 0.0, "end_seconds": 4.0, "pace": "fast"},
            {"start_seconds": 4.0, "end_seconds": 9.0, "pace": "medium"},
        ],
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
        "reaction_shot_candidates": [
            {"start_seconds": 3.0, "end_seconds": 3.4, "score": 0.9}
        ],
        "reaction_shot_placements": [
            {"start_seconds": 3.0, "end_seconds": 3.5}
        ],
        "but_therefore_story_report": {
            "status": "story_analysis_ready",
            "but_therefore_ratio": 0.80,
        },
        "story_moments": [
            {"moment_type": "but"},
            {"moment_type": "therefore"},
            {"moment_type": "and"},
        ],
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
        "can_render": False,
        "can_apply_fixes": False,
        "can_execute_timeline": False,
        "can_reorder_timeline": False,
        "can_trim": False,
        "can_extend": False,
        "can_insert_effects": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _check(report, check_id):
    for item in report.checks:
        if item.check_id == check_id:
            return item
    raise AssertionError(f"check missing: {check_id}")


def _assert_output_stays_review_only(report):
    assert report.review_required is True
    assert report.can_apply_fixes is False
    assert report.can_render is False
    assert report.can_execute_timeline is False
    assert report.can_reorder_timeline is False
    assert report.can_trim is False
    assert report.can_extend is False
    assert report.can_insert_effects is False
    assert report.metadata["review_only"] is True
    assert report.metadata["media_unchanged"] is True

    for suggestion in report.suggestions:
        assert suggestion.can_auto_apply is False
        assert suggestion.review_required is True


def test_case_a_good_block7_inputs_are_ready_or_ready_with_warnings_and_never_executable():
    report = validate_final_quality(_base_job())

    assert report.status in {"final_quality_ready", "final_quality_ready_with_warnings"}
    assert report.blocking_count == 0
    assert _check(report, "hook_present").status == "passed"
    assert _check(report, "emotional_arc_deviation").status == "passed"
    assert _check(report, "pacing_not_monotone").status == "passed"
    assert _check(report, "pattern_interrupts_present").status == "passed"
    assert _check(report, "reaction_shots_reviewed").status == "passed"
    assert _check(report, "but_therefore_ratio").status == "passed"
    _assert_output_stays_review_only(report)


def test_case_b_missing_hook_warns_but_does_not_auto_apply_hook():
    report = validate_final_quality(
        _base_job(
            hook_selected_candidate=None,
            hook_candidates=[],
            hook_identification_report={
                "status": "hook_identification_ready",
                "candidates": [],
            },
        )
    )

    assert report.status == "final_quality_ready_with_warnings"
    assert _check(report, "hook_present").status == "warning"
    assert any(
        suggestion.category == "story"
        for suggestion in report.suggestions
    )
    _assert_output_stays_review_only(report)


def test_case_c_block6_safety_blocked_blocks_final_quality():
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
    _assert_output_stays_review_only(report)


def test_case_d_monotone_dynamic_pacing_warns_but_does_not_apply_pacing_fix():
    report = validate_final_quality(
        _base_job(
            dynamic_pacing_report={
                "status": "pacing_analysis_ready_with_warnings",
                "monotony_score": 0.85,
                "monotony_risk": True,
                "missing_breathing_room": True,
                "breathing_room_score": 0.20,
            }
        )
    )

    assert report.status == "final_quality_ready_with_warnings"
    assert _check(report, "pacing_not_monotone").status == "warning"
    assert _check(report, "breathing_room_present").status == "warning"
    _assert_output_stays_review_only(report)


def test_case_e_reaction_placeholder_warns_but_does_not_insert_reaction():
    report = validate_final_quality(
        _base_job(
            reaction_shot_placement_report={
                "status": "reaction_placement_ready_with_warnings",
                "placeholder_count": 2,
            },
            reaction_shot_placements=[],
        )
    )

    assert report.status == "final_quality_ready_with_warnings"
    assert _check(report, "reaction_shots_reviewed").status == "warning"
    _assert_output_stays_review_only(report)


def test_case_f_weak_but_therefore_ratio_warns_but_does_not_remove_and_moments():
    report = validate_final_quality(
        _base_job(
            but_therefore_story_report={
                "status": "story_analysis_ready_with_warnings",
                "but_therefore_ratio": 0.25,
            },
            story_transitions=[
                {"transition_type": "and"},
                {"transition_type": "and"},
                {"transition_type": "but"},
            ],
        )
    )

    assert report.status == "final_quality_ready_with_warnings"
    assert _check(report, "but_therefore_ratio").status == "warning"
    _assert_output_stays_review_only(report)


def test_case_g_any_can_render_true_blocks_and_output_can_render_stays_false():
    report = validate_final_quality(
        _base_job(
            can_render=True,
            timeline_safety_validator_report={
                "status": "timeline_safety_ready",
                "can_render": True,
                "can_execute_timeline": False,
                "censor_protection_missing": False,
                "protected_item_danger": False,
                "continuity_block_override": False,
            },
        )
    )

    assert report.status == "final_quality_blocked"
    assert _check(report, "no_render_permission").status == "blocked"
    _assert_output_stays_review_only(report)


def test_case_h_any_execution_flag_true_blocks_and_output_execution_flags_stay_false():
    report = validate_final_quality(
        _base_job(
            can_apply_fixes=True,
            can_execute_timeline=True,
            can_reorder_timeline=True,
            can_trim=True,
            can_extend=True,
            can_insert_effects=True,
        )
    )

    assert report.status == "final_quality_blocked"
    assert _check(report, "no_execution_permission").status == "blocked"
    _assert_output_stays_review_only(report)
