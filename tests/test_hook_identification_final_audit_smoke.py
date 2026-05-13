from __future__ import annotations

from pathlib import Path

from models.hook_identification import HookIdentificationReport


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "hook_identification.py",
    ROOT / "core" / "hook_identification_engine.py",
    ROOT / "core" / "hook_identification_runner.py",
    ROOT / "core" / "hook_identification_signal_adapter.py",
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
    ROOT / "models" / "job.py",
]

HOOK_FULL_SCAN_FILES = {
    ROOT / "models" / "hook_identification.py",
    ROOT / "core" / "hook_identification_engine.py",
    ROOT / "core" / "hook_identification_runner.py",
    ROOT / "core" / "hook_identification_signal_adapter.py",
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
]

ALLOWED_SAFETY_FIELD_TOKENS = [
    "can_reorder_timeline",
    "hook_can_reorder_timeline",
    "no_timeline_reorder_in_2b_37",
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


def _hook_relevant_text(path: Path) -> str:
    text = _text(path)

    if path in HOOK_FULL_SCAN_FILES:
        return text

    if path.name == "gaming_pipeline.py":
        return "\n".join(
            [
                _between(
                    text,
                    "from core.hook_identification_runner import",
                    "from core.audio_normalization_runner import",
                ),
                _between(
                    text,
                    "HOOK_IDENTIFICATION_STARTED",
                    "EMOTIONAL_ARC_BUILDER_STARTED",
                ),
            ]
        )

    if path.name == "unified_edit_signal_registry.py":
        return "\n".join(
            [
                _between(
                    text,
                    "from core.hook_identification_signal_adapter import",
                    "from models.unified_edit_signal_result import",
                ),
                _between(
                    text,
                    "hook_identification_report = _job_attr",
                    "if final_cut_list_signals:",
                ),
            ]
        )

    if path.name == "job.py":
        return "\n".join(
            [
                _between(
                    text,
                    "hook_identification_report: dict",
                    "emotional_arc_report: dict",
                ),
                _between(
                    text,
                    "hook_identification_report=dict",
                    "emotional_arc_report=dict",
                ),
            ]
        )

    return text


def _without_allowed_safety_fields(text: str) -> str:
    cleaned = text
    for token in ALLOWED_SAFETY_FIELD_TOKENS:
        cleaned = cleaned.replace(token, "")
    return cleaned


def test_hook_identification_product_files_exist() -> None:
    missing = [path.relative_to(ROOT).as_posix() for path in PRODUCT_FILES if not path.exists()]

    assert missing == []


def test_hook_identification_product_files_have_no_bom_and_end_with_newline() -> None:
    violations: list[str] = []

    for path in PRODUCT_FILES:
        content = path.read_bytes()
        if content.startswith(b"\xef\xbb\xbf"):
            violations.append(f"{path.relative_to(ROOT)}:bom")
        if not content.endswith(b"\n"):
            violations.append(f"{path.relative_to(ROOT)}:missing_newline")

    assert violations == []


def test_hook_identification_has_no_forbidden_media_operations() -> None:
    violations: list[str] = []

    for path in PRODUCT_FILES:
        text = _without_allowed_safety_fields(_hook_relevant_text(path))
        for token in FORBIDDEN_MEDIA_TOKENS:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}:{token}")

    assert violations == []


def test_hook_identification_report_forces_review_only_contract() -> None:
    report = HookIdentificationReport.from_dict(
        {
            "status": "hook_candidate_found",
            "review_required": False,
            "can_apply_hook": True,
            "can_reorder_timeline": True,
            "can_render": True,
            "metadata": {},
        }
    )
    data = report.to_dict()

    assert data["review_required"] is True
    assert data["can_apply_hook"] is False
    assert data["can_reorder_timeline"] is False
    assert data["can_render"] is False
    assert data["metadata"]["review_only"] is True
    assert data["metadata"]["hook_identification_only"] is True
    assert data["metadata"]["media_unchanged"] is True
    assert data["metadata"]["no_execution_in_2b_37"] is True
    assert data["metadata"]["no_render_in_2b_37"] is True
    assert data["metadata"]["no_timeline_reorder_in_2b_37"] is True


def test_hook_identification_static_tokens_do_not_set_hook_to_zero() -> None:
    text = "\n".join(_hook_relevant_text(path) for path in PRODUCT_FILES)

    forbidden_zero_tokens = [
        "hook_start_seconds = 0",
        "start_seconds=0.0",
        '"start_seconds": 0.0',
        "'start_seconds': 0.0",
    ]

    violations = [
        token
        for token in forbidden_zero_tokens
        if token in text and "missing" not in token
    ]

    assert violations == []
