from pathlib import Path

from core.final_cut_list_signal_adapter import adapt_final_cut_list_report_to_signals


ROOT = Path(__file__).resolve().parents[1]

BLOCK5_PRODUCT_FILES = [
    ROOT / "core" / "segment_classifier.py",
    ROOT / "core" / "murch_scoring_system.py",
    ROOT / "core" / "cut_list_generator.py",
    ROOT / "core" / "clip_duration_optimizer.py",
    ROOT / "core" / "transition_decision_engine.py",
    ROOT / "core" / "continuity_checker.py",
    ROOT / "core" / "cut_list_finalizer.py",
    ROOT / "core" / "segment_classification_runner.py",
    ROOT / "core" / "murch_scoring_runner.py",
    ROOT / "core" / "cut_list_runner.py",
    ROOT / "core" / "clip_duration_runner.py",
    ROOT / "core" / "transition_decision_runner.py",
    ROOT / "core" / "continuity_check_runner.py",
    ROOT / "core" / "cut_list_finalizer_runner.py",
    ROOT / "core" / "segment_classification_signal_adapter.py",
    ROOT / "core" / "murch_scoring_signal_adapter.py",
    ROOT / "core" / "cut_list_signal_adapter.py",
    ROOT / "core" / "clip_duration_signal_adapter.py",
    ROOT / "core" / "transition_decision_signal_adapter.py",
    ROOT / "core" / "continuity_check_signal_adapter.py",
    ROOT / "core" / "final_cut_list_signal_adapter.py",
]

FORBIDDEN_EXECUTION_STRINGS = [
    "apply_final_cutlist",
    "execute_final_cutlist",
    "timeline_apply_now",
    "execute_cut",
    "render_now",
    "censor_now",
    "delete_segment",
    "hard_remove",
    "remove_now",
    "auto_remove",
    "auto_cut",
    "auto_trim",
    "auto_highlight",
    "auto_hook",
    "auto_mute",
    "apply_transition",
]

FORBIDDEN_TIMELINE_HIGHLIGHT_STRINGS = [
    "TimelineBuilder",
    "LongformTimelineBuilder",
    "timeline_builder",
    "longform_timeline_builder",
    "HighlightSelector",
    "highlight_selector",
]

FORBIDDEN_RENDER_FFMPEG_STRINGS = [
    "ffmpeg",
    "ensure_ffmpeg_on_path",
    "RenderProcessor",
    "render_processor",
    "FinalRenderDriver",
    "final_render_driver",
    "subprocess.run",
    "Popen(",
]

ALLOWED_REPORT_APPLY_NAMES = [
    "apply_cut_list_run_report_to_job",
    "apply_transition_decision_run_report_to_job",
    "apply_cut_list_finalization_run_report_to_job",
]

FINAL_ACTIONS = [
    "FINAL_KEEP_REVIEW",
    "FINAL_KEEP_HIGH_VALUE",
    "FINAL_TRIM_REVIEW",
    "FINAL_REMOVE_REVIEW",
    "FINAL_PROTECT",
    "FINAL_CENSOR_KEEP",
    "FINAL_TECHNICAL_REVIEW",
    "FINAL_BLOCKED_BY_CONTINUITY",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _scrub_allowed_report_apply_names(text: str) -> str:
    scrubbed = text
    for allowed in ALLOWED_REPORT_APPLY_NAMES:
        scrubbed = scrubbed.replace(allowed, "")
        scrubbed = scrubbed.replace(allowed.lower(), "")
    return scrubbed


def _final_item(action: str, index: int) -> dict:
    start = float(index * 10)
    return {
        "final_item_id": f"final_item_{index}",
        "source_item_id": f"cut_item_{index}",
        "segment_id": f"segment_{index}",
        "start_seconds": start,
        "end_seconds": start + 4.0,
        "center_seconds": start + 2.0,
        "duration_seconds": 4.0,
        "final_action": action,
        "final_confidence": 0.85,
        "priority": "high" if action in {"FINAL_PROTECT", "FINAL_CENSOR_KEEP"} else "medium",
        "reason": f"{action.lower()}_requires_review",
        "decision_basis": {"review_only": True},
        "metadata": {"audit": True},
    }


def test_block5_product_files_do_not_bind_timeline_or_highlight_selector() -> None:
    for path in BLOCK5_PRODUCT_FILES:
        text = _read(path)
        for forbidden in FORBIDDEN_TIMELINE_HIGHLIGHT_STRINGS:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_block5_product_files_do_not_call_ffmpeg_or_render_drivers() -> None:
    for path in BLOCK5_PRODUCT_FILES:
        text = _read(path)
        lowered = text.lower()
        for forbidden in FORBIDDEN_RENDER_FFMPEG_STRINGS:
            haystack = lowered if forbidden.islower() else text
            needle = forbidden if forbidden.islower() else forbidden
            assert needle not in haystack, f"{forbidden} found in {path}"


def test_block5_product_files_do_not_contain_execution_strings() -> None:
    for path in BLOCK5_PRODUCT_FILES:
        text = _scrub_allowed_report_apply_names(_read(path).lower())
        for forbidden in FORBIDDEN_EXECUTION_STRINGS:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_finalizer_action_hints_remain_review_protect_preserve_or_block() -> None:
    result = adapt_final_cut_list_report_to_signals(
        {
            "status": "ok",
            "source": "cut_list_finalizer",
            "final_items": [
                _final_item(action, index)
                for index, action in enumerate(FINAL_ACTIONS, start=1)
            ],
        }
    )

    assert result.status == "ok"
    assert result.signals

    allowed_prefixes = ("review_", "protect_", "preserve_", "block_")
    for signal in result.signals:
        action_hint = signal["action_hint"]
        assert action_hint.startswith(allowed_prefixes), signal
        for forbidden in FORBIDDEN_EXECUTION_STRINGS:
            assert forbidden not in action_hint.lower(), signal
        assert signal["metadata"]["review_only"] is True


def test_final_review_actions_do_not_become_execution_hints() -> None:
    result = adapt_final_cut_list_report_to_signals(
        {
            "final_items": [
                _final_item("FINAL_REMOVE_REVIEW", 1),
                _final_item("FINAL_TRIM_REVIEW", 2),
                _final_item("FINAL_CENSOR_KEEP", 3),
                _final_item("FINAL_BLOCKED_BY_CONTINUITY", 4),
            ]
        }
    )
    by_type = {signal["signal_type"]: signal for signal in result.signals}

    remove_signal = by_type["final_cut_list_remove_review"]
    trim_signal = by_type["final_cut_list_trim_review"]
    censor_signal = by_type["final_cut_list_censor_keep"]
    blocked_signal = by_type["final_cut_list_blocked_by_continuity"]

    assert remove_signal["action_hint"] == "review_final_remove_candidate"
    assert remove_signal["action_hint"] not in {
        "remove_now",
        "hard_remove",
        "auto_remove",
        "delete_segment",
    }

    assert trim_signal["action_hint"] == "review_final_trim_candidate"
    assert trim_signal["action_hint"] not in {"auto_trim", "apply_cut"}

    assert censor_signal["action_hint"] == "preserve_final_segment_for_censor_sfx"
    assert censor_signal["action_hint"] != "censor_now"

    assert blocked_signal["action_hint"] == "block_final_cutlist_until_review"
    assert blocked_signal["action_hint"] not in {
        "timeline_apply_now",
        "execute_cut",
        "execute_final_cutlist",
    }
