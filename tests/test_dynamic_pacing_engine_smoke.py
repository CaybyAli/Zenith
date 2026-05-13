from __future__ import annotations

from core.dynamic_pacing_engine import build_dynamic_pacing_for_job
from models.dynamic_pacing import DynamicPacingReport


def _item(
    item_id: str,
    segment_id: str,
    start: float,
    end: float,
    **overrides,
) -> dict:
    data = {
        "item_id": item_id,
        "source_segment_id": segment_id,
        "source_start_seconds": start,
        "source_end_seconds": end,
        "duration_seconds": end - start,
        "action": "keep_review",
        "review_required": True,
        "protected": False,
        "censor_sfx_required": False,
        "continuity_blocked": False,
        "safety_status": "ok",
        "warnings": [],
        "blocking_errors": [],
    }
    data.update(overrides)
    return data


def _job(items: list[dict], **overrides) -> dict:
    data = {
        "job_id": "job_dynamic_pacing_engine",
        "review_timeline_dashboard_package_report": {
            "status": "ready_for_dashboard",
            "dashboard_package": {
                "dashboard_package_id": "dashboard_dynamic_pacing_engine",
                "package_status": "ready_for_dashboard",
                "item_cards": items,
                "blocking_errors": [],
                "warnings": [],
                "metadata": {
                    "dashboard_only": True,
                    "media_unchanged": True,
                },
            },
        },
    }
    data.update(overrides)
    return data


def _suggestion_types(report) -> set[str]:
    return {suggestion.suggestion_type for suggestion in report.suggestions}


def test_engine_scores_cut_rates_and_energy_target_ranges() -> None:
    items = [
        _item(
            "high_slow",
            "seg_high_slow",
            0.0,
            6.0,
            content_value_score=0.10,
        ),
        _item("mid_good", "seg_mid_good", 6.0, 10.0, content_value_score=0.65),
        _item("low_fast", "seg_low_fast", 10.0, 12.0, content_value_score=0.30),
        _item("high_fast_1", "seg_high_fast_1", 12.0, 14.0, content_value_score=0.90),
        _item("high_fast_2", "seg_high_fast_2", 14.0, 16.0, content_value_score=0.88),
        _item("high_fast_3", "seg_high_fast_3", 16.0, 18.0, content_value_score=0.86),
    ]
    report = build_dynamic_pacing_for_job(
        _job(
            items,
            emotional_arc_points=[
                {
                    "point_id": "arc_high_slow",
                    "source_item_id": "high_slow",
                    "source_segment_id": "seg_high_slow",
                    "start_seconds": 0.0,
                    "end_seconds": 6.0,
                    "duration_seconds": 6.0,
                    "actual_energy_score": 0.92,
                    "arc_phase": "climax",
                }
            ],
        )
    )

    by_item = {segment.source_item_id: segment for segment in report.pacing_segments}
    suggestion_types = _suggestion_types(report)

    assert len(report.pacing_segments) == 6
    assert by_item["high_slow"].energy_score == 0.92
    assert by_item["high_slow"].arc_phase == "climax"
    assert by_item["high_slow"].target_cut_rate_min == 20.0
    assert by_item["high_slow"].target_cut_rate_max == 40.0
    assert by_item["high_slow"].actual_cut_rate == 10.0
    assert by_item["high_slow"].pacing_status == "pacing_too_slow_for_energy"

    assert by_item["mid_good"].energy_score == 0.65
    assert by_item["mid_good"].target_cut_rate_min == 10.0
    assert by_item["mid_good"].target_cut_rate_max == 20.0
    assert by_item["mid_good"].actual_cut_rate == 15.0
    assert by_item["mid_good"].pacing_status == "good_pacing_match"

    assert by_item["low_fast"].energy_score == 0.30
    assert by_item["low_fast"].target_cut_rate_min == 4.0
    assert by_item["low_fast"].target_cut_rate_max == 10.0
    assert by_item["low_fast"].actual_cut_rate == 30.0
    assert by_item["low_fast"].pacing_status == "pacing_too_fast_for_energy"

    assert "pacing_too_slow_for_energy" in suggestion_types
    assert "pacing_too_fast_for_energy" in suggestion_types
    assert "clip_too_long_review" in suggestion_types
    assert "clip_too_short_review" in suggestion_types
    assert "missing_breathing_room" in suggestion_types
    assert report.fast_run_count >= 3
    assert report.review_required is True
    assert report.can_apply_pacing is False
    assert report.can_split_clips is False
    assert report.can_merge_clips is False
    assert report.can_trim is False
    assert report.can_extend is False
    assert report.can_reorder_timeline is False
    assert report.can_render is False


def test_engine_detects_monotone_pacing_risk() -> None:
    report = build_dynamic_pacing_for_job(
        _job(
            [
                _item(f"mono_{index}", f"seg_mono_{index}", index * 5.0, index * 5.0 + 5.0, content_value_score=0.65)
                for index in range(4)
            ]
        )
    )

    assert report.monotony_score >= 0.75
    assert "monotone_pacing_risk" in _suggestion_types(report)


def test_engine_marks_censor_protected_and_continuity_items_review_only() -> None:
    report = build_dynamic_pacing_for_job(
        _job(
            [
                _item(
                    "protected",
                    "seg_protected",
                    0.0,
                    5.0,
                    action="protect",
                    protected=True,
                ),
                _item(
                    "censor",
                    "seg_censor",
                    5.0,
                    10.0,
                    action="censor_keep",
                    censor_sfx_required=True,
                ),
                _item(
                    "continuity",
                    "seg_continuity",
                    10.0,
                    15.0,
                    action="blocked_by_continuity",
                    continuity_blocked=True,
                ),
            ]
        )
    )

    by_item = {segment.source_item_id: segment for segment in report.pacing_segments}
    suggestion_types = _suggestion_types(report)

    assert report.status == "blocked"
    assert by_item["protected"].pacing_status == "protected_pacing_preserved"
    assert by_item["censor"].pacing_status == "censor_pacing_review_required"
    assert by_item["continuity"].pacing_status == "continuity_pacing_blocked"
    assert "protected_pacing_preserved" in suggestion_types
    assert "censor_pacing_review_required" in suggestion_types
    assert "continuity_pacing_blocked" in suggestion_types
    assert "continuity_pacing_blocked" in report.blocking_reasons


def test_engine_returns_safe_report_when_timeline_items_are_missing() -> None:
    report = build_dynamic_pacing_for_job(_job([]))

    assert report.status == "no_timeline_items"
    assert report.pacing_segments == []
    assert "no_review_timeline_items_available" in report.warnings
    assert report.can_apply_pacing is False
    assert report.can_render is False


def test_dynamic_pacing_report_from_dict_forces_review_only_contract() -> None:
    report = DynamicPacingReport.from_dict(
        {
            "status": "pacing_analysis_ready",
            "review_required": False,
            "can_apply_pacing": True,
            "can_split_clips": True,
            "can_merge_clips": True,
            "can_trim": True,
            "can_extend": True,
            "can_reorder_timeline": True,
            "can_render": True,
            "metadata": {},
        }
    )
    data = report.to_dict()

    assert data["review_required"] is True
    assert data["can_apply_pacing"] is False
    assert data["can_split_clips"] is False
    assert data["can_merge_clips"] is False
    assert data["can_trim"] is False
    assert data["can_extend"] is False
    assert data["can_reorder_timeline"] is False
    assert data["can_render"] is False
    assert data["metadata"]["review_only"] is True
    assert data["metadata"]["dynamic_pacing_only"] is True
    assert data["metadata"]["media_unchanged"] is True
    assert data["metadata"]["no_execution_in_2b_39"] is True
    assert data["metadata"]["no_render_in_2b_39"] is True
    assert data["metadata"]["no_timeline_reorder_in_2b_39"] is True
    assert data["metadata"]["no_pacing_apply_in_2b_39"] is True
    assert data["metadata"]["no_split_merge_trim_extend_in_2b_39"] is True
