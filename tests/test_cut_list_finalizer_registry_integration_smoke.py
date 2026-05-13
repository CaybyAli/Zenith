from pathlib import Path

from core.unified_edit_signal_registry import build_unified_edit_signal_result


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_FILE = ROOT / "core" / "unified_edit_signal_registry.py"
ADAPTER_FILE = ROOT / "core" / "final_cut_list_signal_adapter.py"
TEST_FILE = ROOT / "tests" / "test_cut_list_finalizer_registry_integration_smoke.py"

FINAL_ACTIONS = [
    "FINAL_KEEP_REVIEW",
    "FINAL_KEEP_HIGH_VALUE",
    "FINAL_TRIM_REVIEW",
    "FINAL_REMOVE_REVIEW",
    "FINAL_PROTECT",
    "FINAL_CENSOR_KEEP",
    "FINAL_TECHNICAL_REVIEW",
    "FINAL_BLOCKED_BY_CONTINUITY",
    "FINAL_UNKNOWN_REVIEW",
]

FINAL_SIGNAL_TYPES = [
    "final_cut_list_keep_review",
    "final_cut_list_keep_high_value",
    "final_cut_list_trim_review",
    "final_cut_list_remove_review",
    "final_cut_list_protect",
    "final_cut_list_censor_keep",
    "final_cut_list_technical_review",
    "final_cut_list_blocked_by_continuity",
    "final_cut_list_unknown_review",
]


def _job_with_final_items() -> dict:
    final_items = []
    for index, action in enumerate(FINAL_ACTIONS, start=1):
        final_items.append(
            {
                "final_item_id": f"final_{index}",
                "source_item_id": f"item_{index}",
                "segment_id": f"seg_{index}",
                "start_seconds": float(index * 10),
                "end_seconds": float(index * 10 + 2),
                "final_action": action,
                "final_confidence": 0.8,
                "priority": "high",
                "reason": "review",
            }
        )

    return {
        "final_cut_list_report": {
            "status": "ok",
            "source": "cut_list_finalizer",
            "final_items": final_items,
        }
    }


def test_registry_collects_cut_list_finalizer_source_counts():
    result = build_unified_edit_signal_result(_job_with_final_items())

    assert result.source_counts["cut_list_finalizer"] == len(FINAL_ACTIONS)


def test_registry_collects_all_final_cut_list_type_counts():
    result = build_unified_edit_signal_result(_job_with_final_items())

    for signal_type in FINAL_SIGNAL_TYPES:
        assert result.type_counts[signal_type] == 1


def test_registry_imports_adapter_and_source_constant():
    text = REGISTRY_FILE.read_text(encoding="utf-8")

    assert "adapt_final_cut_list_report_to_signals" in text
    assert 'SOURCE_CUT_LIST_FINALIZER = "cut_list_finalizer"' in text
    assert "final_cut_list_report" in text
    assert "final_cut_list_items" in text
    assert "source_counts[SOURCE_CUT_LIST_FINALIZER]" in text


def test_registry_keeps_existing_sources():
    text = REGISTRY_FILE.read_text(encoding="utf-8")
    existing_sources = [
        "continuity_check",
        "transition_decision",
        "clip_duration_optimizer",
        "cut_list_generator",
        "murch_scoring",
        "segment_classifier",
        "content_value",
        "profanity_censor",
        "dead_content",
        "sentence_boundary",
        "keyword_emotion",
        "interaction_classification",
        "scene_change",
        "motion_analysis",
        "face_reaction",
        "stutter_detection",
        "screen_content",
        "visual_energy",
    ]

    for source in existing_sources:
        assert source in text


def test_registry_and_adapter_do_not_contain_execution_terms():
    forbidden = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "auto_cut",
        "auto_trim",
        "auto_transition",
        "auto_fade",
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

    for path in [REGISTRY_FILE, ADAPTER_FILE]:
        text = path.read_text(encoding="utf-8").lower()
        for word in forbidden:
            assert word not in text, f"{word} found in {path}"


def test_no_bom_and_newline():
    for path in [REGISTRY_FILE, ADAPTER_FILE, TEST_FILE]:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path
