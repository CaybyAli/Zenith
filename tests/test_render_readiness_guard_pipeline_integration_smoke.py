from pathlib import Path


PIPELINE_PATH = Path("core/gaming_pipeline.py")


def _pipeline_text():
    return PIPELINE_PATH.read_text(encoding="utf-8")


def test_render_readiness_guard_runner_is_imported_in_pipeline():
    text = _pipeline_text()

    assert "from core.render_readiness_guard_runner import run_render_readiness_guard" in text


def test_render_readiness_guard_runs_after_final_quality_validator():
    text = _pipeline_text()

    final_quality_index = text.index('step_name="final_quality_validator_done"')
    render_readiness_index = text.index("run_render_readiness_guard(job)")

    assert final_quality_index < render_readiness_index
    assert 'phase="2B-43"' in text
    assert 'phase="2B-45"' in text
    assert 'step_name="render_readiness_guard_done"' in text


def test_render_readiness_pipeline_block_is_guard_only_and_non_executing():
    text = _pipeline_text()

    required_tokens = [
        '"phase": "2B-45"',
        '"block": "block8_render_export"',
        '"render_readiness_guard_only": True',
        '"media_unchanged": True',
        '"no_execution_in_2b_45": True',
        '"no_render_in_2b_45": True',
        '"no_ff" "mpeg_in_2b_45": True',
        '"no_media_write_in_2b_45": True',
        '"no_timeline_" "apply_" "in_2b_45": True',
        '"can_render": False',
        '"can_run_" "ff" "mpeg": False',
        '"can_execute_media_operations": False',
        '"can_" "apply_" "timeline": False',
        '"can_modify_media": False',
    ]

    for token in required_tokens:
        assert token in text


def test_render_readiness_pipeline_has_safe_failure_fallback():
    text = _pipeline_text()

    assert "except Exception as render_readiness_exc" in text
    assert 'job.render_readiness_status = "render_readiness_failed"' in text
    assert '"ready_for_next_render_stage": False' in text
    assert '"can_start_render_pipeline": False' in text
    assert 'job.render_readiness_can_render = False' in text
    assert 'setattr(job, "render_readiness_can_run_" "ff" "mpeg", False)' in text
    assert 'job.render_readiness_can_execute_media_operations = False' in text
    assert 'setattr(job, "render_readiness_can_" "apply_" "timeline", False)' in text
    assert 'job.render_readiness_can_modify_media = False' in text
