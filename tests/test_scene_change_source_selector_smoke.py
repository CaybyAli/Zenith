from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.scene_change_source_selector import (
    select_scene_change_source,
    select_scene_change_source_for_job,
)
from models.scene_change_source import SceneChangeSourceSelection


def _make_video_stub(path: Path) -> Path:
    path.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64)
    return path


def test_source_selector_prefers_raw_video_path(tmp_path: Path) -> None:
    raw_video = _make_video_stub(tmp_path / "raw.mp4")
    manifest_source = _make_video_stub(tmp_path / "other.mp4")
    manifest = {"source_path": str(manifest_source)}

    selection = select_scene_change_source(
        raw_video_path=str(raw_video),
        preprocessing_manifest=manifest,
    )

    assert selection.status == "selected"
    assert selection.selected_type == "raw_video_path"
    assert selection.selected_path == str(raw_video)
    assert selection.source_exists is True


def test_source_selector_preprocessing_manifest_fallback(tmp_path: Path) -> None:
    source_path = _make_video_stub(tmp_path / "source.mp4")
    manifest = {"source_path": str(source_path)}

    selection = select_scene_change_source(
        raw_video_path=None,
        preprocessing_manifest=manifest,
    )

    assert selection.status == "selected_fallback"
    assert selection.selected_type == "preprocessing_source_path"
    assert selection.selected_path == str(source_path)
    assert selection.source_exists is True
    assert "used_preprocessing_manifest_source_path" in selection.warnings


def test_source_selector_missing_raw_video_path_returns_blocked(tmp_path: Path) -> None:
    missing = tmp_path / "missing.mp4"

    selection = select_scene_change_source(
        raw_video_path=str(missing),
        require_existing_file=True,
    )

    assert selection.status == "blocked_missing_video_source"
    assert selection.selected_type == "raw_video_path"
    assert selection.selected_path == str(missing)
    assert "raw_video_path_file_missing" in selection.errors


def test_source_selector_no_source_returns_skipped() -> None:
    selection = select_scene_change_source(
        raw_video_path=None,
        preprocessing_manifest=None,
    )

    assert selection.status == "skipped_no_video_source"
    assert selection.selected_type == "none"
    assert selection.selected_path is None
    assert "no_scene_change_video_source_available" in selection.errors


def test_source_selector_fallback_paths(tmp_path: Path) -> None:
    fallback_video = _make_video_stub(tmp_path / "fallback.mp4")

    selection = select_scene_change_source(
        raw_video_path=None,
        preprocessing_manifest=None,
        fallback_paths={"video_path": str(fallback_video)},
    )

    assert selection.status == "selected_fallback"
    assert selection.selected_type == "fallback_video_path"
    assert selection.selected_path == str(fallback_video)
    assert selection.source_exists is True


def test_source_selector_checked_sources_recorded(tmp_path: Path) -> None:
    raw_video = _make_video_stub(tmp_path / "raw.mp4")

    selection = select_scene_change_source(
        raw_video_path=str(raw_video),
    )

    assert len(selection.checked_sources) >= 1
    assert any(
        src.get("type") == "raw_video_path" for src in selection.checked_sources
    )


def test_scene_change_source_selection_roundtrip() -> None:
    selection = SceneChangeSourceSelection(
        status="selected",
        selected_path="/tmp/video.mp4",
        selected_type="raw_video_path",
        checked_sources=[
            {
                "type": "raw_video_path",
                "path": "/tmp/video.mp4",
                "exists": True,
                "usable": True,
                "reason": "selected_raw_video_path",
            }
        ],
        source_exists=True,
        recommendation="analyze_video",
        warnings=[],
        errors=[],
        metadata={"kind": "roundtrip"},
    )

    loaded = SceneChangeSourceSelection.from_dict(selection.to_dict())

    assert loaded.status == "selected"
    assert loaded.selected_path == "/tmp/video.mp4"
    assert loaded.selected_type == "raw_video_path"
    assert loaded.source_exists is True
    assert loaded.recommendation == "analyze_video"
    assert loaded.metadata["kind"] == "roundtrip"
    assert len(loaded.checked_sources) == 1


def test_scene_change_source_selection_from_dict_invalid_data() -> None:
    loaded = SceneChangeSourceSelection.from_dict(None)
    assert loaded.status == "failed"
    assert loaded.selected_path is None
    assert loaded.selected_type is None
    assert loaded.checked_sources == []


def test_select_source_for_job_prefers_raw_video_path(tmp_path: Path) -> None:
    raw_video = _make_video_stub(tmp_path / "raw.mp4")
    other = _make_video_stub(tmp_path / "other.mp4")
    job = SimpleNamespace(
        raw_video_path=str(raw_video),
        preprocessing_manifest={"source_path": str(other)},
    )

    selection = select_scene_change_source_for_job(job)

    assert selection.status == "selected"
    assert selection.selected_type == "raw_video_path"
    assert selection.selected_path == str(raw_video)


def test_select_source_for_job_preprocessing_manifest_fallback(tmp_path: Path) -> None:
    source_path = _make_video_stub(tmp_path / "source.mp4")
    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest={"source_path": str(source_path)},
    )

    selection = select_scene_change_source_for_job(job)

    assert selection.status == "selected_fallback"
    assert selection.selected_type == "preprocessing_source_path"
    assert selection.selected_path == str(source_path)


def test_select_source_for_job_fallback_field(tmp_path: Path) -> None:
    fallback_video = _make_video_stub(tmp_path / "video.mp4")
    job = SimpleNamespace(
        raw_video_path=None,
        preprocessing_manifest=None,
        video_path=str(fallback_video),
    )

    selection = select_scene_change_source_for_job(job)

    assert selection.status == "selected_fallback"
    assert selection.selected_type == "fallback_video_path"
    assert selection.selected_path == str(fallback_video)


def test_select_source_for_empty_job_returns_skipped() -> None:
    job = SimpleNamespace()

    selection = select_scene_change_source_for_job(job)

    assert selection.status == "skipped_no_video_source"
    assert selection.selected_type == "none"
    assert selection.selected_path is None


def test_scene_change_source_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/scene_change_source.py"),
        Path("core/scene_change_source_selector.py"),
        Path("tests/test_scene_change_source_selector_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
