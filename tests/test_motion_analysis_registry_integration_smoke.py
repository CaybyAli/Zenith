from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result


REPO_ROOT = Path(__file__).resolve().parents[1]


def _motion_segment(
    classification: str,
    start_seconds: float,
    end_seconds: float,
    avg_motion_score: float,
    max_motion_score: float,
    recommendation: str = "review",
) -> dict:
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": end_seconds - start_seconds,
        "avg_motion_score": avg_motion_score,
        "max_motion_score": max_motion_score,
        "classification": classification,
        "recommendation": recommendation,
        "warnings": [],
        "errors": [],
    }


def _result_for_motion_segments(segments: list[dict]):
    job = SimpleNamespace(
        energy_peak_report={},
        filler_word_report={},
        audio_normalization_report={},
        beat_detection_report={},
        scene_change_report={},
        scene_changes=[],
        motion_analysis_report={
            "motion_segments": segments,
        },
        motion_analysis_segments=[],
        motion_analysis_result={},
    )

    return build_unified_edit_signal_result(job)


def _signal_by_type(result, signal_type: str) -> dict:
    for signal in result.signals:
        if signal.get("signal_type") == signal_type:
            return signal

    raise AssertionError(f"Signal type not found: {signal_type}")


def test_registry_collects_motion_high_activity_segment_from_report():
    result = _result_for_motion_segments(
        [
            _motion_segment(
                classification="high_motion",
                start_seconds=1.0,
                end_seconds=3.0,
                avg_motion_score=0.45,
                max_motion_score=0.85,
            )
        ]
    )

    assert result.status == "ok"
    assert result.source_counts["motion_analysis"] == 1
    assert result.type_counts["motion_high_activity_segment"] == 1


def test_registry_collects_motion_dead_visual_candidate():
    result = _result_for_motion_segments(
        [
            _motion_segment(
                classification="dead_visual_candidate",
                start_seconds=10.0,
                end_seconds=14.0,
                avg_motion_score=0.01,
                max_motion_score=0.02,
                recommendation="review_or_trim_dead_visual",
            )
        ]
    )

    assert result.status == "ok"
    assert result.source_counts["motion_analysis"] == 1
    assert result.type_counts["motion_dead_visual_candidate"] == 1


def test_registry_collects_motion_low_static_and_medium_types():
    result = _result_for_motion_segments(
        [
            _motion_segment(
                classification="low_motion",
                start_seconds=1.0,
                end_seconds=3.0,
                avg_motion_score=0.04,
                max_motion_score=0.06,
            ),
            _motion_segment(
                classification="static",
                start_seconds=5.0,
                end_seconds=7.0,
                avg_motion_score=0.0,
                max_motion_score=0.0,
            ),
            _motion_segment(
                classification="medium_motion",
                start_seconds=9.0,
                end_seconds=11.0,
                avg_motion_score=0.20,
                max_motion_score=0.30,
            ),
        ]
    )

    assert result.status == "ok"
    assert result.source_counts["motion_analysis"] == 3
    assert result.type_counts["motion_low_activity_segment"] == 1
    assert result.type_counts["motion_static_segment"] == 1
    assert result.type_counts["motion_medium_activity_segment"] == 1


def test_dead_visual_signal_stays_review_trim_hint_not_auto_remove():
    result = _result_for_motion_segments(
        [
            _motion_segment(
                classification="dead_visual_candidate",
                start_seconds=20.0,
                end_seconds=25.0,
                avg_motion_score=0.01,
                max_motion_score=0.02,
                recommendation="review_or_trim_dead_visual",
            )
        ]
    )

    signal = _signal_by_type(result, "motion_dead_visual_candidate")
    action_hint = signal["action_hint"]

    assert action_hint == "review_or_trim_dead_visual"
    assert action_hint != "remove_now"
    assert action_hint != "hard_remove"
    assert action_hint != "auto_remove"


def test_empty_motion_report_does_not_crash():
    result = _result_for_motion_segments([])

    assert result.status == "skipped_no_signals"
    assert "motion_analysis" not in result.source_counts
    assert result.signal_count == 0
    assert result.warnings


def test_registry_stays_compatible_with_scene_change_source():
    job = SimpleNamespace(
        energy_peak_report={},
        filler_word_report={},
        audio_normalization_report={},
        beat_detection_report={},
        scene_change_report={
            "scene_changes": [
                {
                    "time_seconds": 2.0,
                    "frame_index": 12,
                    "scene_score": 0.9,
                    "confidence": 0.9,
                    "change_type": "hard_scene_change",
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
        scene_changes=[],
        motion_analysis_report={},
        motion_analysis_segments=[],
        motion_analysis_result={},
    )

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["scene_change"] == 1
    assert result.type_counts["scene_hard_cut_point"] == 1


def test_registry_can_collect_motion_segments_fallback_from_job_field():
    job = SimpleNamespace(
        energy_peak_report={},
        filler_word_report={},
        audio_normalization_report={},
        beat_detection_report={},
        scene_change_report={},
        scene_changes=[],
        motion_analysis_report={},
        motion_analysis_segments=[
            _motion_segment(
                classification="high_motion",
                start_seconds=30.0,
                end_seconds=33.0,
                avg_motion_score=0.40,
                max_motion_score=0.80,
            )
        ],
        motion_analysis_result={},
    )

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["motion_analysis"] == 1
    assert result.type_counts["motion_high_activity_segment"] == 1


def test_motion_registry_test_files_do_not_have_bom():
    files = [
        REPO_ROOT / "core" / "unified_edit_signal_registry.py",
        REPO_ROOT / "tests" / "test_motion_analysis_registry_integration_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_motion_registry_test_files_end_with_newline():
    files = [
        REPO_ROOT / "core" / "unified_edit_signal_registry.py",
        REPO_ROOT / "tests" / "test_motion_analysis_registry_integration_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
