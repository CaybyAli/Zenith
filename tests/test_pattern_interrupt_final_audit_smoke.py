from __future__ import annotations

from pathlib import Path

from models.pattern_interrupt import PatternInterruptReport


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "pattern_interrupt.py",
    ROOT / "core" / "pattern_interrupt_engine.py",
    ROOT / "core" / "pattern_interrupt_runner.py",
    ROOT / "core" / "pattern_interrupt_signal_adapter.py",
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
    ROOT / "models" / "job.py",
]

PATTERN_INTERRUPT_FULL_SCAN_FILES = {
    ROOT / "models" / "pattern_interrupt.py",
    ROOT / "core" / "pattern_interrupt_engine.py",
    ROOT / "core" / "pattern_interrupt_runner.py",
    ROOT / "core" / "pattern_interrupt_signal_adapter.py",
}

FORBIDDEN_MEDIA_TOKENS = [
    "subprocess",
    "os.system",
    "ffmpeg",
    "render_video",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "delete_media",
    "remove_file",
    "trim_now",
    "censor_now",
    "mute_track",
    "apply_timeline",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "apply_pattern",
    "execute_pattern",
    "insert_zoom",
    "apply_zoom",
    "insert_text_overlay",
    "apply_text_overlay",
    "insert_sfx",
    "apply_sfx",
    "add_overlay",
    "add_effect",
]

ALLOWED_SAFETY_FIELD_TOKENS = [
    "can_insert_zoom",
    "pattern_interrupt_can_insert_zoom",
    "can_insert_text_overlay",
    "pattern_interrupt_can_insert_text_overlay",
    "can_insert_sfx",
    "pattern_interrupt_can_insert_sfx",
    "can_reorder_timeline",
    "pattern_interrupt_can_reorder_timeline",
    "no_timeline_reorder_in_2b_40",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _between(text: str, start_token: str, end_token: str | None = None) -> str:
    start = text.find(start_token)
    assert start != -1, f"Missing start token: {start_token}"
    if end_token is None:
        return text[start:]
    end = text.find(end_token, start)
    assert end != -1, f"Missing end token: {end_token}"
    return text[start:end]


def _pattern_interrupt_relevant_text(path: Path) -> str:
    text = _text(path)

    if path in PATTERN_INTERRUPT_FULL_SCAN_FILES:
        return text

    if path.name == "gaming_pipeline.py":
        return "\n".join(
            [
                _between(
                    text,
                    "from core.pattern_interrupt_runner import",
                    "from core.audio_normalization_runner import",
                ),
                _between(
                    text,
                    "PATTERN_INTERRUPT_ENGINE_STARTED",
                    "timeline_safety_validation_status",
                ),
            ]
        )

    if path.name == "unified_edit_signal_registry.py":
        return "\n".join(
            [
                _between(
                    text,
                    "from core.pattern_interrupt_signal_adapter import",
                    "from models.unified_edit_signal_result import",
                ),
                _between(
                    text,
                    "pattern_interrupt_report = _job_attr",
                    "if final_cut_list_signals:",
                ),
            ]
        )

    if path.name == "job.py":
        return "\n".join(
            [
                _between(
                    text,
                    "pattern_interrupt_report: dict",
                    "silence_detection_report: dict",
                ),
                _between(
                    text,
                    "pattern_interrupt_report=dict",
                    "silence_detection_report=dict",
                ),
            ]
        )

    return text


def _without_allowed_safety_fields(text: str) -> str:
    cleaned = text
    for token in ALLOWED_SAFETY_FIELD_TOKENS:
        cleaned = cleaned.replace(token, "")
    return cleaned


def test_pattern_interrupt_product_files_exist() -> None:
    missing = [
        path.relative_to(ROOT).as_posix() for path in PRODUCT_FILES if not path.exists()
    ]

    assert missing == []


def test_pattern_interrupt_product_files_have_no_bom_and_end_with_newline() -> None:
    violations: list[str] = []

    for path in PRODUCT_FILES:
        content = path.read_bytes()
        if content.startswith(b"\xef\xbb\xbf"):
            violations.append(f"{path.relative_to(ROOT)}:bom")
        if not content.endswith(b"\n"):
            violations.append(f"{path.relative_to(ROOT)}:missing_newline")

    assert violations == []


def test_pattern_interrupt_has_no_forbidden_media_operations() -> None:
    violations: list[str] = []

    for path in PRODUCT_FILES:
        text = _without_allowed_safety_fields(
            _pattern_interrupt_relevant_text(path)
        )
        for token in FORBIDDEN_MEDIA_TOKENS:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}:{token}")

    assert violations == []


def test_pattern_interrupt_report_forces_review_only_contract() -> None:
    report = PatternInterruptReport.from_dict(
        {
            "status": "pattern_interrupt_analysis_ready",
            "review_required": False,
            "can_apply_interrupts": True,
            "can_insert_zoom": True,
            "can_insert_text_overlay": True,
            "can_insert_sfx": True,
            "can_reorder_timeline": True,
            "can_trim": True,
            "can_extend": True,
            "can_render": True,
            "metadata": {},
        }
    )
    data = report.to_dict()

    assert data["review_required"] is True
    assert data["can_apply_interrupts"] is False
    assert data["can_insert_zoom"] is False
    assert data["can_insert_text_overlay"] is False
    assert data["can_insert_sfx"] is False
    assert data["can_reorder_timeline"] is False
    assert data["can_trim"] is False
    assert data["can_extend"] is False
    assert data["can_render"] is False
    assert data["metadata"]["review_only"] is True
    assert data["metadata"]["pattern_interrupt_only"] is True
    assert data["metadata"]["media_unchanged"] is True
    assert data["metadata"]["no_execution_in_2b_40"] is True
    assert data["metadata"]["no_render_in_2b_40"] is True
    assert data["metadata"]["no_timeline_reorder_in_2b_40"] is True
    assert data["metadata"]["no_pattern_apply_in_2b_40"] is True
    assert data["metadata"]["no_zoom_insert_in_2b_40"] is True
    assert data["metadata"]["no_text_overlay_insert_in_2b_40"] is True
    assert data["metadata"]["no_sfx_insert_in_2b_40"] is True


def test_pattern_interrupt_static_pipeline_order_after_dynamic_pacing() -> None:
    text = _text(ROOT / "core" / "gaming_pipeline.py")

    pacing_index = text.index("run_dynamic_pacing_for_job(")
    pacing_apply_index = text.index("apply_dynamic_pacing_run_report_to_job(")
    pattern_index = text.index("run_pattern_interrupt_for_job(")
    pattern_apply_index = text.index("store_pattern_interrupt_run_report_to_job(")

    assert pacing_index < pacing_apply_index < pattern_index < pattern_apply_index


def test_pattern_interrupt_static_registry_source_exists() -> None:
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert 'SOURCE_PATTERN_INTERRUPT = "pattern_interrupt"' in text
    assert "adapt_pattern_interrupt_report_to_signals" in text
    assert "pattern_interrupt_report" in text
