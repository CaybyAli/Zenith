from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result


REPO_ROOT = Path(__file__).resolve().parents[1]


VIDEO_INTELLIGENCE_SOURCES = [
    "scene_change",
    "motion_analysis",
    "face_reaction",
    "stutter_detection",
    "screen_content",
    "visual_energy",
]


EXPECTED_SIGNAL_TYPES = [
    "scene_hard_cut_point",
    "motion_high_activity_segment",
    "motion_dead_visual_candidate",
    "face_high_reaction_segment",
    "face_shock_reaction_candidate",
    "stutter_segment_candidate",
    "freeze_segment_candidate",
    "screen_gameplay_segment",
    "screen_loading_segment",
    "visual_peak_energy_segment",
    "visual_technical_warning_segment",
]


REQUIRED_SIGNAL_FIELDS = [
    "signal_id",
    "signal_type",
    "source",
    "start_seconds",
    "end_seconds",
    "center_seconds",
    "signal_score",
    "priority",
    "action_hint",
    "metadata",
]


FORBIDDEN_ACTION_HINTS = {
    "remove_now",
    "hard_remove",
    "auto_remove",
    "delete_segment",
    "force_cut",
    "auto_highlight",
}


def _synthetic_job() -> SimpleNamespace:
    return SimpleNamespace(
        energy_peak_report={},
        filler_word_report={},
        audio_normalization_report={},
        beat_detection_report={},
        silence_detection_report={},
        silence_classifications=[],
        scene_change_report={
            "scene_changes": [
                {
                    "time_seconds": 10.0,
                    "frame_index": 300,
                    "change_type": "hard_scene_change",
                    "scene_score": 0.91,
                    "confidence": 0.93,
                    "warnings": [],
                    "errors": [],
                },
            ],
        },
        motion_analysis_report={
            "motion_segments": [
                {
                    "start_seconds": 20.0,
                    "end_seconds": 24.0,
                    "duration_seconds": 4.0,
                    "classification": "high_motion",
                    "avg_motion_score": 0.72,
                    "max_motion_score": 0.94,
                    "confidence": 0.91,
                    "recommendation": "review",
                    "warnings": [],
                    "errors": [],
                },
                {
                    "start_seconds": 30.0,
                    "end_seconds": 36.0,
                    "duration_seconds": 6.0,
                    "classification": "dead_visual_candidate",
                    "avg_motion_score": 0.06,
                    "max_motion_score": 0.10,
                    "confidence": 0.88,
                    "recommendation": "review",
                    "warnings": [],
                    "errors": [],
                },
            ],
        },
        face_reaction_report={
            "face_reaction_segments": [
                {
                    "start_seconds": 40.0,
                    "end_seconds": 43.0,
                    "duration_seconds": 3.0,
                    "reaction_type": "hype_candidate",
                    "avg_reaction_score": 0.78,
                    "max_reaction_score": 0.95,
                    "avg_face_area_ratio": 0.16,
                    "confidence": 0.92,
                    "recommendation": "review",
                    "warnings": [],
                    "errors": [],
                },
                {
                    "start_seconds": 50.0,
                    "end_seconds": 53.0,
                    "duration_seconds": 3.0,
                    "reaction_type": "shock_candidate",
                    "avg_reaction_score": 0.80,
                    "max_reaction_score": 0.97,
                    "avg_face_area_ratio": 0.18,
                    "confidence": 0.94,
                    "recommendation": "review",
                    "warnings": [],
                    "errors": [],
                },
            ],
        },
        stutter_detection_report={
            "stutter_detection_segments": [
                {
                    "start_seconds": 60.0,
                    "end_seconds": 62.0,
                    "duration_seconds": 2.0,
                    "classification": "stutter_segment",
                    "duplicate_frame_count": 12,
                    "avg_duplicate_score": 0.74,
                    "max_duplicate_score": 0.91,
                    "confidence": 0.89,
                    "recommendation": "review",
                    "warnings": [],
                    "errors": [],
                },
                {
                    "start_seconds": 70.0,
                    "end_seconds": 74.0,
                    "duration_seconds": 4.0,
                    "classification": "freeze_segment",
                    "duplicate_frame_count": 38,
                    "avg_duplicate_score": 0.86,
                    "max_duplicate_score": 0.98,
                    "confidence": 0.96,
                    "recommendation": "review",
                    "warnings": [],
                    "errors": [],
                },
            ],
        },
        screen_content_report={
            "screen_content_segments": [
                {
                    "start_seconds": 80.0,
                    "end_seconds": 90.0,
                    "duration_seconds": 10.0,
                    "screen_type": "gameplay",
                    "avg_confidence": 0.88,
                    "max_confidence": 0.96,
                    "point_count": 20,
                    "confidence": 0.94,
                    "recommendation": "review",
                    "warnings": [],
                    "errors": [],
                },
                {
                    "start_seconds": 95.0,
                    "end_seconds": 100.0,
                    "duration_seconds": 5.0,
                    "screen_type": "loading",
                    "avg_confidence": 0.84,
                    "max_confidence": 0.93,
                    "point_count": 10,
                    "confidence": 0.91,
                    "recommendation": "review",
                    "warnings": [],
                    "errors": [],
                },
            ],
        },
        visual_energy_report={
            "visual_energy_segments": [
                {
                    "start_seconds": 110.0,
                    "end_seconds": 113.0,
                    "duration_seconds": 3.0,
                    "classification": "peak_visual_energy",
                    "avg_visual_energy_score": 0.88,
                    "max_visual_energy_score": 0.98,
                    "min_visual_energy_score": 0.70,
                    "recommendation": "review",
                    "warnings": [],
                    "errors": [],
                },
                {
                    "start_seconds": 120.0,
                    "end_seconds": 123.0,
                    "duration_seconds": 3.0,
                    "classification": "technical_warning",
                    "avg_visual_energy_score": 0.45,
                    "max_visual_energy_score": 0.76,
                    "min_visual_energy_score": 0.20,
                    "recommendation": "review",
                    "warnings": [],
                    "errors": [],
                },
            ],
        },
    )


def test_block3_unified_registry_collects_all_video_intelligence_sources() -> None:
    result = build_unified_edit_signal_result(_synthetic_job())

    assert result.status == "ok"

    for source in VIDEO_INTELLIGENCE_SOURCES:
        assert source in result.source_counts
        assert result.source_counts[source] >= 1


def test_block3_unified_registry_contains_expected_video_signal_types() -> None:
    result = build_unified_edit_signal_result(_synthetic_job())

    for signal_type in EXPECTED_SIGNAL_TYPES:
        assert signal_type in result.type_counts
        assert result.type_counts[signal_type] >= 1

    assert result.signal_count >= 10


def test_all_block3_video_intelligence_signals_have_required_fields() -> None:
    result = build_unified_edit_signal_result(_synthetic_job())

    video_signals = [
        signal
        for signal in result.signals
        if signal.get("source") in VIDEO_INTELLIGENCE_SOURCES
    ]

    assert video_signals

    for signal in video_signals:
        for field_name in REQUIRED_SIGNAL_FIELDS:
            assert field_name in signal, f"{field_name} missing in {signal}"

        assert signal["signal_id"]
        assert signal["signal_type"]
        assert signal["source"]
        assert signal["start_seconds"] is not None
        assert signal["end_seconds"] is not None
        assert signal["center_seconds"] is not None
        assert isinstance(signal["metadata"], dict)


def test_block3_video_intelligence_signals_have_no_forbidden_action_hints() -> None:
    result = build_unified_edit_signal_result(_synthetic_job())

    for signal in result.signals:
        if signal.get("source") in VIDEO_INTELLIGENCE_SOURCES:
            assert signal.get("action_hint") not in FORBIDDEN_ACTION_HINTS


def test_unified_signal_audit_file_has_no_bom_and_ends_with_newline() -> None:
    content = (
        REPO_ROOT
        / "tests"
        / "test_block3_video_intelligence_unified_signal_audit_smoke.py"
    ).read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.endswith(b"\n")
