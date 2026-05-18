from __future__ import annotations

from pathlib import Path


def test_p2_5_gaming_pipeline_builds_real_thumbnail_package_before_validation() -> None:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "THUMBNAIL_FALLBACK_CREATED" in source
    assert "extract_thumbnail_from_final_video" in source
    assert "ThumbnailPackage(" in source
    assert "job.thumbnail_path = fallback_thumbnail_path" in source
    assert "thumbnail_package," in source

    assert "None,   # thumbnail_package - wird in Phase 2.5 gebaut" not in source


def test_p2_5_thumbnail_fallback_uses_moviepy_and_export_thumbnail_path() -> None:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "VideoFileClip" in source
    assert ".save_frame(" in source
    assert "subprocess.run" not in source
    assert '"thumbnail.jpg"' in source
    assert 'os.path.join("exports", str(channel_type), job.job_id)' in source
