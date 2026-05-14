from pathlib import Path

PIPELINE_PATH = Path("core/gaming_pipeline.py")


def test_pipeline_runs_dashboard_delivery_after_render_verification_contract() -> None:
    text = PIPELINE_PATH.read_text(encoding="utf-8")

    assert "from core.render_dashboard_delivery_package_runner import" in text
    assert "run_render_dashboard_delivery_package" in text

    verification_index = text.index("run_render_verification_contract(job)")
    dashboard_index = text.index("run_render_dashboard_delivery_package(job)")

    assert verification_index < dashboard_index


def test_pipeline_has_2b57_safety_metadata() -> None:
    text = PIPELINE_PATH.read_text(encoding="utf-8")

    assert 'phase="2B-57"' in text
    assert "render_dashboard_delivery_package_only" in text
    assert "dashboard_only" in text
    assert "package_only" in text
    assert "no_dashboard_" in text
    assert "no_video_" in text
    assert "no_output_copy_in_2b_57" in text
    assert "no_thumb" in text
    assert "no_" in text
    assert "no_ff" in text
    assert "no_timeline_" in text
    assert "render_dashboard_delivery_package_done" in text
