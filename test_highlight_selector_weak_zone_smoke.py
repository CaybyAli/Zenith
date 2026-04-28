from __future__ import annotations

import os
import shutil
import subprocess

from core.edit_signal_extractor import EditSignalExtractor
from core.highlight_selector import HighlightSelector
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
        job_id="job_highlight_selector_weak_zone_smoke",
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


def create_low_activity_video(output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:size=640x360:rate=25:duration=14",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=stereo",
        "-t",
        "14",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def main() -> None:
    test_dir = os.path.join("tmp", "highlight_selector_weak_zone_smoke")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    video_path = os.path.join(test_dir, "sample_weak_zone_video.mp4")
    create_low_activity_video(video_path)

    job = build_job(video_path)
    analysis_result = AnalysisResult(
        job_id=job.job_id,
        duration_seconds=14.0,
        file_size_bytes=os.path.getsize(video_path),
        usable_for_shorts=False,
        usable_for_longform=False,
        analysis_confidence=0.8,
        notes=["synthetic weak zone test"],
    )

    signals = EditSignalExtractor().extract(job, analysis_result)
    result = HighlightSelector().select(job, analysis_result, signals)

    weak_zones = result["weak_zones"]
    summary = result["summary"]

    assert len(weak_zones) >= 1
    assert summary["weak_zones"] == len(weak_zones)
    assert all(zone.candidate_kind == "drop_zone" for zone in weak_zones)
    assert all(zone.highlight_score >= 0.45 for zone in weak_zones)

    print("HIGHLIGHT SELECTOR WEAK ZONE SMOKE TEST PASSED")
    print(
        {
            "signals": summary["signal_count"],
            "highlight_candidates": summary["highlight_candidates"],
            "weak_zones": len(weak_zones),
        }
    )


if __name__ == "__main__":
    main()