from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result


REPO_ROOT = Path(__file__).resolve().parents[1]


def _visual_segment(
    classification: str,
    start_seconds: float,
    end_seconds: float,
    avg_score: float,
    max_score: float,
    min_score: float = 0.1,
) -> dict:
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": end_seconds - start_seconds,
        "avg_visual_energy_score": avg_score,
        "max_visual_energy_score": max_score,
        "min_visual_energy_score": min_score,
        "classification": classification,
        "recommendation": "review",
        "warnings": [],
        "errors": [],
    }


def _empty_job() -> SimpleNamespace:
    return SimpleNamespace(
        energy_peak_report={},
        filler_word_report={},
        audio_normalization_report={},
        beat_detection_report={},
        scene_change_report={},
        scene_changes=[],
        motion_analysis_report={},
        motion_analysis_segments=[],
        motion_analysis_result={},
        face_reaction_report={},
        face_reaction_segments=[],
        face_reaction_result={},
        stutter_detection_report={},
        stutter_detection_segments=[],
        stutter_detection_result={},
        screen_content_report={},
        screen_content_segments=[],
        screen_content_result={},
        visual_energy_report={},
        visual_energy_segments=[],
        visual_energy_result={},
    )


def _job_with_visual_segments(segments: list[dict]) -> SimpleNamespace:
    job = _empty_job()
    job.visual_energy_report = {
        "visual_energy_segments": segments,
    }
    return job


def test_registry_collects_visual_energy_source_counts_and_types() -> None:
    result = build_unified_edit_signal_result(
        _job_with_visual_segments(
            [
                _visual_segment("peak_visual_energy", 1.0, 2.0, 0.90, 0.96),
                _visual_segment("high_visual_energy", 3.0, 4.0, 0.72, 0.80),
                _visual_segment("low_visual_energy", 5.0, 6.0, 0.12, 0.20),
                _visual_segment("technical_warning", 7.0, 8.0, 0.40, 0.60),
            ]
        )
    )

    assert result.status == "ok"
    assert result.source_counts["visual_energy"] == 4
    assert result.type_counts["visual_peak_energy_segment"] == 1
    assert result.type_counts["visual_high_energy_segment"] == 1
    assert result.type_counts["visual_low_energy_segment"] == 1
    assert result.type_counts["visual_technical_warning_segment"] == 1


def test_registry_visual_energy_signals_do_not_auto_remove_or_auto_highlight() -> None:
    result = build_unified_edit_signal_result(
        _job_with_visual_segments(
            [
                _visual_segment("low_visual_energy", 1.0, 2.0, 0.12, 0.20),
                _visual_segment("peak_visual_energy", 3.0, 4.0, 0.91, 0.98),
            ]
        )
    )

    forbidden = {
        "remove_now",
        "hard_remove",
        "auto_remove",
        "auto_highlight",
        "force_cut",
    }

    for signal in result.signals:
        if signal.get("source") == "visual_energy":
            assert signal["action_hint"] not in forbidden
            assert signal["metadata"]["no_cut_decision"] is True
            assert signal["metadata"]["no_auto_remove"] is True
            assert signal["metadata"]["no_auto_highlight"] is True


def test_empty_visual_energy_report_does_not_crash() -> None:
    result = build_unified_edit_signal_result(_job_with_visual_segments([]))

    assert result.status == "skipped_no_signals"
    assert "visual_energy" not in result.source_counts
    assert result.signal_count == 0
    assert result.warnings


def test_registry_collects_visual_energy_segments_fallback_from_job_field() -> None:
    job = _empty_job()
    job.visual_energy_report = {}
    job.visual_energy_segments = [
        _visual_segment("high_visual_energy", 11.0, 13.0, 0.75, 0.84)
    ]

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["visual_energy"] == 1
    assert result.type_counts["visual_high_energy_segment"] == 1


def test_registry_collects_visual_energy_segments_fallback_from_result_field() -> None:
    job = _empty_job()
    job.visual_energy_report = {}
    job.visual_energy_segments = []
    job.visual_energy_result = {
        "segments": [
            _visual_segment("technical_warning", 15.0, 16.0, 0.40, 0.60)
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["visual_energy"] == 1
    assert result.type_counts["visual_technical_warning_segment"] == 1


def test_registry_stays_compatible_with_screen_content_source() -> None:
    job = _job_with_visual_segments(
        [_visual_segment("peak_visual_energy", 20.0, 21.0, 0.90, 0.96)]
    )
    job.screen_content_report = {
        "screen_content_segments": [
            {
                "start_seconds": 1.0,
                "end_seconds": 2.0,
                "duration_seconds": 1.0,
                "screen_type": "gameplay",
                "avg_confidence": 0.80,
                "max_confidence": 0.90,
                "point_count": 3,
                "recommendation": "review",
                "warnings": [],
                "errors": [],
            }
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["visual_energy"] == 1
    assert result.source_counts["screen_content"] == 1
    assert result.type_counts["visual_peak_energy_segment"] == 1
    assert result.type_counts["screen_gameplay_segment"] == 1


def test_visual_energy_registry_test_files_do_not_have_bom() -> None:
    files = [
        REPO_ROOT / "core" / "unified_edit_signal_registry.py",
        REPO_ROOT / "tests" / "test_visual_energy_registry_integration_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_visual_energy_registry_test_files_end_with_newline() -> None:
    files = [
        REPO_ROOT / "core" / "unified_edit_signal_registry.py",
        REPO_ROOT / "tests" / "test_visual_energy_registry_integration_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
