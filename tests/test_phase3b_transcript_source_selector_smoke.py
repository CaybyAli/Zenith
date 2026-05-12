from __future__ import annotations

from pathlib import Path

from core.transcript_source_selector import (
    SOURCE_TYPE_ANALYSIS,
    SOURCE_TYPE_RAW_VIDEO,
    SOURCE_TYPE_SPEECH,
    TranscriptSourceSelection,
    select_transcript_source,
    select_transcript_source_for_job,
)
from models.job import Job
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
        job_id="job_phase3b_source_selector_001",
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


def test_selection_dataclass_to_dict_roundtrip() -> None:
    selection = TranscriptSourceSelection(
        status="selected",
        selected_path="x.wav",
        selected_type=SOURCE_TYPE_SPEECH,
        recommendation="transcribe_speech_audio",
    )

    data = selection.to_dict()

    assert data["status"] == "selected"
    assert data["selected_path"] == "x.wav"
    assert data["selected_type"] == SOURCE_TYPE_SPEECH
    assert data["recommendation"] == "transcribe_speech_audio"


def test_speech_audio_is_preferred_when_present(tmp_path: Path) -> None:
    speech = tmp_path / "speech_16k_mono.wav"
    speech.write_bytes(b"PCM")
    analysis = tmp_path / "analysis.wav"
    analysis.write_bytes(b"PCM")

    manifest = {
        "speech_audio_path": str(speech),
        "analysis_audio_path": str(analysis),
    }

    selection = select_transcript_source(
        preprocessing_manifest=manifest,
        raw_video_path=None,
    )

    assert selection.status == "selected"
    assert selection.selected_type == SOURCE_TYPE_SPEECH
    assert selection.selected_path == str(speech)
    assert selection.recommendation == "transcribe_speech_audio"


def test_analysis_audio_is_fallback_when_speech_missing(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis.wav"
    analysis.write_bytes(b"PCM")

    manifest = {
        "speech_audio_path": str(tmp_path / "speech_16k_mono.wav"),
        "analysis_audio_path": str(analysis),
    }

    selection = select_transcript_source(
        preprocessing_manifest=manifest,
        raw_video_path=None,
    )

    assert selection.status == "selected_fallback"
    assert selection.selected_type == SOURCE_TYPE_ANALYSIS
    assert selection.selected_path == str(analysis)
    assert "analysis_audio_used_for_transcript" in selection.warnings


def test_blocked_when_preprocessed_paths_declared_but_missing(tmp_path: Path) -> None:
    manifest = {
        "speech_audio_path": str(tmp_path / "speech_16k_mono.wav"),
        "analysis_audio_path": str(tmp_path / "analysis.wav"),
    }

    selection = select_transcript_source(
        preprocessing_manifest=manifest,
        raw_video_path=str(tmp_path / "video.mp4"),
    )

    assert selection.status == "blocked_missing_preprocessed_audio"
    assert selection.selected_path is None
    assert "preprocessed_audio_missing" in selection.errors


def test_raw_video_fallback_when_no_preprocessed_paths(tmp_path: Path) -> None:
    raw_video = tmp_path / "video.mp4"
    raw_video.write_bytes(b"\x00\x00\x00\x20ftyp")

    selection = select_transcript_source(
        preprocessing_manifest=None,
        raw_video_path=str(raw_video),
        allow_raw_video_fallback=True,
    )

    assert selection.status == "selected_fallback"
    assert selection.selected_type == SOURCE_TYPE_RAW_VIDEO
    assert selection.selected_path == str(raw_video)
    assert "raw_video_used_for_transcript" in selection.warnings


def test_raw_video_fallback_can_be_disabled(tmp_path: Path) -> None:
    raw_video = tmp_path / "video.mp4"
    raw_video.write_bytes(b"\x00\x00\x00\x20ftyp")

    selection = select_transcript_source(
        preprocessing_manifest=None,
        raw_video_path=str(raw_video),
        allow_raw_video_fallback=False,
    )

    assert selection.status == "skipped_no_audio_source"
    assert selection.selected_path is None


def test_missing_everything_is_skipped() -> None:
    selection = select_transcript_source(
        preprocessing_manifest=None,
        raw_video_path=None,
    )

    assert selection.status == "skipped_no_audio_source"
    assert selection.selected_path is None
    assert selection.recommendation == "no_audio_source_available"


def test_select_for_job_reads_preprocessing_manifest(tmp_path: Path) -> None:
    speech = tmp_path / "speech_16k_mono.wav"
    speech.write_bytes(b"PCM")

    job = _make_job(
        raw_video_path=str(tmp_path / "video.mp4"),
        preprocessing_manifest={
            "speech_audio_path": str(speech),
            "analysis_audio_path": str(tmp_path / "analysis.wav"),
        },
    )

    selection = select_transcript_source_for_job(job=job)

    assert selection.status == "selected"
    assert selection.selected_type == SOURCE_TYPE_SPEECH


def test_select_for_job_falls_back_to_raw_video_without_manifest(tmp_path: Path) -> None:
    raw_video = tmp_path / "video.mp4"
    raw_video.write_bytes(b"\x00\x00\x00\x20ftyp")

    job = _make_job(raw_video_path=str(raw_video))

    selection = select_transcript_source_for_job(job=job)

    assert selection.status == "selected_fallback"
    assert selection.selected_type == SOURCE_TYPE_RAW_VIDEO


def test_phase3b_source_selector_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("core/transcript_source_selector.py"),
        Path("tests/test_phase3b_transcript_source_selector_smoke.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
