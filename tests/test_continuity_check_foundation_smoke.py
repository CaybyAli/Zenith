from pathlib import Path

from core.continuity_checker import run_continuity_check
from models.continuity_check import ContinuityCheckResult, ContinuityIssue


ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    ROOT / "models" / "continuity_check.py",
    ROOT / "core" / "continuity_checker.py",
    ROOT / "tests" / "test_continuity_check_foundation_smoke.py",
]

PRODUCT_FILES = [
    ROOT / "models" / "continuity_check.py",
    ROOT / "core" / "continuity_checker.py",
]

FORBIDDEN_STRINGS = [
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


def _decision(
    transition_type="hard_cut_review",
    start=0.0,
    end=4.0,
    **extra,
):
    data = {
        "decision_id": "decision_1",
        "source_item_id": "item_1",
        "segment_id": "seg_1",
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": (start + end) / 2.0,
        "duration_seconds": end - start,
        "transition_type": transition_type,
        "transition_confidence": 0.85,
        "priority": "medium",
        "proposed_action": "review_transition",
        "cut_list_action": "KEEP",
        "duration_status": "duration_ok",
        "warnings": [],
        "errors": [],
        "metadata": {"test": True},
    }
    data.update(extra)
    return data


def _cut_item(
    item_id="item_1",
    start=0.0,
    end=4.0,
    action="KEEP",
    **extra,
):
    data = {
        "item_id": item_id,
        "segment_id": f"seg_{item_id}",
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": (start + end) / 2.0,
        "duration_seconds": end - start,
        "proposed_action": action,
        "action_confidence": 0.8,
        "priority": "medium",
    }
    data.update(extra)
    return data


def _signal(signal_type, center=2.0, signal_id=None):
    return {
        "signal_id": signal_id or f"sig_{signal_type}",
        "signal_type": signal_type,
        "center_seconds": center,
        "confidence": 0.9,
        "priority": "high",
    }


def _issue_types(result):
    return {issue.issue_type for issue in result.issues}


def test_continuity_issue_roundtrip():
    issue = ContinuityIssue(
        issue_id="issue_1",
        source_item_id="item_1",
        segment_id="seg_1",
        start_seconds=1.0,
        end_seconds=2.0,
        center_seconds=1.5,
        duration_seconds=1.0,
        issue_type="sentence_break_risk",
        severity="high",
        confidence=0.9,
        priority="high",
        is_blocking=True,
        is_protected_context=True,
        requires_review=True,
        recommendation="review_sentence_boundary_continuity",
        reason="test",
        evidence={"review_only": True},
        source_signal_ids=["sig_1"],
        warnings=["warn"],
        errors=["err"],
        metadata={"source": "test"},
    )

    assert ContinuityIssue.from_dict(issue.to_dict()).to_dict() == issue.to_dict()


def test_continuity_check_result_roundtrip():
    issue = ContinuityIssue(
        issue_id="issue_1",
        issue_type="context_jump_risk",
        severity="high",
        confidence=0.8,
        priority="high",
        recommendation="review_context_jump_continuity",
    )
    result = ContinuityCheckResult(
        status="completed_with_warnings",
        issues=[issue],
        recommendation="review_context_jump_continuity",
        metadata={"source": "test"},
    )

    assert ContinuityCheckResult.from_dict(result.to_dict()).to_dict() == result.to_dict()


def test_no_inputs_are_skipped():
    result = run_continuity_check()

    assert result.status == "skipped_no_transition_decisions"
    assert result.issue_count == 0
    assert result.recommendation == "continuity_check_skipped_no_inputs"


def test_hard_cut_with_sentence_protection_creates_sentence_break_risk():
    result = run_continuity_check(
        transition_decisions=[_decision("hard_cut_review")],
        unified_signals=[_signal("sentence_boundary_protection")],
    )

    assert "sentence_break_risk" in _issue_types(result)
    assert result.sentence_break_risk_count == 1


def test_question_answer_context_with_remove_risk_creates_context_jump_risk():
    result = run_continuity_check(
        transition_decisions=[_decision("hard_cut_review")],
        cut_list_items=[_cut_item(action="REVIEW_REMOVE")],
        unified_signals=[_signal("interaction_question_answer_segment")],
    )

    assert "context_jump_risk" in _issue_types(result)
    assert result.context_jump_risk_count >= 1


def test_censor_keep_with_trim_or_remove_risk_creates_censor_context_risk():
    result = run_continuity_check(
        transition_decisions=[_decision("hard_cut_review")],
        cut_list_items=[_cut_item(action="REVIEW_TRIM")],
        unified_signals=[_signal("profanity_censor_sfx_required")],
    )

    assert "censor_context_risk" in _issue_types(result)
    assert result.censor_context_risk_count == 1


def test_invalid_timing_creates_invalid_timing_issue():
    result = run_continuity_check(
        transition_decisions=[_decision("hard_cut_review", start=5.0, end=3.0)],
    )

    assert "invalid_timing" in _issue_types(result)
    assert result.timing_issue_count >= 1


def test_overlapping_items_create_overlap_risk():
    result = run_continuity_check(
        cut_list_items=[
            _cut_item("item_1", 0.0, 5.0),
            _cut_item("item_2", 4.0, 8.0),
        ],
    )

    assert "overlap_risk" in _issue_types(result)
    assert result.timing_issue_count >= 1


def test_large_gap_between_keep_items_creates_gap_risk():
    result = run_continuity_check(
        cut_list_items=[
            _cut_item("item_1", 0.0, 2.0),
            _cut_item("item_2", 5.0, 7.0),
        ],
    )

    assert "gap_risk" in _issue_types(result)
    assert result.timing_issue_count >= 1


def test_no_cut_protect_with_hard_cut_review_creates_transition_conflict():
    result = run_continuity_check(
        transition_decisions=[_decision("hard_cut_review")],
        unified_signals=[_signal("transition_no_cut_protect")],
    )

    assert "transition_conflict" in _issue_types(result)
    assert result.transition_conflict_count == 1


def test_technical_warning_creates_technical_continuity_risk():
    result = run_continuity_check(
        transition_decisions=[_decision("quick_fade_review")],
        unified_signals=[_signal("stutter_segment_candidate")],
    )

    assert "technical_continuity_risk" in _issue_types(result)
    assert result.technical_issue_count >= 1


def test_safe_inputs_are_ok_and_continuity_ok():
    result = run_continuity_check(
        transition_decisions=[_decision("hard_cut_review")],
        cut_list_items=[_cut_item(action="KEEP")],
    )

    assert result.status == "ok"
    assert result.issue_count == 0
    assert result.recommendation == "continuity_ok"


def test_product_files_have_no_forbidden_execution_strings():
    for path in PRODUCT_FILES:
        text = path.read_text(encoding="utf-8").lower()
        for forbidden in FORBIDDEN_STRINGS:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_new_files_have_no_bom_and_end_with_newline():
    for file_path in NEW_FILES:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
