from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = PROJECT_ROOT / "core/gaming_pipeline.py"


def _source() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def test_pipeline_imports_profanity_censor_runner() -> None:
    source = _source()

    assert "from core.profanity_censor_runner import" in source
    assert "run_profanity_censor_for_job" in source
    assert "apply_profanity_censor_run_report_to_job" in source


def test_pipeline_contains_profanity_censor_events() -> None:
    source = _source()

    assert "PROFANITY_CENSOR_STARTED" in source
    assert "PROFANITY_CENSOR_DONE" in source
    assert "PROFANITY_CENSOR_SKIPPED" in source
    assert "PROFANITY_CENSOR_FAILED" in source


def test_pipeline_contains_profanity_censor_checkpoint() -> None:
    assert 'step_name="profanity_censor_done"' in _source()


def test_pipeline_uses_runner_and_apply() -> None:
    source = _source()

    assert "run_profanity_censor_for_job(" in source
    assert "apply_profanity_censor_run_report_to_job(" in source


def test_pipeline_wraps_profanity_censor_in_try_except() -> None:
    source = _source()

    assert "try:" in source[source.index("PROFANITY_CENSOR_STARTED"):]
    assert "except Exception as profanity_censor_exc" in source


def test_pipeline_block_position_after_content_value_before_registry() -> None:
    source = _source()

    content_value_index = source.index("CONTENT_VALUE_STARTED")
    profanity_index = source.index("PROFANITY_CENSOR_STARTED")
    registry_index = source.index("UNIFIED_EDIT_SIGNALS_STARTED")

    assert content_value_index < profanity_index < registry_index


def test_profanity_censor_pipeline_file_has_no_bom_and_ends_with_newline() -> None:
    content = PIPELINE_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.endswith(b"\n")
