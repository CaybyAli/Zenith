from __future__ import annotations

import os
import shutil
import subprocess

from core.edit_signal_extractor import EditSignalExtractor
from core.highlight_candidate_repository import HighlightCandidateRepository
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
        job_id="job_highlight_candidate_repository_smoke",
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
        "sine=frequency=900:sample_rate=44100:duration=14",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def main() -> None:
    test_dir = os.path.join("tmp", "highlight_candidate_repository_smoke")
    export_path = os.path.join(test_dir, "export")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    video_path = os.path.join(test_dir, "sample_repository_video.mp4")
    create_sample_video(video_path)

    job = build_job(video_path)
    analysis_result = AnalysisResult(
        job_id=job.job_id,
        duration_seconds=14.0,
        file_size_bytes=os.path.getsize(video_path),
        usable_for_shorts=False,
        usable_for_longform=False,
        analysis_confidence=0.8,
        notes=["synthetic repository test"],
    )

    signals = EditSignalExtractor().extract(job, analysis_result)
    selection = HighlightSelector().select(job, analysis_result, signals)

    repository = HighlightCandidateRepository()
    saved_file = repository.save_result(
        export_path,
        edit_signals=signals,
        highlight_candidates=selection["highlight_candidates"],
        weak_zones=selection["weak_zones"],
        summary=selection["summary"],
    )

    loaded = repository.load_result(export_path)

    assert os.path.exists(saved_file)
    assert len(loaded["edit_signals"]) == len(signals)
    assert len(loaded["highlight_candidates"]) == len(selection["highlight_candidates"])
    assert len(loaded["weak_zones"]) == len(selection["weak_zones"])
    assert loaded["summary"]["signal_count"] == selection["summary"]["signal_count"]

    print("HIGHLIGHT CANDIDATE REPOSITORY SMOKE TEST PASSED")
    print(
        {
            "saved_file": saved_file,
            "signals": len(loaded["edit_signals"]),
            "highlight_candidates": len(loaded["highlight_candidates"]),
            "weak_zones": len(loaded["weak_zones"]),
        }
    )


if __name__ == "__main__":
    main()