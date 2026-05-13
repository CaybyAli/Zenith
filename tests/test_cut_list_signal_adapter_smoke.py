from pathlib import Path

from core.cut_list_signal_adapter import (
    CutListSignalAdapterResult,
    adapt_cut_list_item_to_signal,
    adapt_cut_list_report_to_signals,
)
from models.cut_list import (
    CUT_LIST_ACTION_CENSOR_KEEP,
    CUT_LIST_ACTION_KEEP,
    CUT_LIST_ACTION_PROTECT,
    CUT_LIST_ACTION_REVIEW_KEEP,
    CUT_LIST_ACTION_REVIEW_REMOVE,
    CUT_LIST_ACTION_REVIEW_TRIM,
    CUT_LIST_ACTION_TECHNICAL_REVIEW,
    CUT_LIST_ACTION_UNKNOWN_REVIEW,
    CutListItem,
)
from models.cut_list_run import CutListRunReport


ROOT = Path(__file__).resolve().parents[1]


def _item(action: str) -> CutListItem:
    return CutListItem(
        item_id=f"item_{action.lower()}",
        segment_id=f"seg_{action.lower()}",
        proposed_action=action,
        action_confidence=0.8,
        reason=f"reason for {action}",
        metadata={"test": True},
    )


def test_keep_maps_to_keep_candidate():
    signal = adapt_cut_list_item_to_signal(_item(CUT_LIST_ACTION_KEEP))

    assert signal["signal_type"] == "cut_list_keep_candidate"
    assert signal["source"] == "cut_list_generator"
    assert signal["action_hint"] == "review_keep_candidate"
    assert signal["priority"] == "high"


def test_review_keep_maps_to_review_keep():
    signal = adapt_cut_list_item_to_signal(_item(CUT_LIST_ACTION_REVIEW_KEEP))

    assert signal["signal_type"] == "cut_list_review_keep"
    assert signal["action_hint"] == "review_keep_candidate"
    assert signal["priority"] == "medium"


def test_review_trim_maps_to_review_trim():
    signal = adapt_cut_list_item_to_signal(_item(CUT_LIST_ACTION_REVIEW_TRIM))

    assert signal["signal_type"] == "cut_list_review_trim"
    assert signal["action_hint"] == "review_trim_candidate"
    assert signal["priority"] == "medium"


def test_review_remove_maps_to_review_remove_only():
    signal = adapt_cut_list_item_to_signal(_item(CUT_LIST_ACTION_REVIEW_REMOVE))

    assert signal["signal_type"] == "cut_list_review_remove"
    assert signal["action_hint"] == "review_remove_candidate"
    assert signal["priority"] == "medium"
    assert signal["action_hint"] != "remove_now"
    assert signal["action_hint"] != "auto_remove"


def test_protect_maps_to_protect_segment():
    signal = adapt_cut_list_item_to_signal(_item(CUT_LIST_ACTION_PROTECT))

    assert signal["signal_type"] == "cut_list_protect_segment"
    assert signal["action_hint"] == "protect_segment_from_cut"
    assert signal["priority"] == "high"


def test_censor_keep_maps_to_censor_keep():
    signal = adapt_cut_list_item_to_signal(_item(CUT_LIST_ACTION_CENSOR_KEEP))

    assert signal["signal_type"] == "cut_list_censor_keep"
    assert signal["action_hint"] == "preserve_segment_for_censor_sfx"
    assert signal["priority"] == "high"


def test_technical_review_maps_to_technical_review():
    signal = adapt_cut_list_item_to_signal(_item(CUT_LIST_ACTION_TECHNICAL_REVIEW))

    assert signal["signal_type"] == "cut_list_technical_review"
    assert signal["action_hint"] == "review_technical_cut_risk"
    assert signal["priority"] == "high"


def test_unknown_review_maps_to_unknown_review():
    signal = adapt_cut_list_item_to_signal(_item(CUT_LIST_ACTION_UNKNOWN_REVIEW))

    assert signal["signal_type"] == "cut_list_unknown_review"
    assert signal["action_hint"] == "review_unknown_cut_decision"
    assert signal["priority"] == "low"


def test_report_adapter_counts_all_signal_types():
    report = CutListRunReport(
        status="ok",
        items=[
            _item(CUT_LIST_ACTION_KEEP),
            _item(CUT_LIST_ACTION_REVIEW_KEEP),
            _item(CUT_LIST_ACTION_REVIEW_TRIM),
            _item(CUT_LIST_ACTION_REVIEW_REMOVE),
            _item(CUT_LIST_ACTION_PROTECT),
            _item(CUT_LIST_ACTION_CENSOR_KEEP),
            _item(CUT_LIST_ACTION_TECHNICAL_REVIEW),
            _item(CUT_LIST_ACTION_UNKNOWN_REVIEW),
        ],
    )

    result = adapt_cut_list_report_to_signals(report)

    assert result.status == "ok"
    assert result.signal_count == 8
    assert result.keep_signal_count == 1
    assert result.review_keep_signal_count == 1
    assert result.review_trim_signal_count == 1
    assert result.review_remove_signal_count == 1
    assert result.protect_signal_count == 1
    assert result.censor_keep_signal_count == 1
    assert result.technical_review_signal_count == 1
    assert result.unknown_review_signal_count == 1


def test_no_forbidden_action_hints_are_emitted():
    report = CutListRunReport(
        status="ok",
        items=[
            _item(CUT_LIST_ACTION_KEEP),
            _item(CUT_LIST_ACTION_REVIEW_REMOVE),
            _item(CUT_LIST_ACTION_CENSOR_KEEP),
            _item(CUT_LIST_ACTION_PROTECT),
        ],
    )

    result = adapt_cut_list_report_to_signals(report)

    forbidden = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "auto_cut",
        "auto_trim",
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

    for signal in result.signals:
        action_hint = str(signal.get("action_hint") or "").lower()
        for word in forbidden:
            assert word not in action_hint


def test_empty_input_is_safe():
    result = adapt_cut_list_report_to_signals([])

    assert result.status == "empty"
    assert result.signal_count == 0
    assert result.signals == []


def test_invalid_action_is_safe():
    result = adapt_cut_list_report_to_signals(
        [
            {
                "item_id": "bad",
                "segment_id": "seg_bad",
                "proposed_action": "BAD_ACTION",
            }
        ]
    )

    assert result.status == "empty"
    assert result.signal_count == 0
    assert result.warnings == ["unsupported_cut_list_action:BAD_ACTION"]


def test_signal_has_required_fields_and_metadata():
    signal = adapt_cut_list_item_to_signal(
        CutListItem(
            item_id="item_meta",
            segment_id="seg_meta",
            start_seconds=1.0,
            end_seconds=3.0,
            center_seconds=2.0,
            duration_seconds=2.0,
            proposed_action=CUT_LIST_ACTION_CENSOR_KEEP,
            action_confidence=0.88,
            segment_type="censor_required_segment",
            murch_score=0.7,
            content_value_score=0.6,
            censor_required=True,
            reason="needs later censor handling",
        )
    )

    assert signal["signal_id"] == "cut_list_signal_item_meta"
    assert signal["segment_id"] == "seg_meta"
    assert signal["start_seconds"] == 1.0
    assert signal["end_seconds"] == 3.0
    assert signal["confidence"] == 0.88
    assert signal["metadata"]["cut_list_action"] == CUT_LIST_ACTION_CENSOR_KEEP
    assert signal["metadata"]["censor_required"] is True


def test_adapter_result_roundtrip():
    result = adapt_cut_list_report_to_signals([_item(CUT_LIST_ACTION_PROTECT)])
    restored = CutListSignalAdapterResult.from_dict(result.to_dict())

    assert restored.status == "ok"
    assert restored.signal_count == 1
    assert restored.protect_signal_count == 1
    assert restored.signals[0]["signal_type"] == "cut_list_protect_segment"


def test_product_file_does_not_contain_forbidden_operational_terms():
    path = ROOT / "core" / "cut_list_signal_adapter.py"
    text = path.read_text(encoding="utf-8").lower()

    forbidden = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "auto_cut",
        "auto_trim",
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

    for word in forbidden:
        assert word not in text


def test_new_files_have_no_bom_and_end_with_newline():
    files = [
        ROOT / "core" / "cut_list_signal_adapter.py",
        ROOT / "tests" / "test_cut_list_signal_adapter_smoke.py",
    ]

    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert raw.endswith(b"\n")
