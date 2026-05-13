from pathlib import Path

from core.final_cut_list_signal_adapter import (
    FinalCutListSignalAdapterResult,
    adapt_final_cut_list_report_to_signals,
)


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_FILE = ROOT / "core" / "final_cut_list_signal_adapter.py"
TEST_FILE = ROOT / "tests" / "test_cut_list_finalizer_signal_adapter_smoke.py"


ACTION_TO_TYPE = {
    "FINAL_KEEP_REVIEW": "final_cut_list_keep_review",
    "FINAL_KEEP_HIGH_VALUE": "final_cut_list_keep_high_value",
    "FINAL_TRIM_REVIEW": "final_cut_list_trim_review",
    "FINAL_REMOVE_REVIEW": "final_cut_list_remove_review",
    "FINAL_PROTECT": "final_cut_list_protect",
    "FINAL_CENSOR_KEEP": "final_cut_list_censor_keep",
    "FINAL_TECHNICAL_REVIEW": "final_cut_list_technical_review",
    "FINAL_BLOCKED_BY_CONTINUITY": "final_cut_list_blocked_by_continuity",
    "FINAL_UNKNOWN_REVIEW": "final_cut_list_unknown_review",
}


def _item(action: str) -> dict:
    return {
        "final_item_id": f"item_{action.lower()}",
        "source_item_id": "source_1",
        "segment_id": "seg_1",
        "start_seconds": 1.0,
        "end_seconds": 2.0,
        "final_action": action,
        "final_confidence": 0.8,
        "priority": "high",
        "reason": "review",
        "metadata": {"review_only": True},
    }


def test_each_final_action_maps_to_expected_signal_type():
    for action, signal_type in ACTION_TO_TYPE.items():
        result = adapt_final_cut_list_report_to_signals([_item(action)])

        assert result.status == "ok"
        assert result.signal_count == 1
        assert result.signals[0]["signal_type"] == signal_type
        assert result.signals[0]["source"] == "cut_list_finalizer"


def test_counts_by_signal_type():
    result = adapt_final_cut_list_report_to_signals(
        [_item(action) for action in ACTION_TO_TYPE]
    )

    assert result.keep_review_signal_count == 1
    assert result.keep_high_value_signal_count == 1
    assert result.trim_review_signal_count == 1
    assert result.remove_review_signal_count == 1
    assert result.protect_signal_count == 1
    assert result.censor_keep_signal_count == 1
    assert result.technical_review_signal_count == 1
    assert result.blocked_by_continuity_signal_count == 1
    assert result.unknown_review_signal_count == 1


def test_empty_and_invalid_inputs_are_safe():
    empty = adapt_final_cut_list_report_to_signals([])
    invalid = adapt_final_cut_list_report_to_signals(None)

    assert empty.status == "empty"
    assert empty.signal_count == 0
    assert invalid.status == "empty"
    assert invalid.signal_count == 0


def test_required_fields_and_metadata_are_present():
    result = adapt_final_cut_list_report_to_signals([_item("FINAL_PROTECT")])
    signal = result.signals[0]

    for field in [
        "signal_id",
        "signal_type",
        "source",
        "source_item_id",
        "segment_id",
        "start_seconds",
        "end_seconds",
        "confidence",
        "priority",
        "action_hint",
        "metadata",
    ]:
        assert field in signal

    assert signal["metadata"]["final_action"] == "FINAL_PROTECT"
    assert signal["metadata"]["review_only"] is True


def test_adapter_result_roundtrip():
    result = adapt_final_cut_list_report_to_signals([_item("FINAL_KEEP_REVIEW")])

    assert FinalCutListSignalAdapterResult.from_dict(result.to_dict()).to_dict() == (
        result.to_dict()
    )


def test_product_file_does_not_contain_forbidden_action_hints():
    text = PRODUCT_FILE.read_text(encoding="utf-8").lower()
    forbidden = [
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
        "render_now",
        "execute_cut",
        "apply_final_cutlist",
        "execute_final_cutlist",
    ]

    for word in forbidden:
        assert word not in text, f"{word} found in {PRODUCT_FILE}"


def test_no_bom_and_newline():
    for path in [PRODUCT_FILE, TEST_FILE]:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path
