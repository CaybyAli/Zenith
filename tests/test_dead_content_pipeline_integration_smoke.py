from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_dead_content_pipeline_imports_runner_and_apply() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "from core.dead_content_runner import" in source
    assert "run_dead_content_detection_for_job" in source
    assert "apply_dead_content_run_report_to_job" in source


def test_dead_content_pipeline_events_present() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "DEAD_CONTENT_STARTED" in source
    assert "DEAD_CONTENT_DONE" in source
    assert "DEAD_CONTENT_SKIPPED" in source
    assert "DEAD_CONTENT_FAILED" in source


def test_dead_content_pipeline_checkpoint_present() -> None:
    source = _read("core/gaming_pipeline.py")

    assert 'step_name="dead_content_done"' in source


def test_dead_content_pipeline_uses_runner_apply_and_try_except() -> None:
    source = _read("core/gaming_pipeline.py")

    block_start = source.index("DEAD_CONTENT_STARTED")
    block_end = source.index('step_name="dead_content_done"')
    block = source[block_start:block_end]

    assert "try:" in block
    assert "except Exception as dead_content_exc:" in block
    assert "run_dead_content_detection_for_job(" in block
    assert "apply_dead_content_run_report_to_job(" in block


def test_dead_content_pipeline_position_after_filler_before_registry() -> None:
    source = _read("core/gaming_pipeline.py")

    filler_index = source.index("FILLER_WORD_DETECTION_STARTED")
    dead_index = source.index("DEAD_CONTENT_STARTED")
    registry_index = source.index("UNIFIED_EDIT_SIGNALS_STARTED")

    assert filler_index < dead_index < registry_index


def test_dead_content_pipeline_position_after_interaction() -> None:
    source = _read("core/gaming_pipeline.py")

    interaction_index = source.index("INTERACTION_CLASSIFICATION_STARTED")
    dead_index = source.index("DEAD_CONTENT_STARTED")

    assert interaction_index < dead_index


def test_dead_content_pipeline_file_has_no_bom_and_ends_with_newline() -> None:
    for relative_path in (
        "core/gaming_pipeline.py",
        "tests/test_dead_content_pipeline_integration_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
