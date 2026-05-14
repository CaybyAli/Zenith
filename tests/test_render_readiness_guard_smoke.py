from types import SimpleNamespace

from core.render_readiness_guard import evaluate_render_readiness


def _base_job(**overrides):
    data = {
        "job_id": "job-render-readiness-smoke",
        "status": "routed",
        "review_timeline_plan": {"status": "ready"},
        "review_timeline_plan_report": {"status": "ready"},
        "review_timeline_plan_status": "ready",
        "review_timeline_plan_items": [
            {
                "item_id": "clip-1",
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "duration_seconds": 5.0,
            }
        ],
        "timeline_approval_gate": {
            "status": "approved",
            "approval_status": "approved",
            "approved_by": "human_reviewer",
        },
        "timeline_approval_gate_report": {
            "status": "approved",
            "approval_status": "approved",
            "approved_by": "human_reviewer",
        },
        "timeline_approval_status": "approved",
        "timeline_approved_by": "human_reviewer",
        "timeline_can_proceed_to_execution": False,
        "timeline_can_render": False,
        "timeline_safety_validator": {"status": "safe"},
        "timeline_safety_validator_report": {"status": "safe"},
        "timeline_safety_validation_status": "safe",
        "timeline_is_safe_for_future_execution": True,
        "timeline_is_safe_for_render": False,
        "timeline_safety_blocking_errors": [],
        "review_timeline_dashboard_package": {"status": "ready"},
        "review_timeline_dashboard_package_report": {"status": "ready"},
        "review_timeline_dashboard_package_status": "ready",
        "review_timeline_dashboard_can_render": False,
        "review_timeline_dashboard_is_safe_for_render": False,
        "review_timeline_dashboard_blocking_errors": [],
        "review_timeline_dashboard_warnings": [],
        "final_quality_validation_report": {
            "status": "final_quality_ready",
            "blocking_count": 0,
            "blocking_reasons": [],
            "overall_quality_score": 0.85,
        },
        "final_quality_validation_status": "final_quality_ready",
        "final_quality_overall_score": 0.85,
        "final_quality_blocking_count": 0,
        "final_quality_warning_count": 0,
        "final_quality_can_render": False,
        "final_quality_can_execute_timeline": False,
        "final_quality_blocking_reasons": [],
        "final_quality_warnings": [],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _check(report, check_id):
    for item in report.checks:
        if item.check_id == check_id:
            return item
    raise AssertionError(f"check missing: {check_id}")


def _assert_never_render_flags(report):
    assert report.can_render is False
    assert report.can_run_ffmpeg is False
    assert report.can_execute_media_operations is False
    assert report.can_apply_timeline is False
    assert report.can_modify_media is False

    data = report.to_dict()
    assert data["can_render"] is False
    assert data["can_run_ffmpeg"] is False
    assert data["can_execute_media_operations"] is False
    assert data["can_apply_timeline"] is False
    assert data["can_modify_media"] is False


def test_guard_can_be_ready_for_next_render_stage_but_never_can_render():
    report = evaluate_render_readiness(_base_job())

    assert report.status == "render_readiness_ready"
    assert report.ready_for_next_render_stage is True
    assert report.can_start_render_pipeline is True
    assert report.blocking_count == 0
    assert report.total_checks >= 13
    assert report.metadata["phase"] == "2B-45"
    assert report.metadata["render_readiness_guard_only"] is True
    assert report.metadata["media_unchanged"] is True
    assert report.metadata["no_render_in_2b_45"] is True
    _assert_never_render_flags(report)


def test_guard_blocks_when_review_timeline_plan_missing():
    report = evaluate_render_readiness(
        _base_job(
            review_timeline_plan={},
            review_timeline_plan_report={},
            review_timeline_plan_status=None,
        )
    )

    assert report.status == "render_readiness_blocked"
    assert _check(report, "review_timeline_plan_present").status == "blocked"
    assert report.ready_for_next_render_stage is False
    assert report.can_start_render_pipeline is False
    _assert_never_render_flags(report)


def test_guard_blocks_when_timeline_items_missing():
    report = evaluate_render_readiness(_base_job(review_timeline_plan_items=[]))

    assert report.status == "render_readiness_blocked"
    assert _check(report, "review_timeline_items_present").status == "blocked"
    _assert_never_render_flags(report)


def test_guard_blocks_when_approval_is_not_approved():
    for approval_status in [None, "pending", "rejected", "needs_manual_changes", "blocked"]:
        report = evaluate_render_readiness(
            _base_job(
                timeline_approval_status=approval_status,
                timeline_approved_by=None,
                timeline_approval_gate={
                    "status": approval_status,
                    "approval_status": approval_status,
                },
                timeline_approval_gate_report={
                    "status": approval_status,
                    "approval_status": approval_status,
                },
            )
        )

        assert report.status == "render_readiness_blocked"
        assert _check(report, "timeline_approval_approved").status == "blocked"
        _assert_never_render_flags(report)


def test_guard_blocks_when_safety_blocked_or_failed():
    for safety_status in ["blocked", "failed", "timeline_safety_blocked"]:
        report = evaluate_render_readiness(
            _base_job(
                timeline_safety_validation_status=safety_status,
                timeline_is_safe_for_future_execution=False,
                timeline_safety_blocking_errors=["unsafe_timeline"],
            )
        )

        assert report.status == "render_readiness_blocked"
        assert _check(report, "timeline_safety_passed").status == "blocked"
        _assert_never_render_flags(report)


def test_guard_blocks_when_dashboard_package_blocked_failed_or_missing():
    for dashboard_status in [None, "blocked", "failed"]:
        report = evaluate_render_readiness(
            _base_job(
                review_timeline_dashboard_package={},
                review_timeline_dashboard_package_report={},
                review_timeline_dashboard_package_status=dashboard_status,
            )
        )

        assert report.status == "render_readiness_blocked"
        assert _check(report, "dashboard_package_ready").status == "blocked"
        _assert_never_render_flags(report)


def test_guard_blocks_when_final_quality_missing():
    report = evaluate_render_readiness(
        _base_job(
            final_quality_validation_report={},
            final_quality_validator={},
            final_quality_validation_status=None,
        )
    )

    assert report.status == "render_readiness_blocked"
    assert _check(report, "final_quality_available").status == "blocked"
    assert _check(report, "final_quality_not_blocked").status == "blocked"
    _assert_never_render_flags(report)


def test_guard_blocks_when_final_quality_blocked():
    report = evaluate_render_readiness(
        _base_job(
            final_quality_validation_status="final_quality_blocked",
            final_quality_blocking_count=1,
            final_quality_blocking_reasons=["quality_blocked"],
        )
    )

    assert report.status == "render_readiness_blocked"
    assert _check(report, "final_quality_not_blocked").status == "blocked"
    _assert_never_render_flags(report)


def test_guard_blocks_when_blocking_errors_exist():
    report = evaluate_render_readiness(
        _base_job(timeline_safety_blocking_errors=["timing_overlap"])
    )

    assert report.status == "render_readiness_blocked"
    assert _check(report, "timeline_safety_passed").status == "blocked"
    assert _check(report, "no_blocking_errors").status == "blocked"
    _assert_never_render_flags(report)


def test_guard_blocks_when_old_can_render_permission_leaks():
    report = evaluate_render_readiness(_base_job(timeline_can_render=True))

    assert report.status == "render_readiness_blocked"
    assert _check(report, "no_render_permission_leaked").status == "blocked"
    _assert_never_render_flags(report)


def test_guard_blocks_when_old_execution_permission_leaks():
    report = evaluate_render_readiness(
        _base_job(
            final_quality_can_execute_timeline=True,
            story_can_trim=True,
            reaction_shot_can_move_clip=True,
        )
    )

    assert report.status == "render_readiness_blocked"
    assert _check(report, "no_execution_permission_leaked").status == "blocked"
    _assert_never_render_flags(report)


def test_guard_warns_when_human_approval_chain_unclear():
    report = evaluate_render_readiness(
        _base_job(
            timeline_approved_by=None,
            timeline_approval_gate={"status": "approved", "approval_status": "approved"},
            timeline_approval_gate_report={"status": "approved", "approval_status": "approved"},
        )
    )

    assert report.status == "render_readiness_ready_with_warnings"
    assert _check(report, "human_approval_chain_present").status == "warning"
    assert report.ready_for_next_render_stage is True
    assert report.can_start_render_pipeline is True
    _assert_never_render_flags(report)


def test_guard_warns_when_final_quality_score_low():
    report = evaluate_render_readiness(
        _base_job(final_quality_overall_score=0.50)
    )

    assert report.status == "render_readiness_ready_with_warnings"
    assert _check(report, "final_quality_score_reasonable").status == "warning"
    assert report.ready_for_next_render_stage is True
    assert report.can_start_render_pipeline is True
    _assert_never_render_flags(report)


def test_guard_blocks_when_render_stage_already_started():
    report = evaluate_render_readiness(
        _base_job(render_output_path="exports/job/final.mp4")
    )

    assert report.status == "render_readiness_blocked"
    assert _check(report, "render_stage_not_started").status == "blocked"
    _assert_never_render_flags(report)
