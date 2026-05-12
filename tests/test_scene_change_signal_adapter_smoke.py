from __future__ import annotations

from pathlib import Path

from core.scene_change_signal_adapter import (
    SceneChangeSignalAdapterResult,
    adapt_scene_change_report_to_signals,
    adapt_scene_changes_to_signals,
    build_scene_change_signal,
)


ADAPTER_PATH = Path("core/scene_change_signal_adapter.py")
TEST_PATH = Path("tests/test_scene_change_signal_adapter_smoke.py")


def _hard_change() -> dict:
    return {
        "time_seconds": 12.5,
        "frame_index": 125,
        "scene_score": 0.91,
        "change_type": "hard_scene_change",
        "confidence": 0.94,
        "is_false_positive_candidate": False,
        "warnings": [],
        "errors": [],
    }


def _soft_change() -> dict:
    return {
        "time_seconds": 20.0,
        "frame_index": 200,
        "scene_score": 0.42,
        "change_type": "soft_transition",
        "confidence": 0.66,
        "is_false_positive_candidate": False,
    }


def _flash_change() -> dict:
    return {
        "time_seconds": 33.3,
        "frame_index": 333,
        "scene_score": 0.98,
        "change_type": "flash_or_explosion_candidate",
        "confidence": 0.80,
        "is_false_positive_candidate": True,
        "warnings": ["flash_or_explosion_candidate"],
    }


def test_hard_scene_change_becomes_hard_cut_signal() -> None:
    signal = build_scene_change_signal(_hard_change(), source_index=0)

    assert signal["signal_type"] == "scene_hard_cut_point"
    assert signal["source"] == "scene_change"
    assert signal["action_hint"] == "candidate_cut_boundary"
    assert signal["priority"] == "high"
    assert signal["signal_score"] == 0.91
    assert signal["center_seconds"] == 12.5
    assert signal["reason"] == "hard_scene_change_detected"


def test_soft_transition_becomes_soft_transition_signal() -> None:
    signal = build_scene_change_signal(_soft_change(), source_index=1)

    assert signal["signal_type"] == "scene_soft_transition"
    assert signal["source"] == "scene_change"
    assert signal["action_hint"] == "avoid_hard_cut_or_review_transition"
    assert signal["priority"] == "medium"
    assert signal["signal_score"] == 0.42
    assert signal["center_seconds"] == 20.0
    assert signal["reason"] == "soft_transition_detected"


def test_flash_becomes_review_signal_not_safe_cutpoint() -> None:
    signal = build_scene_change_signal(_flash_change(), source_index=2)

    assert signal["signal_type"] == "scene_flash_or_explosion_candidate"
    assert signal["source"] == "scene_change"
    assert signal["action_hint"] == "review_false_positive_scene_change"
    assert signal["action_hint"] != "candidate_cut_boundary"
    assert signal["priority"] == "medium"
    assert signal["reason"] == "flash_or_explosion_candidate_detected"


def test_adapt_scene_changes_to_signals_counts_all_types() -> None:
    result = adapt_scene_changes_to_signals(
        [
            _hard_change(),
            _soft_change(),
            _flash_change(),
        ]
    )

    assert result.status == "ok"
    assert result.signal_count == 3
    assert result.hard_cut_signal_count == 1
    assert result.soft_transition_signal_count == 1
    assert result.false_positive_signal_count == 1
    assert result.recommendation == "scene_change_signals_available"


def test_empty_report_does_not_crash() -> None:
    result = adapt_scene_change_report_to_signals({"scene_changes": []})

    assert result.status == "skipped_no_scene_changes"
    assert result.signal_count == 0
    assert result.signals == []
    assert result.recommendation == "no_scene_changes_to_adapt"


def test_invalid_scene_change_entries_do_not_crash() -> None:
    result = adapt_scene_changes_to_signals(
        [
            None,
            "bad",
            {},
            _hard_change(),
        ]
    )

    assert result.status == "completed_with_warnings"
    assert result.signal_count == 1
    assert result.hard_cut_signal_count == 1
    assert "invalid_scene_change_entry_0" in result.warnings
    assert "invalid_scene_change_entry_1" in result.warnings
    assert "invalid_scene_change_entry_2" in result.warnings


def test_signal_contains_required_fields() -> None:
    signal = build_scene_change_signal(_hard_change(), source_index=0)

    required_fields = [
        "signal_id",
        "signal_type",
        "source",
        "start_seconds",
        "end_seconds",
        "center_seconds",
        "duration_seconds",
        "signal_score",
        "priority",
        "action_hint",
        "reason",
        "confidence",
        "metadata",
    ]

    for field_name in required_fields:
        assert field_name in signal


def test_signal_metadata_contains_original_scene_change_data() -> None:
    signal = build_scene_change_signal(_hard_change(), source_index=7)
    metadata = signal["metadata"]

    assert metadata["original_change_type"] == "hard_scene_change"
    assert metadata["frame_index"] == 125
    assert metadata["is_false_positive_candidate"] is False
    assert metadata["scene_score"] == 0.91
    assert metadata["source_index"] == 7
    assert metadata["warnings"] == []
    assert metadata["errors"] == []


def test_adapt_scene_change_report_to_signals_reads_report_dict() -> None:
    report = {
        "scene_changes": [
            _hard_change(),
            _soft_change(),
        ]
    }

    result = adapt_scene_change_report_to_signals(report)

    assert result.status == "ok"
    assert result.signal_count == 2
    assert result.signals[0]["signal_type"] == "scene_hard_cut_point"
    assert result.signals[1]["signal_type"] == "scene_soft_transition"


def test_adapter_result_roundtrip() -> None:
    result = SceneChangeSignalAdapterResult(
        status="ok",
        signals=[build_scene_change_signal(_hard_change(), source_index=0)],
        signal_count=1,
        hard_cut_signal_count=1,
        soft_transition_signal_count=0,
        false_positive_signal_count=0,
        warnings=["demo_warning"],
        errors=[],
        recommendation="scene_change_signals_available",
    )

    loaded = SceneChangeSignalAdapterResult.from_dict(result.to_dict())

    assert loaded.status == "ok"
    assert loaded.signal_count == 1
    assert loaded.hard_cut_signal_count == 1
    assert loaded.signals[0]["signal_type"] == "scene_hard_cut_point"
    assert loaded.warnings == ["demo_warning"]
    assert loaded.recommendation == "scene_change_signals_available"


def test_scene_change_signal_adapter_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        ADAPTER_PATH,
        TEST_PATH,
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
