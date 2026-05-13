from __future__ import annotations

from pathlib import Path

from models.emotional_arc import EmotionalArcReport


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "emotional_arc.py",
    ROOT / "core" / "emotional_arc_builder.py",
    ROOT / "core" / "emotional_arc_runner.py",
    ROOT / "core" / "emotional_arc_signal_adapter.py",
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
    ROOT / "models" / "job.py",
]

EMOTIONAL_ARC_FULL_SCAN_FILES = {
    ROOT / "models" / "emotional_arc.py",
    ROOT / "core" / "emotional_arc_builder.py",
    ROOT / "core" / "emotional_arc_runner.py",
    ROOT / "core" / "emotional_arc_signal_adapter.py",
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
    "apply_arc",
    "execute_arc",
]

ALLOWED_SAFETY_FIELD_TOKENS = [
    "can_apply_arc",
    "can_reorder_timeline",
    "emotional_arc_can_reorder_timeline",
    "no_timeline_reorder_in_2b_38",
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


def _emotional_arc_relevant_text(path: Path) -> str:
    text = _text(path)

    if path in EMOTIONAL_ARC_FULL_SCAN_FILES:
        return text

    if path.name == "gaming_pipeline.py":
        return "\n".join(
            [
                _between(
                    text,
                    "from core.emotional_arc_runner import",
                    "from core.audio_normalization_runner import",
                ),
                _between(
                    text,
                    "EMOTIONAL_ARC_BUILDER_STARTED",
                    "timeline_safety_validation_status",
                ),
            ]
        )

    if path.name == "unified_edit_signal_registry.py":
        return "\n".join(
            [
                _between(
                    text,
                    "from core.emotional_arc_signal_adapter import",
                    "from models.unified_edit_signal_result import",
                ),
                _between(
                    text,
                    "emotional_arc_report = _job_attr",
                    "if final_cut_list_signals:",
                ),
            ]
        )

    if path.name == "job.py":
        return "\n".join(
            [
                _between(
                    text,
                    "emotional_arc_report: dict",
                    "silence_detection_report: dict",
                ),
                _between(
                    text,
                    "emotional_arc_report=dict",
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


def test_emotional_arc_product_files_exist() -> None:
    missing = [path.relative_to(ROOT).as_posix() for path in PRODUCT_FILES if not path.exists()]

    assert missing == []


def test_emotional_arc_product_files_have_no_bom_and_end_with_newline() -> None:
    violations: list[str] = []

    for path in PRODUCT_FILES:
        content = path.read_bytes()
        if content.startswith(b"\xef\xbb\xbf"):
            violations.append(f"{path.relative_to(ROOT)}:bom")
        if not content.endswith(b"\n"):
            violations.append(f"{path.relative_to(ROOT)}:missing_newline")

    assert violations == []


def test_emotional_arc_has_no_forbidden_media_operations() -> None:
    violations: list[str] = []

    for path in PRODUCT_FILES:
        text = _without_allowed_safety_fields(_emotional_arc_relevant_text(path))
        for token in FORBIDDEN_MEDIA_TOKENS:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}:{token}")

    assert violations == []


def test_emotional_arc_report_forces_review_only_contract() -> None:
    report = EmotionalArcReport.from_dict(
        {
            "status": "arc_analysis_ready",
            "review_required": False,
            "can_apply_arc": True,
            "can_reorder_timeline": True,
            "can_trim": True,
            "can_extend": True,
            "can_render": True,
            "metadata": {},
        }
    )
    data = report.to_dict()

    assert data["review_required"] is True
    assert data["can_apply_arc"] is False
    assert data["can_reorder_timeline"] is False
    assert data["can_trim"] is False
    assert data["can_extend"] is False
    assert data["can_render"] is False
    assert data["metadata"]["review_only"] is True
    assert data["metadata"]["emotional_arc_only"] is True
    assert data["metadata"]["media_unchanged"] is True
    assert data["metadata"]["no_execution_in_2b_38"] is True
    assert data["metadata"]["no_render_in_2b_38"] is True
    assert data["metadata"]["no_timeline_reorder_in_2b_38"] is True
    assert data["metadata"]["no_arc_apply_in_2b_38"] is True


def test_emotional_arc_static_pipeline_order_after_hook_identification() -> None:
    text = _text(ROOT / "core" / "gaming_pipeline.py")

    hook_index = text.index("run_hook_identification_for_job(")
    hook_apply_index = text.index("apply_hook_identification_run_report_to_job(")
    arc_index = text.index("run_emotional_arc_builder_for_job(")
    arc_apply_index = text.index("apply_emotional_arc_run_report_to_job(")

    assert hook_index < hook_apply_index < arc_index < arc_apply_index


def test_emotional_arc_static_registry_source_exists() -> None:
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert 'SOURCE_EMOTIONAL_ARC = "emotional_arc"' in text
    assert "adapt_emotional_arc_report_to_signals" in text
    assert "emotional_arc_report" in text
