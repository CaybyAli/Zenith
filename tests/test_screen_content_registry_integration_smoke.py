from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result


REPO_ROOT = Path(__file__).resolve().parents[1]


def _screen_segment(
    screen_type: str,
    start_seconds: float,
    end_seconds: float,
    avg_confidence: float,
    max_confidence: float,
) -> dict:
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": end_seconds - start_seconds,
        "screen_type": screen_type,
        "avg_confidence": avg_confidence,
        "max_confidence": max_confidence,
        "point_count": 3,
        "recommendation": "review",
        "warnings": [],
        "errors": [],
    }


def _stutter_segment(
    classification: str,
    start_seconds: float,
    end_seconds: float,
) -> dict:
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": end_seconds - start_seconds,
        "start_frame_index": int(start_seconds * 10),
        "end_frame_index": int(end_seconds * 10),
        "duplicate_frame_count": 4,
        "avg_duplicate_score": 0.990,
        "max_duplicate_score": 0.999,
        "classification": classification,
        "recommendation": "review",
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


def _job_with_screen_segments(segments: list[dict]):
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
        screen_content_report={
            "screen_content_segments": segments,
        },
        screen_content_segments=[],
        screen_content_result={},
    )


def _signal_by_type(result, signal_type: str) -> dict:
    for signal in result.signals:
        if signal.get("signal_type") == signal_type:
            return signal

    raise AssertionError(f"Signal type not found: {signal_type}")


def test_registry_collects_screen_content_source_counts_and_types():
    result = build_unified_edit_signal_result(
        _job_with_screen_segments(
            [
                _screen_segment("gameplay", 1.0, 2.0, 0.70, 0.80),
                _screen_segment("loading", 3.0, 4.0, 0.85, 0.90),
                _screen_segment("victory_screen", 5.0, 6.0, 0.92, 0.98),
                _screen_segment("black_screen", 7.0, 8.0, 0.88, 0.95),
            ]
        )
    )

    assert result.status == "ok"
    assert result.source_counts["screen_content"] == 4
    assert result.type_counts["screen_gameplay_segment"] == 1
    assert result.type_counts["screen_loading_segment"] == 1
    assert result.type_counts["screen_victory_segment"] == 1
    assert result.type_counts["screen_black_segment"] == 1


def test_registry_screen_content_signals_do_not_auto_remove():
    result = build_unified_edit_signal_result(
        _job_with_screen_segments(
            [
                _screen_segment("loading", 1.0, 2.0, 0.85, 0.90),
                _screen_segment("black_screen", 3.0, 4.0, 0.88, 0.95),
            ]
        )
    )

    forbidden = {"remove_now", "hard_remove", "auto_remove", "delete_segment"}
    for signal in result.signals:
        if signal.get("source") == "screen_content":
            assert signal["action_hint"] not in forbidden


def test_empty_screen_content_report_does_not_crash():
    result = build_unified_edit_signal_result(_job_with_screen_segments([]))

    assert result.status == "skipped_no_signals"
    assert "screen_content" not in result.source_counts
    assert result.signal_count == 0
    assert result.warnings


def test_registry_collects_screen_segments_fallback_from_job_field():
    job = _job_with_screen_segments([])
    job.screen_content_report = {}
    job.screen_content_segments = [
        _screen_segment("loading", 11.0, 13.0, 0.85, 0.90)
    ]

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["screen_content"] == 1
    assert result.type_counts["screen_loading_segment"] == 1


def test_registry_collects_screen_segments_fallback_from_result_field():
    job = _job_with_screen_segments([])
    job.screen_content_report = {}
    job.screen_content_segments = []
    job.screen_content_result = {
        "segments": [
            _screen_segment("victory_screen", 15.0, 16.0, 0.92, 0.98)
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["screen_content"] == 1
    assert result.type_counts["screen_victory_segment"] == 1


def test_registry_stays_compatible_with_scene_change_source():
    job = _job_with_screen_segments(
        [_screen_segment("gameplay", 20.0, 21.0, 0.70, 0.80)]
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
    assert result.source_counts["screen_content"] == 1
    assert result.type_counts["scene_hard_cut_point"] == 1
    assert result.type_counts["screen_gameplay_segment"] == 1


def test_registry_stays_compatible_with_motion_analysis_source():
    job = _job_with_screen_segments(
        [_screen_segment("loading", 20.0, 22.0, 0.85, 0.90)]
    )
    job.motion_analysis_report = {
        "motion_segments": [
            _motion_segment("high_motion", 30.0, 31.0, 0.45, 0.85)
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["motion_analysis"] == 1
    assert result.source_counts["screen_content"] == 1
    assert result.type_counts["motion_high_activity_segment"] == 1
    assert result.type_counts["screen_loading_segment"] == 1


def test_registry_stays_compatible_with_face_reaction_source():
    job = _job_with_screen_segments(
        [_screen_segment("victory_screen", 20.0, 21.0, 0.92, 0.98)]
    )
    job.face_reaction_report = {
        "face_reaction_segments": [
            _face_segment("hype_candidate", 40.0, 41.0, 0.70, 0.90)
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["face_reaction"] == 1
    assert result.source_counts["screen_content"] == 1
    assert result.type_counts["face_high_reaction_segment"] == 1
    assert result.type_counts["screen_victory_segment"] == 1


def test_registry_stays_compatible_with_stutter_detection_source():
    job = _job_with_screen_segments(
        [_screen_segment("black_screen", 20.0, 21.0, 0.88, 0.95)]
    )
    job.stutter_detection_report = {
        "stutter_segments": [
            _stutter_segment("freeze_segment", 50.0, 51.0)
        ]
    }

    result = build_unified_edit_signal_result(job)

    assert result.status == "ok"
    assert result.source_counts["stutter_detection"] == 1
    assert result.source_counts["screen_content"] == 1
    assert result.type_counts["freeze_segment_candidate"] == 1
    assert result.type_counts["screen_black_segment"] == 1


def test_screen_content_registry_test_files_do_not_have_bom():
    files = [
        REPO_ROOT / "core" / "unified_edit_signal_registry.py",
        REPO_ROOT / "tests" / "test_screen_content_registry_integration_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_screen_content_registry_test_files_end_with_newline():
    files = [
        REPO_ROOT / "core" / "unified_edit_signal_registry.py",
        REPO_ROOT / "tests" / "test_screen_content_registry_integration_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
