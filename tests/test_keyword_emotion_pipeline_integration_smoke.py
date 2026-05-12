from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _read(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_pipeline_imports_keyword_emotion_runner() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "from core.keyword_emotion_runner import (" in source
    assert "run_keyword_emotion_for_job" in source
    assert "apply_keyword_emotion_run_report_to_job" in source


def test_pipeline_contains_keyword_emotion_started_event() -> None:
    assert "KEYWORD_EMOTION_STARTED" in _read("core/gaming_pipeline.py")


def test_pipeline_contains_keyword_emotion_done_event() -> None:
    assert "KEYWORD_EMOTION_DONE" in _read("core/gaming_pipeline.py")


def test_pipeline_contains_keyword_emotion_skipped_event() -> None:
    assert "KEYWORD_EMOTION_SKIPPED" in _read("core/gaming_pipeline.py")


def test_pipeline_contains_keyword_emotion_failed_event() -> None:
    assert "KEYWORD_EMOTION_FAILED" in _read("core/gaming_pipeline.py")


def test_pipeline_contains_keyword_emotion_checkpoint() -> None:
    assert 'step_name="keyword_emotion_done"' in _read("core/gaming_pipeline.py")


def test_pipeline_uses_runner_and_apply() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "keyword_emotion_report = run_keyword_emotion_for_job(" in source
    assert "apply_keyword_emotion_run_report_to_job(job, keyword_emotion_report)" in source


def test_pipeline_keyword_emotion_block_has_try_except() -> None:
    source = _read("core/gaming_pipeline.py")
    start = source.index("KEYWORD_EMOTION_STARTED")
    failed = source.index("KEYWORD_EMOTION_FAILED", start)
    block = source[start:failed + 500]

    assert "try:" in block
    assert "except Exception as keyword_emotion_exc" in block


def test_pipeline_keyword_emotion_runs_after_sentence_boundary() -> None:
    source = _read("core/gaming_pipeline.py")

    sentence_boundary_index = source.index("SENTENCE_BOUNDARY_STARTED")
    keyword_emotion_index = source.index("KEYWORD_EMOTION_STARTED")

    assert sentence_boundary_index < keyword_emotion_index


def test_pipeline_keyword_emotion_runs_before_filler_word_detection() -> None:
    source = _read("core/gaming_pipeline.py")

    keyword_emotion_index = source.index("KEYWORD_EMOTION_STARTED")
    filler_index = source.index("FILLER_WORD_DETECTION_STARTED")

    assert keyword_emotion_index < filler_index


def test_keyword_emotion_pipeline_file_has_no_bom_and_newline() -> None:
    content = _path("core/gaming_pipeline.py").read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.endswith(b"\n")
