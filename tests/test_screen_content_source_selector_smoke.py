from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.screen_content_source_selector import select_screen_content_source
from models.screen_content_source import (
    SCREEN_CONTENT_SELECTED_TYPE_FALLBACK_VIDEO_PATH,
    SCREEN_CONTENT_SELECTED_TYPE_NONE,
    SCREEN_CONTENT_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH,
    SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH,
    SCREEN_CONTENT_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    SCREEN_CONTENT_SOURCE_STATUS_SELECTED,
    SCREEN_CONTENT_SOURCE_STATUS_SELECTED_FALLBACK,
    SCREEN_CONTENT_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    ScreenContentSourceSelection,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_screen_content_source_selection_roundtrip():
    selection = ScreenContentSourceSelection(
        status=SCREEN_CONTENT_SOURCE_STATUS_SELECTED,
        selected_path="video.mp4",
        selected_type=SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH,
        checked_sources=[
            {
                "source_type": SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH,
                "path": "video.mp4",
                "exists": True,
                "status": "exists",
            }
        ],
        source_exists=True,
        recommendation="run_screen_content_classification",
        warnings=[],
        errors=[],
        metadata={"unit": "test"},
    )

    restored = ScreenContentSourceSelection.from_dict(selection.to_dict())

    assert restored.to_dict() == selection.to_dict()


def test_source_selector_prefers_raw_video_path(tmp_path):
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake video placeholder")
    preprocessing_video = tmp_path / "preprocessing.mp4"
    preprocessing_video.write_bytes(b"fake video placeholder")

    job = SimpleNamespace(
        raw_video_path=str(raw_video),
        preprocessing_manifest={"source_path": str(preprocessing_video)},
    )

    selection = select_screen_content_source(job)

    assert selection.status == SCREEN_CONTENT_SOURCE_STATUS_SELECTED
    assert selection.selected_path == str(raw_video)
    assert selection.selected_type == SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH
    assert selection.source_exists is True


def test_source_selector_uses_preprocessing_manifest_fallback(tmp_path):
    preprocessing_video = tmp_path / "preprocessing.mp4"
    preprocessing_video.write_bytes(b"fake video placeholder")

    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={"source_path": str(preprocessing_video)},
    )

    selection = select_screen_content_source(job)

    assert selection.status == SCREEN_CONTENT_SOURCE_STATUS_SELECTED_FALLBACK
    assert selection.selected_path == str(preprocessing_video)
    assert selection.selected_type == SCREEN_CONTENT_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH
    assert selection.warnings


def test_source_selector_uses_fallback_video_path(tmp_path):
    fallback_video = tmp_path / "fallback.mp4"
    fallback_video.write_bytes(b"fake video placeholder")

    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={},
        video_path=str(fallback_video),
    )

    selection = select_screen_content_source(job)

    assert selection.status == SCREEN_CONTENT_SOURCE_STATUS_SELECTED_FALLBACK
    assert selection.selected_path == str(fallback_video)
    assert selection.selected_type == SCREEN_CONTENT_SELECTED_TYPE_FALLBACK_VIDEO_PATH
    assert selection.metadata["fallback_field"] == "video_path"


def test_missing_raw_video_path_is_blocked(tmp_path):
    missing_raw = tmp_path / "missing_raw.mp4"

    job = SimpleNamespace(raw_video_path=str(missing_raw), preprocessing_manifest={})

    selection = select_screen_content_source(job)

    assert selection.status == SCREEN_CONTENT_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE
    assert selection.selected_path == str(missing_raw)
    assert selection.selected_type == SCREEN_CONTENT_SELECTED_TYPE_RAW_VIDEO_PATH
    assert selection.source_exists is False
    assert selection.warnings


def test_no_video_source_is_skipped():
    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={},
        input_file=None,
        source_file=None,
        video_path=None,
        file_path=None,
    )

    selection = select_screen_content_source(job)

    assert selection.status == SCREEN_CONTENT_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE
    assert selection.selected_path is None
    assert selection.selected_type == SCREEN_CONTENT_SELECTED_TYPE_NONE
    assert selection.warnings


def test_new_screen_content_source_selector_files_do_not_have_bom():
    files = [
        REPO_ROOT / "models" / "screen_content_source.py",
        REPO_ROOT / "core" / "screen_content_source_selector.py",
        REPO_ROOT / "tests" / "test_screen_content_source_selector_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_screen_content_source_selector_files_end_with_newline():
    files = [
        REPO_ROOT / "models" / "screen_content_source.py",
        REPO_ROOT / "core" / "screen_content_source_selector.py",
        REPO_ROOT / "tests" / "test_screen_content_source_selector_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
