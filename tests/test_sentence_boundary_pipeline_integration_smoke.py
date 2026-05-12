from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _read(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_pipeline_imports_sentence_boundary_runner() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "from core.sentence_boundary_runner import (" in source
    assert "run_sentence_boundary_for_job" in source
    assert "apply_sentence_boundary_run_report_to_job" in source


def test_pipeline_contains_sentence_boundary_started_event() -> None:
    assert "SENTENCE_BOUNDARY_STARTED" in _read("core/gaming_pipeline.py")


def test_pipeline_contains_sentence_boundary_done_event() -> None:
    assert "SENTENCE_BOUNDARY_DONE" in _read("core/gaming_pipeline.py")


def test_pipeline_contains_sentence_boundary_skipped_event() -> None:
    assert "SENTENCE_BOUNDARY_SKIPPED" in _read("core/gaming_pipeline.py")


def test_pipeline_contains_sentence_boundary_failed_event() -> None:
    assert "SENTENCE_BOUNDARY_FAILED" in _read("core/gaming_pipeline.py")


def test_pipeline_contains_sentence_boundary_checkpoint() -> None:
    source = _read("core/gaming_pipeline.py")

    assert 'step_name="sentence_boundary_done"' in source


def test_pipeline_uses_runner_and_apply() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "sentence_boundary_report = run_sentence_boundary_for_job(" in source
    assert "apply_sentence_boundary_run_report_to_job(job, sentence_boundary_report)" in source


def test_pipeline_sentence_boundary_block_has_try_except() -> None:
    source = _read("core/gaming_pipeline.py")
    start = source.index("SENTENCE_BOUNDARY_STARTED")
    failed = source.index("SENTENCE_BOUNDARY_FAILED", start)
    block = source[start:failed + 500]

    assert "try:" in block
    assert "except Exception as sentence_boundary_exc" in block


def test_pipeline_sentence_boundary_runs_after_transcript() -> None:
    source = _read("core/gaming_pipeline.py")

    transcript_index = source.index("TRANSCRIPT_DONE")
    sentence_boundary_index = source.index("SENTENCE_BOUNDARY_STARTED")

    assert transcript_index < sentence_boundary_index


def test_pipeline_sentence_boundary_runs_before_filler_word_detection() -> None:
    source = _read("core/gaming_pipeline.py")

    sentence_boundary_index = source.index("SENTENCE_BOUNDARY_STARTED")
    filler_index = source.index("FILLER_WORD_DETECTION_STARTED")

    assert sentence_boundary_index < filler_index


def test_sentence_boundary_pipeline_file_has_no_bom_and_newline() -> None:
    content = _path("core/gaming_pipeline.py").read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.endswith(b"\n")
