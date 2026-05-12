from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.ffmpeg_helper import get_ffmpeg_path
from core.filler_word_runner import run_filler_word_detection_for_job
from core.preprocessing_pipeline import run_preprocessing_pipeline_for_job
from core.transcript_runner import (
    apply_transcript_run_report_to_job,
    run_transcript_for_job,
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


JOB_ID = "phase3b_proof_001"
TMP_ROOT = REPO_ROOT / "tmp" / "phase3b_proof"
PREPROCESSED_ROOT = TMP_ROOT / "preprocessed"
SOURCE_DIR = TMP_ROOT / "input"


def _build_speech_like_test_video(target: Path, speech_wav: Path | None = None) -> Path:
    ffmpeg = get_ffmpeg_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    if speech_wav is not None and Path(speech_wav).exists():
        command = [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-loglevel", "error",
            "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=8:size=320x240:rate=24",
            "-i", str(speech_wav),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(target),
        ]
    else:
        command = [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-loglevel", "error",
            "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=3:size=320x240:rate=24",
            "-f", "lavfi",
            "-i", "sine=frequency=220:duration=3",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(target),
        ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return target


def _check_whisper_available() -> dict[str, bool]:
    info: dict[str, bool] = {"faster_whisper": False, "openai_whisper": False}
    try:
        import faster_whisper  # noqa: F401
        info["faster_whisper"] = True
    except Exception:
        pass
    try:
        import whisper  # noqa: F401
        info["openai_whisper"] = True
    except Exception:
        pass
    return info


def main() -> int:
    # Look for an externally provided speech sample BEFORE we wipe TMP_ROOT.
    speech_sample = TMP_ROOT / "input" / "speech_sample.wav"
    speech_sample_exists = speech_sample.exists()
    speech_sample_bytes = speech_sample.read_bytes() if speech_sample_exists else None

    if TMP_ROOT.exists():
        shutil.rmtree(TMP_ROOT)

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    if speech_sample_bytes is not None:
        restored = SOURCE_DIR / "speech_sample.wav"
        restored.write_bytes(speech_sample_bytes)
        source_path = _build_speech_like_test_video(
            SOURCE_DIR / "sample.mp4", speech_wav=restored
        )
    else:
        source_path = _build_speech_like_test_video(SOURCE_DIR / "sample.mp4")

    whisper_status = _check_whisper_available()

    job = Job(
        job_id=JOB_ID,
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path=str(source_path),
    )

    preprocess_report = run_preprocessing_pipeline_for_job(
        job=job,
        source_path=source_path,
        root_dir=PREPROCESSED_ROOT,
        metadata={"stage": "3-A", "proof": True},
    )

    speech_path = Path(preprocess_report["preprocessing_manifest"]["speech_audio_path"])

    transcript_report = run_transcript_for_job(
        job=job,
        allow_raw_video_fallback=True,
        require_existing_file=True,
        metadata={"stage": "3-B", "job_id": JOB_ID},
    )
    apply_transcript_run_report_to_job(job, transcript_report)

    filler_report = run_filler_word_detection_for_job(job=job)
    job.filler_word_status = filler_report.status
    job.filler_word_transcript_source = filler_report.transcript_source
    job.filler_word_occurrence_count = filler_report.occurrence_count

    job_dump_path = TMP_ROOT / "job.json"
    job_dump_path.write_text(
        json.dumps(job.to_dict(), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    summary = {
        "job_id": JOB_ID,
        "input": str(source_path),
        "speech_wav_path": str(speech_path),
        "speech_wav_exists": speech_path.exists(),
        "speech_wav_size_bytes": speech_path.stat().st_size if speech_path.exists() else None,
        "preprocessing_status": preprocess_report["status"],
        "audio_extraction_status": preprocess_report["audio_extraction_status"],
        "ready_audio_targets": preprocess_report["ready_audio_targets"],
        "transcript_status": transcript_report.status,
        "transcript_source_type": transcript_report.source_type,
        "transcript_source_path": transcript_report.source_path,
        "transcript_engine": transcript_report.engine,
        "transcript_language": transcript_report.language,
        "transcript_segment_count": transcript_report.segment_count,
        "transcript_word_count": transcript_report.word_count,
        "transcript_duration_seconds": transcript_report.duration_seconds,
        "transcript_text_length": len(transcript_report.full_text or ""),
        "transcript_text_preview": (transcript_report.full_text or "")[:160],
        "transcript_warnings": list(transcript_report.warnings or []),
        "transcript_errors": list(transcript_report.errors or []),
        "filler_word_status": filler_report.status,
        "filler_word_transcript_source": filler_report.transcript_source,
        "filler_word_occurrence_count": filler_report.occurrence_count,
        "whisper_engines_available": whisper_status,
        "job_dump_path": str(job_dump_path),
    }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
