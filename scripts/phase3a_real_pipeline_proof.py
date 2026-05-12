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
from core.preprocessing_pipeline import run_preprocessing_pipeline_for_job
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


JOB_ID = "phase3a_proof_001"
TMP_ROOT = REPO_ROOT / "tmp" / "phase3a_proof"
PREPROCESSED_ROOT = TMP_ROOT / "preprocessed"
SOURCE_DIR = TMP_ROOT / "input"


def _build_test_video(target: Path) -> Path:
    ffmpeg = get_ffmpeg_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-loglevel", "error",
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=2:size=320x240:rate=24",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(target),
    ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return target


def main() -> int:
    if TMP_ROOT.exists():
        shutil.rmtree(TMP_ROOT)

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    source_path = _build_test_video(SOURCE_DIR / "sample.mp4")

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

    report = run_preprocessing_pipeline_for_job(
        job=job,
        source_path=source_path,
        root_dir=PREPROCESSED_ROOT,
        metadata={"stage": "3-A", "proof": True},
    )

    manifest = report["preprocessing_manifest"]
    analysis = Path(manifest["analysis_audio_path"])
    speech = Path(manifest["speech_audio_path"])
    music = Path(manifest["music_audio_path"])

    job_dump_path = TMP_ROOT / "job.json"
    job_dump_path.write_text(
        json.dumps(job.to_dict(), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    cache_validation = report["cache_validation"]

    summary = {
        "job_id": JOB_ID,
        "input": str(source_path),
        "analysis_wav_path": str(analysis),
        "analysis_wav_size_bytes": analysis.stat().st_size if analysis.exists() else None,
        "speech_wav_path": str(speech),
        "speech_wav_size_bytes": speech.stat().st_size if speech.exists() else None,
        "music_wav_path": str(music),
        "music_wav_size_bytes": music.stat().st_size if music.exists() else None,
        "manifest_path": report["manifest_path"],
        "preprocessing_status": report["status"],
        "audio_extraction_status": report["audio_extraction_status"],
        "ready_audio_targets": report["ready_audio_targets"],
        "missing_audio_targets": report["missing_audio_targets"],
        "failed_audio_targets": report["failed_audio_targets"],
        "cache_validation_ready_targets": cache_validation.get("ready_targets"),
        "cache_validation_missing_targets": cache_validation.get("missing_targets"),
        "job_audio_extraction_status": job.audio_extraction_status,
        "job_ready_audio_targets": job.ready_audio_targets,
        "job_missing_audio_targets": job.missing_audio_targets,
        "job_failed_audio_targets": job.failed_audio_targets,
        "job_dump_path": str(job_dump_path),
    }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
