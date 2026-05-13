from pathlib import Path

from core.clip_duration_signal_adapter import (
    ClipDurationSignalAdapterResult,
    adapt_clip_duration_report_to_signals,
    adapt_clip_duration_recommendation_to_signal,
)


ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    ROOT / "core" / "clip_duration_signal_adapter.py",
    ROOT / "tests" / "test_clip_duration_signal_adapter_smoke.py",
]

FORBIDDEN_ACTION_HINTS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_extend",
    "auto_highlight",
    "highlight_now",
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
    "apply_cut",
    "render_now",
    "execute_cut",
    "final_cut",
]


def _recommendation(status: str, recommendation_id: str = "rec_1") -> dict:
    return {
        "recommendation_id": recommendation_id,
        "source_item_id": f"item_{recommendation_id}",
        "segment_id": f"segment_{recommendation_id}",
        "start_seconds": 10.0,
        "end_seconds": 18.0,
        "center_seconds": 14.0,
        "duration_seconds": 8.0,
        "confidence": 0.8,
        "priority": "medium",
        "proposed_action": "KEEP",
        "duration_status": status,
        "recommended_min_duration_seconds": 4.0,
        "recommended_max_duration_seconds": 90.0,
        "recommended_target_duration_seconds": 18.0,
        "suggested_start_seconds": None,
        "suggested_end_seconds": None,
        "suggested_duration_seconds": None,
        "adjustment_seconds": 0.0,
        "is_review_required": status != "duration_ok",
        "is_protected": status == "protect_duration",
        "is_censor_keep": status == "censor_keep_duration",
        "is_invalid_timing": status == "invalid_timing_review",
        "reason": f"{status}_reason",
        "decision_basis": {"review_only": True},
    }


def test_duration_ok_maps_to_clip_duration_ok_signal():
    signal = adapt_clip_duration_recommendation_to_signal(
        _recommendation("duration_ok")
    )

    assert signal["signal_type"] == "clip_duration_ok"
    assert signal["source"] == "clip_duration_optimizer"
    assert signal["action_hint"] == "review_duration_ok"
    assert signal["priority"] == "low"


def test_too_short_and_extend_map_to_too_short_review_signal():
    result = adapt_clip_duration_report_to_signals(
        [
            _recommendation("too_short_review", "short_1"),
            _recommendation("extend_review", "extend_1"),
        ]
    )

    assert result.signal_count == 2
    assert result.too_short_signal_count == 2
    assert {
        signal["signal_type"] for signal in result.signals
    } == {"clip_duration_too_short_review"}


def test_too_long_and_trim_map_to_too_long_review_signal():
    result = adapt_clip_duration_report_to_signals(
        [
            _recommendation("too_long_review", "long_1"),
            _recommendation("trim_review", "trim_1"),
        ]
    )

    assert result.signal_count == 2
    assert result.too_long_signal_count == 2
    assert {
        signal["signal_type"] for signal in result.signals
    } == {"clip_duration_too_long_review"}
    assert {
        signal["action_hint"] for signal in result.signals
    } == {"review_trim_duration_candidate"}


def test_protect_maps_to_clip_duration_protected_signal():
    signal = adapt_clip_duration_recommendation_to_signal(
        _recommendation("protect_duration")
    )

    assert signal["signal_type"] == "clip_duration_protected"
    assert signal["action_hint"] == "protect_duration_from_blind_trim"
    assert signal["priority"] == "high"


def test_censor_keep_maps_to_clip_duration_censor_keep_signal():
    signal = adapt_clip_duration_recommendation_to_signal(
        _recommendation("censor_keep_duration")
    )

    assert signal["signal_type"] == "clip_duration_censor_keep"
    assert signal["action_hint"] == "preserve_duration_for_censor_sfx"
    assert signal["priority"] == "high"


def test_technical_maps_to_clip_duration_technical_review_signal():
    signal = adapt_clip_duration_recommendation_to_signal(
        _recommendation("technical_review")
    )

    assert signal["signal_type"] == "clip_duration_technical_review"
    assert signal["action_hint"] == "review_duration_technical_risk"
    assert signal["priority"] == "high"


def test_invalid_timing_maps_to_clip_duration_invalid_timing_signal():
    signal = adapt_clip_duration_recommendation_to_signal(
        _recommendation("invalid_timing_review")
    )

    assert signal["signal_type"] == "clip_duration_invalid_timing"
    assert signal["action_hint"] == "review_invalid_clip_timing"
    assert signal["priority"] == "high"


def test_unknown_maps_to_clip_duration_unknown_review_signal():
    signal = adapt_clip_duration_recommendation_to_signal(
        _recommendation("unknown_review")
    )

    assert signal["signal_type"] == "clip_duration_unknown_review"
    assert signal["action_hint"] == "review_unknown_duration_decision"
    assert signal["priority"] == "low"


def test_invalid_status_is_safe_unknown_review():
    signal = adapt_clip_duration_recommendation_to_signal(
        _recommendation("does_not_exist")
    )

    assert signal["signal_type"] == "clip_duration_unknown_review"
    assert signal["metadata"]["duration_status"] == "unknown_review"


def test_empty_input_is_safe():
    result = adapt_clip_duration_report_to_signals([])

    assert result.status == "empty"
    assert result.signal_count == 0
    assert result.recommendation == "clip_duration_signal_adapter_empty"


def test_required_signal_fields_exist():
    signal = adapt_clip_duration_recommendation_to_signal(
        _recommendation("duration_ok")
    )

    required_fields = [
        "signal_id",
        "signal_type",
        "source",
        "source_item_id",
        "segment_id",
        "start_seconds",
        "end_seconds",
        "center_seconds",
        "duration_seconds",
        "confidence",
        "priority",
        "action_hint",
        "reason",
        "metadata",
    ]

    for field in required_fields:
        assert field in signal


def test_metadata_is_preserved_as_review_only():
    signal = adapt_clip_duration_recommendation_to_signal(
        {
            **_recommendation("trim_review"),
            "suggested_start_seconds": 11.0,
            "suggested_end_seconds": 19.0,
            "suggested_duration_seconds": 8.0,
            "adjustment_seconds": -12.0,
        }
    )

    metadata = signal["metadata"]

    assert metadata["duration_status"] == "trim_review"
    assert metadata["suggested_start_seconds"] == 11.0
    assert metadata["suggested_end_seconds"] == 19.0
    assert metadata["suggested_duration_seconds"] == 8.0
    assert metadata["adjustment_seconds"] == -12.0
    assert metadata["review_only"] is True


def test_adapter_result_roundtrip():
    result = adapt_clip_duration_report_to_signals(
        [
            _recommendation("duration_ok", "ok_1"),
            _recommendation("protect_duration", "protect_1"),
        ]
    )

    loaded = ClipDurationSignalAdapterResult.from_dict(result.to_dict())

    assert loaded.to_dict() == result.to_dict()


def test_report_container_and_plan_container_are_supported():
    report_result = adapt_clip_duration_report_to_signals(
        {
            "recommendations": [
                _recommendation("duration_ok", "ok_1"),
            ]
        }
    )
    plan_result = adapt_clip_duration_report_to_signals(
        {
            "clip_duration_plan": {
                "recommendations": [
                    _recommendation("censor_keep_duration", "censor_1"),
                ]
            }
        }
    )

    assert report_result.duration_ok_signal_count == 1
    assert plan_result.censor_keep_signal_count == 1


def test_no_forbidden_action_hints_are_emitted():
    result = adapt_clip_duration_report_to_signals(
        [
            _recommendation("duration_ok", "ok_1"),
            _recommendation("extend_review", "extend_1"),
            _recommendation("trim_review", "trim_1"),
            _recommendation("protect_duration", "protect_1"),
            _recommendation("censor_keep_duration", "censor_1"),
            _recommendation("technical_review", "technical_1"),
            _recommendation("invalid_timing_review", "invalid_1"),
            _recommendation("unknown_review", "unknown_1"),
        ]
    )

    dumped = str(result.to_dict()).lower()

    for forbidden in FORBIDDEN_ACTION_HINTS:
        assert forbidden not in dumped


def test_new_files_have_no_bom_and_end_with_newline():
    for file_path in NEW_FILES:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
