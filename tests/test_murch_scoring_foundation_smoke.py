from __future__ import annotations

from pathlib import Path

from core.murch_scoring_system import (
    build_murch_breakdown,
    clamp_score,
    default_murch_weights,
    score_segments_with_murch,
    score_segment_with_murch,
)
from models.murch_scoring import (
    MURCH_TIER_HIGH,
    MURCH_TIER_LOW,
    MURCH_TIER_PROTECTED,
    MURCH_TIER_TECHNICAL_WARNING,
    STATUS_SKIPPED_NO_SEGMENTS,
    MurchScoreBreakdown,
    MurchScoringResult,
    MurchSegmentScore,
)
from models.segment_classification import SegmentClassification


PROJECT_ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    PROJECT_ROOT / "models" / "murch_scoring.py",
    PROJECT_ROOT / "core" / "murch_scoring_system.py",
    PROJECT_ROOT / "tests" / "test_murch_scoring_foundation_smoke.py",
]

FORBIDDEN_ACTION_PARTS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
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
]


def test_murch_score_breakdown_roundtrip() -> None:
    breakdown = MurchScoreBreakdown(
        emotion_score=0.8,
        story_score=0.7,
        rhythm_score=0.6,
        eye_trace_score=0.5,
        screen_direction_score=0.4,
        spatial_continuity_score=0.3,
        weighted_score=0.7,
        weights=default_murch_weights(),
        evidence={"reason": "smoke"},
        warnings=["warn"],
        errors=[],
        metadata={"phase": "2B-26-A"},
    )

    loaded = MurchScoreBreakdown.from_dict(breakdown.to_dict())

    assert loaded.to_dict() == breakdown.to_dict()


def test_murch_segment_score_roundtrip() -> None:
    score = MurchSegmentScore(
        segment_id="segment_1",
        start_seconds=1.0,
        end_seconds=4.0,
        center_seconds=2.5,
        duration_seconds=3.0,
        segment_type="highlight",
        murch_score=0.82,
        murch_tier=MURCH_TIER_HIGH,
        emotion_score=0.9,
        story_score=0.8,
        rhythm_score=0.7,
        eye_trace_score=0.6,
        screen_direction_score=0.5,
        spatial_continuity_score=0.4,
        protection_score=0.0,
        risk_score=0.0,
        dead_content_risk_score=0.0,
        technical_risk_score=0.0,
        censor_required=False,
        is_high_murch_score=True,
        recommendation="review_high_murch_score_segment",
        evidence={"reason": "smoke"},
        source_segment_id="segment_1",
        source_signal_ids=["signal_1"],
        metadata={"phase": "2B-26-A"},
    )

    loaded = MurchSegmentScore.from_dict(score.to_dict())

    assert loaded.to_dict() == score.to_dict()


def test_murch_scoring_result_roundtrip() -> None:
    segment_score = MurchSegmentScore(
        segment_id="segment_1",
        murch_score=0.82,
        murch_tier=MURCH_TIER_HIGH,
        recommendation="review_high_murch_score_segment",
    )
    result = MurchScoringResult(
        status="ok",
        segment_scores=[segment_score],
        segment_score_count=1,
        high_score_count=1,
        avg_murch_score=0.82,
        max_murch_score=0.82,
        min_murch_score=0.82,
        recommendation="review_murch_scoring_result",
        metadata={"phase": "2B-26-A"},
    )

    loaded = MurchScoringResult.from_dict(result.to_dict())

    assert loaded.to_dict() == result.to_dict()


def test_default_murch_weights_have_six_criteria_and_sum_to_one() -> None:
    weights = default_murch_weights()

    assert set(weights) == {
        "emotion",
        "story",
        "rhythm",
        "eye_trace",
        "screen_direction",
        "spatial_continuity",
    }
    assert abs(sum(weights.values()) - 1.0) < 0.000001


def test_high_emotional_segment_gets_high_score() -> None:
    segment = SegmentClassification(
        segment_id="high_emotion",
        start_seconds=10.0,
        end_seconds=20.0,
        center_seconds=15.0,
        duration_seconds=10.0,
        segment_type="highlight",
        confidence=0.9,
        segment_score=0.9,
        content_value_score=0.9,
        is_highlight_candidate=True,
        source_signal_ids=["s1", "s2"],
        evidence={
            "signal_types": [
                "content_value_high_segment",
                "keyword_hype_segment",
                "face_high_reaction_segment",
            ]
        },
    )

    result = score_segment_with_murch(segment)

    assert result.murch_tier == MURCH_TIER_HIGH
    assert result.is_high_murch_score is True
    assert result.murch_score >= 0.72
    assert result.recommendation == "review_high_murch_score_segment"


def test_protected_context_stays_protected() -> None:
    segment = SegmentClassification(
        segment_id="protected_context",
        segment_type="protected_context",
        confidence=0.8,
        segment_score=0.55,
        protection_score=0.9,
        is_protected_context=True,
        evidence={"signal_types": ["interaction_question_answer_segment"]},
    )

    result = score_segment_with_murch(segment)

    assert result.murch_tier == MURCH_TIER_PROTECTED
    assert result.is_protected_context is True
    assert result.recommendation == "review_protected_murch_context"


def test_dead_candidate_lowers_score_but_never_removes() -> None:
    segment = SegmentClassification(
        segment_id="dead_candidate",
        segment_type="dead_candidate",
        confidence=0.7,
        segment_score=0.2,
        content_value_score=0.1,
        dead_content_score=0.9,
        is_dead_candidate=True,
        evidence={"signal_types": ["dead_content_dead_air_candidate"]},
    )

    result = score_segment_with_murch(segment)

    assert result.murch_tier == MURCH_TIER_LOW
    assert result.is_low_murch_score is True
    assert result.recommendation == "review_low_murch_score_segment"
    assert "remove" not in result.recommendation
    assert "delete" not in result.recommendation
    assert "cut" not in result.recommendation


def test_technical_warning_becomes_technical_warning_tier() -> None:
    segment = SegmentClassification(
        segment_id="technical_warning",
        segment_type="technical_warning",
        confidence=0.8,
        segment_score=0.4,
        technical_risk_score=0.9,
        is_technical_warning=True,
        evidence={"signal_types": ["stutter_segment_candidate"]},
    )

    result = score_segment_with_murch(segment)

    assert result.murch_tier == MURCH_TIER_TECHNICAL_WARNING
    assert result.technical_risk_score >= 0.75
    assert result.recommendation == "review_technical_murch_warning"


def test_censor_required_is_preserved_and_not_removed() -> None:
    segment = SegmentClassification(
        segment_id="censor_required",
        segment_type="censor_required_segment",
        confidence=0.8,
        segment_score=0.7,
        content_value_score=0.7,
        censor_required=True,
        evidence={"signal_types": ["profanity_censor_sfx_required"]},
    )

    result = score_segment_with_murch(segment)

    assert result.censor_required is True
    assert result.is_censor_required is True
    assert result.recommendation == "review_murch_score_with_censor_sfx"
    assert "remove" not in result.recommendation
    assert "delete" not in result.recommendation


def test_low_segment_gets_low_tier() -> None:
    segment = SegmentClassification(
        segment_id="low_segment",
        segment_type="normal_content",
        confidence=0.1,
        segment_score=0.1,
        content_value_score=0.05,
        dead_content_score=0.7,
    )

    result = score_segment_with_murch(segment)

    assert result.murch_tier == MURCH_TIER_LOW
    assert result.recommendation == "review_low_murch_score_segment"


def test_no_segments_returns_skipped_no_segments() -> None:
    result = score_segments_with_murch([])

    assert result.status == STATUS_SKIPPED_NO_SEGMENTS
    assert result.segment_score_count == 0
    assert result.recommendation == "murch_scoring_skipped_no_segments"


def test_all_scores_are_clamped_between_zero_and_one() -> None:
    assert clamp_score(-99) == 0.0
    assert clamp_score(99) == 1.0
    assert clamp_score("bad") == 0.0

    segment = SegmentClassification(
        segment_id="clamp_segment",
        segment_type="highlight",
        confidence=99.0,
        segment_score=99.0,
        content_value_score=99.0,
        technical_risk_score=-99.0,
        is_highlight_candidate=True,
    )

    result = score_segment_with_murch(segment)
    values = [
        result.murch_score,
        result.emotion_score,
        result.story_score,
        result.rhythm_score,
        result.eye_trace_score,
        result.screen_direction_score,
        result.spatial_continuity_score,
        result.protection_score,
        result.risk_score,
        result.dead_content_risk_score,
        result.technical_risk_score,
    ]

    for value in values:
        assert 0.0 <= value <= 1.0


def test_build_murch_breakdown_has_all_rule_of_six_scores() -> None:
    segment = SegmentClassification(
        segment_id="breakdown_segment",
        segment_type="highlight",
        segment_score=0.8,
        content_value_score=0.8,
        is_highlight_candidate=True,
    )

    breakdown = build_murch_breakdown(segment)

    assert 0.0 <= breakdown.emotion_score <= 1.0
    assert 0.0 <= breakdown.story_score <= 1.0
    assert 0.0 <= breakdown.rhythm_score <= 1.0
    assert 0.0 <= breakdown.eye_trace_score <= 1.0
    assert 0.0 <= breakdown.screen_direction_score <= 1.0
    assert 0.0 <= breakdown.spatial_continuity_score <= 1.0
    assert 0.0 <= breakdown.weighted_score <= 1.0


def test_no_automatic_cut_remove_or_render_action_is_created() -> None:
    segments = [
        SegmentClassification(
            segment_id="high",
            segment_type="highlight",
            segment_score=0.9,
            content_value_score=0.9,
            is_highlight_candidate=True,
        ),
        SegmentClassification(
            segment_id="low",
            segment_type="dead_candidate",
            segment_score=0.1,
            dead_content_score=0.9,
            is_dead_candidate=True,
        ),
    ]

    result = score_segments_with_murch(segments)

    serialized = str(result.to_dict())
    for forbidden in FORBIDDEN_ACTION_PARTS:
        assert forbidden not in serialized


def test_new_files_have_no_bom_and_end_with_newline() -> None:
    for path in NEW_FILES:
        data = path.read_bytes()

        assert data.startswith(b"\xef\xbb\xbf") is False
        assert data.endswith(b"\n")
