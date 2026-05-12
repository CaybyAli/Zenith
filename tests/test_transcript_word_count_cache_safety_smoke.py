from __future__ import annotations

from pathlib import Path
from typing import Any

from core.transcript_runner import (
    apply_transcript_run_report_to_job,
    build_transcript_run_report,
    detect_transcript_cache_status,
)
from core.transcript_segment_normalizer import (
    TranscriptSegmentNormalizationResult,
    normalize_transcript_segments,
)
from core.transcript_source_selector import TranscriptSourceSelection
from models.job import Job
from models.transcript_result import TranscriptResult
from models.transcript_run import TranscriptRunReport
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
    ) -> None:
        self.start_seconds = start_seconds
        self.end_seconds = end_seconds
        self.text = text
        self.words = list(words or [])


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def _selection() -> TranscriptSourceSelection:
    return TranscriptSourceSelection(
        status="selected",
        selected_path="speech.wav",
        selected_type="speech_audio",
        recommendation="transcribe_speech_audio",
    )


def _job() -> Job:
    return Job(
        job_id="job_2b_19_d",
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


def test_job_file_has_no_mojibake_comments() -> None:
    source = _read("models/job.py")

    forbidden_strings = [
        "\u00f0\u0178",
        "f\u00c3\u00bcr",
        "\u00c3",
    ]

    for forbidden in forbidden_strings:
        assert forbidden not in source

    assert "# New fields for dashboard" in source
    assert "# New rerender fields" in source


def test_normalization_result_has_word_timestamp_count() -> None:
    result = TranscriptSegmentNormalizationResult(status="ok")

    assert hasattr(result, "word_timestamp_count")
    assert result.word_timestamp_count == 0
    assert result.to_dict()["word_timestamp_count"] == 0


def test_normalizer_counts_all_words_and_timestamped_words_separately() -> None:
    result = normalize_transcript_segments(
        [
            {
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "text": "Hallo schoene Welt",
                "words": [
                    {"word": "Hallo", "start": 0.0, "end": 0.4},
                    {"word": "schoene"},
                    {"word": "Welt", "start": 0.8, "end": 1.2},
                ],
            }
        ]
    )

    assert result.status == "ok"
    assert result.word_count == 3
    assert result.word_timestamp_count == 2
    assert result.has_word_level_timestamps is True


def test_transcript_run_report_has_separate_word_count_fields() -> None:
    report = TranscriptRunReport(
        status="ok",
        word_count=3,
        normalized_word_count=3,
        word_timestamp_count=2,
    )

    data = report.to_dict()

    assert data["word_count"] == 3
    assert data["normalized_word_count"] == 3
    assert data["word_timestamp_count"] == 2


def test_build_report_sets_text_normalized_and_timestamp_word_counts() -> None:
    def fake_transcribe(source_path: str) -> TranscriptResult:
        return TranscriptResult(
            source_path=source_path,
            language="de",
            engine="fake-engine",
            full_text="Hallo schoene Welt",
            segments=[
                WordSegment(
                    start_seconds=0.0,
                    end_seconds=2.0,
                    text="Hallo schoene Welt",
                    words=[
                        {"word": "Hallo", "start": 0.0, "end": 0.4},
                        {"word": "schoene"},
                        {"word": "Welt", "start": 0.8, "end": 1.2},
                    ],
                )
            ],
        )

    report = build_transcript_run_report(
        selection=_selection(),
        transcribe_fn=fake_transcribe,
        metadata={"stage": "2B-19-D"},
    )

    assert report.status == "ok"
    assert report.word_count == 3
    assert report.normalized_word_count == 3
    assert report.word_timestamp_count == 2
    assert report.has_word_level_timestamps is True


def test_apply_report_to_job_writes_word_count_fields() -> None:
    def fake_transcribe(source_path: str) -> TranscriptResult:
        return TranscriptResult(
            source_path=source_path,
            language="de",
            engine="fake-engine",
            full_text="Hallo schoene Welt",
            segments=[
                WordSegment(
                    start_seconds=0.0,
                    end_seconds=2.0,
                    text="Hallo schoene Welt",
                    words=[
                        {"word": "Hallo", "start": 0.0, "end": 0.4},
                        {"word": "schoene"},
                        {"word": "Welt", "start": 0.8, "end": 1.2},
                    ],
                )
            ],
        )

    report = build_transcript_run_report(
        selection=_selection(),
        transcribe_fn=fake_transcribe,
        metadata={"stage": "2B-19-D"},
    )

    job = _job()
    apply_transcript_run_report_to_job(job, report)

    assert job.transcript_word_count == 3
    assert job.transcript_normalized_word_count == 3
    assert job.transcript_word_timestamp_count == 2
    assert job.transcript_has_word_level_timestamps is True

    restored = Job.from_dict(job.to_dict())

    assert restored.transcript_word_count == 3
    assert restored.transcript_normalized_word_count == 3
    assert restored.transcript_word_timestamp_count == 2
    assert restored.transcript_has_word_level_timestamps is True


def test_old_job_dict_loads_with_word_count_defaults() -> None:
    old_data = {
        "job_id": "legacy_job_2b_19_d",
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

    assert job.transcript_word_count == 0
    assert job.transcript_normalized_word_count == 0
    assert job.transcript_word_timestamp_count == 0


def test_cache_safety_reports_not_configured_without_fake_cache() -> None:
    job = _job()

    cache_status = detect_transcript_cache_status(job)

    assert cache_status["status"] == "cache_not_configured"
    assert cache_status["recommendation"] == "transcript_cache_not_configured"
    assert "transcript_cache_not_configured" in cache_status["warnings"]
    assert cache_status["errors"] == []


def test_transcript_files_do_not_contain_cut_logic() -> None:
    combined = "\n".join(
        [
            _read("core/transcript_segment_normalizer.py"),
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


def test_word_count_cleanup_files_have_no_bom_and_end_with_newline() -> None:
    checked_files = [
        "core/transcript_segment_normalizer.py",
        "core/transcript_runner.py",
        "models/transcript_run.py",
        "models/job.py",
        "tests/test_transcript_word_count_cache_safety_smoke.py",
    ]

    for relative_path in checked_files:
        data = (PROJECT_ROOT / relative_path).read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{relative_path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{relative_path} must end with newline"
