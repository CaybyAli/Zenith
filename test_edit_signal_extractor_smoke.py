from __future__ import annotations

import os
import shutil
import subprocess

from core.edit_signal_extractor import EditSignalExtractor
from models.analysis_result import AnalysisResult
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


def build_job(video_path: str) -> Job:
    return Job(
        job_id="job_edit_signal_extractor_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube", "tiktok"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path=video_path,
    )


def create_sample_video(output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=640x360:rate=25:duration=12",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=880:sample_rate=44100:duration=12",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def main() -> None:
    test_dir = os.path.join("tmp", "edit_signal_extractor_smoke")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    video_path = os.path.join(test_dir, "sample_signal_video.mp4")
    create_sample_video(video_path)

    job = build_job(video_path)
    analysis_result = AnalysisResult(
        job_id=job.job_id,
        duration_seconds=12.0,
        file_size_bytes=os.path.getsize(video_path),
        usable_for_shorts=False,
        usable_for_longform=False,
        analysis_confidence=0.8,
        notes=["synthetic signal test"],
    )

    extractor = EditSignalExtractor()
    signals = extractor.extract(job, analysis_result)

    assert len(signals) >= 3
    assert any(signal.signal_type == "duration_context" for signal in signals)
    assert any(signal.signal_type in {"audio_peak", "audio_activity", "silence_zone"} for signal in signals)
    assert any(signal.signal_type in {"motion_peak", "motion_activity", "low_motion_zone"} for signal in signals)
    assert all(signal.job_id == job.job_id for signal in signals)

    print("EDIT SIGNAL EXTRACTOR SMOKE TEST PASSED")
    print(
        {
            "signals": len(signals),
            "signal_types": sorted({signal.signal_type for signal in signals}),
        }
    )


if __name__ == "__main__":
    main()