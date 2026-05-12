from __future__ import annotations

from pathlib import Path
from typing import Any

from core.filler_word_runner import (
    extract_transcript_source_from_job,
    run_filler_word_detection_for_job,
)
from core.transcript_runner import (
    apply_transcript_run_report_to_job,
    run_transcript_for_job,
)
from core.transcript_source_selector import SOURCE_TYPE_SPEECH
from models.job import Job
from models.transcript_result import TranscriptResult, TranscriptSegment
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
    raw_video_path: str,
    preprocessing_manifest: dict[str, Any] | None = None,
    ready_audio_targets: list[str] | None = None,
) -> Job:
    job = Job(
        job_id="job_phase3b_pipeline_001",
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
    if ready_audio_targets is not None:
        job.ready_audio_targets = list(ready_audio_targets)
    return job


class _FakeProcessor:
    def __init__(self, behavior: str = "ok") -> None:
        self.behavior = behavior

    def transcribe(self, source_path: str) -> TranscriptResult:
        if self.behavior == "ok":
            segments = [
                TranscriptSegment(
                    start_seconds=0.0,
                    end_seconds=1.4,
                    text="äh ich glaube das ist halt ein test.",
                    confidence=None,
                ),
                TranscriptSegment(
                    start_seconds=1.5,
                    end_seconds=3.2,
                    text="ähm ja also so funktioniert es.",
                    confidence=None,
                ),
            ]
            return TranscriptResult(
                source_path=source_path,
                language="de",
                segments=segments,
                full_text=" ".join(segment.text for segment in segments),
                engine="fake",
            )

        from core.transcript_processor import TranscriptUnavailableError

        if self.behavior == "unavailable":
            raise TranscriptUnavailableError("no engine available")

        raise RuntimeError(f"unexpected behavior={self.behavior}")


def test_filler_word_runner_reads_transcript_segments_from_job(tmp_path: Path) -> None:
    speech = tmp_path / "speech_16k_mono.wav"
    speech.write_bytes(b"PCM")

    job = _make_job(
        raw_video_path=str(tmp_path / "video.mp4"),
        preprocessing_manifest={
            "speech_audio_path": str(speech),
            "analysis_audio_path": str(tmp_path / "analysis.wav"),
        },
    )

    report = run_transcript_for_job(job=job, transcript_processor=_FakeProcessor("ok"))
    apply_transcript_run_report_to_job(job, report)

    transcript_data, source_label = extract_transcript_source_from_job(job)

    assert transcript_data is not None
    assert source_label == "job.transcript_segments"
    assert len(transcript_data) == report.segment_count


def test_filler_word_detection_can_use_real_transcript(tmp_path: Path) -> None:
    speech = tmp_path / "speech_16k_mono.wav"
    speech.write_bytes(b"PCM")

    job = _make_job(
        raw_video_path=str(tmp_path / "video.mp4"),
        preprocessing_manifest={
            "speech_audio_path": str(speech),
            "analysis_audio_path": str(tmp_path / "analysis.wav"),
        },
    )

    transcript_report = run_transcript_for_job(
        job=job, transcript_processor=_FakeProcessor("ok")
    )
    apply_transcript_run_report_to_job(job, transcript_report)

    filler_report = run_filler_word_detection_for_job(job=job)

    assert filler_report.status in {"ok", "completed_with_warnings"}
    assert filler_report.transcript_source == "job.transcript_segments"
    assert filler_report.transcript_word_count > 0
    assert filler_report.occurrence_count >= 1


def test_filler_word_detection_stays_skipped_when_transcript_unavailable(
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

    transcript_report = run_transcript_for_job(
        job=job, transcript_processor=_FakeProcessor("unavailable")
    )
    apply_transcript_run_report_to_job(job, transcript_report)

    assert job.transcript_status == "whisper_unavailable"
    assert job.transcript_segments == []
    assert job.transcript_text == ""

    filler_report = run_filler_word_detection_for_job(job=job)

    assert filler_report.status == "skipped_no_transcript"


def test_transcript_status_marks_speech_audio_source(tmp_path: Path) -> None:
    speech = tmp_path / "speech_16k_mono.wav"
    speech.write_bytes(b"PCM")

    job = _make_job(
        raw_video_path=str(tmp_path / "video.mp4"),
        preprocessing_manifest={
            "speech_audio_path": str(speech),
            "analysis_audio_path": str(tmp_path / "analysis.wav"),
        },
        ready_audio_targets=["analysis_audio", "speech_audio"],
    )

    report = run_transcript_for_job(job=job, transcript_processor=_FakeProcessor("ok"))
    apply_transcript_run_report_to_job(job, report)

    assert job.transcript_source_type == SOURCE_TYPE_SPEECH
    assert job.transcript_source_path == str(speech)


def test_pipeline_source_imports_transcript_lifeline_before_filler() -> None:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    transcript_idx = source.find("# ── Transcript Lifeline (3-B)")
    filler_idx = source.find("# ── Filler Word Detection (2B-10-C)")

    assert transcript_idx > 0, "Transcript lifeline section is missing"
    assert filler_idx > 0, "Filler word detection section is missing"
    assert transcript_idx < filler_idx, (
        "Transcript lifeline must come BEFORE filler word detection"
    )

    assert "run_transcript_for_job" in source
    assert "apply_transcript_run_report_to_job" in source
    assert "TRANSCRIPT_STARTED" in source
    assert "TRANSCRIPT_DONE" in source
    assert "TRANSCRIPT_SKIPPED" in source
    assert "TRANSCRIPT_BLOCKED" in source
    assert "TRANSCRIPT_FAILED" in source


def test_pipeline_persists_transcript_checkpoint() -> None:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    assert 'step_name="transcript_done"' in source


def test_phase3b_pipeline_integration_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("core/transcript_source_selector.py"),
        Path("core/transcript_runner.py"),
        Path("core/gaming_pipeline.py"),
        Path("models/job.py"),
        Path("models/transcript_run.py"),
        Path("tests/test_phase3b_transcript_source_selector_smoke.py"),
        Path("tests/test_phase3b_transcript_runner_smoke.py"),
        Path("tests/test_phase3b_transcript_pipeline_integration_smoke.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
