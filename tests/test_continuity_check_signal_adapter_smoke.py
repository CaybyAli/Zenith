from pathlib import Path

from core.continuity_check_signal_adapter import (
    ContinuityCheckSignalAdapterResult,
    adapt_continuity_check_report_to_signals,
    adapt_continuity_issue_to_signal,
)
from models.continuity_check import ContinuityIssue


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_FILE = ROOT / "core" / "continuity_check_signal_adapter.py"
TEST_FILE = ROOT / "tests" / "test_continuity_check_signal_adapter_smoke.py"

FORBIDDEN_ACTION_HINTS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_transition",
    "auto_fade",
    "auto_j_cut",
    "auto_l_cut",
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
    "apply_transition",
]


def _issue(issue_type, index=1, **extra):
    data = {
        "issue_id": f"issue_{index}",
        "source_item_id": f"item_{index}",
        "segment_id": f"seg_{index}",
        "start_seconds": float(index * 10),
        "end_seconds": float(index * 10 + 4),
        "center_seconds": float(index * 10 + 2),
        "duration_seconds": 4.0,
        "issue_type": issue_type,
        "severity": "high",
        "confidence": 0.85,
        "priority": "high",
        "is_blocking": issue_type in {
            "sentence_break_risk",
            "censor_context_risk",
            "protected_context_violation",
        },
        "is_protected_context": issue_type in {
            "sentence_break_risk",
            "context_jump_risk",
            "censor_context_risk",
            "protected_context_violation",
        },
        "is_censor_context": issue_type == "censor_context_risk",
        "is_technical_issue": issue_type
        in {"invalid_timing", "overlap_risk", "gap_risk", "technical_continuity_risk"},
        "requires_review": True,
        "recommendation": "review_continuity",
        "reason": f"{issue_type}_reason",
        "evidence": {"review_only": True},
        "source_signal_ids": [f"sig_{index}"],
        "warnings": [],
        "errors": [],
        "metadata": {"source": "test"},
    }
    data.update(extra)
    return data


def test_sentence_break_risk_maps_to_continuity_sentence_break_risk():
    signal = adapt_continuity_issue_to_signal(_issue("sentence_break_risk"))

    assert signal["signal_type"] == "continuity_sentence_break_risk"
    assert signal["source"] == "continuity_check"
    assert signal["action_hint"] == "review_sentence_boundary_continuity"
    assert signal["priority"] == "high"


def test_context_jump_risk_maps_to_continuity_context_jump_risk():
    signal = adapt_continuity_issue_to_signal(_issue("context_jump_risk"))

    assert signal["signal_type"] == "continuity_context_jump_risk"
    assert signal["action_hint"] == "review_context_jump_continuity"


def test_censor_context_risk_maps_to_continuity_censor_context_risk():
    signal = adapt_continuity_issue_to_signal(_issue("censor_context_risk"))

    assert signal["signal_type"] == "continuity_censor_context_risk"
    assert signal["action_hint"] == "protect_censor_context_continuity"


def test_invalid_overlap_and_gap_map_to_continuity_timing_issue():
    result = adapt_continuity_check_report_to_signals(
        {
            "issues": [
                _issue("invalid_timing", 1),
                _issue("overlap_risk", 2),
                _issue("gap_risk", 3),
            ]
        }
    )

    assert result.timing_issue_signal_count == 3
    assert {signal["signal_type"] for signal in result.signals} == {
        "continuity_timing_issue"
    }


def test_transition_conflict_maps_to_continuity_transition_conflict():
    signal = adapt_continuity_issue_to_signal(_issue("transition_conflict"))

    assert signal["signal_type"] == "continuity_transition_conflict"
    assert signal["action_hint"] == "review_transition_conflict"


def test_protected_violation_maps_to_continuity_protected_context_violation():
    signal = adapt_continuity_issue_to_signal(_issue("protected_context_violation"))

    assert signal["signal_type"] == "continuity_protected_context_violation"
    assert signal["action_hint"] == "protect_context_from_cut"


def test_technical_risk_maps_to_continuity_technical_risk():
    signal = adapt_continuity_issue_to_signal(_issue("technical_continuity_risk"))

    assert signal["signal_type"] == "continuity_technical_risk"
    assert signal["action_hint"] == "review_technical_continuity"


def test_unknown_maps_to_continuity_unknown_review():
    signal = adapt_continuity_issue_to_signal(_issue("unsupported_type"))

    assert signal["signal_type"] == "continuity_unknown_review"
    assert signal["action_hint"] == "review_unknown_continuity"


def test_adapter_has_no_forbidden_action_hints():
    result = adapt_continuity_check_report_to_signals(
        {
            "issues": [
                _issue("sentence_break_risk", 1),
                _issue("context_jump_risk", 2),
                _issue("censor_context_risk", 3),
                _issue("invalid_timing", 4),
                _issue("transition_conflict", 5),
                _issue("protected_context_violation", 6),
                _issue("technical_continuity_risk", 7),
                _issue("unknown_continuity_review", 8),
            ]
        }
    )

    dumped = str(result.to_dict()).lower()
    for forbidden in FORBIDDEN_ACTION_HINTS:
        assert forbidden not in dumped


def test_empty_input_is_safe():
    result = adapt_continuity_check_report_to_signals(None)

    assert result.status == "empty"
    assert result.signals == []
    assert result.signal_count == 0


def test_invalid_input_is_safe():
    result = adapt_continuity_check_report_to_signals({"issues": ["bad"]})

    assert result.status == "ok"
    assert result.signal_count == 1
    assert result.signals[0]["signal_type"] == "continuity_unknown_review"


def test_required_fields_are_present():
    signal = adapt_continuity_issue_to_signal(_issue("sentence_break_risk"))

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
        "signal_score",
        "confidence",
        "priority",
        "action_hint",
        "reason",
        "metadata",
    ]

    for field in required_fields:
        assert field in signal


def test_metadata_is_preserved_and_review_only():
    issue = ContinuityIssue.from_dict(_issue("censor_context_risk"))

    signal = adapt_continuity_issue_to_signal(issue)

    assert signal["metadata"]["issue_type"] == "censor_context_risk"
    assert signal["metadata"]["evidence"]["review_only"] is True
    assert signal["metadata"]["review_only"] is True


def test_adapter_result_roundtrip():
    result = adapt_continuity_check_report_to_signals(
        {"issues": [_issue("sentence_break_risk")]}
    )

    loaded = ContinuityCheckSignalAdapterResult.from_dict(result.to_dict())

    assert loaded.to_dict() == result.to_dict()


def test_new_files_have_no_bom_and_end_with_newline():
    for file_path in [ADAPTER_FILE, TEST_FILE]:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
