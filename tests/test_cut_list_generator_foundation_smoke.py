from pathlib import Path

from core.cut_list_generator import (
    build_cut_list_item,
    clamp_score,
    generate_cut_list_plan,
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
    CUT_LIST_STATUS_SKIPPED_NO_SEGMENTS,
    CutListItem,
    CutListPlan,
)


ROOT = Path(__file__).resolve().parents[1]


def test_cut_list_item_roundtrip():
    item = CutListItem(
        item_id="item_1",
        segment_id="seg_1",
        proposed_action=CUT_LIST_ACTION_KEEP,
        action_confidence=0.9,
        priority="high",
        reason="test",
    )

    restored = CutListItem.from_dict(item.to_dict())

    assert restored.item_id == "item_1"
    assert restored.segment_id == "seg_1"
    assert restored.proposed_action == CUT_LIST_ACTION_KEEP
    assert restored.action_confidence == 0.9


def test_cut_list_plan_roundtrip():
    plan = CutListPlan(
        status="ok",
        items=[
            CutListItem(item_id="item_1", proposed_action=CUT_LIST_ACTION_KEEP),
            CutListItem(item_id="item_2", proposed_action=CUT_LIST_ACTION_REVIEW_TRIM),
        ],
        recommendation="test",
    )
    plan.refresh_counts()

    restored = CutListPlan.from_dict(plan.to_dict())

    assert restored.status == "ok"
    assert restored.item_count == 2
    assert restored.keep_count == 1
    assert restored.review_trim_count == 1


def test_no_segments_returns_skipped_no_segments():
    plan = generate_cut_list_plan(segment_classifications=[])

    assert plan.status == CUT_LIST_STATUS_SKIPPED_NO_SEGMENTS
    assert plan.item_count == 0
    assert plan.recommendation == "cut_list_skipped_no_segments"


def test_high_murch_highlight_becomes_keep_or_review_keep():
    plan = generate_cut_list_plan(
        segment_classifications=[
            {
                "segment_id": "seg_high",
                "segment_type": "highlight",
                "content_value_score": 0.9,
            }
        ],
        murch_scores=[
            {
                "segment_id": "seg_high",
                "murch_score": 0.95,
                "tier": "high",
            }
        ],
    )

    assert plan.item_count == 1
    assert plan.items[0].proposed_action in {
        CUT_LIST_ACTION_KEEP,
        CUT_LIST_ACTION_REVIEW_KEEP,
    }


def test_protected_context_becomes_protect():
    item = build_cut_list_item(
        segment={
            "segment_id": "seg_protected",
            "segment_type": "protected_context",
            "is_protected": True,
        },
        murch_score={"segment_id": "seg_protected", "murch_score": 0.5},
    )

    assert item.proposed_action == CUT_LIST_ACTION_PROTECT
    assert item.is_protected is True
    assert item.is_keep_candidate is True


def test_censor_required_becomes_censor_keep():
    item = build_cut_list_item(
        segment={
            "segment_id": "seg_censor",
            "segment_type": "censor_required_segment",
            "censor_required": True,
        },
        murch_score={"segment_id": "seg_censor", "murch_score": 0.5},
    )

    assert item.proposed_action == CUT_LIST_ACTION_CENSOR_KEEP
    assert item.censor_required is True
    assert item.is_keep_candidate is True


def test_dead_candidate_becomes_review_only():
    item = build_cut_list_item(
        segment={
            "segment_id": "seg_dead",
            "segment_type": "dead_candidate",
            "content_value_score": 0.1,
        },
        murch_score={"segment_id": "seg_dead", "murch_score": 0.1},
    )

    assert item.proposed_action in {
        CUT_LIST_ACTION_REVIEW_REMOVE,
        CUT_LIST_ACTION_REVIEW_TRIM,
    }
    assert item.proposed_action != "REMOVE"
    assert item.proposed_action != "CUT"


def test_filler_becomes_review_trim():
    item = build_cut_list_item(
        segment={
            "segment_id": "seg_filler",
            "segment_type": "filler",
            "content_value_score": 0.2,
        },
        murch_score={"segment_id": "seg_filler", "murch_score": 0.3},
    )

    assert item.proposed_action == CUT_LIST_ACTION_REVIEW_TRIM
    assert item.is_trim_candidate is True


def test_technical_warning_becomes_technical_review():
    item = build_cut_list_item(
        segment={
            "segment_id": "seg_technical",
            "segment_type": "technical_warning",
            "technical_warning": True,
        },
        murch_score={"segment_id": "seg_technical", "murch_score": 0.5},
    )

    assert item.proposed_action == CUT_LIST_ACTION_TECHNICAL_REVIEW
    assert item.is_technical_review is True


def test_unknown_becomes_unknown_review():
    item = build_cut_list_item(
        segment={
            "segment_id": "seg_unknown",
            "segment_type": "unknown",
        },
        murch_score={"segment_id": "seg_unknown", "murch_score": 0.3},
    )

    assert item.proposed_action == CUT_LIST_ACTION_UNKNOWN_REVIEW


def test_score_clamping():
    assert clamp_score(-1) == 0.0
    assert clamp_score(0.5) == 0.5
    assert clamp_score(2) == 1.0
    assert clamp_score("bad") == 0.0


def test_no_direct_action_names_are_created():
    plan = generate_cut_list_plan(
        segment_classifications=[
            {"segment_id": "seg_1", "segment_type": "dead_candidate"},
            {"segment_id": "seg_2", "segment_type": "highlight"},
            {"segment_id": "seg_3", "segment_type": "censor_required_segment"},
        ],
        murch_scores=[
            {"segment_id": "seg_1", "murch_score": 0.1},
            {"segment_id": "seg_2", "murch_score": 0.9},
            {"segment_id": "seg_3", "murch_score": 0.5},
        ],
    )

    forbidden_actions = {
        "REMOVE",
        "CUT",
        "DELETE",
        "MUTE",
        "HIGHLIGHT",
    }

    for item in plan.items:
        assert item.proposed_action not in forbidden_actions


def test_foundation_product_files_do_not_contain_blocked_operational_terms():
    files = [
        ROOT / "models" / "cut_list.py",
        ROOT / "core" / "cut_list_generator.py",
    ]

    forbidden = [
        "TimelineBuilder",
        "HighlightSelector",
        "FFmpeg",
        "CUT_NOW",
        "REMOVE_NOW",
        "MUTE_NOW",
        "DELETE_NOW",
        "CENSOR_NOW",
        "r" + "ender_now",
    ]

    for path in files:
        text = path.read_text(encoding="utf-8")
        for word in forbidden:
            assert word not in text


def test_new_files_have_no_bom_and_end_with_newline():
    files = [
        ROOT / "models" / "cut_list.py",
        ROOT / "core" / "cut_list_generator.py",
        ROOT / "tests" / "test_cut_list_generator_foundation_smoke.py",
    ]

    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert raw.endswith(b"\n")
