from __future__ import annotations

from pathlib import Path

from core.screen_content_signal_adapter import (
    ScreenContentSignalAdapterResult,
    adapt_screen_content_report_to_signals,
    adapt_screen_content_segments_to_signals,
    build_screen_content_signal,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _segment(
    screen_type: str,
    start_seconds: float = 1.0,
    end_seconds: float = 2.0,
    avg_confidence: float = 0.80,
    max_confidence: float = 0.90,
    recommendation: str = "review",
) -> dict:
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": end_seconds - start_seconds,
        "screen_type": screen_type,
        "avg_confidence": avg_confidence,
        "max_confidence": max_confidence,
        "point_count": 3,
        "recommendation": recommendation,
        "warnings": [],
        "errors": [],
    }


def _single_signal(screen_type: str) -> dict:
    result = adapt_screen_content_segments_to_signals([_segment(screen_type)])

    assert result.status == "ok"
    assert result.signal_count == 1
    return result.signals[0]


def test_gameplay_maps_to_screen_gameplay_segment():
    signal = _single_signal("gameplay")

    assert signal["signal_type"] == "screen_gameplay_segment"
    assert signal["source"] == "screen_content"
    assert signal["action_hint"] == "keep_content_context"
    assert signal["priority"] == "medium"
    assert signal["reason"] == "gameplay_screen_detected"


def test_menu_maps_to_screen_menu_segment():
    signal = _single_signal("menu")

    assert signal["signal_type"] == "screen_menu_segment"
    assert signal["action_hint"] == "review_possible_trim_menu"
    assert signal["priority"] == "medium"
    assert signal["reason"] == "menu_screen_detected"


def test_lobby_maps_to_screen_lobby_segment():
    signal = _single_signal("lobby")

    assert signal["signal_type"] == "screen_lobby_segment"
    assert signal["action_hint"] == "review_possible_trim_lobby"
    assert signal["priority"] == "medium"
    assert signal["reason"] == "lobby_screen_detected"


def test_loading_maps_to_screen_loading_segment():
    signal = _single_signal("loading")

    assert signal["signal_type"] == "screen_loading_segment"
    assert signal["action_hint"] == "review_possible_trim_loading"
    assert signal["priority"] == "high"
    assert signal["reason"] == "loading_screen_detected"


def test_scoreboard_maps_to_screen_scoreboard_segment():
    signal = _single_signal("scoreboard")

    assert signal["signal_type"] == "screen_scoreboard_segment"
    assert signal["action_hint"] == "review_scoreboard_context"
    assert signal["priority"] == "medium"
    assert signal["reason"] == "scoreboard_screen_detected"


def test_death_screen_maps_to_screen_death_segment():
    signal = _single_signal("death_screen")

    assert signal["signal_type"] == "screen_death_segment"
    assert signal["action_hint"] == "review_death_context"
    assert signal["priority"] == "medium"
    assert signal["reason"] == "death_screen_detected"


def test_victory_screen_maps_to_screen_victory_segment():
    signal = _single_signal("victory_screen")

    assert signal["signal_type"] == "screen_victory_segment"
    assert signal["action_hint"] == "keep_or_highlight_victory"
    assert signal["priority"] == "high"
    assert signal["reason"] == "victory_screen_detected"


def test_black_screen_maps_to_screen_black_segment():
    signal = _single_signal("black_screen")

    assert signal["signal_type"] == "screen_black_segment"
    assert signal["action_hint"] == "review_possible_trim_black_screen"
    assert signal["priority"] == "high"
    assert signal["reason"] == "black_screen_detected"


def test_intro_outro_maps_to_screen_intro_outro_candidate():
    signal = _single_signal("intro_outro_candidate")

    assert signal["signal_type"] == "screen_intro_outro_candidate"
    assert signal["action_hint"] == "review_intro_outro_boundary"
    assert signal["priority"] == "medium"
    assert signal["reason"] == "intro_outro_candidate_detected"


def test_screen_content_signals_do_not_auto_remove():
    result = adapt_screen_content_segments_to_signals(
        [
            _segment("loading"),
            _segment("black_screen", 3.0, 4.0),
            _segment("menu", 5.0, 6.0),
        ]
    )

    forbidden = {"remove_now", "hard_remove", "auto_remove", "delete_segment"}
    for signal in result.signals:
        assert signal["action_hint"] not in forbidden


def test_empty_report_is_safe():
    result = adapt_screen_content_report_to_signals({})

    assert result.status == "skipped_no_screen_content_segments"
    assert result.signal_count == 0
    assert result.warnings
    assert result.errors == []


def test_invalid_entries_are_safe():
    result = adapt_screen_content_segments_to_signals(
        [None, "bad", _segment("unknown"), _segment("gameplay")]
    )

    assert result.status == "completed_with_warnings"
    assert result.signal_count == 1
    assert result.gameplay_signal_count == 1
    assert result.warnings


def test_required_signal_fields_are_present():
    signal = build_screen_content_signal(_segment("loading"), source_index=7)

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


def test_signal_metadata_contains_original_screen_context():
    segment = _segment(
        "victory_screen",
        avg_confidence=0.91,
        max_confidence=0.97,
        recommendation="keep_or_highlight_victory_screen",
    )

    signal = build_screen_content_signal(segment, source_index=3)
    metadata = signal["metadata"]

    assert metadata["original_screen_type"] == "victory_screen"
    assert metadata["avg_confidence"] == 0.91
    assert metadata["max_confidence"] == 0.97
    assert metadata["point_count"] == 3
    assert metadata["recommendation"] == "keep_or_highlight_victory_screen"
    assert metadata["source_index"] == 3
    assert metadata["warnings"] == []
    assert metadata["errors"] == []


def test_screen_content_signal_adapter_result_roundtrip():
    result = adapt_screen_content_segments_to_signals(
        [_segment("gameplay"), _segment("loading", 3.0, 4.0)]
    )

    restored = ScreenContentSignalAdapterResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_screen_content_signal_adapter_files_do_not_have_bom():
    files = [
        REPO_ROOT / "core" / "screen_content_signal_adapter.py",
        REPO_ROOT / "tests" / "test_screen_content_signal_adapter_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_screen_content_signal_adapter_files_end_with_newline():
    files = [
        REPO_ROOT / "core" / "screen_content_signal_adapter.py",
        REPO_ROOT / "tests" / "test_screen_content_signal_adapter_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
