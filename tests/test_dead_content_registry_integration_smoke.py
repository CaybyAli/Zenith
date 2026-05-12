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
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
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
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _candidate(candidate_type: str, start: float, score: float = 0.7) -> dict:
    return {
        "candidate_id": f"{candidate_type}_{start}",
        "start_seconds": start,
        "end_seconds": start + 1.0,
        "center_seconds": start + 0.5,
        "duration_seconds": 1.0,
        "text": "test",
        "candidate_type": candidate_type,
        "dead_content_score": score,
        "confidence": score,
        "protected_by_context": candidate_type == "protected_context_candidate",
        "protection_reasons": ["context"]
        if candidate_type == "protected_context_candidate"
        else [],
        "evidence": {},
        "recommendation": "review_dead_content_candidate",
        "metadata": {"content_value_score": 0.0},
        "warnings": [],
        "errors": [],
    }


def _dead_content_job() -> SimpleNamespace:
    candidates = [
        _candidate("dead_air_candidate", 1.0, 0.92),
        _candidate("low_value_content_candidate", 3.0, 0.7),
        _candidate("filler_pause_candidate", 5.0, 0.7),
        _candidate("loading_or_menu_candidate", 7.0, 0.7),
        _candidate("private_or_meta_review_candidate", 9.0, 0.88),
        _candidate("protected_context_candidate", 11.0, 0.88),
    ]
    return _base_job(
        dead_content_report={
            "status": "ok",
            "candidates": candidates,
            "candidate_count": len(candidates),
        }
    )


def test_registry_collects_dead_content_source_counts() -> None:
    result = build_unified_edit_signal_result(_dead_content_job())

    assert result.source_counts["dead_content"] >= 6


def test_registry_collects_dead_content_type_counts() -> None:
    result = build_unified_edit_signal_result(_dead_content_job())

    assert result.type_counts["dead_content_dead_air_candidate"] == 1
    assert result.type_counts["dead_content_low_value_candidate"] == 1
    assert result.type_counts["dead_content_filler_pause_candidate"] == 1
    assert result.type_counts["dead_content_loading_or_menu_candidate"] == 1
    assert result.type_counts["dead_content_private_or_meta_review_candidate"] == 1
    assert result.type_counts["dead_content_protected_context_candidate"] == 1
    assert result.type_counts["dead_content_high_score_candidate"] >= 1


def test_registry_dead_content_signals_have_no_forbidden_action_hints() -> None:
    result = build_unified_edit_signal_result(_dead_content_job())
    dead_content_hints = {
        signal["action_hint"]
        for signal in result.signals
        if signal.get("source") == "dead_content"
    }

    assert dead_content_hints
    assert not dead_content_hints.intersection(FORBIDDEN_ACTION_HINTS)


def test_registry_empty_dead_content_report_is_safe() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert "dead_content" not in result.source_counts
    assert result.status == "skipped_no_signals"


def test_registry_dead_content_fallback_candidates_and_scores() -> None:
    job = _base_job(
        dead_content_candidates=[_candidate("low_value_content_candidate", 1.0)],
        dead_content_segment_scores=[
            {
                "segment_id": "score_1",
                "start_seconds": 3.0,
                "end_seconds": 4.0,
                "text": "",
                "dead_content_score": 0.9,
                "candidate_type": "dead_air_candidate",
                "review_required": True,
                "evidence": {},
                "metadata": {},
            }
        ],
    )

    result = build_unified_edit_signal_result(job)

    assert result.source_counts["dead_content"] >= 1
    assert result.type_counts["dead_content_low_value_candidate"] == 1


def test_registry_keeps_existing_source_integrations() -> None:
    source = (PROJECT_ROOT / "core/unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )
    expected_sources = {
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


def test_dead_content_registry_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/unified_edit_signal_registry.py",
        "tests/test_dead_content_registry_integration_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
