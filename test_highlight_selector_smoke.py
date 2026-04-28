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
        job_id="job_highlight_selector_smoke",
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
        "testsrc=size=640x360:rate=25:duration=14",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:sample_rate=44100:duration=14",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def main() -> None:
    test_dir = os.path.join("tmp", "highlight_selector_smoke")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    video_path = os.path.join(test_dir, "sample_highlight_video.mp4")
    create_sample_video(video_path)

    job = build_job(video_path)
    analysis_result = AnalysisResult(
        job_id=job.job_id,
        duration_seconds=14.0,
        file_size_bytes=os.path.getsize(video_path),
        usable_for_shorts=False,
        usable_for_longform=False,
        analysis_confidence=0.8,
        notes=["synthetic highlight selector test"],
    )

    signals = EditSignalExtractor().extract(job, analysis_result)
    result = HighlightSelector().select(job, analysis_result, signals)

    highlight_candidates = result["highlight_candidates"]
    weak_zones = result["weak_zones"]
    summary = result["summary"]

    assert len(highlight_candidates) >= 1
    assert summary["signal_count"] >= 3
    assert summary["highlight_candidates"] == len(highlight_candidates)
    assert summary["weak_zones"] == len(weak_zones)
    assert all(candidate.job_id == job.job_id for candidate in highlight_candidates)
    assert all(candidate.highlight_score >= 0.45 for candidate in highlight_candidates)
    assert any(
        candidate.candidate_kind in {"speech_peak", "action_peak", "unknown"}
        for candidate in highlight_candidates
    )

    print("HIGHLIGHT SELECTOR SMOKE TEST PASSED")
    print(
        {
            "signals": summary["signal_count"],
            "highlight_candidates": len(highlight_candidates),
            "weak_zones": len(weak_zones),
            "candidate_kinds": sorted({candidate.candidate_kind for candidate in highlight_candidates}),
        }
    )


if __name__ == "__main__":
    main()