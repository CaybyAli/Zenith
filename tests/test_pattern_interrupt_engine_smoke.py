from __future__ import annotations

from core.pattern_interrupt_engine import build_pattern_interrupt_for_job
from models.pattern_interrupt import PatternInterruptReport


def _item(
    index: int,
    start: float | None,
    end: float | None,
    **overrides,
) -> dict:
    data = {
        "item_id": f"card_{index}",
        "source_segment_id": f"seg_{index}",
        "action": "keep_review",
        "review_required": True,
        "protected": False,
        "censor_sfx_required": False,
        "continuity_blocked": False,
        "safety_status": "ok",
        "warnings": [],
        "blocking_errors": [],
    }
    if start is not None:
        data["source_start_seconds"] = start
    if end is not None:
        data["source_end_seconds"] = end
    if start is not None and end is not None:
        data["duration_seconds"] = end - start
    data.update(overrides)
    return data


def _job(items: list[dict], **overrides) -> dict:
    data = {
        "job_id": "job_pattern_interrupt_engine",
        "review_timeline_dashboard_package_report": {
            "status": "ready_for_dashboard",
            "dashboard_package": {
                "dashboard_package_id": "dashboard_pattern_interrupt_engine",
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


def test_engine_builds_windows_and_detects_monotony_risk() -> None:
    report = build_pattern_interrupt_for_job(
        _job(
            [
                _item(index, index * 10.0, index * 10.0 + 10.0, content_value_score=0.50)
                for index in range(12)
            ]
        )
    )

    assert len(report.windows) == 2
    assert all(45.0 <= window.duration_seconds <= 90.0 for window in report.windows)

    first_window = report.windows[0]
    suggestion_types = _suggestion_types(report)

    assert first_window.average_energy_score == 0.50
    assert first_window.average_cut_rate == 6.0
    assert first_window.energy_variation_score == 0.0
    assert first_window.pacing_variation_score == 0.0
    assert first_window.monotony_score >= 0.62
    assert first_window.interrupt_needed is True
    assert "monotony_risk" in suggestion_types
    assert "pattern_interrupt_needed" in suggestion_types
    assert report.interrupt_needed_count >= 1
    assert report.review_required is True
    assert report.can_apply_interrupts is False
    assert report.can_insert_zoom is False
    assert report.can_insert_text_overlay is False
    assert report.can_insert_sfx is False
    assert report.can_reorder_timeline is False
    assert report.can_trim is False
    assert report.can_extend is False
    assert report.can_render is False


def test_engine_allows_short_timeline_and_order_fallback_timing() -> None:
    report = build_pattern_interrupt_for_job(
        _job(
            [
                _item(0, None, None, content_value_score=0.60),
                _item(1, None, None, content_value_score=0.62),
            ]
        )
    )

    assert len(report.windows) == 1
    assert report.windows[0].duration_seconds == 30.0
    assert "using_pattern_interrupt_order_fallback_timing" in report.warnings


def test_engine_uses_related_sources_for_interrupt_suggestions() -> None:
    items = [
        _item(0, 0.0, 10.0, content_value_score=0.52),
        _item(1, 10.0, 20.0, content_value_score=0.53),
        _item(2, 20.0, 30.0, content_value_score=0.54),
        _item(3, 30.0, 40.0, content_value_score=0.55),
        _item(
            4,
            40.0,
            50.0,
            action="censor_keep",
            censor_sfx_required=True,
        ),
        _item(5, 50.0, 60.0, action="protect", protected=True),
        _item(
            6,
            60.0,
            70.0,
            action="blocked_by_continuity",
            continuity_blocked=True,
        ),
    ]

    report = build_pattern_interrupt_for_job(
        _job(
            items,
            dynamic_pacing_suggestions=[
                {
                    "suggestion_id": "dynamic_breathing",
                    "suggestion_type": "missing_breathing_room",
                    "source_item_id": "card_0",
                    "source_segment_id": "seg_0",
                    "review_required": True,
                    "can_auto_apply": False,
                }
            ],
            emotional_arc_suggestions=[
                {
                    "suggestion_id": "arc_flat",
                    "suggestion_type": "flat_energy_curve",
                    "source_item_id": "card_1",
                    "review_required": True,
                    "can_auto_apply": False,
                }
            ],
            face_reaction_segments=[
                {
                    "source_item_id": "card_2",
                    "source_segment_id": "seg_2",
                    "start_seconds": 20.0,
                    "end_seconds": 30.0,
                    "reaction_score": 0.95,
                }
            ],
            keyword_emotion_matches=[
                {
                    "source_item_id": "card_3",
                    "source_segment_id": "seg_3",
                    "start_seconds": 30.0,
                    "end_seconds": 40.0,
                    "keyword_score": 0.90,
                    "matched_keyword": "no way",
                }
            ],
        )
    )

    suggestion_types = _suggestion_types(report)

    assert report.status == "blocked"
    assert "breathing_break_candidate" in suggestion_types
    assert "energy_shift_needed" in suggestion_types
    assert "zoom_reaction_candidate" in suggestion_types
    assert "text_overlay_candidate" in suggestion_types
    assert "sfx_candidate" in suggestion_types
    assert "censor_interrupt_review_required" in suggestion_types
    assert "protected_interrupt_preserved" in suggestion_types
    assert "continuity_interrupt_blocked" in suggestion_types
    assert "continuity_interrupt_blocked" in report.blocking_reasons


def test_engine_returns_safe_report_when_timeline_items_are_missing() -> None:
    report = build_pattern_interrupt_for_job(_job([]))

    assert report.status == "no_timeline_items"
    assert report.windows == []
    assert "no_review_timeline_items_available" in report.warnings
    assert report.can_apply_interrupts is False
    assert report.can_render is False


def test_pattern_interrupt_report_from_dict_forces_review_only_contract() -> None:
    report = PatternInterruptReport.from_dict(
        {
            "status": "pattern_interrupt_analysis_ready",
            "review_required": False,
            "can_apply_interrupts": True,
            "can_insert_zoom": True,
            "can_insert_text_overlay": True,
            "can_insert_sfx": True,
            "can_reorder_timeline": True,
            "can_trim": True,
            "can_extend": True,
            "can_render": True,
            "metadata": {},
        }
    )
    data = report.to_dict()

    assert data["review_required"] is True
    assert data["can_apply_interrupts"] is False
    assert data["can_insert_zoom"] is False
    assert data["can_insert_text_overlay"] is False
    assert data["can_insert_sfx"] is False
    assert data["can_reorder_timeline"] is False
    assert data["can_trim"] is False
    assert data["can_extend"] is False
    assert data["can_render"] is False
    assert data["metadata"]["review_only"] is True
    assert data["metadata"]["pattern_interrupt_only"] is True
    assert data["metadata"]["media_unchanged"] is True
    assert data["metadata"]["no_execution_in_2b_40"] is True
    assert data["metadata"]["no_render_in_2b_40"] is True
    assert data["metadata"]["no_timeline_reorder_in_2b_40"] is True
    assert data["metadata"]["no_pattern_apply_in_2b_40"] is True
    assert data["metadata"]["no_zoom_insert_in_2b_40"] is True
    assert data["metadata"]["no_text_overlay_insert_in_2b_40"] is True
    assert data["metadata"]["no_sfx_insert_in_2b_40"] is True
