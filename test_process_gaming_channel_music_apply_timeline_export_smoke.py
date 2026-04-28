from __future__ import annotations

import json
import os
import shutil
import subprocess
from types import SimpleNamespace

from app import process_gaming_channel
from core.local_music_catalog_repository import LocalMusicCatalogRepository
from core.music_apply_timeline_repository import MusicApplyTimelineRepository
from core.publish_package_builder import PublishPackageBuilder
from models.analysis_result import AnalysisResult
from models.edit_decision import EditDecision
from models.job import Job
from models.local_music_asset import LocalMusicAsset
from models.metadata_package import MetadataPackage
from models.publish_decision import PublishDecision
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
        "sine=frequency=1140:sample_rate=44100:duration=14",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def create_sample_music(output_path: str, frequency: int) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cmd = [
        r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={frequency}:sample_rate=44100:duration=8",
        "-c:a",
        "libmp3lame",
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
            job_id="job_process_gaming_channel_music_apply_timeline_export_smoke",
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


class FakeAnalyzer:
    def analyze(self, job):
        return AnalysisResult(
            job_id=job.job_id,
            duration_seconds=720.0,
            file_size_bytes=os.path.getsize(job.raw_video_path),
            usable_for_shorts=True,
            usable_for_longform=True,
            analysis_confidence=0.86,
            notes=["process gaming channel music apply timeline export smoke"],
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
            decision_reason="not needed for music apply timeline export smoke",
        )


class FakeRenderer:
    def render(self, job, edit_decision, final_edit_package=None, music_application_plan=None):
        output_path = os.path.join(
            "tmp",
            "process_gaming_channel_music_apply_timeline_export_smoke",
            "rendered_video.mp4",
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copyfile(job.raw_video_path, output_path)
        return output_path


class FakeSubtitleProcessor:
    def generate(self, job, edit_decision):
        return []


class FakeTitleGenerator:
    def generate(self, job):
        return TitlePackage(
            job_id=job.job_id,
            primary_title="Process Gaming Channel Music Apply Timeline Export Smoke",
            backup_titles=["Backup"],
            title_score=8.2,
        )


class FakeMetadataGenerator:
    def generate(self, job, title_package):
        return MetadataPackage(
            job_id=job.job_id,
            description="Process gaming channel music apply timeline export smoke description",
            hashtags=["#zenith", "#main", "#musictimeline"],
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


class FakeAutopublishGate:
    def decide(self, job, validator_result):
        return PublishDecision(
            job_id=job.job_id,
            decision="autopublish_allowed",
            reason="music apply timeline export smoke",
        )


class FakeShortsGenerator:
    def generate(self, package, shorts_decision, platform_targets=None):
        return []


class FakePublisher:
    def publish(self, publish_package, publish_decision):
        raise RuntimeError("Publisher should not be called in this smoke test")


class FakeExportManager:
    def export(self, publish_package):
        export_path = os.path.join(
            "exports",
            publish_package.channel_type.value,
            publish_package.job_id,
        )
        os.makedirs(export_path, exist_ok=True)

        video_target = os.path.join(export_path, "video.mp4")
        metadata_target = os.path.join(export_path, "metadata.json")

        shutil.copyfile(publish_package.video_path, video_target)

        if publish_package.thumbnail_path:
            thumbnail_target = os.path.join(export_path, "thumbnail.jpg")
            shutil.copyfile(publish_package.thumbnail_path, thumbnail_target)

        with open(metadata_target, "w", encoding="utf-8") as f:
            json.dump({"status": "ok"}, f, indent=4)

        return export_path


class FakeJobRepository:
    def save_job(self, job, export_path, publish_package, shorts_paths):
        job_path = os.path.join(export_path, "job.json")
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "job_id": job.job_id,
                    "channel_type": job.channel_type.value,
                    "platform_targets": job.target_platforms,
                },
                f,
                indent=4,
            )


def main() -> None:
    test_dir = os.path.join("tmp", "process_gaming_channel_music_apply_timeline_export_smoke")
    export_path = os.path.join(
        "exports",
        ChannelType.GAMING_MAIN.value,
        "job_process_gaming_channel_music_apply_timeline_export_smoke",
    )
    catalog_music_dir = os.path.join("assets", "audio", "gaming_main", "music")
    catalog_path = os.path.join("data", "music_catalogs", "gaming_main_music_catalog.json")

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

    music_intro_path = os.path.join(catalog_music_dir, "main_intro_bed.mp3")
    music_calm_path = os.path.join(catalog_music_dir, "main_calm_bed.mp3")

    create_sample_music(music_intro_path, 640)
    create_sample_music(music_calm_path, 520)

    assets = [
        LocalMusicAsset(
            asset_id="music_001",
            channel_type="gaming_main",
            title="Main Intro Bed",
            file_path=music_intro_path,
            duration_seconds=8.0,
            energy_level=0.61,
            mood_tags=["focused"],
            cue_kinds=["intro_bed", "transition_bed"],
            notes=[],
        ),
        LocalMusicAsset(
            asset_id="music_004",
            channel_type="gaming_main",
            title="Main Calm Bed",
            file_path=music_calm_path,
            duration_seconds=8.0,
            energy_level=0.28,
            mood_tags=["calm"],
            cue_kinds=["calm_bed", "transition_bed"],
            notes=[],
        ),
    ]
    LocalMusicCatalogRepository(catalog_path=catalog_path).save_assets(assets)

    result = process_gaming_channel(
        channel_label="Main",
        channel_type=ChannelType.GAMING_MAIN,
        raw_video_path=video_path,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        intake=FakeIntakeManager(),
        router=FakeRouter(),
        job_store=FakeJobStore(),
        analyzer=FakeAnalyzer(),
        cutter=FakeCutter(),
        shorts_engine=FakeShortsEngine(),
        title_gen=FakeTitleGenerator(),
        metadata_gen=FakeMetadataGenerator(),
        thumbnail_forge=FakeThumbnailForge(thumbnail_path),
        validator=FakeValidator(),
        publish_package_builder=PublishPackageBuilder(),
        renderer=FakeRenderer(),
        subtitle_processor=FakeSubtitleProcessor(),
        autopublish_gate=FakeAutopublishGate(),
        shorts_generator=FakeShortsGenerator(),
        publisher=FakePublisher(),
        export_manager=FakeExportManager(),
        repo=FakeJobRepository(),
        mode=Mode.NORMAL,
        scheduler=None,
        classifier=None,
    )

    assert result["pipeline"]["music_apply_timeline"] is not None

    loaded_timeline = MusicApplyTimelineRepository().load_timeline(export_path)
    assert loaded_timeline is not None
    assert len(loaded_timeline.segments) == 2
    assert result["pipeline"]["music_apply_timeline"].timeline_id == loaded_timeline.timeline_id
    assert result["pipeline"]["music_apply_result"]["music_apply_timeline_id"] == loaded_timeline.timeline_id
    assert os.path.exists(os.path.join(export_path, "music_apply_timeline.json"))

    print("PROCESS GAMING CHANNEL MUSIC APPLY TIMELINE EXPORT SMOKE TEST PASSED")
    print(
        {
            "timeline_id": loaded_timeline.timeline_id,
            "segments": len(loaded_timeline.segments),
            "asset_ids": [segment.asset_id for segment in loaded_timeline.segments],
            "timeline_score": loaded_timeline.timeline_score,
        }
    )


if __name__ == "__main__":
    main()