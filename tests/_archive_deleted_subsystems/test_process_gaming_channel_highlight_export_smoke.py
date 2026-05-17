from __future__ import annotations

import os
import shutil
import subprocess
from types import SimpleNamespace

from app import process_gaming_channel
from core.publish_package_builder import PublishPackageBuilder
from core.highlight_candidate_repository import HighlightCandidateRepository
from models.job import Job
from models.publish_decision import PublishDecision
from models.publish_result import PublishResult
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    PlatformType,
    TargetFormat,
    ValidatorStatus,
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
        "sine=frequency=970:sample_rate=44100:duration=14",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


class FakeJobStore:
    def update_job(self, job):
        return None


class FakeIntakeManager:
    def create_gaming_job(
        self,
        *,
        channel_type,
        raw_video_path,
        target_format,
        target_platforms,
        mode,
    ):
        return Job(
            job_id="job_process_gaming_channel_highlight_export_smoke",
            job_type=JobType.GAMING,
            channel_type=channel_type,
            target_format=target_format,
            target_platforms=target_platforms,
            status=JobStatus.ROUTED,
            mode=mode,
            autopublish_class=AutopublishClass.MANUAL_ONLY,
            confidence_score=0.0,
            validator_status=ValidatorStatus.NOT_VALIDATED,
            raw_video_path=raw_video_path,
        )


class FakeRouter:
    def route(self, job):
        return job


class FakeSubtitleProcessor:
    def generate(self, job, edit_decision):
        return []


class FakeTitleGenerator:
    def generate(self, job):
        from models.title_package import TitlePackage

        return TitlePackage(
            job_id=job.job_id,
            primary_title="Process Gaming Channel Highlight Export Smoke",
            backup_titles=["Backup"],
            title_score=8.1,
        )


class FakeMetadataGenerator:
    def generate(self, job, title_package):
        from models.metadata_package import MetadataPackage

        return MetadataPackage(
            job_id=job.job_id,
            description="Process gaming channel highlight export smoke description",
            hashtags=["#zenith", "#highlight", "#export"],
        )


class FakeThumbnailForge:
    def __init__(self, thumbnail_path: str):
        self.thumbnail_path = thumbnail_path

    def generate(self, job, final_video_path):
        from models.thumbnail_package import ThumbnailPackage

        return ThumbnailPackage(
            job_id=job.job_id,
            selected_thumbnail=self.thumbnail_path,
            thumbnail_variants=[self.thumbnail_path],
            thumbnail_scores=[0.92],
            selected_index=0,
        )


class FakeValidator:
    def validate(self, job, final_video_path, title_package, metadata, thumbnail_package):
        return SimpleNamespace(ready_for_publish=True)


class FakeAutopublishGate:
    def decide(self, job, validator_result):
        return PublishDecision(
            job_id=job.job_id,
            decision="autopublish_allowed",
            reason="highlight export smoke",
        )


class FakeShortsGenerator:
    def generate(self, package, shorts_decision, platform_targets=None):
        return []


class FakePublisher:
    def publish(self, publish_package, publish_decision):
        return PublishResult(
            job_id=publish_package.job_id,
            platform=publish_package.platform,
            publish_status="published",
            message="published in smoke test",
            platform_video_id=f"{publish_package.platform.value}_smoke_123",
        )


class FakeExportManager:
    def export(self, publish_package):
        export_path = os.path.join(
            "exports",
            publish_package.channel_type.value,
            publish_package.job_id,
        )
        os.makedirs(export_path, exist_ok=True)

        video_target = os.path.join(export_path, "video.mp4")
        thumbnail_target = os.path.join(export_path, "thumbnail.jpg")
        metadata_target = os.path.join(export_path, "metadata.json")

        shutil.copyfile(publish_package.video_path, video_target)
        shutil.copyfile(publish_package.thumbnail_path, thumbnail_target)

        with open(metadata_target, "w", encoding="utf-8") as f:
            f.write('{"status": "ok"}')

        return export_path


class FakeJobRepository:
    def save_job(self, job, export_path, publish_package, shorts_paths):
        job_path = os.path.join(export_path, "job.json")
        with open(job_path, "w", encoding="utf-8") as f:
            f.write(
                (
                    "{"
                    f'"job_id": "{job.job_id}", '
                    f'"channel_type": "{job.channel_type.value}", '
                    f'"platform_targets": {job.target_platforms!r}'
                    "}"
                ).replace("'", '"')
            )


class FakeScheduler:
    def is_due(self, scheduled_at):
        return True


def main() -> None:
    test_dir = os.path.join("tmp", "process_gaming_channel_highlight_export_smoke")
    export_path = os.path.join(
        "exports",
        ChannelType.GAMING_MAIN.value,
        "job_process_gaming_channel_highlight_export_smoke",
    )

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    if os.path.exists(export_path):
        shutil.rmtree(export_path)

    os.makedirs(test_dir, exist_ok=True)

    video_path = os.path.join(test_dir, "sample_video.mp4")
    thumbnail_path = os.path.join(test_dir, "sample_thumb.jpg")

    create_sample_video(video_path)

    with open(thumbnail_path, "wb") as f:
        f.write(b"fake thumbnail bytes")

    result = process_gaming_channel(
        channel_label="Main",
        channel_type=ChannelType.GAMING_MAIN,
        raw_video_path=video_path,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube", "tiktok"],
        intake=FakeIntakeManager(),
        router=FakeRouter(),
        job_store=FakeJobStore(),
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
        autopublish_gate=FakeAutopublishGate(),
        shorts_generator=FakeShortsGenerator(),
        publisher=FakePublisher(),
        export_manager=FakeExportManager(),
        repo=FakeJobRepository(),
        mode=Mode.NORMAL,
        scheduler=FakeScheduler(),
        classifier=None,
    )

    assert result["job"].job_id == "job_process_gaming_channel_highlight_export_smoke"
    assert "highlight_summary" in result["pipeline"]

    loaded = HighlightCandidateRepository().load_result(export_path)

    assert len(loaded["edit_signals"]) >= 3
    assert "signal_count" in loaded["summary"]
    assert os.path.exists(os.path.join(export_path, "highlight_intelligence.json"))

    print("PROCESS GAMING CHANNEL HIGHLIGHT EXPORT SMOKE TEST PASSED")
    print(
        {
            "signals": len(loaded["edit_signals"]),
            "highlight_candidates": len(loaded["highlight_candidates"]),
            "weak_zones": len(loaded["weak_zones"]),
            "summary": loaded["summary"],
        }
    )


if __name__ == "__main__":
    main()