from __future__ import annotations

from core.reaction_shot_placement_engine import ReactionShotPlacementEngine


def _base_job(**extra):
    data = {
        "job_id": "job_reaction_engine_smoke",
        "review_timeline_plan_items": [
            {
                "item_id": "highlight_1",
                "segment_id": "seg_highlight_1",
                "start_seconds": 10.0,
                "end_seconds": 14.0,
                "duration_seconds": 4.0,
                "action": "highlight",
                "hook_score": 0.92,
                "content_value_score": 0.90,
            }
        ],
    }
    data.update(extra)
    return data


def test_engine_builds_candidate_and_after_highlight_placement():
    job = _base_job(
        face_reaction_segments=[
            {
                "segment_id": "face_1",
                "start_seconds": 15.0,
                "end_seconds": 17.0,
                "duration_seconds": 2.0,
                "reaction_type": "hype_reaction",
                "reaction_score": 0.90,
                "face_reaction_score": 0.95,
                "expressiveness_score": 0.95,
            }
        ],
    )

    report = ReactionShotPlacementEngine().build_report(job)

    assert report.total_candidates >= 1
    assert report.total_placements >= 1
    assert report.placements[0].placement_type == "after_highlight"
    assert report.placements[0].suggested_position == "after_trigger"
    assert report.placements[0].reaction_start_seconds >= 14.0
    assert report.placements[0].placement_score > 0.70

    assert report.review_required is True
    assert report.can_apply_reaction_shots is False
    assert report.can_move_clip is False
    assert report.can_insert_clip is False
    assert report.can_trim is False
    assert report.can_extend is False
    assert report.can_reorder_timeline is False
    assert report.can_render is False


def test_engine_extracts_keyword_reaction_candidate():
    job = _base_job(
        keyword_emotion_matches=[
            {
                "segment_id": "kw_1",
                "start_seconds": 15.5,
                "end_seconds": 17.5,
                "duration_seconds": 2.0,
                "matched_text": "haha no way alter krass",
                "keyword_reaction_score": 0.88,
                "emotion_score": 0.84,
            }
        ],
    )

    report = ReactionShotPlacementEngine().build_report(job)

    assert report.total_candidates >= 1
    assert any(
        candidate.reaction_type in {
            "laugh_reaction",
            "shock_reaction",
            "hype_reaction",
            "surprise_reaction",
        }
        for candidate in report.candidates
    )


def test_engine_prefers_reaction_after_trigger_over_before_trigger():
    job = _base_job(
        face_reaction_segments=[
            {
                "segment_id": "face_before",
                "start_seconds": 7.0,
                "end_seconds": 9.0,
                "duration_seconds": 2.0,
                "reaction_type": "shock_reaction",
                "reaction_score": 1.0,
                "face_reaction_score": 1.0,
                "expressiveness_score": 1.0,
            },
            {
                "segment_id": "face_after",
                "start_seconds": 15.0,
                "end_seconds": 17.0,
                "duration_seconds": 2.0,
                "reaction_type": "hype_reaction",
                "reaction_score": 0.72,
                "face_reaction_score": 0.72,
                "expressiveness_score": 0.72,
            },
        ],
    )

    report = ReactionShotPlacementEngine().build_report(job)
    placement = report.placements[0]

    assert placement.reaction_start_seconds == 15.0
    assert placement.suggested_position == "after_trigger"
    assert "reaction_before_trigger_manual_review" not in placement.warnings


def test_engine_marks_reaction_before_trigger_as_manual_review_warning():
    job = _base_job(
        face_reaction_segments=[
            {
                "segment_id": "face_before_only",
                "start_seconds": 7.0,
                "end_seconds": 9.0,
                "duration_seconds": 2.0,
                "reaction_type": "shock_reaction",
                "reaction_score": 0.95,
                "face_reaction_score": 0.95,
                "expressiveness_score": 0.95,
            }
        ],
    )

    report = ReactionShotPlacementEngine().build_report(job)
    placement = report.placements[0]

    assert placement.suggested_position == "manual_review_only"
    assert "reaction_before_trigger_manual_review" in placement.warnings


def test_engine_reviews_short_long_and_strong_long_reaction_duration():
    job = _base_job(
        face_reaction_segments=[
            {
                "segment_id": "too_short",
                "start_seconds": 15.0,
                "end_seconds": 15.6,
                "duration_seconds": 0.6,
                "reaction_type": "hype_reaction",
                "reaction_score": 0.96,
                "face_reaction_score": 0.96,
                "expressiveness_score": 0.96,
            },
            {
                "segment_id": "strong_long",
                "start_seconds": 18.0,
                "end_seconds": 22.5,
                "duration_seconds": 4.5,
                "reaction_type": "shock_reaction",
                "reaction_score": 0.90,
                "face_reaction_score": 0.90,
                "expressiveness_score": 0.90,
            },
            {
                "segment_id": "too_long",
                "start_seconds": 25.0,
                "end_seconds": 31.0,
                "duration_seconds": 6.0,
                "reaction_type": "laugh_reaction",
                "reaction_score": 0.88,
                "face_reaction_score": 0.88,
                "expressiveness_score": 0.88,
            },
        ],
    )

    report = ReactionShotPlacementEngine().build_report(job)

    all_warnings = []
    for candidate in report.candidates:
        all_warnings.extend(candidate.warnings)
    for placement in report.placements:
        all_warnings.extend(placement.warnings)

    assert "too_short_reaction" in all_warnings
    assert "too_long_reaction" in all_warnings
    assert any(
        candidate.duration_seconds == 4.5
        and "too_long_reaction" not in candidate.warnings
        for candidate in report.candidates
    )


def test_engine_marks_consecutive_reaction_risk():
    job = _base_job(
        face_reaction_segments=[
            {
                "segment_id": "face_a",
                "start_seconds": 15.0,
                "end_seconds": 17.0,
                "duration_seconds": 2.0,
                "reaction_type": "hype_reaction",
                "reaction_score": 0.90,
                "face_reaction_score": 0.90,
                "expressiveness_score": 0.90,
            },
            {
                "segment_id": "face_b",
                "start_seconds": 17.5,
                "end_seconds": 19.5,
                "duration_seconds": 2.0,
                "reaction_type": "laugh_reaction",
                "reaction_score": 0.70,
                "face_reaction_score": 0.70,
                "expressiveness_score": 0.70,
            },
        ],
    )

    report = ReactionShotPlacementEngine().build_report(job)

    assert any(
        "consecutive_reaction_risk" in placement.warnings
        for placement in report.placements
    )


def test_engine_creates_manual_placeholder_when_trigger_has_no_reaction():
    job = _base_job(face_reaction_segments=[])

    report = ReactionShotPlacementEngine().build_report(job)

    assert report.missing_reaction_placeholder_count >= 1
    assert any(
        placement.placement_type == "manual_placeholder"
        for placement in report.placements
    )
    assert any(
        "missing_reaction_placeholder" in placement.warnings
        for placement in report.placements
    )


def test_engine_preserves_censor_protected_and_continuity_blocked_items():
    job = _base_job(
        review_timeline_plan_items=[
            {
                "item_id": "censor_item",
                "segment_id": "censor_seg",
                "start_seconds": 10.0,
                "end_seconds": 14.0,
                "duration_seconds": 4.0,
                "action": "censor_keep",
                "content_value_score": 0.80,
            },
            {
                "item_id": "protected_item",
                "segment_id": "protected_seg",
                "start_seconds": 20.0,
                "end_seconds": 24.0,
                "duration_seconds": 4.0,
                "action": "protect",
                "protected": True,
            },
            {
                "item_id": "continuity_item",
                "segment_id": "continuity_seg",
                "start_seconds": 30.0,
                "end_seconds": 34.0,
                "duration_seconds": 4.0,
                "action": "blocked_by_continuity",
                "continuity_blocked": True,
            },
        ],
        face_reaction_segments=[
            {
                "segment_id": "face_after",
                "start_seconds": 15.0,
                "end_seconds": 17.0,
                "duration_seconds": 2.0,
                "reaction_type": "hype_reaction",
                "reaction_score": 0.90,
                "face_reaction_score": 0.90,
                "expressiveness_score": 0.90,
            }
        ],
    )

    report = ReactionShotPlacementEngine().build_report(job)

    placement_types = {placement.placement_type for placement in report.placements}
    assert "censor_review_required" in placement_types
    assert "protected_preserved" in placement_types
    assert "blocked_by_continuity" in placement_types

    assert "reaction_shot_continuity_blocked" in report.blocking_reasons
    assert "reaction_shot_censor_review_required" in report.warnings
    assert "reaction_shot_protected_preserved" in report.warnings