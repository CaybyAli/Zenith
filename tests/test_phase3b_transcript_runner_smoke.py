from __future__ import annotations

from pathlib import Path
from typing import Any

from core.transcript_processor import TranscriptUnavailableError
from core.transcript_runner import (
    apply_transcript_run_report_to_job,
    build_transcript_run_report,
    run_transcript_for_job,
)
from core.transcript_source_selector import (
    SOURCE_TYPE_SPEECH,
    TranscriptSourceSelection,
)
from models.job import Job
from models.transcript_result import TranscriptResult, TranscriptSegment
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


def _make_job(
    raw_video_path: str | None = None,
    preprocessing_manifest: dict | None = None,
) -> Job:
    job = Job(
        job_id="job_phase3b_runner_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path=raw_video_path,
    )

    if preprocessing_manifest is not None:
        job.preprocessing_manifest = preprocessing_manifest

    return job


def _ok_result(source_path: str) -> TranscriptResult:
    segments = [
        TranscriptSegment(start_seconds=0.0, end_seconds=1.0, text="Hallo Welt", confidence=None),
        TranscriptSegment(
            start_seconds=1.0,
            end_seconds=2.5,
            text="Das ist ein Test.",
            confidence=None,
        ),
    ]
    return TranscriptResult(
        source_path=source_path,
        language="de",
        segments=segments,
        full_text="Hallo Welt Das ist ein Test.",
        engine="test-engine",
    )


class _FakeTranscriptProcessor:
    def __init__(self, behavior: str = "ok") -> None:
        self.behavior = behavior
        self.calls: list[str] = []

    def transcribe(self, source_path: str) -> TranscriptResult:
        self.calls.append(source_path)

        if self.behavior == "ok":
            return _ok_result(source_path)

        if self.behavior == "unavailable":
            raise TranscriptUnavailableError("no whisper engine available")

        if self.behavior == "missing":
            raise FileNotFoundError(f"missing: {source_path}")

        if self.behavior == "empty":
            return TranscriptResult(
                source_path=source_path,
                language="en",
                segments=[],
                full_text="",
                engine="empty-engine",
            )

        raise RuntimeError(f"unexpected behavior={self.behavior}")


def test_run_returns_ok_when_engine_succeeds(tmp_path: Path) -> None:
    speech = tmp_path / "speech_16k_mono.wav"
    speech.write_bytes(b"PCM")

    job = _make_job(
        raw_video_path=str(tmp_path / "video.mp4"),
        preprocessing_manifest={
            "speech_audio_path": str(speech),
            "analysis_audio_path": str(tmp_path / "analysis.wav"),
        },
    )

    fake = _FakeTranscriptProcessor(behavior="ok")
    report = run_transcript_for_job(job=job, transcript_processor=fake)

    assert isinstance(report, TranscriptRunReport)
    assert report.status == "ok"
    assert report.source_type == SOURCE_TYPE_SPEECH
    assert report.source_path == str(speech)
    assert report.segment_count == 2
    assert report.full_text
    assert report.language == "de"
    assert report.engine == "test-engine"
    assert fake.calls == [str(speech)]


def test_run_returns_whisper_unavailable_on_unavailable_engine(tmp_path: Path) -> None:
    speech = tmp_path / "speech_16k_mono.wav"
    speech.write_bytes(b"PCM")

    job = _make_job(
        raw_video_path=str(tmp_path / "video.mp4"),
        preprocessing_manifest={
            "speech_audio_path": str(speech),
            "analysis_audio_path": str(tmp_path / "analysis.wav"),
        },
    )

    fake = _FakeTranscriptProcessor(behavior="unavailable")
    report = run_transcript_for_job(job=job, transcript_processor=fake)

    assert report.status == "whisper_unavailable"
    assert report.recommendation == "install_whisper_engine"
    assert "whisper_unavailable" in report.warnings
    assert report.errors
    assert report.segments == []


def test_run_returns_blocked_when_source_unavailable_at_engine_layer(
    tmp_path: Path,
) -> None:
    speech = tmp_path / "speech_16k_mono.wav"
    speech.write_bytes(b"PCM")

    job = _make_job(
        raw_video_path=str(tmp_path / "video.mp4"),
        preprocessing_manifest={
            "speech_audio_path": str(speech),
            "analysis_audio_path": str(tmp_path / "analysis.wav"),
        },
    )

    fake = _FakeTranscriptProcessor(behavior="missing")
    report = run_transcript_for_job(job=job, transcript_processor=fake)

    assert report.status == "blocked_missing_preprocessed_audio"
    assert report.recommendation == "generate_preprocessed_audio"


def test_run_marks_empty_result_as_completed_with_warnings(tmp_path: Path) -> None:
    speech = tmp_path / "speech_16k_mono.wav"
    speech.write_bytes(b"PCM")

    job = _make_job(
        raw_video_path=str(tmp_path / "video.mp4"),
        preprocessing_manifest={
            "speech_audio_path": str(speech),
            "analysis_audio_path": str(tmp_path / "analysis.wav"),
        },
    )

    fake = _FakeTranscriptProcessor(behavior="empty")
    report = run_transcript_for_job(job=job, transcript_processor=fake)

    assert report.status == "completed_with_warnings"
    assert "transcript_empty" in report.warnings
    assert report.segment_count == 0
    assert report.full_text == ""


def test_run_skipped_when_no_audio_source() -> None:
    job = _make_job(raw_video_path=None, preprocessing_manifest=None)

    fake = _FakeTranscriptProcessor(behavior="ok")
    report = run_transcript_for_job(job=job, transcript_processor=fake)

    assert report.status == "skipped_no_audio_source"
    assert fake.calls == []


def test_run_blocked_when_preprocessed_paths_declared_but_missing(
    tmp_path: Path,
) -> None:
    job = _make_job(
        raw_video_path=str(tmp_path / "video.mp4"),
        preprocessing_manifest={
            "speech_audio_path": str(tmp_path / "speech_16k_mono.wav"),
            "analysis_audio_path": str(tmp_path / "analysis.wav"),
        },
    )

    fake = _FakeTranscriptProcessor(behavior="ok")
    report = run_transcript_for_job(job=job, transcript_processor=fake)

    assert report.status == "blocked_missing_preprocessed_audio"
    assert fake.calls == []


def test_apply_run_report_to_job_sets_fields(tmp_path: Path) -> None:
    speech = tmp_path / "speech_16k_mono.wav"
    speech.write_bytes(b"PCM")

    job = _make_job(
        raw_video_path=str(tmp_path / "video.mp4"),
        preprocessing_manifest={
            "speech_audio_path": str(speech),
            "analysis_audio_path": str(tmp_path / "analysis.wav"),
        },
    )

    fake = _FakeTranscriptProcessor(behavior="ok")
    report = run_transcript_for_job(job=job, transcript_processor=fake)
    apply_transcript_run_report_to_job(job, report)

    assert job.transcript_status == "ok"
    assert job.transcript_source_path == str(speech)
    assert job.transcript_source_type == SOURCE_TYPE_SPEECH
    assert job.transcript_segment_count == 2
    assert job.transcript_text
    assert job.transcript_language == "de"
    assert isinstance(job.transcript_segments, list)
    assert len(job.transcript_segments) == 2

    restored = Job.from_dict(job.to_dict())
    assert restored.transcript_status == job.transcript_status
    assert restored.transcript_source_path == job.transcript_source_path
    assert restored.transcript_source_type == job.transcript_source_type
    assert restored.transcript_segments == job.transcript_segments
    assert restored.transcript_text == job.transcript_text
    assert restored.transcript_segment_count == job.transcript_segment_count
    assert restored.transcript_language == job.transcript_language


def test_old_job_dict_loads_without_transcript_fields() -> None:
    legacy_data = {
        "job_id": "legacy_job_001",
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

    restored = Job.from_dict(legacy_data)

    assert restored.transcript_report == {}
    assert restored.transcript_status is None
    assert restored.transcript_source_path is None
    assert restored.transcript_source_type is None
    assert restored.transcript_segments == []
    assert restored.transcript_text == ""
    assert restored.transcript_segment_count == 0
    assert restored.transcript_duration_seconds == 0.0
    assert restored.transcript_language is None
    assert restored.transcript_recommendation is None


def test_build_report_from_failed_selection_short_circuits() -> None:
    selection = TranscriptSourceSelection(
        status="skipped_no_audio_source",
        selected_path=None,
        selected_type=None,
        recommendation="no_audio_source_available",
        warnings=["no_audio_source_available"],
    )

    def _never(_path: str) -> Any:
        raise AssertionError("transcribe must not be called when source is skipped")

    report = build_transcript_run_report(selection=selection, transcribe_fn=_never)

    assert report.status == "skipped_no_audio_source"
    assert report.recommendation == "no_audio_source_available"


def test_phase3b_runner_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("core/transcript_runner.py"),
        Path("models/transcript_run.py"),
        Path("tests/test_phase3b_transcript_runner_smoke.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
