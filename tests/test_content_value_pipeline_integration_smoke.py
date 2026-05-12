from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_content_value_pipeline_imports_runner_and_apply() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "from core.content_value_runner import" in source
    assert "run_content_value_for_job" in source
    assert "apply_content_value_run_report_to_job" in source


def test_content_value_pipeline_events_present() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "CONTENT_VALUE_STARTED" in source
    assert "CONTENT_VALUE_DONE" in source
    assert "CONTENT_VALUE_SKIPPED" in source
    assert "CONTENT_VALUE_FAILED" in source


def test_content_value_pipeline_checkpoint_present() -> None:
    source = _read("core/gaming_pipeline.py")

    assert 'step_name="content_value_done"' in source


def test_content_value_pipeline_uses_runner_apply_and_try_except() -> None:
    source = _read("core/gaming_pipeline.py")

    block_start = source.index("CONTENT_VALUE_STARTED")
    block_end = source.index('step_name="content_value_done"')
    block = source[block_start:block_end]

    assert "try:" in block
    assert "except Exception as content_value_exc:" in block
    assert "run_content_value_for_job(" in block
    assert "apply_content_value_run_report_to_job(" in block


def test_content_value_pipeline_position_after_dead_content_before_registry() -> None:
    source = _read("core/gaming_pipeline.py")

    dead_index = source.index("DEAD_CONTENT_STARTED")
    content_index = source.index("CONTENT_VALUE_STARTED")
    registry_index = source.index("UNIFIED_EDIT_SIGNALS_STARTED")

    assert dead_index < content_index < registry_index


def test_content_value_pipeline_file_has_no_bom_and_ends_with_newline() -> None:
    for relative_path in (
        "core/gaming_pipeline.py",
        "tests/test_content_value_pipeline_integration_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
