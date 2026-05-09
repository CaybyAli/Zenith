from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from core.job_profile_metadata import (
    PROFILE_METADATA_KEYS,
    apply_profile_metadata_to_job,
    build_profile_metadata,
)
from core.profile_manager import ProfileManager
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


PROFILES_DIR = Path(__file__).parent.parent / "profiles"


def _fake_job():
    return SimpleNamespace()


def _real_job() -> Job:
    return Job(
        job_id="job_profile_metadata_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.CREATED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/test.mp4",
    )


def test_build_profile_metadata_contains_required_fields():
    profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("gaming_main")

    metadata = build_profile_metadata(
        profile=profile,
        profile_snapshot_path="exports/gaming_main/job_x/profile_snapshot.json",
    )

    assert set(PROFILE_METADATA_KEYS) <= set(metadata.keys())
    assert metadata["profile_id"] == "gaming_main"
    assert metadata["quality_mode"] == "pro"
    assert metadata["profile_version"] == "1.0.0"
    assert metadata["profile_snapshot_path"] == "exports/gaming_main/job_x/profile_snapshot.json"
    assert metadata["profile_source"] == "json_profile_manager"
    assert metadata["cut_aggressiveness"] == 0.85
    assert metadata["source_aspect_ratio"] == "32:9"
    assert metadata["target_format"] == "16:9"
    assert metadata["reframing_mode"] == "intelligent_crop"

    json.dumps(metadata)


def test_apply_profile_metadata_to_fake_job_sets_fields():
    profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("gaming_main")
    job = _fake_job()

    metadata = apply_profile_metadata_to_job(
        job=job,
        profile=profile,
        profile_snapshot_path="exports/gaming_main/job_x/profile_snapshot.json",
    )

    assert job.profile_id == "gaming_main"
    assert job.quality_mode == "pro"
    assert job.profile_version == "1.0.0"
    assert job.profile_snapshot_path == "exports/gaming_main/job_x/profile_snapshot.json"
    assert job.profile_source == "json_profile_manager"
    assert job.profile_metadata == metadata


def test_job_to_dict_and_from_dict_preserve_profile_metadata():
    profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("gaming_main")
    job = _real_job()

    metadata = apply_profile_metadata_to_job(
        job=job,
        profile=profile,
        profile_snapshot_path="exports/gaming_main/job_profile_metadata_smoke/profile_snapshot.json",
    )

    data = job.to_dict()

    assert data["profile_id"] == "gaming_main"
    assert data["quality_mode"] == "pro"
    assert data["profile_version"] == "1.0.0"
    assert data["profile_snapshot_path"] == "exports/gaming_main/job_profile_metadata_smoke/profile_snapshot.json"
    assert data["profile_source"] == "json_profile_manager"
    assert data["profile_metadata"] == metadata

    loaded = Job.from_dict(data)

    assert loaded.profile_id == "gaming_main"
    assert loaded.quality_mode == "pro"
    assert loaded.profile_version == "1.0.0"
    assert loaded.profile_snapshot_path == "exports/gaming_main/job_profile_metadata_smoke/profile_snapshot.json"
    assert loaded.profile_source == "json_profile_manager"
    assert loaded.profile_metadata == metadata


def test_fallback_profile_metadata_is_serializable():
    profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("unknown_profile_xyz")

    metadata = build_profile_metadata(
        profile=profile,
        profile_snapshot_path=None,
    )

    assert metadata["profile_id"] == "unknown_profile_xyz"
    assert metadata["quality_mode"] == "balanced"
    assert metadata["profile_version"] == "1.0.0"
    assert metadata["profile_snapshot_path"] is None
    assert metadata["profile_source"] == "json_profile_manager"

    json.dumps(metadata)
