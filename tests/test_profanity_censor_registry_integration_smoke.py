from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_ACTION_HINTS = {
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
}


def _base_job(**overrides) -> SimpleNamespace:
    data = {
        "energy_peak_report": {},
        "filler_word_report": {},
        "audio_normalization_report": {},
        "beat_detection_report": {},
        "silence_detection_report": {},
        "silence_classifications": [],
        "sentence_boundary_report": {},
        "keyword_emotion_report": {},
        "interaction_classification_report": {},
        "scene_change_report": {},
        "motion_analysis_report": {},
        "face_reaction_report": {},
        "stutter_detection_report": {},
        "screen_content_report": {},
        "visual_energy_report": {},
        "dead_content_report": {},
        "dead_content_candidates": [],
        "dead_content_segment_scores": [],
        "content_value_report": {},
        "content_value_segment_scores": [],
        "profanity_censor_report": {},
        "profanity_censor_matches": [],
        "profanity_censor_segment_results": [],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _match(match_id: str, timing_source: str, start: float) -> dict:
    return {
        "match_id": match_id,
        "start_seconds": start,
        "end_seconds": start + 0.2,
        "center_seconds": start + 0.1,
        "duration_seconds": 0.2,
        "text": "SEVERE_TOKEN",
        "matched_text": "SEVERE_TOKEN",
        "normalized_match": "severe_token",
        "severity": "severe",
        "category": "severe_profanity",
        "censor_required": True,
        "censor_action": "censor_sfx_overlay_candidate",
        "replacement_sfx": "quack",
        "timing_source": timing_source,
        "confidence": 0.9,
    }


def _profanity_job() -> SimpleNamespace:
    return _base_job(
        profanity_censor_report={
            "status": "ok",
            "matches": [
                _match("m_word", "word_timestamp", 1.0),
                _match("m_segment", "segment_fallback", 3.0),
            ],
        }
    )


def test_registry_collects_profanity_censor_source_counts() -> None:
    result = build_unified_edit_signal_result(_profanity_job())

    assert result.source_counts["profanity_censor"] == 4


def test_registry_collects_profanity_censor_required_type_count() -> None:
    result = build_unified_edit_signal_result(_profanity_job())

    assert result.type_counts["profanity_censor_sfx_required"] == 2


def test_registry_collects_word_timed_type_count() -> None:
    result = build_unified_edit_signal_result(_profanity_job())

    assert result.type_counts["profanity_censor_word_timed_overlay"] == 1


def test_registry_collects_segment_fallback_type_count() -> None:
    result = build_unified_edit_signal_result(_profanity_job())

    assert result.type_counts["profanity_censor_segment_fallback_overlay"] == 1


def test_mild_terms_create_no_censor_required_registry_signals() -> None:
    mild = _match("m_mild", "segment_fallback", 1.0)
    mild.update(
        {
            "severity": "mild",
            "censor_required": False,
            "censor_action": "none",
            "replacement_sfx": None,
        }
    )
    result = build_unified_edit_signal_result(
        _base_job(profanity_censor_report={"matches": [mild]})
    )

    assert "profanity_censor" not in result.source_counts
    assert "profanity_censor_sfx_required" not in result.type_counts


def test_registry_profanity_signals_have_no_forbidden_action_hints() -> None:
    result = build_unified_edit_signal_result(_profanity_job())
    hints = {
        signal["action_hint"]
        for signal in result.signals
        if signal.get("source") == "profanity_censor"
    }

    assert hints
    assert not hints.intersection(FORBIDDEN_ACTION_HINTS)


def test_empty_profanity_report_is_safe() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert "profanity_censor" not in result.source_counts


def test_registry_keeps_existing_source_integrations() -> None:
    source = (PROJECT_ROOT / "core/unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )
    expected_sources = {
        "content_value",
        "dead_content",
        "filler_word",
        "sentence_boundary",
        "keyword_emotion",
        "interaction_classification",
        "scene_change",
        "motion_analysis",
        "face_reaction",
        "stutter_detection",
        "screen_content",
        "visual_energy",
    }

    for expected_source in expected_sources:
        assert expected_source in source


def test_profanity_censor_registry_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/unified_edit_signal_registry.py",
        "tests/test_profanity_censor_registry_integration_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
