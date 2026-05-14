from pathlib import Path


PIPELINE_PATH = Path("core/gaming_pipeline.py")


def _pipeline_text():
    return PIPELINE_PATH.read_text(encoding="utf-8")


def test_final_quality_validator_runner_is_imported_in_pipeline():
    text = _pipeline_text()

    assert "from core.final_quality_validator_runner import run_final_quality_validator" in text


def test_final_quality_validator_runs_after_but_therefore_story_engine():
    text = _pipeline_text()

    but_index = text.index('phase="2B-42"')
    final_quality_index = text.index('phase="2B-43"')

    assert but_index < final_quality_index
    assert "run_but_therefore_story_for_job" in text
    assert "run_final_quality_validator(job)" in text
    assert 'step_name="but_therefore_story_engine_done"' in text
    assert 'step_name="final_quality_validator_done"' in text


def test_final_quality_pipeline_block_is_review_only_and_non_executing():
    text = _pipeline_text()

    required_tokens = [
        '"phase": "2B-43"',
        '"block": "block7_story_pacing"',
        '"review_only": True',
        '"final_quality_validator_only": True',
        '"media_unchanged": True',
        '"no_execution_in_2b_43": True',
        '"no_render_in_2b_43": True',
        '"no_timeline_reorder_in_2b_43": True',
        '"no_quality_fix_apply_in_2b_43": True',
        '"can_apply_fixes": False',
        '"can_render": False',
        '"can_execute_timeline": False',
        '"can_reorder_timeline": False',
        '"can_trim": False',
        '"can_extend": False',
        '"can_insert_effects": False',
    ]

    for token in required_tokens:
        assert token in text


def test_final_quality_pipeline_has_safe_failure_fallback():
    text = _pipeline_text()

    assert "except Exception as final_quality_exc" in text
    assert 'job.final_quality_validation_status = "failed"' in text
    assert '"blocking_reasons": ["final_quality_validator_failed"]' in text
    assert 'job.final_quality_can_apply_fixes = False' in text
    assert 'job.final_quality_can_render = False' in text
    assert 'job.final_quality_can_execute_timeline = False' in text
    assert 'job.final_quality_can_reorder_timeline = False' in text
    assert 'job.final_quality_can_trim = False' in text
    assert 'job.final_quality_can_extend = False' in text
    assert 'job.final_quality_can_insert_effects = False' in text
