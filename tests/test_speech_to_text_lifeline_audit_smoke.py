from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.transcript_runner import (
    apply_transcript_run_report_to_job,
    build_transcript_run_report,
)
from core.transcript_source_selector import TranscriptSourceSelection
from models.transcript_result import TranscriptResult, TranscriptSegment


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _read(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def _function_names(relative_path: str) -> set[str]:
    tree = ast.parse(_read(relative_path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_transcript_lifeline_files_exist() -> None:
    required_files = [
        "core/transcript_source_selector.py",
        "core/transcript_runner.py",
        "core/transcript_processor.py",
        "models/transcript_run.py",
    ]

    for relative_path in required_files:
        assert _path(relative_path).is_file(), f"Missing transcript lifeline file: {relative_path}"


def test_transcript_runner_has_public_lifeline_hooks() -> None:
    names = _function_names("core/transcript_runner.py")

    assert "run_transcript_for_job" in names
    assert "apply_transcript_run_report_to_job" in names
    assert "build_transcript_run_report" in names


def test_job_model_contains_block4_transcript_fields() -> None:
    source = _read("models/job.py")

    required_fields = [
        "transcript_report",
        "transcript_status",
        "transcript_segments",
        "transcript_text",
        "transcript_segment_count",
        "transcript_source_path",
        "transcript_source_type",
        "transcript_language",
        "transcript_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in source, f"Missing job transcript field: {field_name}"


def test_gaming_pipeline_has_transcript_checkpoints_before_filler_word_detection() -> None:
    source = _read("core/gaming_pipeline.py")

    required_markers = [
        "TRANSCRIPT_STARTED",
        "TRANSCRIPT_DONE",
        "TRANSCRIPT_SKIPPED",
        "TRANSCRIPT_BLOCKED",
        "TRANSCRIPT_FAILED",
        "transcript_done",
    ]

    for marker in required_markers:
        assert marker in source, f"Missing transcript pipeline marker: {marker}"

    transcript_index = source.index("transcript_done")
    filler_index = source.index("Filler Word Detection")

    assert transcript_index < filler_index, "Transcript pipeline must run before Filler Word Detection"


def test_transcript_segments_have_start_end_and_text() -> None:
    selection = TranscriptSourceSelection(
        status="selected",
        selected_path="dummy.wav",
        selected_type="speech_audio",
        recommendation="transcribe_speech_audio",
    )

    def fake_transcribe(source_path: str) -> TranscriptResult:
        return TranscriptResult(
            source_path=source_path,
            language="de",
            engine="fake-test-engine",
            full_text="Hallo Welt. Das ist ein Transcript Test.",
            segments=[
                TranscriptSegment(
                    start_seconds=0.0,
                    end_seconds=1.2,
                    text="Hallo Welt.",
                    confidence=0.95,
                ),
                TranscriptSegment(
                    start_seconds=1.3,
                    end_seconds=3.0,
                    text="Das ist ein Transcript Test.",
                    confidence=0.9,
                ),
            ],
        )

    report = build_transcript_run_report(
        selection=selection,
        transcribe_fn=fake_transcribe,
        metadata={"stage": "2B-19-A-audit"},
    )

    assert report.status == "ok"
    assert report.segment_count == 2
    assert report.full_text
    assert report.language == "de"

    for segment in report.segments:
        assert "start_seconds" in segment
        assert "end_seconds" in segment
        assert "text" in segment
        assert isinstance(segment["start_seconds"], float)
        assert isinstance(segment["end_seconds"], float)
        assert segment["end_seconds"] > segment["start_seconds"]
        assert str(segment["text"]).strip()


def test_apply_transcript_report_to_job_sets_job_fields() -> None:
    class DummyJob:
        def __init__(self) -> None:
            self.touched = False

        def touch(self) -> None:
            self.touched = True

    selection = TranscriptSourceSelection(
        status="selected",
        selected_path="speech.wav",
        selected_type="speech_audio",
    )

    def fake_transcribe(source_path: str) -> TranscriptResult:
        return TranscriptResult(
            source_path=source_path,
            language="de",
            engine="fake-test-engine",
            full_text="Ein sauberer Transcript Text.",
            segments=[
                TranscriptSegment(
                    start_seconds=0.0,
                    end_seconds=2.0,
                    text="Ein sauberer Transcript Text.",
                    confidence=None,
                ),
            ],
        )

    report = build_transcript_run_report(
        selection=selection,
        transcribe_fn=fake_transcribe,
        metadata={"stage": "2B-19-A-audit"},
    )

    job = DummyJob()
    apply_transcript_run_report_to_job(job, report)

    assert job.transcript_report["status"] == "ok"
    assert job.transcript_status == "ok"
    assert job.transcript_source_path == "speech.wav"
    assert job.transcript_source_type == "speech_audio"
    assert job.transcript_segments == report.segments
    assert job.transcript_text == report.full_text
    assert job.transcript_segment_count == 1
    assert job.transcript_language == "de"
    assert job.transcript_recommendation == "use_transcript"
    assert job.touched is True


def test_filler_word_detection_can_use_job_transcript_segments() -> None:
    runner_source = _read("core/filler_word_runner.py")
    detector_source = _read("core/filler_word_detector.py")
    combined_source = runner_source + "\n" + detector_source

    assert "transcript_segments" in combined_source
    assert "job.transcript_segments" in combined_source
    assert "skipped_no_transcript" in combined_source


def test_transcript_files_do_not_make_cut_decisions() -> None:
    transcript_files = [
        "core/transcript_source_selector.py",
        "core/transcript_runner.py",
        "core/transcript_processor.py",
        "models/transcript_run.py",
        "models/transcript_result.py",
    ]

    forbidden_strings = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "cut_sentence_now",
    ]

    for relative_path in transcript_files:
        source = _read(relative_path)
        for forbidden in forbidden_strings:
            assert forbidden not in source, f"{relative_path} must not contain cut trigger: {forbidden}"


def test_audit_files_have_no_bom_and_end_with_newline() -> None:
    checked_files = [
        "core/transcript_source_selector.py",
        "core/transcript_runner.py",
        "core/transcript_processor.py",
        "models/transcript_run.py",
        "models/transcript_result.py",
        "models/job.py",
        "core/gaming_pipeline.py",
        "core/filler_word_detector.py",
        "core/filler_word_runner.py",
        "tests/test_speech_to_text_lifeline_audit_smoke.py",
    ]

    for relative_path in checked_files:
        data = _path(relative_path).read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{relative_path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{relative_path} must end with newline"
