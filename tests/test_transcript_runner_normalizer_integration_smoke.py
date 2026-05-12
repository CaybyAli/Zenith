from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.transcript_runner import (
    apply_transcript_run_report_to_job,
    build_transcript_run_report,
)
from core.transcript_source_selector import TranscriptSourceSelection
from models.job import Job
from models.transcript_result import TranscriptResult
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class WordSegment:
    def __init__(
        self,
        start_seconds: float,
        end_seconds: float,
        text: str,
        words: list[dict[str, Any]] | None = None,
        confidence: float | None = None,
    ) -> None:
        self.start_seconds = start_seconds
        self.end_seconds = end_seconds
        self.text = text
        self.words = list(words or [])
        self.confidence = confidence


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def _function_names(relative_path: str) -> set[str]:
    tree = ast.parse(_read(relative_path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _selection() -> TranscriptSourceSelection:
    return TranscriptSourceSelection(
        status="selected",
        selected_path="speech.wav",
        selected_type="speech_audio",
        recommendation="transcribe_speech_audio",
    )


def _job() -> Job:
    return Job(
        job_id="job_2b_19_c",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="video.mp4",
    )


def test_runner_imports_normalize_transcript_segments() -> None:
    source = _read("core/transcript_runner.py")

    assert "normalize_transcript_segments" in source
    assert "from core.transcript_segment_normalizer import normalize_transcript_segments" in source


def test_runner_public_functions_still_exist() -> None:
    names = _function_names("core/transcript_runner.py")

    assert "build_transcript_run_report" in names
    assert "run_transcript_for_job" in names
    assert "apply_transcript_run_report_to_job" in names


def test_build_report_outputs_normalized_segments() -> None:
    def fake_transcribe(source_path: str) -> TranscriptResult:
        return TranscriptResult(
            source_path=source_path,
            language="de",
            engine="fake-engine",
            full_text="Hallo Welt",
            segments=[
                WordSegment(
                    start_seconds=0.0,
                    end_seconds=1.5,
                    text="Hallo Welt",
                )
            ],
        )

    report = build_transcript_run_report(
        selection=_selection(),
        transcribe_fn=fake_transcribe,
        metadata={"stage": "2B-19-C"},
    )

    assert report.status == "ok"
    assert report.segment_count == 1
    assert report.normalized_segment_count == 1
    assert report.valid_segment_count == 1
    assert report.invalid_segment_count == 0
    assert report.segment_normalization_status == "ok"

    segment = report.segments[0]

    assert segment["start_seconds"] == 0.0
    assert segment["end_seconds"] == 1.5
    assert segment["duration_seconds"] == 1.5
    assert segment["text"] == "Hallo Welt"
    assert segment["is_valid"] is True
    assert segment["words"] == []
    assert segment["source_index"] == 0
    assert segment["warnings"] == []
    assert segment["errors"] == []


def test_words_with_timestamps_set_word_level_readiness() -> None:
    def fake_transcribe(source_path: str) -> TranscriptResult:
        return TranscriptResult(
            source_path=source_path,
            language="de",
            engine="fake-engine",
            full_text="Hallo Welt",
            segments=[
                WordSegment(
                    start_seconds=0.0,
                    end_seconds=1.4,
                    text="Hallo Welt",
                    words=[
                        {"word": "Hallo", "start": 0.0, "end": 0.5},
                        {"word": "Welt", "start": 0.6, "end": 1.2},
                    ],
                )
            ],
        )

    report = build_transcript_run_report(
        selection=_selection(),
        transcribe_fn=fake_transcribe,
        metadata={"stage": "2B-19-C"},
    )

    assert report.status == "ok"
    assert report.word_count == 2
    assert report.has_word_level_timestamps is True
    assert report.segments[0]["words"][0]["word"] == "Hallo"
    assert report.segments[0]["words"][0]["start_seconds"] == 0.0
    assert report.segments[0]["words"][0]["end_seconds"] == 0.5


def test_mixed_valid_and_invalid_segments_completed_with_warnings() -> None:
    def fake_transcribe(source_path: str) -> TranscriptResult:
        return TranscriptResult(
            source_path=source_path,
            language="de",
            engine="fake-engine",
            full_text="Gültig Ungültig",
            segments=[
                WordSegment(
                    start_seconds=0.0,
                    end_seconds=1.0,
                    text="Gültig",
                ),
                WordSegment(
                    start_seconds=3.0,
                    end_seconds=2.0,
                    text="Ungültig",
                ),
            ],
        )

    report = build_transcript_run_report(
        selection=_selection(),
        transcribe_fn=fake_transcribe,
        metadata={"stage": "2B-19-C"},
    )

    assert report.status == "completed_with_warnings"
    assert report.segment_count == 2
    assert report.normalized_segment_count == 2
    assert report.valid_segment_count == 1
    assert report.invalid_segment_count == 1
    assert report.segment_normalization_status == "completed_with_warnings"
    assert "end_before_start" in report.errors
    assert report.segments[1]["is_valid"] is False


def test_all_invalid_segments_fail_cleanly_without_crashing() -> None:
    def fake_transcribe(source_path: str) -> TranscriptResult:
        return TranscriptResult(
            source_path=source_path,
            language="de",
            engine="fake-engine",
            full_text="Kaputt",
            segments=[
                WordSegment(
                    start_seconds=-1.0,
                    end_seconds=0.5,
                    text="Kaputt",
                )
            ],
        )

    report = build_transcript_run_report(
        selection=_selection(),
        transcribe_fn=fake_transcribe,
        metadata={"stage": "2B-19-C"},
    )

    assert report.status == "failed"
    assert report.segment_count == 1
    assert report.valid_segment_count == 0
    assert report.invalid_segment_count == 1
    assert report.segment_normalization_status == "failed"
    assert "negative_timestamp" in report.errors


def test_apply_transcript_report_to_job_writes_normalizer_fields() -> None:
    def fake_transcribe(source_path: str) -> TranscriptResult:
        return TranscriptResult(
            source_path=source_path,
            language="de",
            engine="fake-engine",
            full_text="Hallo Welt",
            segments=[
                WordSegment(
                    start_seconds=0.0,
                    end_seconds=1.4,
                    text="Hallo Welt",
                    words=[
                        {"word": "Hallo", "start": 0.0, "end": 0.5},
                        {"word": "Welt", "start": 0.6, "end": 1.2},
                    ],
                )
            ],
        )

    report = build_transcript_run_report(
        selection=_selection(),
        transcribe_fn=fake_transcribe,
        metadata={"stage": "2B-19-C"},
    )

    job = _job()
    apply_transcript_run_report_to_job(job, report)

    assert job.transcript_status == "ok"
    assert job.transcript_segment_count == 1
    assert job.transcript_normalized_segment_count == 1
    assert job.transcript_valid_segment_count == 1
    assert job.transcript_invalid_segment_count == 0
    assert job.transcript_word_count == 2
    assert job.transcript_has_word_level_timestamps is True
    assert job.transcript_segment_normalization_status == "ok"
    assert job.transcript_segment_normalization_recommendation == "use_normalized_segments"

    restored = Job.from_dict(job.to_dict())

    assert restored.transcript_normalized_segment_count == 1
    assert restored.transcript_valid_segment_count == 1
    assert restored.transcript_invalid_segment_count == 0
    assert restored.transcript_word_count == 2
    assert restored.transcript_has_word_level_timestamps is True
    assert restored.transcript_segment_normalization_status == "ok"
    assert restored.transcript_segment_normalization_recommendation == "use_normalized_segments"


def test_old_job_dict_loads_with_normalizer_defaults() -> None:
    old_data = {
        "job_id": "legacy_job_2b_19_c",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }

    job = Job.from_dict(old_data)

    assert job.transcript_normalized_segment_count == 0
    assert job.transcript_valid_segment_count == 0
    assert job.transcript_invalid_segment_count == 0
    assert job.transcript_word_count == 0
    assert job.transcript_has_word_level_timestamps is False
    assert job.transcript_segment_normalization_status is None
    assert job.transcript_segment_normalization_recommendation is None


def test_runner_and_model_do_not_contain_cut_logic() -> None:
    combined = "\n".join(
        [
            _read("core/transcript_runner.py"),
            _read("models/transcript_run.py"),
            _read("models/job.py"),
        ]
    )

    forbidden_strings = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "cut_sentence_now",
    ]

    for forbidden in forbidden_strings:
        assert forbidden not in combined


def test_runner_integration_files_have_no_bom_and_end_with_newline() -> None:
    checked_files = [
        "core/transcript_runner.py",
        "models/transcript_run.py",
        "models/job.py",
        "tests/test_transcript_runner_normalizer_integration_smoke.py",
    ]

    for relative_path in checked_files:
        data = (PROJECT_ROOT / relative_path).read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{relative_path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{relative_path} must end with newline"
