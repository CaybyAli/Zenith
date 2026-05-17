from __future__ import annotations

import os
import shutil
import subprocess
from types import SimpleNamespace

from app import run_gaming_pipeline_for_job
from core.publish_package_builder import PublishPackageBuilder
from models.job import Job
from models.metadata_package import MetadataPackage
from models.thumbnail_package import ThumbnailPackage
from models.title_package import TitlePackage
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
        job_id="job_run_gaming_pipeline_highlight_smoke",
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
        "sine=frequency=950:sample_rate=44100:duration=14",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


class FakeSubtitleProcessor:
    def generate(self, job, edit_decision):
        return []


class FakeTitleGenerator:
    def generate(self, job):
        return TitlePackage(
            job_id=job.job_id,
            primary_title="Run Gaming Pipeline Highlight Smoke",
            backup_titles=["Backup"],
            title_score=8.0,
        )


class FakeMetadataGenerator:
    def generate(self, job, title_package):
        return MetadataPackage(
            job_id=job.job_id,
            description="Run gaming pipeline highlight smoke description",
            hashtags=["#zenith", "#highlight"],
        )


class FakeThumbnailForge:
    def __init__(self, thumbnail_path: str):
        self.thumbnail_path = thumbnail_path

    def generate(self, job, final_video_path):
        return ThumbnailPackage(
            job_id=job.job_id,
            selected_thumbnail=self.thumbnail_path,
            thumbnail_variants=[self.thumbnail_path],
            thumbnail_scores=[0.9],
            selected_index=0,
        )


class FakeValidator:
    def validate(self, job, final_video_path, title_package, metadata, thumbnail_package):
        return SimpleNamespace(ready_for_publish=True)


def main() -> None:
    test_dir = os.path.join("tmp", "run_gaming_pipeline_highlight_smoke")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    video_path = os.path.join(test_dir, "sample_pipeline_video.mp4")
    thumbnail_path = os.path.join(test_dir, "sample_thumb.jpg")

    create_sample_video(video_path)

    with open(thumbnail_path, "wb") as f:
        f.write(b"fake thumbnail bytes")

    job = build_job(video_path)

    result = run_gaming_pipeline_for_job(
        job=job,
        analyzer=__import__("core.gaming_analyzer", fromlist=["GamingAnalyzer"]).GamingAnalyzer(),
        cutter=__import__("core.gaming_cutter", fromlist=["GamingCutter"]).GamingCutter(),
        shorts_engine=__import__("core.shorts_decision_engine", fromlist=["ShortsDecisionEngine"]).ShortsDecisionEngine(),
        title_gen=FakeTitleGenerator(),
        metadata_gen=FakeMetadataGenerator(),
        thumbnail_forge=FakeThumbnailForge(thumbnail_path),
        validator=FakeValidator(),
        publish_package_builder=PublishPackageBuilder(),
        renderer=__import__("core.render_processor", fromlist=["RenderProcessor"]).RenderProcessor(),
        subtitle_processor=FakeSubtitleProcessor(),
    )

    assert result["analysis_result"].job_id == job.job_id
    assert len(result["edit_signals"]) >= 3
    assert isinstance(result["highlight_candidates"], list)
    assert isinstance(result["weak_zones"], list)
    assert "signal_count" in result["highlight_summary"]
    assert len(result["publish_packages"]) >= 1
    assert os.path.exists(result["final_video_path"])

    print("RUN GAMING PIPELINE HIGHLIGHT SMOKE TEST PASSED")
    print(
        {
            "signals": len(result["edit_signals"]),
            "highlight_candidates": len(result["highlight_candidates"]),
            "weak_zones": len(result["weak_zones"]),
            "publish_packages": len(result["publish_packages"]),
        }
    )


if __name__ == "__main__":
    main()