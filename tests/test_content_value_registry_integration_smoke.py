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
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _score(value_tier: str, start: float, score: float = 0.7, **overrides) -> dict:
    data = {
        "segment_id": f"{value_tier}_{start}",
        "start_seconds": start,
        "end_seconds": start + 1.0,
        "center_seconds": start + 0.5,
        "duration_seconds": 1.0,
        "text": "test",
        "content_value_score": score,
        "final_score": score,
        "protection_score": 0.0,
        "dead_content_penalty_score": 0.0,
        "technical_penalty_score": 0.0,
        "value_tier": value_tier,
        "review_label": f"review_{value_tier}",
        "is_hook_candidate": False,
        "is_protected_context": value_tier == "protected",
        "evidence": {},
        "recommendation": f"review_{value_tier}",
        "warnings": [],
        "errors": [],
    }
    data.update(overrides)
    return data


def _content_value_job() -> SimpleNamespace:
    scores = [
        _score("high", 1.0, 0.85),
        _score("medium", 3.0, 0.55),
        _score("low", 5.0, 0.25),
        _score("protected", 7.0, 0.35, protection_score=0.9),
        _score("high", 9.0, 0.88, is_hook_candidate=True),
        _score("technical_warning", 11.0, 0.3, technical_penalty_score=0.9),
    ]
    return _base_job(
        content_value_report={
            "status": "ok",
            "segment_scores": scores,
            "segment_score_count": len(scores),
        }
    )


def test_registry_collects_content_value_source_counts() -> None:
    result = build_unified_edit_signal_result(_content_value_job())

    assert result.source_counts["content_value"] >= 6


def test_registry_collects_content_value_type_counts() -> None:
    result = build_unified_edit_signal_result(_content_value_job())

    assert result.type_counts["content_value_high_segment"] == 2
    assert result.type_counts["content_value_mid_segment"] == 1
    assert result.type_counts["content_value_low_segment"] == 1
    assert result.type_counts["content_value_protected_context"] == 1
    assert result.type_counts["content_value_hook_candidate"] == 1
    assert result.type_counts["content_value_technical_warning"] == 1


def test_registry_content_value_signals_have_no_forbidden_action_hints() -> None:
    result = build_unified_edit_signal_result(_content_value_job())
    content_value_hints = {
        signal["action_hint"]
        for signal in result.signals
        if signal.get("source") == "content_value"
    }

    assert content_value_hints
    assert not content_value_hints.intersection(FORBIDDEN_ACTION_HINTS)


def test_registry_empty_content_value_report_is_safe() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert "content_value" not in result.source_counts
    assert result.status == "skipped_no_signals"


def test_registry_content_value_fallback_segment_scores() -> None:
    job = _base_job(
        content_value_segment_scores=[
            _score("high", 1.0, 0.85),
        ],
    )

    result = build_unified_edit_signal_result(job)

    assert result.source_counts["content_value"] == 1
    assert result.type_counts["content_value_high_segment"] == 1


def test_registry_keeps_existing_source_integrations() -> None:
    source = (PROJECT_ROOT / "core/unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )
    expected_sources = {
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


def test_content_value_registry_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/unified_edit_signal_registry.py",
        "tests/test_content_value_registry_integration_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
