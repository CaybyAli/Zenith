from __future__ import annotations

import os
import shutil
import subprocess
from shutil import copyfile
from types import SimpleNamespace

from app import run_gaming_pipeline_for_job
from core.publish_package_builder import PublishPackageBuilder
from models.analysis_result import AnalysisResult
from models.edit_decision import EditDecision
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
        job_id="job_run_gaming_pipeline_final_render_consumption_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_UNCUT,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
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
        "testsrc=size=320x180:rate=10:duration=14",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1020:sample_rate=44100:duration=14",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


class FakeAnalyzer:
    def analyze(self, job):
        return AnalysisResult(
            job_id=job.job_id,
            duration_seconds=720.0,
            file_size_bytes=os.path.getsize(job.raw_video_path),
            usable_for_shorts=True,
            usable_for_longform=True,
            analysis_confidence=0.86,
            notes=["final render consumption smoke"],
        )


class FakeCutter:
    def build_cut(self, job, analysis_result):
        return EditDecision(
            job_id=job.job_id,
            selected_segments=["0.0s - end"],
            removed_segments=[],
            target_runtime=analysis_result.duration_seconds,
            hook_candidate_range="0.0s - 3.0s",
            cut_style="basic_full_clip",
            cut_confidence=0.5,
        )


class FakeShortsEngine:
    def decide(self, job, analysis_result, edit_decision):
        return SimpleNamespace(
            job_id=job.job_id,
            shorts_count=0,
            selected_segments=[],
            decision_reason="not needed for final render consumption smoke",
        )


class CapturingRenderer:
    def __init__(self) -> None:
        self.received_final_edit_package = None

    def render(self, job, edit_decision, final_edit_package=None):
        self.received_final_edit_package = final_edit_package
        output_path = os.path.join(
            "tmp",
            "run_gaming_pipeline_final_render_consumption_smoke",
            "rendered_video.mp4",
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        copyfile(job.raw_video_path, output_path)
        return output_path


class FakeSubtitleProcessor:
    def generate(self, job, edit_decision):
        return []


class FakeTitleGenerator:
    def generate(self, job):
        return TitlePackage(
            job_id=job.job_id,
            primary_title="Run Gaming Pipeline Final Render Consumption Smoke",
            backup_titles=["Backup"],
            title_score=8.2,
        )


class FakeMetadataGenerator:
    def generate(self, job, title_package):
        return MetadataPackage(
            job_id=job.job_id,
            description="Run gaming pipeline final render consumption smoke description",
            hashtags=["#zenith", "#final", "#render"],
        )


class FakeThumbnailForge:
    def __init__(self, thumbnail_path: str):
        self.thumbnail_path = thumbnail_path

    def generate(self, job, final_video_path):
        return ThumbnailPackage(
            job_id=job.job_id,
            selected_thumbnail=self.thumbnail_path,
            thumbnail_variants=[self.thumbnail_path],
            thumbnail_scores=[0.91],
            selected_index=0,
        )


class FakeValidator:
    def validate(self, job, final_video_path, title_package, metadata, thumbnail_package):
        return SimpleNamespace(ready_for_publish=True)


def main() -> None:
    test_dir = os.path.join("tmp", "run_gaming_pipeline_final_render_consumption_smoke")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    video_path = os.path.join(test_dir, "sample_video.mp4")
    thumbnail_path = os.path.join(test_dir, "sample_thumb.jpg")

    create_sample_video(video_path)

    with open(thumbnail_path, "wb") as f:
        f.write(b"fake thumbnail bytes")

    job = build_job(video_path)
    renderer = CapturingRenderer()

    result = run_gaming_pipeline_for_job(
        job=job,
        analyzer=FakeAnalyzer(),
        cutter=FakeCutter(),
        shorts_engine=FakeShortsEngine(),
        title_gen=FakeTitleGenerator(),
        metadata_gen=FakeMetadataGenerator(),
        thumbnail_forge=FakeThumbnailForge(thumbnail_path),
        validator=FakeValidator(),
        publish_package_builder=PublishPackageBuilder(),
        renderer=renderer,
        subtitle_processor=FakeSubtitleProcessor(),
    )

    assert result["final_edit_package"] is not None
    assert renderer.received_final_edit_package is not None
    assert renderer.received_final_edit_package["render_strategy"] == "integrated_timeline_window"
    assert renderer.received_final_edit_package["timeline_end_time"] > renderer.received_final_edit_package["timeline_start_time"]
    assert renderer.received_final_edit_package["audio_cues"] >= 1
    assert renderer.received_final_edit_package["integration_score"] >= 0.70

    print("RUN GAMING PIPELINE FINAL RENDER CONSUMPTION SMOKE TEST PASSED")
    print(renderer.received_final_edit_package)


if __name__ == "__main__":
    main()