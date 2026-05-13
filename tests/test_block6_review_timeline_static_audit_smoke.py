from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


BLOCK6_STRICT_PRODUCT_FILES = [
    "models/review_timeline_plan.py",
    "core/review_timeline_plan_builder.py",
    "core/review_timeline_plan_runner.py",
    "core/review_timeline_plan_signal_adapter.py",
    "models/timeline_approval_gate.py",
    "core/timeline_approval_gate.py",
    "core/timeline_approval_gate_runner.py",
    "core/timeline_approval_gate_signal_adapter.py",
    "models/timeline_safety_validator.py",
    "core/timeline_safety_validator.py",
    "core/timeline_safety_validator_runner.py",
    "core/timeline_safety_validator_signal_adapter.py",
    "models/review_timeline_dashboard_package.py",
    "core/review_timeline_dashboard_package_builder.py",
    "core/review_timeline_dashboard_package_runner.py",
    "core/review_timeline_dashboard_package_signal_adapter.py",
]


BLOCK6_CENTRAL_FILES = [
    "models/job.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
]


ALL_BLOCK6_AUDITED_FILES = BLOCK6_STRICT_PRODUCT_FILES + BLOCK6_CENTRAL_FILES


FORBIDDEN_PRODUCT_TOKENS = [
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
    "execute_timeline",
]


FORBIDDEN_HARD_MEDIA_MARKERS = [
    "D:\\",
    "C:\\",
    "/mnt/",
    "/media/",
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".wav",
    ".mp3",
]


FORBIDDEN_DASHBOARD_ACTION_STRINGS = [
    '"render"',
    "'render'",
    '"execute"',
    "'execute'",
    '"apply"',
    "'apply'",
    '"cut"',
    "'cut'",
    '"trim_now"',
    "'trim_now'",
    '"delete"',
    "'delete'",
    '"mute"',
    "'mute'",
    '"censor_now"',
    "'censor_now'",
    '"apply_timeline"',
    "'apply_timeline'",
    '"execute_timeline"',
    "'execute_timeline'",
]


DASHBOARD_ACTION_PRODUCT_FILES = [
    "models/review_timeline_dashboard_package.py",
    "core/review_timeline_dashboard_package_builder.py",
]


def _read_bytes(relative_path: str) -> bytes:
    return (ROOT / relative_path).read_bytes()


def _read_text(relative_path: str) -> str:
    return _read_bytes(relative_path).decode("utf-8")


def test_block6_product_files_exist() -> None:
    missing_files = [
        relative_path
        for relative_path in ALL_BLOCK6_AUDITED_FILES
        if not (ROOT / relative_path).exists()
    ]

    assert missing_files == []


def test_block6_product_files_have_no_bom() -> None:
    files_with_bom = [
        relative_path
        for relative_path in ALL_BLOCK6_AUDITED_FILES
        if _read_bytes(relative_path).startswith(b"\xef\xbb\xbf")
    ]

    assert files_with_bom == []


def test_block6_product_files_end_with_newline() -> None:
    files_without_newline = [
        relative_path
        for relative_path in ALL_BLOCK6_AUDITED_FILES
        if not _read_bytes(relative_path).endswith(b"\n")
    ]

    assert files_without_newline == []


def test_block6_strict_product_files_do_not_use_forbidden_media_execution_tokens() -> None:
    violations: list[str] = []

    for relative_path in BLOCK6_STRICT_PRODUCT_FILES:
        text = _read_text(relative_path)

        for forbidden_token in FORBIDDEN_PRODUCT_TOKENS:
            if forbidden_token in text:
                violations.append(f"{relative_path}: {forbidden_token}")

    assert violations == []


def test_block6_strict_product_files_do_not_use_hard_media_paths() -> None:
    violations: list[str] = []

    for relative_path in BLOCK6_STRICT_PRODUCT_FILES:
        text = _read_text(relative_path)

        for forbidden_marker in FORBIDDEN_HARD_MEDIA_MARKERS:
            if forbidden_marker in text:
                violations.append(f"{relative_path}: {forbidden_marker}")

    assert violations == []


def test_block6_dashboard_files_do_not_expose_dangerous_dashboard_actions() -> None:
    violations: list[str] = []

    for relative_path in DASHBOARD_ACTION_PRODUCT_FILES:
        text = _read_text(relative_path)

        for forbidden_action in FORBIDDEN_DASHBOARD_ACTION_STRINGS:
            if forbidden_action in text:
                violations.append(f"{relative_path}: {forbidden_action}")

    assert violations == []


def test_block6_safety_metadata_tokens_exist() -> None:
    expected_tokens = [
        "review_only",
        "approval_gate_only",
        "safety_validator_only",
        "dashboard_only",
        "media_unchanged",
        "can_render",
        "is_safe_for_render",
        "no_execution_in_2b_34",
        "no_execution_in_2b_35",
        "no_render_in_2b_34",
        "no_render_in_2b_35",
    ]

    combined_text = "\n".join(
        _read_text(relative_path)
        for relative_path in ALL_BLOCK6_AUDITED_FILES
    )

    missing_tokens = [
        token
        for token in expected_tokens
        if token not in combined_text
    ]

    assert missing_tokens == []