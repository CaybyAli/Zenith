from __future__ import annotations

from core.emotional_arc_builder import build_emotional_arc_for_job
from models.emotional_arc import EMOTIONAL_ARC_PHASES, EmotionalArcReport


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
        "job_id": "job_emotional_arc_builder",
        "review_timeline_dashboard_package_report": {
            "status": "ready_for_dashboard",
            "dashboard_package": {
                "dashboard_package_id": "dashboard_emotional_arc_builder",
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
        "hook_identification_report": {
            "status": "hook_candidate_found",
            "selected_candidate": {
                "candidate_id": "hook_candidate_builder",
                "source_item_id": "card_0",
                "source_segment_id": "seg_0",
                "hook_score": 0.95,
                "confidence": 0.95,
                "review_required": True,
            },
            "candidates": [],
            "review_required": True,
            "can_apply_hook": False,
            "can_reorder_timeline": False,
            "can_render": False,
        },
    }
    data.update(overrides)
    return data


def _curve_items(scores: list[float]) -> list[dict]:
    return [
        _item(
            f"card_{index}",
            f"seg_{index}",
            float(index * 10),
            float(index * 10 + 10),
            content_value_score=score,
        )
        for index, score in enumerate(scores)
    ]


def _suggestion_types(report) -> set[str]:
    return {suggestion.suggestion_type for suggestion in report.suggestions}


def test_builder_creates_arc_points_target_curve_and_deviation_metrics() -> None:
    report = build_emotional_arc_for_job(
        _job(_curve_items([0.95, 0.55, 0.65, 0.85, 0.45, 0.70, 0.80, 1.0, 0.80, 0.50]))
    )

    assert len(report.arc_points) == 10
    assert report.arc_points[0].source_item_id == "card_0"
    assert report.arc_points[0].actual_energy_score == 0.95
    assert report.average_deviation >= 0.0
    assert report.max_deviation >= report.average_deviation

    target_phases = {item["arc_phase"] for item in report.target_curve}
    assert set(EMOTIONAL_ARC_PHASES).issubset(target_phases)
    assert report.review_required is True
    assert report.can_apply_arc is False
    assert report.can_reorder_timeline is False
    assert report.can_trim is False
    assert report.can_extend is False
    assert report.can_render is False


def test_builder_scores_from_direct_sources_and_action_fallbacks() -> None:
    items = [
        _item("keep", "seg_keep", 0.0, 5.0, action="keep_review"),
        _item("trim", "seg_trim", 5.0, 10.0, action="trim_review"),
        _item("remove", "seg_remove", 10.0, 15.0, action="remove_review"),
        _item("censor", "seg_censor", 15.0, 20.0, action="censor_keep"),
        _item(
            "continuity",
            "seg_continuity",
            20.0,
            25.0,
            action="blocked_by_continuity",
            continuity_blocked=True,
        ),
        _item("technical", "seg_technical", 25.0, 30.0, action="technical_review"),
        _item("direct", "seg_direct", 30.0, 35.0, visual_energy_score=0.88),
    ]

    report = build_emotional_arc_for_job(_job(items))
    by_item = {point.source_item_id: point for point in report.arc_points}

    assert by_item["keep"].actual_energy_score == 0.55
    assert by_item["trim"].actual_energy_score == 0.45
    assert by_item["remove"].actual_energy_score == 0.30
    assert by_item["censor"].actual_energy_score == 0.65
    assert by_item["continuity"].actual_energy_score == 0.40
    assert by_item["technical"].actual_energy_score == 0.35
    assert by_item["direct"].actual_energy_score == 0.88
    assert "continuity_arc_blocked" in report.blocking_reasons


def test_builder_emits_weak_hook_missing_climax_and_flat_curve_suggestions() -> None:
    report = build_emotional_arc_for_job(
        _job(
            _curve_items([0.45, 0.48, 0.46, 0.47, 0.45, 0.48, 0.46, 0.47, 0.45, 0.48]),
            hook_identification_report={},
        )
    )

    suggestion_types = _suggestion_types(report)

    assert "weak_hook" in suggestion_types
    assert "missing_climax" in suggestion_types
    assert "flat_energy_curve" in suggestion_types
    assert report.flatness_score >= 0.82


def test_builder_emits_missing_breathing_room_and_abrupt_drop_suggestions() -> None:
    report = build_emotional_arc_for_job(
        _job(_curve_items([0.95, 0.90, 0.92, 0.91, 0.90, 0.92, 0.91, 0.50, 0.88, 0.87]))
    )

    suggestion_types = _suggestion_types(report)

    assert "missing_breathing_room" in suggestion_types
    assert "abrupt_emotional_drop" in suggestion_types


def test_builder_marks_censor_continuity_and_protected_items_review_only() -> None:
    report = build_emotional_arc_for_job(
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

    suggestion_types = _suggestion_types(report)

    assert report.status == "blocked"
    assert "protected_arc_preserved" in suggestion_types
    assert "censor_arc_review_required" in suggestion_types
    assert "continuity_arc_blocked" in suggestion_types
    assert report.can_apply_arc is False
    assert report.can_reorder_timeline is False
    assert report.can_trim is False
    assert report.can_extend is False
    assert report.can_render is False


def test_builder_returns_safe_report_when_timeline_items_are_missing() -> None:
    report = build_emotional_arc_for_job(_job([]))

    assert report.status == "no_timeline_items"
    assert report.arc_points == []
    assert "no_review_timeline_items_available" in report.warnings


def test_emotional_arc_report_from_dict_forces_review_only_contract() -> None:
    report = EmotionalArcReport.from_dict(
        {
            "status": "arc_analysis_ready",
            "review_required": False,
            "can_apply_arc": True,
            "can_reorder_timeline": True,
            "can_trim": True,
            "can_extend": True,
            "can_render": True,
            "metadata": {},
        }
    )
    data = report.to_dict()

    assert data["review_required"] is True
    assert data["can_apply_arc"] is False
    assert data["can_reorder_timeline"] is False
    assert data["can_trim"] is False
    assert data["can_extend"] is False
    assert data["can_render"] is False
    assert data["metadata"]["review_only"] is True
    assert data["metadata"]["emotional_arc_only"] is True
    assert data["metadata"]["media_unchanged"] is True
    assert data["metadata"]["no_execution_in_2b_38"] is True
    assert data["metadata"]["no_render_in_2b_38"] is True
    assert data["metadata"]["no_timeline_reorder_in_2b_38"] is True
    assert data["metadata"]["no_arc_apply_in_2b_38"] is True
