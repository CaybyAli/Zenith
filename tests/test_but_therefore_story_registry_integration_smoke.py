from __future__ import annotations

from pathlib import Path

from core.but_therefore_story_signal_adapter import (
    adapt_but_therefore_story_report_to_signals,
)
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_story_registry",
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
    data.update(overrides)
    return data


def _story_report() -> dict:
    return {
        "report_id": "but_therefore_story_report_registry",
        "job_id": "job_story_registry",
        "status": "story_analysis_ready_with_warnings",
        "moments": [
            {
                "moment_id": "story_but_1",
                "source_item_id": "item_but",
                "source_segment_id": "seg_but",
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "duration_seconds": 2.0,
                "story_role": "but_moment",
                "story_score": 0.92,
                "conflict_score": 0.92,
                "consequence_score": 0.10,
                "reaction_score": 0.10,
                "neutral_score": 0.10,
                "evidence": ["conflict_or_turning_point_signal"],
                "review_required": True,
                "warnings": [],
                "blocking_reasons": [],
                "metadata": {},
            },
            {
                "moment_id": "story_therefore_1",
                "source_item_id": "item_therefore",
                "source_segment_id": "seg_therefore",
                "start_seconds": 2.0,
                "end_seconds": 4.0,
                "duration_seconds": 2.0,
                "story_role": "therefore_moment",
                "story_score": 0.80,
                "conflict_score": 0.10,
                "consequence_score": 0.80,
                "reaction_score": 0.10,
                "neutral_score": 0.10,
                "evidence": ["consequence_or_resolution_signal"],
                "review_required": True,
                "warnings": [],
                "blocking_reasons": [],
                "metadata": {},
            },
            {
                "moment_id": "story_and_1",
                "source_item_id": "item_and",
                "source_segment_id": "seg_and",
                "start_seconds": 4.0,
                "end_seconds": 6.0,
                "duration_seconds": 2.0,
                "story_role": "and_moment",
                "story_score": 0.35,
                "conflict_score": 0.0,
                "consequence_score": 0.0,
                "reaction_score": 0.0,
                "neutral_score": 0.35,
                "evidence": ["neutral_continuation"],
                "review_required": True,
                "warnings": [],
                "blocking_reasons": [],
                "metadata": {},
            },
            {
                "moment_id": "story_reaction_1",
                "source_item_id": "item_reaction",
                "source_segment_id": "seg_reaction",
                "start_seconds": 6.0,
                "end_seconds": 8.0,
                "duration_seconds": 2.0,
                "story_role": "reaction_moment",
                "story_score": 0.88,
                "conflict_score": 0.20,
                "consequence_score": 0.20,
                "reaction_score": 0.88,
                "neutral_score": 0.10,
                "evidence": ["reaction_signal"],
                "review_required": True,
                "warnings": [],
                "blocking_reasons": [],
                "metadata": {},
            },
            {
                "moment_id": "story_payoff_1",
                "source_item_id": "item_payoff",
                "source_segment_id": "seg_payoff",
                "start_seconds": 8.0,
                "end_seconds": 10.0,
                "duration_seconds": 2.0,
                "story_role": "payoff_moment",
                "story_score": 0.90,
                "conflict_score": 0.30,
                "consequence_score": 0.40,
                "reaction_score": 0.30,
                "neutral_score": 0.10,
                "evidence": ["payoff_or_climax_signal"],
                "review_required": True,
                "warnings": [],
                "blocking_reasons": [],
                "metadata": {},
            },
        ],
        "transitions": [],
        "suggestions": [
            {
                "suggestion_type": "too_many_and_moments",
                "severity": "medium",
                "reason": "Too many neutral moments.",
                "review_required": True,
                "can_apply_story_changes": False,
                "metadata": {},
            },
            {
                "suggestion_type": "weak_but_therefore_ratio",
                "severity": "medium",
                "reason": "Weak ratio.",
                "review_required": True,
                "can_apply_story_changes": False,
                "metadata": {},
            },
            {
                "suggestion_type": "orphan_reaction",
                "severity": "medium",
                "reason": "Orphan reaction.",
                "review_required": True,
                "can_apply_story_changes": False,
                "metadata": {},
            },
            {
                "suggestion_type": "missing_payoff",
                "severity": "medium",
                "reason": "Missing payoff.",
                "review_required": True,
                "can_apply_story_changes": False,
                "metadata": {},
            },
            {
                "suggestion_type": "story_flow_break",
                "severity": "medium",
                "reason": "Flow break.",
                "review_required": True,
                "can_apply_story_changes": False,
                "metadata": {},
            },
        ],
        "total_moments": 5,
        "but_count": 1,
        "therefore_count": 1,
        "and_count": 1,
        "reaction_count": 1,
        "payoff_count": 1,
        "strong_story_count": 4,
        "but_therefore_ratio": 0.8,
        "story_flow_score": 0.75,
        "and_streak_max": 3,
        "orphan_reaction_count": 1,
        "missing_payoff_count": 1,
        "review_required": True,
        "can_apply_story_changes": False,
        "can_remove_and_moments": False,
        "can_reorder_timeline": False,
        "can_trim": False,
        "can_extend": False,
        "can_render": False,
        "warnings": ["too_many_and_moments_in_a_row"],
        "blocking_reasons": [],
        "recommendation": "review_but_therefore_story_warnings",
        "metadata": {
            "review_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_42": True,
            "no_render_in_2b_42": True,
            "no_timeline_reorder_in_2b_42": True,
            "no_story_apply_in_2b_42": True,
            "no_and_moment_remove_in_2b_42": True,
        },
    }


def test_signal_adapter_emits_but_therefore_story_signals() -> None:
    result = adapt_but_therefore_story_report_to_signals(_story_report())
    signal_types = {signal["signal_type"] for signal in result.signals}

    assert "but_therefore_story_ready_with_warnings" in signal_types
    assert "story_but_moment" in signal_types
    assert "story_therefore_moment" in signal_types
    assert "story_and_moment" in signal_types
    assert "story_reaction_moment" in signal_types
    assert "story_payoff_moment" in signal_types
    assert "story_too_many_and_moments" in signal_types
    assert "story_weak_but_therefore_ratio" in signal_types
    assert "story_orphan_reaction" in signal_types
    assert "story_missing_payoff" in signal_types
    assert "story_flow_break" in signal_types

    first_signal = result.signals[0]
    assert first_signal["source"] == "but_therefore_story"
    assert first_signal["action_hint"] == "review_but_therefore_story"
    assert first_signal["metadata"]["review_only"] is True
    assert first_signal["metadata"]["media_unchanged"] is True
    assert first_signal["metadata"]["no_execution_in_2b_42"] is True
    assert first_signal["metadata"]["no_render_in_2b_42"] is True
    assert first_signal["metadata"]["no_timeline_reorder_in_2b_42"] is True
    assert first_signal["metadata"]["no_story_apply_in_2b_42"] is True
    assert first_signal["metadata"]["no_and_moment_remove_in_2b_42"] is True
    assert first_signal["metadata"]["can_apply_story_changes"] is False
    assert first_signal["metadata"]["can_remove_and_moments"] is False
    assert first_signal["metadata"]["can_reorder_timeline"] is False
    assert first_signal["metadata"]["can_trim"] is False
    assert first_signal["metadata"]["can_extend"] is False
    assert first_signal["metadata"]["can_render"] is False


def test_registry_imports_and_processes_but_therefore_story() -> None:
    text = (ROOT / "core" / "unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )

    assert "from core.but_therefore_story_signal_adapter import" in text
    assert "adapt_but_therefore_story_report_to_signals" in text
    assert 'SOURCE_BUT_THEREFORE_STORY = "but_therefore_story"' in text
    assert "but_therefore_story_report" in text
    assert "source_counts[SOURCE_BUT_THEREFORE_STORY]" in text


def test_registry_runtime_counts_but_therefore_story_signals() -> None:
    job = Job.from_dict(
        _job_payload(
            but_therefore_story_report=_story_report(),
        )
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["but_therefore_story"] >= 10
    assert result.type_counts["but_therefore_story_ready_with_warnings"] == 1
    assert result.type_counts["story_but_moment"] == 1
    assert result.type_counts["story_therefore_moment"] == 1
    assert result.type_counts["story_and_moment"] == 1
    assert result.type_counts["story_reaction_moment"] == 1
    assert result.type_counts["story_payoff_moment"] == 1
    assert result.type_counts["story_too_many_and_moments"] == 1
    assert result.type_counts["story_weak_but_therefore_ratio"] == 1
    assert result.type_counts["story_orphan_reaction"] == 1
    assert result.type_counts["story_missing_payoff"] == 1
    assert result.type_counts["story_flow_break"] == 1
