from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_and_runs_asset_manifest_after_blueprint():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "run_render_command_blueprint_for_job" in text
    assert "run_render_asset_manifest_for_job" in text
    assert text.index("run_render_command_blueprint_for_job") < text.index(
        "run_render_asset_manifest_for_job"
    )

    assert 'phase="2B-48"' in text
    assert "RENDER_ASSET_MANIFEST_STARTED" in text
    assert "render_asset_manifest_done" in text


def test_pipeline_keeps_2b48_manifest_only_metadata():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert '"render_asset_manifest_only": True' in text
    assert '"dry_run_only": True' in text
    assert '"paths_are_hints_only": True' in text
    assert '"media_unchanged": True' in text
    assert '"no_execution_in_2b_48": True' in text
    assert '"no_render_in_2b_48": True' in text
    assert '"no_media_read_in_2b_48": True' in text
    assert '"no_media_write_in_2b_48": True' in text
    assert '"no_directory_create_in_2b_48": True' in text


def test_pipeline_keeps_2b48_capability_flags_false():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert '"can_create_directories": False' in text
    assert '"can_write_files": False' in text
    assert '"can_open_media": False' in text
    assert '"can_render": False' in text
    assert '"can_run_ff" "mpeg": False' in text
