from __future__ import annotations

from core.hook_identification_engine import identify_hook_candidates_for_job


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
        "job_id": "job_hook_engine",
        "review_timeline_dashboard_package_report": {
            "status": "ready_for_dashboard",
            "dashboard_package": {
                "dashboard_package_id": "dashboard_hook_engine",
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
        "energy_peak_report": {"peaks": []},
        "keyword_emotion_report": {"segment_scores": []},
    }
    data.update(overrides)
    return data


def test_hook_engine_finds_candidate_and_uses_core_score_formula() -> None:
    job = _job(
        [_item("card_a", "seg_a", 10.0, 15.0)],
        energy_peak_report={
            "peaks": [
                {
                    "segment_id": "seg_a",
                    "start_seconds": 10.0,
                    "end_seconds": 15.0,
                    "peak_score": 0.8,
                    "energy_score": 0.8,
                }
            ]
        },
        keyword_emotion_report={
            "segment_scores": [
                {
                    "segment_id": "seg_a",
                    "start_seconds": 10.0,
                    "end_seconds": 15.0,
                    "shock_score": 0.6,
                    "emotion_score": 0.7,
                }
            ]
        },
    )

    report = identify_hook_candidates_for_job(job)
    candidate = report.selected_candidate

    assert report.status == "hook_candidate_found"
    assert candidate is not None
    assert candidate.source_segment_id == "seg_a"
    assert candidate.energy_peak_score == 0.8
    assert candidate.surprise_factor_score == 0.6
    assert candidate.emotional_value_score == 0.7
    assert candidate.hook_score == 0.71
    assert candidate.review_required is True
    assert candidate.review_only is True
    assert report.can_apply_hook is False
    assert report.can_reorder_timeline is False
    assert report.can_render is False


def test_hook_engine_prefers_higher_hook_score() -> None:
    job = _job(
        [
            _item("card_low", "seg_low", 1.0, 6.0),
            _item("card_high", "seg_high", 8.0, 13.0),
        ],
        energy_peak_report={
            "peaks": [
                {"segment_id": "seg_low", "peak_score": 0.55},
                {"segment_id": "seg_high", "peak_score": 0.95},
            ]
        },
        keyword_emotion_report={
            "segment_scores": [
                {"segment_id": "seg_low", "shock_score": 0.5, "emotion_score": 0.5},
                {"segment_id": "seg_high", "shock_score": 0.8, "emotion_score": 0.9},
            ]
        },
    )

    report = identify_hook_candidates_for_job(job)

    assert report.selected_candidate is not None
    assert report.selected_candidate.source_segment_id == "seg_high"
    assert report.best_hook_score == report.selected_candidate.hook_score


def test_hook_engine_prefers_three_to_eight_seconds_when_scores_tie() -> None:
    job = _job(
        [
            _item("card_long", "seg_long", 1.0, 11.0),
            _item("card_ideal", "seg_ideal", 12.0, 17.0),
        ],
        energy_peak_report={
            "peaks": [
                {"segment_id": "seg_long", "peak_score": 0.8},
                {"segment_id": "seg_ideal", "peak_score": 0.8},
            ]
        },
        keyword_emotion_report={
            "segment_scores": [
                {"segment_id": "seg_long", "shock_score": 0.8, "emotion_score": 0.8},
                {"segment_id": "seg_ideal", "shock_score": 0.8, "emotion_score": 0.8},
            ]
        },
    )

    report = identify_hook_candidates_for_job(job)
    long_candidate = next(
        candidate
        for candidate in report.candidates
        if candidate.source_segment_id == "seg_long"
    )

    assert report.selected_candidate is not None
    assert report.selected_candidate.source_segment_id == "seg_ideal"
    assert "hook_duration_too_long_preferred_3_to_8_seconds" in long_candidate.warnings


def test_hook_engine_marks_short_and_long_candidates_without_trimming() -> None:
    job = _job(
        [
            _item("card_short", "seg_short", 1.0, 2.5),
            _item("card_long", "seg_long", 3.0, 13.0),
        ],
        energy_peak_report={
            "peaks": [
                {"segment_id": "seg_short", "peak_score": 0.95},
                {"segment_id": "seg_long", "peak_score": 0.9},
            ]
        },
        keyword_emotion_report={
            "segment_scores": [
                {"segment_id": "seg_short", "shock_score": 0.9, "emotion_score": 0.9},
                {"segment_id": "seg_long", "shock_score": 0.9, "emotion_score": 0.9},
            ]
        },
    )

    report = identify_hook_candidates_for_job(job)
    by_segment = {
        candidate.source_segment_id: candidate
        for candidate in report.candidates
    }

    assert "hook_duration_too_short_preferred_3_to_8_seconds" in (
        by_segment["seg_short"].warnings
    )
    assert "hook_duration_too_long_preferred_3_to_8_seconds" in (
        by_segment["seg_long"].warnings
    )
    assert by_segment["seg_short"].start_seconds == 1.0
    assert by_segment["seg_short"].end_seconds == 2.5


def test_hook_engine_keeps_safety_review_only_for_protected_censor_and_continuity() -> None:
    job = _job(
        [
            _item(
                "card_safe",
                "seg_safe",
                1.0,
                6.0,
                protected=True,
                censor_sfx_required=True,
            ),
            _item(
                "card_blocked",
                "seg_blocked",
                8.0,
                13.0,
                continuity_blocked=True,
            ),
        ],
        energy_peak_report={
            "peaks": [
                {"segment_id": "seg_safe", "peak_score": 0.8},
                {"segment_id": "seg_blocked", "peak_score": 0.99},
            ]
        },
        keyword_emotion_report={
            "segment_scores": [
                {"segment_id": "seg_safe", "shock_score": 0.8, "emotion_score": 0.8},
                {"segment_id": "seg_blocked", "shock_score": 0.99, "emotion_score": 0.99},
            ]
        },
    )

    report = identify_hook_candidates_for_job(job)
    blocked = next(
        candidate
        for candidate in report.candidates
        if candidate.source_segment_id == "seg_blocked"
    )

    assert report.selected_candidate is not None
    assert report.selected_candidate.source_segment_id == "seg_safe"
    assert "protected_context_preserved" in report.selected_candidate.safety_flags
    assert "censor_segment_preserved" in report.selected_candidate.safety_flags
    assert "continuity_blocked_review_required" in blocked.blocking_reasons
    assert report.can_apply_hook is False
    assert report.can_reorder_timeline is False
    assert report.can_render is False


def test_hook_engine_returns_safe_no_candidate_report_when_empty() -> None:
    report = identify_hook_candidates_for_job(_job([]))

    assert report.status == "no_safe_hook_candidate"
    assert report.selected_candidate is None
    assert report.total_candidates == 0
    assert report.review_required is True
    assert report.can_apply_hook is False
    assert report.can_reorder_timeline is False
    assert report.can_render is False
    assert "no_review_timeline_items_available" in report.warnings
