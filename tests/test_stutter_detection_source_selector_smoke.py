from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.stutter_detection_source_selector import select_stutter_detection_source
from models.stutter_detection_source import (
    STUTTER_SELECTED_TYPE_FALLBACK_VIDEO_PATH,
    STUTTER_SELECTED_TYPE_NONE,
    STUTTER_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH,
    STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH,
    STUTTER_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE,
    STUTTER_SOURCE_STATUS_SELECTED,
    STUTTER_SOURCE_STATUS_SELECTED_FALLBACK,
    STUTTER_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE,
    StutterDetectionSourceSelection,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_raw_video_path_is_preferred(tmp_path):
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake video placeholder")

    fallback_video = tmp_path / "fallback.mp4"
    fallback_video.write_bytes(b"fake video placeholder")

    job = SimpleNamespace(
        raw_video_path=str(raw_video),
        preprocessing_manifest={"source_path": str(fallback_video)},
        video_path=str(fallback_video),
    )

    selection = select_stutter_detection_source(job)

    assert selection.status == STUTTER_SOURCE_STATUS_SELECTED
    assert selection.selected_path == str(raw_video)
    assert selection.selected_type == STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH
    assert selection.source_exists is True


def test_preprocessing_manifest_source_path_is_used_as_fallback(tmp_path):
    source_video = tmp_path / "preprocessed_source.mp4"
    source_video.write_bytes(b"fake video placeholder")

    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={"source_path": str(source_video)},
    )

    selection = select_stutter_detection_source(job)

    assert selection.status == STUTTER_SOURCE_STATUS_SELECTED_FALLBACK
    assert selection.selected_path == str(source_video)
    assert selection.selected_type == STUTTER_SELECTED_TYPE_PREPROCESSING_SOURCE_PATH
    assert selection.source_exists is True


def test_fallback_video_path_is_used(tmp_path):
    fallback_video = tmp_path / "fallback_video.mp4"
    fallback_video.write_bytes(b"fake video placeholder")

    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={},
        video_path=str(fallback_video),
    )

    selection = select_stutter_detection_source(job)

    assert selection.status == STUTTER_SOURCE_STATUS_SELECTED_FALLBACK
    assert selection.selected_path == str(fallback_video)
    assert selection.selected_type == STUTTER_SELECTED_TYPE_FALLBACK_VIDEO_PATH
    assert selection.source_exists is True
    assert selection.metadata["fallback_field"] == "video_path"


def test_missing_raw_source_blocks_stutter_detection(tmp_path):
    missing_raw = tmp_path / "missing_raw.mp4"

    job = SimpleNamespace(
        raw_video_path=str(missing_raw),
        preprocessing_manifest={},
    )

    selection = select_stutter_detection_source(job)

    assert selection.status == STUTTER_SOURCE_STATUS_BLOCKED_MISSING_VIDEO_SOURCE
    assert selection.selected_path == str(missing_raw)
    assert selection.selected_type == STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH
    assert selection.source_exists is False
    assert selection.warnings


def test_missing_all_sources_skips_stutter_detection():
    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={},
        input_file=None,
        source_file=None,
        video_path=None,
        file_path=None,
    )

    selection = select_stutter_detection_source(job)

    assert selection.status == STUTTER_SOURCE_STATUS_SKIPPED_NO_VIDEO_SOURCE
    assert selection.selected_path is None
    assert selection.selected_type == STUTTER_SELECTED_TYPE_NONE
    assert selection.source_exists is False
    assert selection.warnings


def test_stutter_detection_source_selection_roundtrip():
    selection = StutterDetectionSourceSelection(
        status=STUTTER_SOURCE_STATUS_SELECTED,
        selected_path="video.mp4",
        selected_type=STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH,
        checked_sources=[
            {
                "source_type": STUTTER_SELECTED_TYPE_RAW_VIDEO_PATH,
                "path": "video.mp4",
                "exists": True,
                "status": "exists",
            }
        ],
        source_exists=True,
        recommendation="run_stutter_detection",
        warnings=[],
        errors=[],
        metadata={"unit": "test"},
    )

    restored = StutterDetectionSourceSelection.from_dict(selection.to_dict())

    assert restored.to_dict() == selection.to_dict()


def test_new_stutter_source_files_do_not_have_bom():
    files = [
        REPO_ROOT / "models" / "stutter_detection_source.py",
        REPO_ROOT / "core" / "stutter_detection_source_selector.py",
        REPO_ROOT / "tests" / "test_stutter_detection_source_selector_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_new_stutter_source_files_end_with_newline():
    files = [
        REPO_ROOT / "models" / "stutter_detection_source.py",
        REPO_ROOT / "core" / "stutter_detection_source_selector.py",
        REPO_ROOT / "tests" / "test_stutter_detection_source_selector_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
