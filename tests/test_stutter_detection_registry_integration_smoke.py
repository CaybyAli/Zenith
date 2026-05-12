from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result


REPO_ROOT = Path(__file__).resolve().parents[1]


def _stutter_segment(
    classification: str,
    start_seconds: float,
    end_seconds: float,
    duplicate_frame_count: int,
    avg_duplicate_score: float,
    max_duplicate_score: float,
    recommendation: str = "review",
) -> dict:
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": end_seconds - start_seconds,
        "start_frame_index": int(start_seconds * 10),
        "end_frame_index": int(end_seconds * 10),
        "duplicate_frame_count": duplicate_frame_count,
        "avg_duplicate_score": avg_duplicate_score,
        "max_duplicate_score": max_duplicate_score,
        "classification": classification,
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


def _face_segment(
    reaction_type: str,
    start_seconds: float,
    end_seconds: float,
    avg_reaction_score: float,
    max_reaction_score: float,
) -> dict:
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": end_seconds - start_seconds,
        "avg_reaction_score": avg_reaction_score,
        "max_reaction_score": max_reaction_score,
        "avg_face_area_ratio": 0.08,
        "reaction_type": reaction_type,
        "recommendation": "review",
        "warnings": [],
        "errors": [],
    }


def _job_with_stutter_segments(segments: list[dict]):
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
        stutter_detection_report={
            "stutter_segments": segments,
        },
        stutter_detection_segments=[],
        stutter_detection_result={},
    )


def _signal_by_type(result, signal_type: str) -> dict:
    for signal in result.signals:
        if signal.get("signal_type") == signal_type:
            return signal

    raise AssertionError(f"Signal type not found: {signal_type}")


def test_registry_collects_stutter_detection_source_counts_and_types():
    result = build_unified_edit_signal_result(
        _job_with_stutter_segments(
            [
                _stutter_segment("stutter_segment", 1.0, 2.0, 4, 0.990, 0.999),
                _stutter_segment("freeze_segment", 3.0, 5.0, 20, 0.995, 1.0),
                _stutter_segment("encoding_drop_candidate", 7.0, 7.3, 2, 0.988, 0.992),
            ]
        )
    )

    assert result.status == "ok"
    assert result.source_counts["stutter_detection"] == 3
    assert result.type_counts["stutter_segment_candidate"] == 1
    assert result.type_counts["freeze_segment_candidate"] == 1
    assert result.type_counts["encoding_drop_candidate"] == 1


def test_registry_stutter_signals_do_not_auto_remove():
    result = build_unified_edit_signal_result(
        _job_with_stutter_segments(
            [_stutter_segment("stutter_segment", 1.0, 2.0, 4, 0.990, 0.999)]
        )
    )

    signal = _signal_by_type(result, "stutter_segment_candidate")
    action_hint = signal["action_hint"]

    assert action_hint == "review_stutter_segment"
    for forbidden in {"remove_now", "hard_remove", "auto_remove", "delete_segment"}:
        assert forbidden not in action_hint


def test_empty_stutter_detection_report_does_not_crash():
    result = build_unified_edit_signal_result(_job_with_stutter_segments([]))

    assert result.status == "skipped_no_signals"
    assert "stutter_detection" not in result.source_counts
    assert result.signal_count == 0
    assert result.warnings


def test_registry_collects_stutter_segments_fallback_from_job_field():
    job = _job_with_stutter_segments([])
    job.stutter_detection_report = {}
    job.stutter_detection_segments = [
        _stutter_segment("freeze_segment", 11.0, 13.0, 20, 0.995, 1.0)
    ]

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["stutter_detection"] == 1
    assert result.type_counts["freeze_segment_candidate"] == 1


def test_registry_collects_stutter_segments_fallback_from_result_field():
    job = _job_with_stutter_segments([])
    job.stutter_detection_report = {}
    job.stutter_detection_segments = []
    job.stutter_detection_result = {
        "segments": [
            _stutter_segment("encoding_drop_candidate", 15.0, 15.3, 2, 0.988, 0.992)
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["stutter_detection"] == 1
    assert result.type_counts["encoding_drop_candidate"] == 1


def test_registry_stays_compatible_with_scene_change_source():
    job = _job_with_stutter_segments(
        [_stutter_segment("stutter_segment", 20.0, 21.0, 4, 0.990, 0.999)]
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
    assert result.source_counts["stutter_detection"] == 1
    assert result.type_counts["scene_hard_cut_point"] == 1
    assert result.type_counts["stutter_segment_candidate"] == 1


def test_registry_stays_compatible_with_motion_analysis_source():
    job = _job_with_stutter_segments(
        [_stutter_segment("freeze_segment", 20.0, 22.0, 20, 0.995, 1.0)]
    )
    job.motion_analysis_report = {
        "motion_segments": [
            _motion_segment("high_motion", 30.0, 31.0, 0.45, 0.85)
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["motion_analysis"] == 1
    assert result.source_counts["stutter_detection"] == 1
    assert result.type_counts["motion_high_activity_segment"] == 1
    assert result.type_counts["freeze_segment_candidate"] == 1


def test_registry_stays_compatible_with_face_reaction_source():
    job = _job_with_stutter_segments(
        [_stutter_segment("encoding_drop_candidate", 20.0, 20.3, 2, 0.988, 0.992)]
    )
    job.face_reaction_report = {
        "face_reaction_segments": [
            _face_segment("hype_candidate", 40.0, 41.0, 0.70, 0.90)
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["face_reaction"] == 1
    assert result.source_counts["stutter_detection"] == 1
    assert result.type_counts["face_high_reaction_segment"] == 1
    assert result.type_counts["encoding_drop_candidate"] == 1


def test_stutter_registry_test_files_do_not_have_bom():
    files = [
        REPO_ROOT / "core" / "unified_edit_signal_registry.py",
        REPO_ROOT / "tests" / "test_stutter_detection_registry_integration_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_stutter_registry_test_files_end_with_newline():
    files = [
        REPO_ROOT / "core" / "unified_edit_signal_registry.py",
        REPO_ROOT / "tests" / "test_stutter_detection_registry_integration_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
