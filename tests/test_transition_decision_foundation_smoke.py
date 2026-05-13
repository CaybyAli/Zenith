from pathlib import Path

from core.transition_decision_engine import build_transition_decision_plan
from models.transition_decision import TransitionDecision, TransitionDecisionPlan


ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    ROOT / "models" / "transition_decision.py",
    ROOT / "core" / "transition_decision_engine.py",
    ROOT / "tests" / "test_transition_decision_foundation_smoke.py",
]

FORBIDDEN_ACTION_WORDS = [
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

FORBIDDEN_ENGINE_WORDS = [
    "TimelineBuilder",
    "LongformTimelineBuilder",
    "HighlightSelector",
    "highlight_selector",
    "ffmpeg",
    "render_video",
]


def test_transition_decision_roundtrip():
    decision = TransitionDecision(
        decision_id="decision_1",
        source_item_id="item_1",
        segment_id="seg_1",
        start_seconds=1.0,
        end_seconds=5.0,
        center_seconds=3.0,
        duration_seconds=4.0,
        transition_type="hard_cut_review",
        transition_confidence=0.8,
        priority="medium",
        proposed_action="review_transition",
        cut_list_action="KEEP",
        duration_status="duration_ok",
        murch_score=0.75,
        is_scene_change_aligned=True,
        reason="scene_or_candidate_supports_hard_cut_review",
        decision_basis={"review_only": True},
        source_signal_ids=["sig_1"],
        warnings=[],
        errors=[],
        metadata={"source": "test", "review_only": True},
    )

    loaded = TransitionDecision.from_dict(decision.to_dict())

    assert loaded.to_dict() == decision.to_dict()


def test_transition_decision_plan_roundtrip():
    decision = TransitionDecision(
        decision_id="decision_1",
        transition_type="hard_cut_review",
    )
    plan = TransitionDecisionPlan(
        status="ok",
        decisions=[decision],
        decision_count=1,
        hard_cut_review_count=1,
        recommendation="transition_decision_review_plan_ready",
        metadata={"review_only": True},
    )

    loaded = TransitionDecisionPlan.from_dict(plan.to_dict())

    assert loaded.to_dict() == plan.to_dict()


def test_no_recommendations_and_no_items_returns_skipped():
    plan = build_transition_decision_plan()

    assert plan.status == "skipped_no_clip_duration_recommendations"
    assert plan.decision_count == 0
    assert plan.recommendation == "transition_decision_skipped_no_inputs"


def test_scene_hard_cut_signal_returns_hard_cut_review():
    plan = build_transition_decision_plan(
        clip_duration_recommendations=[
            {
                "recommendation_id": "rec_1",
                "source_item_id": "item_1",
                "start_seconds": 10.0,
                "end_seconds": 12.0,
                "duration_status": "duration_ok",
                "confidence": 0.8,
            }
        ],
        unified_signals=[
            {
                "signal_id": "scene_1",
                "signal_type": "scene_hard_cut_point",
                "center_seconds": 11.0,
                "confidence": 0.9,
            }
        ],
    )

    decision = plan.decisions[0]

    assert decision.transition_type == "hard_cut_review"
    assert decision.is_scene_change_aligned is True
    assert decision.proposed_action == "review_transition"


def test_soft_transition_signal_returns_quick_fade_review():
    plan = build_transition_decision_plan(
        clip_duration_recommendations=[
            {
                "recommendation_id": "rec_1",
                "source_item_id": "item_1",
                "start_seconds": 20.0,
                "end_seconds": 22.0,
                "duration_status": "duration_ok",
                "confidence": 0.8,
            }
        ],
        unified_signals=[
            {
                "signal_id": "scene_soft_1",
                "signal_type": "scene_soft_transition",
                "center_seconds": 21.0,
                "confidence": 0.9,
            }
        ],
    )

    assert plan.decisions[0].transition_type == "quick_fade_review"


def test_sentence_protection_returns_no_cut_protect():
    plan = build_transition_decision_plan(
        clip_duration_recommendations=[
            {
                "recommendation_id": "rec_1",
                "source_item_id": "item_1",
                "start_seconds": 30.0,
                "end_seconds": 34.0,
                "duration_status": "duration_ok",
            }
        ],
        unified_signals=[
            {
                "signal_id": "sentence_1",
                "signal_type": "sentence_boundary_protection",
                "center_seconds": 32.0,
            }
        ],
    )

    decision = plan.decisions[0]

    assert decision.transition_type == "no_cut_protect"
    assert decision.is_protected is True
    assert decision.priority == "high"


def test_dialogue_context_returns_j_cut_review():
    plan = build_transition_decision_plan(
        clip_duration_recommendations=[
            {
                "recommendation_id": "rec_1",
                "source_item_id": "item_1",
                "start_seconds": 40.0,
                "end_seconds": 45.0,
                "duration_status": "duration_ok",
            }
        ],
        cut_list_items=[
            {
                "item_id": "item_1",
                "start_seconds": 40.0,
                "end_seconds": 45.0,
                "proposed_action": "KEEP",
            }
        ],
        unified_signals=[
            {
                "signal_id": "dialogue_1",
                "signal_type": "interaction_dialogue_segment",
                "center_seconds": 42.0,
            }
        ],
    )

    decision = plan.decisions[0]

    assert decision.transition_type == "j_cut_review"
    assert decision.is_dialogue_context is True


def test_dialogue_review_keep_returns_l_cut_review():
    plan = build_transition_decision_plan(
        clip_duration_recommendations=[
            {
                "recommendation_id": "rec_1",
                "source_item_id": "item_1",
                "start_seconds": 50.0,
                "end_seconds": 55.0,
                "duration_status": "duration_ok",
            }
        ],
        cut_list_items=[
            {
                "item_id": "item_1",
                "start_seconds": 50.0,
                "end_seconds": 55.0,
                "proposed_action": "REVIEW_KEEP",
            }
        ],
        unified_signals=[
            {
                "signal_id": "dialogue_1",
                "signal_type": "interaction_question_answer_segment",
                "center_seconds": 52.0,
            }
        ],
    )

    assert plan.decisions[0].transition_type == "l_cut_review"


def test_censor_keep_returns_censor_safe_keep():
    plan = build_transition_decision_plan(
        clip_duration_recommendations=[
            {
                "recommendation_id": "rec_1",
                "source_item_id": "item_1",
                "start_seconds": 60.0,
                "end_seconds": 63.0,
                "duration_status": "censor_keep_duration",
                "is_censor_keep": True,
            }
        ],
    )

    decision = plan.decisions[0]

    assert decision.transition_type == "censor_safe_keep"
    assert decision.is_censor_keep is True
    assert decision.priority == "high"


def test_technical_warning_returns_technical_transition_review():
    plan = build_transition_decision_plan(
        clip_duration_recommendations=[
            {
                "recommendation_id": "rec_1",
                "source_item_id": "item_1",
                "start_seconds": 70.0,
                "end_seconds": 60.0,
                "duration_status": "invalid_timing_review",
                "is_invalid_timing": True,
            }
        ],
    )

    decision = plan.decisions[0]

    assert decision.transition_type == "technical_transition_review"
    assert decision.is_technical_review is True
    assert decision.priority == "high"


def test_beat_aligned_returns_hard_cut_or_quick_fade_review():
    plan = build_transition_decision_plan(
        clip_duration_recommendations=[
            {
                "recommendation_id": "rec_1",
                "source_item_id": "item_1",
                "start_seconds": 80.0,
                "end_seconds": 82.0,
                "duration_status": "duration_ok",
            }
        ],
        unified_signals=[
            {
                "signal_id": "beat_1",
                "signal_type": "beat_strong_sync_point",
                "center_seconds": 81.0,
            }
        ],
    )

    decision = plan.decisions[0]

    assert decision.transition_type in {"hard_cut_review", "quick_fade_review"}
    assert decision.is_beat_aligned is True


def test_unknown_returns_transition_unknown_review():
    plan = build_transition_decision_plan(
        clip_duration_recommendations=[
            {
                "recommendation_id": "rec_unknown",
                "source_item_id": "item_unknown",
                "start_seconds": 90.0,
                "end_seconds": 92.0,
                "duration_status": "mystery_status",
            }
        ]
    )

    assert plan.decisions[0].transition_type == "transition_unknown_review"


def test_transition_decision_does_not_emit_automatic_cut_render_or_timeline_actions():
    plan = build_transition_decision_plan(
        clip_duration_recommendations=[
            {
                "recommendation_id": "rec_1",
                "source_item_id": "item_1",
                "start_seconds": 1.0,
                "end_seconds": 5.0,
                "duration_status": "duration_ok",
            }
        ]
    )

    dumped = str(plan.to_dict()).lower()

    for forbidden in FORBIDDEN_ACTION_WORDS:
        assert forbidden not in dumped


def test_new_product_files_do_not_contain_timeline_render_words():
    product_files = [
        ROOT / "models" / "transition_decision.py",
        ROOT / "core" / "transition_decision_engine.py",
    ]

    for file_path in product_files:
        text = file_path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_ENGINE_WORDS:
            assert forbidden not in text


def test_new_files_have_no_bom_and_end_with_newline():
    for file_path in NEW_FILES:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
