from pathlib import Path

from core.transition_decision_signal_adapter import (
    TransitionDecisionSignalAdapterResult,
    adapt_transition_decision_report_to_signals,
    adapt_transition_decision_to_signal,
)


ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    ROOT / "core" / "transition_decision_signal_adapter.py",
    ROOT / "tests" / "test_transition_decision_signal_adapter_smoke.py",
]

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


def _decision(transition_type: str, decision_id: str = "decision_1") -> dict:
    return {
        "decision_id": decision_id,
        "source_item_id": f"item_{decision_id}",
        "segment_id": f"segment_{decision_id}",
        "start_seconds": 10.0,
        "end_seconds": 18.0,
        "center_seconds": 14.0,
        "duration_seconds": 8.0,
        "transition_type": transition_type,
        "transition_confidence": 0.8,
        "priority": "medium",
        "proposed_action": "review_transition",
        "cut_list_action": "KEEP",
        "duration_status": "duration_ok",
        "murch_score": 0.75,
        "is_protected": transition_type == "no_cut_protect",
        "is_censor_keep": transition_type == "censor_safe_keep",
        "is_technical_review": transition_type == "technical_transition_review",
        "is_scene_change_aligned": transition_type in {
            "hard_cut_review",
            "quick_fade_review",
        },
        "is_beat_aligned": transition_type == "hard_cut_review",
        "is_sentence_safe": transition_type == "no_cut_protect",
        "is_dialogue_context": transition_type in {"j_cut_review", "l_cut_review"},
        "reason": f"{transition_type}_reason",
        "decision_basis": {"review_only": True},
        "source_signal_ids": ["sig_1"],
    }


def test_hard_cut_review_maps_to_transition_hard_cut_review_signal():
    signal = adapt_transition_decision_to_signal(_decision("hard_cut_review"))

    assert signal["signal_type"] == "transition_hard_cut_review"
    assert signal["source"] == "transition_decision"
    assert signal["action_hint"] == "review_hard_cut_transition"
    assert signal["priority"] == "medium"


def test_j_cut_review_maps_to_transition_j_cut_review_signal():
    signal = adapt_transition_decision_to_signal(_decision("j_cut_review"))

    assert signal["signal_type"] == "transition_j_cut_review"
    assert signal["action_hint"] == "review_j_cut_transition"
    assert signal["priority"] == "medium"


def test_l_cut_review_maps_to_transition_l_cut_review_signal():
    signal = adapt_transition_decision_to_signal(_decision("l_cut_review"))

    assert signal["signal_type"] == "transition_l_cut_review"
    assert signal["action_hint"] == "review_l_cut_transition"
    assert signal["priority"] == "medium"


def test_quick_fade_review_maps_to_transition_quick_fade_review_signal():
    signal = adapt_transition_decision_to_signal(_decision("quick_fade_review"))

    assert signal["signal_type"] == "transition_quick_fade_review"
    assert signal["action_hint"] == "review_quick_fade_transition"
    assert signal["priority"] == "medium"


def test_no_cut_protect_maps_to_transition_no_cut_protect_signal():
    signal = adapt_transition_decision_to_signal(_decision("no_cut_protect"))

    assert signal["signal_type"] == "transition_no_cut_protect"
    assert signal["action_hint"] == "protect_from_blind_transition"
    assert signal["priority"] == "high"


def test_censor_safe_keep_maps_to_transition_censor_safe_keep_signal():
    signal = adapt_transition_decision_to_signal(_decision("censor_safe_keep"))

    assert signal["signal_type"] == "transition_censor_safe_keep"
    assert signal["action_hint"] == "preserve_transition_for_censor_sfx"
    assert signal["priority"] == "high"


def test_technical_review_maps_to_transition_technical_review_signal():
    signal = adapt_transition_decision_to_signal(
        _decision("technical_transition_review")
    )

    assert signal["signal_type"] == "transition_technical_review"
    assert signal["action_hint"] == "review_transition_technical_risk"
    assert signal["priority"] == "high"


def test_unknown_maps_to_transition_unknown_review_signal():
    signal = adapt_transition_decision_to_signal(_decision("transition_unknown_review"))

    assert signal["signal_type"] == "transition_unknown_review"
    assert signal["action_hint"] == "review_unknown_transition_decision"
    assert signal["priority"] == "low"


def test_invalid_transition_type_is_safe_unknown_review():
    signal = adapt_transition_decision_to_signal(_decision("does_not_exist"))

    assert signal["signal_type"] == "transition_unknown_review"
    assert signal["metadata"]["transition_type"] == "transition_unknown_review"


def test_empty_input_is_safe():
    result = adapt_transition_decision_report_to_signals([])

    assert result.status == "empty"
    assert result.signal_count == 0
    assert result.recommendation == "transition_decision_signal_adapter_empty"


def test_invalid_input_is_safe():
    result = adapt_transition_decision_report_to_signals(None)

    assert result.status == "empty"
    assert result.signal_count == 0


def test_required_signal_fields_exist():
    signal = adapt_transition_decision_to_signal(_decision("hard_cut_review"))

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
    signal = adapt_transition_decision_to_signal(_decision("j_cut_review"))

    metadata = signal["metadata"]

    assert metadata["transition_type"] == "j_cut_review"
    assert metadata["proposed_action"] == "review_transition"
    assert metadata["cut_list_action"] == "KEEP"
    assert metadata["duration_status"] == "duration_ok"
    assert metadata["murch_score"] == 0.75
    assert metadata["is_dialogue_context"] is True
    assert metadata["source_signal_ids"] == ["sig_1"]
    assert metadata["review_only"] is True


def test_adapter_result_roundtrip():
    result = adapt_transition_decision_report_to_signals(
        [
            _decision("hard_cut_review", "hard_1"),
            _decision("no_cut_protect", "protect_1"),
        ]
    )

    loaded = TransitionDecisionSignalAdapterResult.from_dict(result.to_dict())

    assert loaded.to_dict() == result.to_dict()


def test_report_container_and_plan_container_are_supported():
    report_result = adapt_transition_decision_report_to_signals(
        {
            "decisions": [
                _decision("hard_cut_review", "hard_1"),
            ]
        }
    )
    plan_result = adapt_transition_decision_report_to_signals(
        {
            "transition_decision_plan": {
                "decisions": [
                    _decision("censor_safe_keep", "censor_1"),
                ]
            }
        }
    )

    assert report_result.hard_cut_review_signal_count == 1
    assert plan_result.censor_safe_keep_signal_count == 1


def test_all_transition_signal_counts_are_refreshed():
    result = adapt_transition_decision_report_to_signals(
        [
            _decision("hard_cut_review", "hard_1"),
            _decision("j_cut_review", "j_1"),
            _decision("l_cut_review", "l_1"),
            _decision("quick_fade_review", "fade_1"),
            _decision("no_cut_protect", "protect_1"),
            _decision("censor_safe_keep", "censor_1"),
            _decision("technical_transition_review", "technical_1"),
            _decision("transition_unknown_review", "unknown_1"),
        ]
    )

    assert result.signal_count == 8
    assert result.hard_cut_review_signal_count == 1
    assert result.j_cut_review_signal_count == 1
    assert result.l_cut_review_signal_count == 1
    assert result.quick_fade_review_signal_count == 1
    assert result.no_cut_protect_signal_count == 1
    assert result.censor_safe_keep_signal_count == 1
    assert result.technical_review_signal_count == 1
    assert result.unknown_review_signal_count == 1


def test_no_forbidden_action_hints_are_emitted():
    result = adapt_transition_decision_report_to_signals(
        [
            _decision("hard_cut_review", "hard_1"),
            _decision("j_cut_review", "j_1"),
            _decision("l_cut_review", "l_1"),
            _decision("quick_fade_review", "fade_1"),
            _decision("no_cut_protect", "protect_1"),
            _decision("censor_safe_keep", "censor_1"),
            _decision("technical_transition_review", "technical_1"),
            _decision("transition_unknown_review", "unknown_1"),
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
