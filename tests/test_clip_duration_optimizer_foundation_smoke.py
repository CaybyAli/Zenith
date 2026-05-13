from pathlib import Path

from core.clip_duration_optimizer import optimize_clip_durations
from models.clip_duration import (
    ClipDurationOptimizationPlan,
    ClipDurationRecommendation,
)


ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    ROOT / "models" / "clip_duration.py",
    ROOT / "core" / "clip_duration_optimizer.py",
    ROOT / "tests" / "test_clip_duration_optimizer_foundation_smoke.py",
]

FORBIDDEN_ACTION_WORDS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_extend",
    "auto_highlight",
    "highlight_now",
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
    "apply_cut",
    "render_now",
    "execute_cut",
    "final_cut",
]

FORBIDDEN_ENGINE_WORDS = [
    "TimelineBuilder",
    "HighlightSelector",
    "ffmpeg",
    "render_video",
]


def test_clip_duration_recommendation_roundtrip():
    recommendation = ClipDurationRecommendation(
        recommendation_id="rec_1",
        source_item_id="item_1",
        segment_id="seg_1",
        start_seconds=1.0,
        end_seconds=9.0,
        center_seconds=5.0,
        duration_seconds=8.0,
        proposed_action="KEEP",
        duration_status="duration_ok",
        recommended_min_duration_seconds=4.0,
        recommended_max_duration_seconds=90.0,
        recommended_target_duration_seconds=18.0,
        confidence=0.8,
        priority="low",
        is_duration_ok=True,
        reason="clip_duration_inside_safe_review_range",
        decision_basis={"review_only": True},
        source_signal_ids=["sig_1"],
        warnings=[],
        errors=[],
        metadata={"source": "test"},
    )

    loaded = ClipDurationRecommendation.from_dict(recommendation.to_dict())

    assert loaded.to_dict() == recommendation.to_dict()


def test_clip_duration_plan_roundtrip():
    recommendation = ClipDurationRecommendation(
        recommendation_id="rec_1",
        duration_status="duration_ok",
        recommended_min_duration_seconds=4.0,
        recommended_max_duration_seconds=90.0,
    )
    plan = ClipDurationOptimizationPlan(
        status="ok",
        recommendations=[recommendation],
        recommendation_count=1,
        duration_ok_count=1,
        recommendation="clip_duration_review_plan_ready",
        metadata={"review_only": True},
    )

    loaded = ClipDurationOptimizationPlan.from_dict(plan.to_dict())

    assert loaded.to_dict() == plan.to_dict()


def test_no_items_returns_skipped_no_cut_list_items():
    plan = optimize_clip_durations([])

    assert plan.status == "skipped_no_cut_list_items"
    assert plan.recommendation_count == 0
    assert plan.recommendation == "clip_duration_skipped_no_cut_list_items"


def test_keep_with_good_duration_is_duration_ok():
    plan = optimize_clip_durations(
        [
            {
                "id": "keep_good",
                "start_seconds": 10.0,
                "end_seconds": 18.0,
                "proposed_action": "KEEP",
                "segment_type": "highlight",
            }
        ]
    )

    rec = plan.recommendations[0]

    assert rec.duration_status == "duration_ok"
    assert rec.is_duration_ok is True
    assert rec.suggested_start_seconds is None
    assert rec.suggested_end_seconds is None


def test_highlight_too_short_gets_review_extend_status():
    plan = optimize_clip_durations(
        [
            {
                "id": "short_highlight",
                "start_seconds": 10.0,
                "end_seconds": 11.0,
                "proposed_action": "KEEP",
                "segment_type": "highlight",
            }
        ]
    )

    rec = plan.recommendations[0]

    assert rec.duration_status in {"too_short_review", "extend_review"}
    assert rec.is_too_short is True
    assert rec.is_review_required is True
    assert rec.suggested_start_seconds is not None
    assert rec.suggested_end_seconds is not None


def test_filler_too_long_gets_review_trim_status():
    plan = optimize_clip_durations(
        [
            {
                "id": "long_filler",
                "start_seconds": 10.0,
                "end_seconds": 45.0,
                "proposed_action": "REVIEW_TRIM",
                "segment_type": "filler",
            }
        ]
    )

    rec = plan.recommendations[0]

    assert rec.duration_status in {"too_long_review", "trim_review"}
    assert rec.is_too_long is True
    assert rec.is_review_required is True
    assert rec.suggested_start_seconds is not None
    assert rec.suggested_end_seconds is not None


def test_protect_duration_is_preserved_without_trim_suggestion():
    plan = optimize_clip_durations(
        [
            {
                "id": "protected_context",
                "start_seconds": 0.0,
                "end_seconds": 45.0,
                "proposed_action": "PROTECT",
                "segment_type": "protected_context",
            }
        ]
    )

    rec = plan.recommendations[0]

    assert rec.duration_status == "protect_duration"
    assert rec.is_protected is True
    assert rec.priority == "high"
    assert rec.suggested_start_seconds is None
    assert rec.suggested_end_seconds is None


def test_censor_keep_duration_is_preserved():
    plan = optimize_clip_durations(
        [
            {
                "id": "censor_keep",
                "start_seconds": 2.0,
                "end_seconds": 6.0,
                "proposed_action": "CENSOR_KEEP",
                "segment_type": "censor_required_segment",
            }
        ]
    )

    rec = plan.recommendations[0]

    assert rec.duration_status == "censor_keep_duration"
    assert rec.is_censor_keep is True
    assert rec.priority == "high"
    assert rec.suggested_start_seconds is None
    assert rec.suggested_end_seconds is None


def test_review_remove_stays_review_only_and_not_removed():
    plan = optimize_clip_durations(
        [
            {
                "id": "review_remove",
                "start_seconds": 5.0,
                "end_seconds": 17.0,
                "proposed_action": "REVIEW_REMOVE",
                "segment_type": "filler",
            }
        ]
    )

    rec = plan.recommendations[0]

    assert rec.proposed_action == "REVIEW_REMOVE"
    assert rec.is_review_required is True
    assert "review_remove_kept_as_review_only" in rec.warnings
    assert rec.metadata["review_only"] is True
    assert "remove" not in rec.reason.replace("review_remove", "")


def test_invalid_timing_gets_invalid_timing_review():
    plan = optimize_clip_durations(
        [
            {
                "id": "invalid",
                "start_seconds": 20.0,
                "end_seconds": 10.0,
                "proposed_action": "KEEP",
            }
        ]
    )

    rec = plan.recommendations[0]

    assert rec.duration_status == "invalid_timing_review"
    assert rec.is_invalid_timing is True
    assert "invalid_clip_timing" in rec.errors


def test_suggested_start_and_end_are_only_suggestions():
    plan = optimize_clip_durations(
        [
            {
                "id": "trim_candidate",
                "start_seconds": 10.0,
                "end_seconds": 50.0,
                "proposed_action": "REVIEW_TRIM",
                "segment_type": "filler",
            }
        ]
    )

    rec = plan.recommendations[0]

    assert rec.suggested_start_seconds is not None
    assert rec.suggested_end_seconds is not None
    assert rec.start_seconds == 10.0
    assert rec.end_seconds == 50.0
    assert rec.metadata["review_only"] is True


def test_optimizer_does_not_emit_automatic_cut_remove_delete_actions():
    plan = optimize_clip_durations(
        [
            {
                "id": "long_filler",
                "start_seconds": 0.0,
                "end_seconds": 40.0,
                "proposed_action": "REVIEW_TRIM",
                "segment_type": "filler",
            },
            {
                "id": "short_highlight",
                "start_seconds": 50.0,
                "end_seconds": 51.0,
                "proposed_action": "KEEP",
                "segment_type": "highlight",
            },
        ]
    )

    dumped = str(plan.to_dict()).lower()

    for forbidden in FORBIDDEN_ACTION_WORDS:
        assert forbidden not in dumped


def test_new_product_files_do_not_contain_timeline_render_words():
    product_files = [
        ROOT / "models" / "clip_duration.py",
        ROOT / "core" / "clip_duration_optimizer.py",
    ]

    for file_path in product_files:
        text = file_path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_ENGINE_WORDS:
            assert forbidden not in text


def test_new_files_have_no_bom_and_end_with_newline():
    for file_path in NEW_FILES:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
