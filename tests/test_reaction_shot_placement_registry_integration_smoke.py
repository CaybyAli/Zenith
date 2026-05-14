from __future__ import annotations

from pathlib import Path

from core.reaction_shot_placement_signal_adapter import (
    adapt_reaction_shot_placement_report_to_signals,
)
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


def _job_payload(**overrides) -> dict:
    data = {
        "job_id": "job_reaction_shot_registry",
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


def _report(status: str = "reaction_placement_ready_with_warnings") -> dict:
    return {
        "report_id": "reaction_shot_report_registry",
        "job_id": "job_reaction_shot_registry",
        "status": status,
        "candidates": [
            {
                "candidate_id": "reaction_candidate_registry",
                "source_item_id": "reaction_item_registry",
                "source_segment_id": "reaction_seg_registry",
                "start_seconds": 15.0,
                "end_seconds": 17.0,
                "duration_seconds": 2.0,
                "reaction_type": "hype_reaction",
                "reaction_score": 0.90,
                "expressiveness_score": 0.95,
                "audio_reaction_score": 0.60,
                "face_reaction_score": 0.95,
                "keyword_reaction_score": 0.70,
                "confidence": 0.92,
                "review_required": True,
                "warnings": ["consecutive_reaction_risk"],
                "blocking_reasons": [],
                "metadata": {
                    "review_only": True,
                    "media_unchanged": True,
                },
            },
            {
                "candidate_id": "reaction_candidate_short_registry",
                "source_item_id": "reaction_item_short_registry",
                "source_segment_id": "reaction_seg_short_registry",
                "start_seconds": 18.0,
                "end_seconds": 18.5,
                "duration_seconds": 0.5,
                "reaction_type": "laugh_reaction",
                "reaction_score": 0.80,
                "expressiveness_score": 0.80,
                "audio_reaction_score": 0.50,
                "face_reaction_score": 0.80,
                "keyword_reaction_score": 0.70,
                "confidence": 0.81,
                "review_required": True,
                "warnings": ["too_short_reaction"],
                "blocking_reasons": [],
                "metadata": {
                    "review_only": True,
                    "media_unchanged": True,
                },
            },
        ],
        "placements": [
            {
                "placement_id": "reaction_placement_highlight_registry",
                "trigger_item_id": "highlight_item_registry",
                "trigger_segment_id": "highlight_seg_registry",
                "reaction_candidate_id": "reaction_candidate_registry",
                "placement_type": "after_highlight",
                "suggested_position": "after_trigger",
                "trigger_start_seconds": 10.0,
                "trigger_end_seconds": 14.0,
                "reaction_start_seconds": 15.0,
                "reaction_end_seconds": 17.0,
                "suggested_duration_seconds": 2.0,
                "placement_score": 0.88,
                "review_required": True,
                "can_auto_place": False,
                "can_move_clip": False,
                "can_insert_clip": False,
                "can_trim": False,
                "can_extend": False,
                "can_render": False,
                "warnings": ["consecutive_reaction_risk"],
                "blocking_reasons": [],
                "metadata": {},
            },
            {
                "placement_id": "reaction_placement_hook_registry",
                "trigger_item_id": "hook_item_registry",
                "trigger_segment_id": "hook_seg_registry",
                "reaction_candidate_id": "reaction_candidate_registry",
                "placement_type": "after_hook_candidate",
                "suggested_position": "after_trigger",
                "trigger_start_seconds": 20.0,
                "trigger_end_seconds": 24.0,
                "reaction_start_seconds": 25.0,
                "reaction_end_seconds": 27.0,
                "suggested_duration_seconds": 2.0,
                "placement_score": 0.86,
                "review_required": True,
                "can_auto_place": False,
                "can_move_clip": False,
                "can_insert_clip": False,
                "can_trim": False,
                "can_extend": False,
                "can_render": False,
                "warnings": [],
                "blocking_reasons": [],
                "metadata": {},
            },
            {
                "placement_id": "reaction_placement_climax_registry",
                "trigger_item_id": "climax_item_registry",
                "trigger_segment_id": "climax_seg_registry",
                "reaction_candidate_id": "reaction_candidate_registry",
                "placement_type": "after_climax",
                "suggested_position": "after_trigger",
                "trigger_start_seconds": 30.0,
                "trigger_end_seconds": 34.0,
                "reaction_start_seconds": 35.0,
                "reaction_end_seconds": 37.0,
                "suggested_duration_seconds": 2.0,
                "placement_score": 0.84,
                "review_required": True,
                "can_auto_place": False,
                "can_move_clip": False,
                "can_insert_clip": False,
                "can_trim": False,
                "can_extend": False,
                "can_render": False,
                "warnings": [],
                "blocking_reasons": [],
                "metadata": {},
            },
            {
                "placement_id": "reaction_placement_pattern_registry",
                "trigger_item_id": "pattern_item_registry",
                "trigger_segment_id": "pattern_seg_registry",
                "reaction_candidate_id": "reaction_candidate_registry",
                "placement_type": "after_pattern_interrupt",
                "suggested_position": "after_trigger",
                "trigger_start_seconds": 40.0,
                "trigger_end_seconds": 44.0,
                "reaction_start_seconds": 45.0,
                "reaction_end_seconds": 47.0,
                "suggested_duration_seconds": 2.0,
                "placement_score": 0.82,
                "review_required": True,
                "can_auto_place": False,
                "can_move_clip": False,
                "can_insert_clip": False,
                "can_trim": False,
                "can_extend": False,
                "can_render": False,
                "warnings": [],
                "blocking_reasons": [],
                "metadata": {},
            },
            {
                "placement_id": "reaction_placement_placeholder_registry",
                "trigger_item_id": "missing_item_registry",
                "trigger_segment_id": "missing_seg_registry",
                "reaction_candidate_id": None,
                "placement_type": "manual_placeholder",
                "suggested_position": "manual_review_only",
                "trigger_start_seconds": 50.0,
                "trigger_end_seconds": 54.0,
                "reaction_start_seconds": None,
                "reaction_end_seconds": None,
                "suggested_duration_seconds": 0.0,
                "placement_score": 0.0,
                "review_required": True,
                "can_auto_place": False,
                "can_move_clip": False,
                "can_insert_clip": False,
                "can_trim": False,
                "can_extend": False,
                "can_render": False,
                "warnings": ["missing_reaction_placeholder"],
                "blocking_reasons": [],
                "metadata": {},
            },
            {
                "placement_id": "reaction_placement_censor_registry",
                "trigger_item_id": "censor_item_registry",
                "trigger_segment_id": "censor_seg_registry",
                "reaction_candidate_id": "reaction_candidate_registry",
                "placement_type": "censor_review_required",
                "suggested_position": "keep_original_position",
                "trigger_start_seconds": 60.0,
                "trigger_end_seconds": 64.0,
                "reaction_start_seconds": 65.0,
                "reaction_end_seconds": 67.0,
                "suggested_duration_seconds": 2.0,
                "placement_score": 0.50,
                "review_required": True,
                "can_auto_place": False,
                "can_move_clip": False,
                "can_insert_clip": False,
                "can_trim": False,
                "can_extend": False,
                "can_render": False,
                "warnings": ["reaction_shot_censor_review_required"],
                "blocking_reasons": [],
                "metadata": {},
            },
            {
                "placement_id": "reaction_placement_continuity_registry",
                "trigger_item_id": "continuity_item_registry",
                "trigger_segment_id": "continuity_seg_registry",
                "reaction_candidate_id": None,
                "placement_type": "blocked_by_continuity",
                "suggested_position": "manual_review_only",
                "trigger_start_seconds": 70.0,
                "trigger_end_seconds": 74.0,
                "reaction_start_seconds": None,
                "reaction_end_seconds": None,
                "suggested_duration_seconds": 0.0,
                "placement_score": 0.0,
                "review_required": True,
                "can_auto_place": False,
                "can_move_clip": False,
                "can_insert_clip": False,
                "can_trim": False,
                "can_extend": False,
                "can_render": False,
                "warnings": [],
                "blocking_reasons": ["reaction_shot_continuity_blocked"],
                "metadata": {},
            },
            {
                "placement_id": "reaction_placement_protected_registry",
                "trigger_item_id": "protected_item_registry",
                "trigger_segment_id": "protected_seg_registry",
                "reaction_candidate_id": "reaction_candidate_registry",
                "placement_type": "protected_preserved",
                "suggested_position": "keep_original_position",
                "trigger_start_seconds": 80.0,
                "trigger_end_seconds": 84.0,
                "reaction_start_seconds": 85.0,
                "reaction_end_seconds": 87.0,
                "suggested_duration_seconds": 2.0,
                "placement_score": 0.40,
                "review_required": True,
                "can_auto_place": False,
                "can_move_clip": False,
                "can_insert_clip": False,
                "can_trim": False,
                "can_extend": False,
                "can_render": False,
                "warnings": ["reaction_shot_protected_preserved"],
                "blocking_reasons": [],
                "metadata": {},
            },
        ],
        "total_candidates": 2,
        "total_placements": 8,
        "best_placement_score": 0.88,
        "missing_reaction_placeholder_count": 1,
        "review_required": True,
        "can_apply_reaction_shots": False,
        "can_move_clip": False,
        "can_insert_clip": False,
        "can_trim": False,
        "can_extend": False,
        "can_reorder_timeline": False,
        "can_render": False,
        "warnings": [
            "consecutive_reaction_risk",
            "too_short_reaction",
            "missing_reaction_placeholder",
            "reaction_shot_censor_review_required",
            "reaction_shot_protected_preserved",
        ],
        "blocking_reasons": ["reaction_shot_continuity_blocked"],
        "recommendation": "review_reaction_shot_warnings",
        "metadata": {
            "review_only": True,
            "media_unchanged": True,
            "no_execution_in_2b_41": True,
            "no_render_in_2b_41": True,
            "no_timeline_reorder_in_2b_41": True,
            "no_reaction_apply_in_2b_41": True,
            "no_reaction_insert_in_2b_41": True,
            "no_facecam_move_in_2b_41": True,
            "no_zoom_insert_in_2b_41": True,
        },
    }


def test_signal_adapter_emits_reaction_shot_review_signals() -> None:
    result = adapt_reaction_shot_placement_report_to_signals(_report())
    signal_types = {signal["signal_type"] for signal in result.signals}

    assert "reaction_shot_placement_ready_with_warnings" in signal_types
    assert "reaction_shot_candidate_found" in signal_types
    assert "reaction_shot_after_highlight_candidate" in signal_types
    assert "reaction_shot_after_hook_candidate" in signal_types
    assert "reaction_shot_after_climax_candidate" in signal_types
    assert "reaction_shot_after_pattern_interrupt_candidate" in signal_types
    assert "reaction_shot_missing_placeholder" in signal_types
    assert "reaction_shot_too_short_review" in signal_types
    assert "reaction_shot_consecutive_risk" in signal_types
    assert "reaction_shot_censor_review_required" in signal_types
    assert "reaction_shot_continuity_blocked" in signal_types
    assert "reaction_shot_protected_preserved" in signal_types

    first_signal = result.signals[0]
    assert first_signal["source"] == "reaction_shot_placement"
    assert first_signal["action_hint"] == "review_reaction_shot_placement"
    assert first_signal["metadata"]["review_only"] is True
    assert first_signal["metadata"]["media_unchanged"] is True
    assert first_signal["metadata"]["no_execution_in_2b_41"] is True
    assert first_signal["metadata"]["no_render_in_2b_41"] is True
    assert first_signal["metadata"]["no_timeline_reorder_in_2b_41"] is True
    assert first_signal["metadata"]["no_reaction_apply_in_2b_41"] is True
    assert first_signal["metadata"]["no_reaction_insert_in_2b_41"] is True
    assert first_signal["metadata"]["no_facecam_move_in_2b_41"] is True
    assert first_signal["metadata"]["no_zoom_insert_in_2b_41"] is True
    assert first_signal["metadata"]["can_apply_reaction_shots"] is False
    assert first_signal["metadata"]["can_move_clip"] is False
    assert first_signal["metadata"]["can_insert_clip"] is False
    assert first_signal["metadata"]["can_trim"] is False
    assert first_signal["metadata"]["can_extend"] is False
    assert first_signal["metadata"]["can_reorder_timeline"] is False
    assert first_signal["metadata"]["can_render"] is False


def test_signal_adapter_emits_blocked_and_failed_status_signals() -> None:
    blocked = adapt_reaction_shot_placement_report_to_signals(
        _report(status="blocked")
    )
    failed = adapt_reaction_shot_placement_report_to_signals(
        _report(status="failed")
    )

    assert blocked.blocked_signal_count == 1
    assert blocked.signals[0]["signal_type"] == "reaction_shot_placement_blocked"
    assert failed.failed_signal_count == 1
    assert failed.signals[0]["signal_type"] == "reaction_shot_placement_failed"


def test_registry_imports_and_processes_reaction_shot_placement() -> None:
    text = (ROOT / "core" / "unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )

    assert "from core.reaction_shot_placement_signal_adapter import" in text
    assert "adapt_reaction_shot_placement_report_to_signals" in text
    assert 'SOURCE_REACTION_SHOT_PLACEMENT = "reaction_shot_placement"' in text
    assert "reaction_shot_placement_report" in text
    assert "source_counts[SOURCE_REACTION_SHOT_PLACEMENT]" in text


def test_registry_runtime_counts_reaction_shot_placement_signals() -> None:
    job = Job.from_dict(
        _job_payload(
            reaction_shot_placement_report=_report(),
        )
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["reaction_shot_placement"] >= 12
    assert result.type_counts["reaction_shot_placement_ready_with_warnings"] == 1
    assert result.type_counts["reaction_shot_candidate_found"] == 2
    assert result.type_counts["reaction_shot_after_highlight_candidate"] == 1
    assert result.type_counts["reaction_shot_after_hook_candidate"] == 1
    assert result.type_counts["reaction_shot_after_climax_candidate"] == 1
    assert result.type_counts["reaction_shot_after_pattern_interrupt_candidate"] == 1
    assert result.type_counts["reaction_shot_missing_placeholder"] >= 1
    assert result.type_counts["reaction_shot_too_short_review"] >= 1
    assert result.type_counts["reaction_shot_consecutive_risk"] >= 1
    assert result.type_counts["reaction_shot_censor_review_required"] >= 1
    assert result.type_counts["reaction_shot_continuity_blocked"] >= 1
    assert result.type_counts["reaction_shot_protected_preserved"] >= 1


def test_reaction_shot_registry_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/reaction_shot_placement_signal_adapter.py",
        "core/unified_edit_signal_registry.py",
        "tests/test_reaction_shot_placement_registry_integration_smoke.py",
    ):
        content = (ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
