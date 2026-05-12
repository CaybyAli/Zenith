from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _read(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_pipeline_imports_interaction_classification_runner() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "from core.interaction_classification_runner import" in source
    assert "run_interaction_classification_for_job" in source
    assert "apply_interaction_classification_run_report_to_job" in source


def test_pipeline_has_started_event() -> None:
    assert "INTERACTION_CLASSIFICATION_STARTED" in _read("core/gaming_pipeline.py")


def test_pipeline_has_done_event() -> None:
    assert "INTERACTION_CLASSIFICATION_DONE" in _read("core/gaming_pipeline.py")


def test_pipeline_has_skipped_event() -> None:
    assert "INTERACTION_CLASSIFICATION_SKIPPED" in _read("core/gaming_pipeline.py")


def test_pipeline_has_failed_event() -> None:
    assert "INTERACTION_CLASSIFICATION_FAILED" in _read("core/gaming_pipeline.py")


def test_pipeline_has_checkpoint() -> None:
    source = _read("core/gaming_pipeline.py")

    assert 'step_name="interaction_classification_done"' in source


def test_pipeline_uses_runner_and_apply() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "interaction_classification_report = run_interaction_classification_for_job(" in source
    assert "apply_interaction_classification_run_report_to_job(" in source


def test_pipeline_block_has_try_except() -> None:
    source = _read("core/gaming_pipeline.py")
    block_start = source.index("INTERACTION_CLASSIFICATION_STARTED")
    block_end = source.index("FILLER_WORD_DETECTION_STARTED")
    block = source[block_start:block_end]

    assert "try:" in block
    assert "except Exception as interaction_classification_exc" in block


def test_pipeline_block_after_keyword_emotion() -> None:
    source = _read("core/gaming_pipeline.py")

    assert source.index("KEYWORD_EMOTION_STARTED") < source.index(
        "INTERACTION_CLASSIFICATION_STARTED"
    )


def test_pipeline_block_before_filler_word() -> None:
    source = _read("core/gaming_pipeline.py")

    assert source.index("INTERACTION_CLASSIFICATION_STARTED") < source.index(
        "FILLER_WORD_DETECTION_STARTED"
    )


def test_interaction_pipeline_file_hygiene() -> None:
    for relative_path in [
        "core/gaming_pipeline.py",
        "tests/test_interaction_classification_pipeline_integration_smoke.py",
    ]:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
