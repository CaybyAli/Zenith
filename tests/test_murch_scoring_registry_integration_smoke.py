from __future__ import annotations

from pathlib import Path

from core.unified_edit_signal_registry import build_unified_edit_signal_result
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "core" / "unified_edit_signal_registry.py"

FORBIDDEN_ACTION_HINTS = [
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


def _minimal_job_data() -> dict:
    return {
        "job_id": "job_murch_registry_test",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }


def _murch_score(
    tier: str,
    index: int,
    emotion_score: float = 0.4,
    story_score: float = 0.4,
    censor_required: bool = False,
) -> dict:
    start = 20.0 + (index * 10.0)
    end = start + 4.0

    return {
        "segment_id": f"murch_segment_{index}_{tier}",
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": (start + end) / 2.0,
        "duration_seconds": end - start,
        "segment_type": "normal_content",
        "murch_score": 0.9 if tier == "high" else 0.55 if tier == "medium" else 0.25,
        "murch_tier": tier,
        "emotion_score": emotion_score,
        "story_score": story_score,
        "rhythm_score": 0.5,
        "eye_trace_score": 0.5,
        "screen_direction_score": 0.5,
        "spatial_continuity_score": 0.5,
        "protection_score": 0.9 if tier == "protected" else 0.0,
        "risk_score": 0.8 if tier == "technical_warning" else 0.0,
        "dead_content_risk_score": 0.0,
        "technical_risk_score": 0.9 if tier == "technical_warning" else 0.0,
        "censor_required": censor_required,
        "is_censor_required": censor_required,
        "is_protected_context": tier == "protected",
        "recommendation": f"review_{tier}_murch_score_segment",
        "evidence": {"test": True},
        "source_signal_ids": [f"murch_source_sig_{index}"],
        "warnings": [],
        "errors": [],
        "metadata": {"test": True},
    }


def _job_with_murch_scores() -> Job:
    scores = [
        _murch_score("high", 1, emotion_score=0.85, story_score=0.40),
        _murch_score("medium", 2),
        _murch_score("low", 3),
        _murch_score("protected", 4),
        _murch_score("technical_warning", 5),
        _murch_score("medium", 6, censor_required=True),
        _murch_score("high", 7, emotion_score=0.40, story_score=0.85),
    ]

    return Job.from_dict(
        {
            **_minimal_job_data(),
            "murch_scoring_report": {
                "status": "ok",
                "source": "murch_scoring",
                "segment_scores": scores,
                "segment_score_count": len(scores),
                "recommendation": "review_murch_scoring_result",
            },
        }
    )


def test_registry_collects_murch_scoring_source_counts() -> None:
    job = _job_with_murch_scores()

    result = build_unified_edit_signal_result(job)

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.source_counts["murch_scoring"] >= 7


def test_registry_collects_murch_scoring_type_counts() -> None:
    job = _job_with_murch_scores()

    result = build_unified_edit_signal_result(job)

    assert result.type_counts["murch_high_score_segment"] == 2
    assert result.type_counts["murch_medium_score_segment"] == 2
    assert result.type_counts["murch_low_score_segment"] == 1
    assert result.type_counts["murch_protected_context"] == 1
    assert result.type_counts["murch_technical_warning"] == 1
    assert result.type_counts["murch_censor_required_context"] == 1
    assert result.type_counts["murch_emotion_high"] == 1
    assert result.type_counts["murch_story_high"] == 1


def test_registry_murch_signals_are_review_only() -> None:
    job = _job_with_murch_scores()

    result = build_unified_edit_signal_result(job)

    murch_signals = [
        signal for signal in result.signals
        if signal.get("source") == "murch_scoring"
    ]

    assert murch_signals

    for signal in murch_signals:
        action_hint = str(signal.get("action_hint") or "").lower()
        for forbidden in FORBIDDEN_ACTION_HINTS:
            assert forbidden not in action_hint


def test_registry_uses_murch_scoring_adapter() -> None:
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    assert "adapt_murch_scoring_report_to_signals" in text
    assert 'SOURCE_MURCH_SCORING = "murch_scoring"' in text
    assert 'source_counts[SOURCE_MURCH_SCORING]' in text
    assert '_job_attr(job, "murch_scoring_report")' in text
    assert '"murch_scoring_segment_scores"' in text


def test_existing_registry_sources_remain_present() -> None:
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    expected_sources = [
        "segment_classifier",
        "content_value",
        "profanity_censor",
        "dead_content",
        "sentence_boundary",
        "keyword_emotion",
        "interaction_classification",
        "scene_change",
        "motion_analysis",
        "face_reaction",
        "stutter_detection",
        "screen_content",
        "visual_energy",
    ]

    for source in expected_sources:
        assert source in text


def test_registry_file_has_no_bom_and_ends_with_newline() -> None:
    files = [
        REGISTRY_PATH,
        ROOT / "tests" / "test_murch_scoring_registry_integration_smoke.py",
    ]

    for path in files:
        content = path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert content.endswith(b"\n"), f"{path} does not end with newline"
