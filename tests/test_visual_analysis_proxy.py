from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.visual_analysis_proxy import (
    VISUAL_ANALYSIS_PROXY_SELECTED_TYPE,
    ensure_visual_analysis_proxy_for_job,
    resolve_visual_analysis_proxy_path,
    with_visual_analysis_proxy_source_selection,
)
from models.motion_analysis_source import MotionAnalysisSourceSelection


def test_resolve_proxy_path_uses_preprocessing_temp_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ZENITH_VISUAL_ANALYSIS_PROXY_FPS", "2")
    job = SimpleNamespace(
        job_id="job_proxy",
        preprocessing_manifest={"temp_dir": str(tmp_path / "temp")},
    )

    proxy_path = resolve_visual_analysis_proxy_path(job, tmp_path / "source.mp4")

    assert proxy_path == tmp_path / "temp" / "analysis_proxy_960x270_2p0fps.mp4"


def test_small_sources_do_not_create_proxy(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "small.mp4"
    source.write_bytes(b"not a real video")
    job = SimpleNamespace(job_id="job_proxy", preprocessing_manifest={"temp_dir": str(tmp_path)})
    monkeypatch.setenv("ZENITH_VISUAL_ANALYSIS_PROXY_MIN_SOURCE_BYTES", "1024")

    assert ensure_visual_analysis_proxy_for_job(job, source) is None
    assert not hasattr(job, "visual_analysis_proxy_path")


def test_source_selection_can_be_repointed_to_proxy() -> None:
    selection = MotionAnalysisSourceSelection(
        status="selected",
        selected_path="raw.mp4",
        selected_type="raw_video_path",
        source_exists=True,
        recommendation="run_motion_analysis",
    )

    updated = with_visual_analysis_proxy_source_selection(selection, "proxy.mp4")

    assert updated.selected_path == "proxy.mp4"
    assert updated.selected_type == VISUAL_ANALYSIS_PROXY_SELECTED_TYPE
    assert "visual_analysis_proxy_used" in updated.warnings
    assert updated.metadata["visual_analysis_original_path"] == "raw.mp4"
