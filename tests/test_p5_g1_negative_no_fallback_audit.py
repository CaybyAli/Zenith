from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.audio_stream_inspector import AudioStream, AudioStreamInventory
from core.transcript_processor import TranscriptProcessor
from core.transcript_runner import apply_transcript_run_report_to_job, run_transcript_for_job
from core.transcription_engine import FasterWhisperEngine


class FakeSingleTrackInspector:
    def inspect(self, video_path: str) -> AudioStreamInventory:
        return AudioStreamInventory(
            streams=[AudioStream(1, 1, 48000, "aac", 1.0, "mic")],
            is_multi_track=False,
            has_mic_track=True,
            has_discord_track=False,
            has_ingame_track=False,
        )


def test_whisperx_unavailable_marks_job_error_and_does_not_call_faster_whisper(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.mp4"
    source.write_bytes(b"placeholder media")
    monkeypatch.setenv("ZENITH_WHISPERX_DISABLE", "1")

    faster_whisper_calls: list[str] = []

    def fail_on_faster_whisper_call(self, *args, **kwargs):
        faster_whisper_calls.append("called")
        raise AssertionError("faster_whisper_called")

    monkeypatch.setattr(FasterWhisperEngine, "transcribe", fail_on_faster_whisper_call)

    job = SimpleNamespace(
        job_id="job_p5_g1_negative",
        raw_video_path=str(source),
        preprocessing_manifest={},
        transcription_engine="whisperx",
    )

    processor = TranscriptProcessor(
        allow_test_fallback=False,
        transcription_engine="whisperx",
        audio_stream_inspector=FakeSingleTrackInspector(),
    )

    report = run_transcript_for_job(
        job,
        transcript_processor=processor,
        allow_raw_video_fallback=True,
        require_existing_file=True,
        metadata={"stage": "p5_g1_negative", "transcription_engine": "whisperx"},
    )

    apply_transcript_run_report_to_job(job, report)

    assert report.status == "whisper_unavailable"
    assert report.recommendation == "install_whisper_engine"
    assert report.metadata["transcription_engine"] == "whisperx"
    assert job.transcript_status == "whisper_unavailable"
    assert job.transcription_engine == "whisperx"
    assert faster_whisper_calls == []

    print(
        "P5_G1_NEGATIVE_AUDIT "
        f"job_id={job.job_id} "
        f"report_status={report.status} "
        f"job_transcript_status={job.transcript_status} "
        f"job_transcription_engine={job.transcription_engine} "
        f"faster_whisper_calls={len(faster_whisper_calls)}"
    )
