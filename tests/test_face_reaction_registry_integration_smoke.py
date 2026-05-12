from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result


REPO_ROOT = Path(__file__).resolve().parents[1]


def _face_segment(
    reaction_type: str,
    start_seconds: float,
    end_seconds: float,
    avg_reaction_score: float,
    max_reaction_score: float,
    recommendation: str = "review",
) -> dict:
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": end_seconds - start_seconds,
        "avg_reaction_score": avg_reaction_score,
        "max_reaction_score": max_reaction_score,
        "avg_face_area_ratio": 0.08,
        "reaction_type": reaction_type,
        "recommendation": recommendation,
        "warnings": [],
        "errors": [],
    }


def _motion_segment(
    classification: str,
    start_seconds: float,
    end_seconds: float,
    avg_motion_score: float,
    max_motion_score: float,
) -> dict:
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": end_seconds - start_seconds,
        "avg_motion_score": avg_motion_score,
        "max_motion_score": max_motion_score,
        "classification": classification,
        "recommendation": "review",
        "warnings": [],
        "errors": [],
    }


def _job_with_face_segments(segments: list[dict]):
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
        face_reaction_report={
            "face_reaction_segments": segments,
        },
        face_reaction_segments=[],
        face_reaction_result={},
    )


def _signal_by_type(result, signal_type: str) -> dict:
    for signal in result.signals:
        if signal.get("signal_type") == signal_type:
            return signal

    raise AssertionError(f"Signal type not found: {signal_type}")


def test_registry_collects_face_reaction_source_counts_and_types():
    result = build_unified_edit_signal_result(
        _job_with_face_segments(
            [
                _face_segment("hype_candidate", 1.0, 2.0, 0.70, 0.90),
                _face_segment("shock_candidate", 3.0, 4.0, 0.75, 0.95),
                _face_segment("laugh_candidate", 5.0, 6.0, 0.72, 0.91),
                _face_segment("mouth_open_candidate", 7.0, 8.0, 0.50, 0.66),
                _face_segment("neutral_face", 9.0, 10.0, 0.20, 0.30),
            ]
        )
    )

    assert result.status == "ok"
    assert result.source_counts["face_reaction"] == 5
    assert result.type_counts["face_high_reaction_segment"] == 1
    assert result.type_counts["face_shock_reaction_candidate"] == 1
    assert result.type_counts["face_laugh_reaction_candidate"] == 1
    assert result.type_counts["face_mouth_open_candidate"] == 1
    assert result.type_counts["face_neutral_presence_segment"] == 1


def test_registry_face_reaction_signals_do_not_auto_execute_zoom_or_render():
    result = build_unified_edit_signal_result(
        _job_with_face_segments(
            [_face_segment("shock_candidate", 3.0, 4.0, 0.75, 0.95)]
        )
    )

    signal = _signal_by_type(result, "face_shock_reaction_candidate")
    action_hint = signal["action_hint"]

    assert action_hint == "review_reaction_zoom_candidate"
    assert "execute_zoom" not in action_hint
    assert "auto_zoom" not in action_hint
    assert "render" not in action_hint


def test_empty_face_reaction_report_does_not_crash():
    result = build_unified_edit_signal_result(_job_with_face_segments([]))

    assert result.status == "skipped_no_signals"
    assert "face_reaction" not in result.source_counts
    assert result.signal_count == 0
    assert result.warnings


def test_registry_collects_face_segments_fallback_from_job_field():
    job = _job_with_face_segments([])
    job.face_reaction_report = {}
    job.face_reaction_segments = [
        _face_segment("hype_candidate", 11.0, 12.0, 0.70, 0.90)
    ]

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["face_reaction"] == 1
    assert result.type_counts["face_high_reaction_segment"] == 1


def test_registry_collects_face_segments_fallback_from_result_field():
    job = _job_with_face_segments([])
    job.face_reaction_report = {}
    job.face_reaction_segments = []
    job.face_reaction_result = {
        "segments": [
            _face_segment("laugh_candidate", 13.0, 14.0, 0.72, 0.91)
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["face_reaction"] == 1
    assert result.type_counts["face_laugh_reaction_candidate"] == 1


def test_registry_stays_compatible_with_scene_change_source():
    job = _job_with_face_segments(
        [_face_segment("hype_candidate", 20.0, 21.0, 0.70, 0.90)]
    )
    job.scene_change_report = {
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
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["scene_change"] == 1
    assert result.source_counts["face_reaction"] == 1
    assert result.type_counts["scene_hard_cut_point"] == 1
    assert result.type_counts["face_high_reaction_segment"] == 1


def test_registry_stays_compatible_with_motion_analysis_source():
    job = _job_with_face_segments(
        [_face_segment("shock_candidate", 20.0, 21.0, 0.75, 0.95)]
    )
    job.motion_analysis_report = {
        "motion_segments": [
            _motion_segment("high_motion", 30.0, 31.0, 0.45, 0.85)
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["motion_analysis"] == 1
    assert result.source_counts["face_reaction"] == 1
    assert result.type_counts["motion_high_activity_segment"] == 1
    assert result.type_counts["face_shock_reaction_candidate"] == 1


def test_face_reaction_registry_test_files_do_not_have_bom():
    files = [
        REPO_ROOT / "core" / "unified_edit_signal_registry.py",
        REPO_ROOT / "tests" / "test_face_reaction_registry_integration_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_face_reaction_registry_test_files_end_with_newline():
    files = [
        REPO_ROOT / "core" / "unified_edit_signal_registry.py",
        REPO_ROOT / "tests" / "test_face_reaction_registry_integration_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
