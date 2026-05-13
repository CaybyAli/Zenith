from pathlib import Path

from core.cut_list_finalizer import finalize_cut_list
from models.final_cut_list import (
    FINAL_ACTION_BLOCKED_BY_CONTINUITY,
    FINAL_ACTION_CENSOR_KEEP,
    FINAL_ACTION_KEEP_HIGH_VALUE,
    FINAL_ACTION_KEEP_REVIEW,
    FINAL_ACTION_PROTECT,
    FINAL_ACTION_REMOVE_REVIEW,
    FINAL_ACTION_TECHNICAL_REVIEW,
    FINAL_ACTION_TRIM_REVIEW,
    FINAL_ACTION_UNKNOWN_REVIEW,
    FinalCutListItem,
    FinalCutListPlan,
)


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_FILES = [
    ROOT / "models" / "final_cut_list.py",
    ROOT / "core" / "cut_list_finalizer.py",
]
TEST_FILE = ROOT / "tests" / "test_cut_list_finalizer_foundation_smoke.py"


def _item(action: str = "UNKNOWN_REVIEW", **overrides):
    data = {
        "item_id": "item_1",
        "segment_id": "seg_1",
        "start_seconds": 1.0,
        "end_seconds": 4.0,
        "proposed_action": action,
        "action_confidence": 0.7,
    }
    data.update(overrides)
    return data


def _first_action(**kwargs) -> str:
    plan = finalize_cut_list(**kwargs)
    assert plan.final_items
    return plan.final_items[0].final_action


def test_final_cut_list_item_roundtrip():
    item = FinalCutListItem(
        final_item_id="final_1",
        source_item_id="item_1",
        segment_id="seg_1",
        start_seconds=1.0,
        end_seconds=2.0,
        center_seconds=1.5,
        duration_seconds=1.0,
        final_action=FINAL_ACTION_KEEP_REVIEW,
        final_confidence=0.5,
        priority="medium",
        reason="review",
        decision_basis={"review_only": True},
        source_signal_ids=["sig_1"],
        warnings=["warn"],
        metadata={"k": "v"},
    )

    assert FinalCutListItem.from_dict(item.to_dict()).to_dict() == item.to_dict()


def test_final_cut_list_plan_roundtrip():
    plan = FinalCutListPlan(
        status="ok",
        final_items=[
            FinalCutListItem(
                final_item_id="final_1",
                final_action=FINAL_ACTION_PROTECT,
                is_protected=True,
            )
        ],
        recommendation="final_cut_list_ready_for_review",
    )

    assert FinalCutListPlan.from_dict(plan.to_dict()).to_dict() == plan.to_dict()


def test_no_inputs_skips_safely():
    plan = finalize_cut_list()

    assert plan.status == "skipped_no_inputs"
    assert plan.final_item_count == 0
    assert plan.recommendation == "final_cut_list_skipped_no_inputs"


def test_keep_high_murch_becomes_high_value_review():
    action = _first_action(
        cut_list_items=[_item("KEEP")],
        murch_scores=[{"segment_id": "seg_1", "murch_score": 0.9}],
    )

    assert action == FINAL_ACTION_KEEP_HIGH_VALUE


def test_review_keep_remains_review_keep():
    assert _first_action(cut_list_items=[_item("REVIEW_KEEP")]) == (
        FINAL_ACTION_KEEP_REVIEW
    )


def test_review_trim_and_too_long_become_trim_review():
    assert _first_action(cut_list_items=[_item("REVIEW_TRIM")]) == (
        FINAL_ACTION_TRIM_REVIEW
    )
    assert _first_action(
        cut_list_items=[_item("REVIEW_KEEP")],
        clip_duration_recommendations=[
            {"source_item_id": "item_1", "duration_status": "too_long_review"}
        ],
    ) == FINAL_ACTION_TRIM_REVIEW


def test_review_remove_stays_review_only():
    plan = finalize_cut_list(cut_list_items=[_item("REVIEW_REMOVE")])
    item = plan.final_items[0]

    assert item.final_action == FINAL_ACTION_REMOVE_REVIEW
    assert "REMOVE_NOW" not in item.to_dict().values()
    assert item.is_remove_candidate is True


def test_protect_and_censor_keep_are_hard_protected():
    assert _first_action(cut_list_items=[_item("PROTECT")]) == FINAL_ACTION_PROTECT
    assert _first_action(cut_list_items=[_item("CENSOR_KEEP")]) == (
        FINAL_ACTION_CENSOR_KEEP
    )


def test_technical_risk_becomes_technical_review():
    assert _first_action(cut_list_items=[_item("TECHNICAL_REVIEW")]) == (
        FINAL_ACTION_TECHNICAL_REVIEW
    )


def test_continuity_blocking_wins_over_other_evidence():
    action = _first_action(
        cut_list_items=[_item("KEEP")],
        continuity_issues=[
            {
                "issue_id": "issue_1",
                "source_item_id": "item_1",
                "issue_type": "context_jump_risk",
                "severity": "critical",
                "is_blocking": True,
            }
        ],
    )

    assert action == FINAL_ACTION_BLOCKED_BY_CONTINUITY


def test_invalid_timing_is_not_executable():
    action = _first_action(
        cut_list_items=[
            _item("REVIEW_TRIM", start_seconds=5.0, end_seconds=4.0)
        ],
    )

    assert action in {
        FINAL_ACTION_BLOCKED_BY_CONTINUITY,
        FINAL_ACTION_TECHNICAL_REVIEW,
    }


def test_unknown_becomes_unknown_review():
    assert _first_action(cut_list_items=[_item("UNKNOWN_REVIEW")]) == (
        FINAL_ACTION_UNKNOWN_REVIEW
    )


def test_product_files_do_not_contain_execution_terms():
    forbidden = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "auto_cut",
        "auto_trim",
        "auto_transition",
        "auto_fade",
        "render_now",
        "execute_cut",
        "apply_final_cutlist",
        "execute_final_cutlist",
    ]

    for path in PRODUCT_FILES:
        text = path.read_text(encoding="utf-8").lower()
        for word in forbidden:
            assert word not in text, f"{word} found in {path}"


def test_no_bom_and_newline():
    for path in PRODUCT_FILES + [TEST_FILE]:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path
