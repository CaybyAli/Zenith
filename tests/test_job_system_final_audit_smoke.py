from __future__ import annotations

import json
from pathlib import Path

from core.job_profile_metadata import apply_profile_metadata_to_job
from core.job_recovery import apply_recovery_report_to_job, build_recovery_report
from core.job_state_persistence import (
    build_job_state_checkpoint,
    persist_job_state_checkpoint,
)
from core.job_state_transitions import transition_job_state
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


ROOT_DIR = Path(__file__).parent.parent
PROFILES_DIR = ROOT_DIR / "profiles"


def _job() -> Job:
    return Job(
        job_id="job_system_final_audit_smoke",
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


def test_job_model_persists_profile_state_and_recovery_fields():
    job = _job()
    profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("gaming_main")

    metadata = apply_profile_metadata_to_job(
        job=job,
        profile=profile,
        profile_snapshot_path=(
            "exports/gaming_main/job_system_final_audit_smoke/profile_snapshot.json"
        ),
    )

    transition_job_state(
        job,
        JobStatus.ANALYZING,
        module="gaming_pipeline",
        reason="pipeline_analysis_started",
    )

    recovery_report = {
        "recovery_status": "clean_complete",
        "resume_safety": "safe",
        "recommended_action": "review_or_publish",
        "checkpoint_count": 7,
        "state_history_count": 7,
        "reason": "job_reached_reviewable_complete_state",
    }
    apply_recovery_report_to_job(job, recovery_report)

    data = job.to_dict()
    json.dumps(data)

    assert data["profile_id"] == "gaming_main"
    assert data["quality_mode"] == "pro"
    assert data["profile_version"] == "1.0.0"
    assert data["profile_snapshot_path"].endswith("profile_snapshot.json")
    assert data["profile_source"] == "json_profile_manager"
    assert data["profile_metadata"] == metadata
    assert len(data["state_history"]) == 1
    assert data["recovery_status"] == "clean_complete"
    assert data["resume_safety"] == "safe"
    assert data["recovery_report"]["recommended_action"] == "review_or_publish"

    loaded = Job.from_dict(data)

    assert loaded.profile_id == "gaming_main"
    assert loaded.quality_mode == "pro"
    assert loaded.profile_version == "1.0.0"
    assert loaded.profile_source == "json_profile_manager"
    assert loaded.profile_metadata == metadata
    assert len(loaded.state_history) == 1
    assert loaded.recovery_status == "clean_complete"
    assert loaded.resume_safety == "safe"
    assert loaded.recovery_report["recovery_status"] == "clean_complete"


def test_full_state_flow_checkpoint_and_recovery_report(tmp_path):
    job = _job()
    profile = ProfileManager(profiles_dir=PROFILES_DIR).load_profile("gaming_main")

    apply_profile_metadata_to_job(
        job=job,
        profile=profile,
        profile_snapshot_path=tmp_path / "profile_snapshot.json",
    )

    transition_job_state(
        job,
        JobStatus.ANALYZING,
        module="gaming_pipeline",
        reason="pipeline_analysis_started",
    )
    transition_job_state(
        job,
        JobStatus.ANALYZED,
        module="gaming_pipeline",
        reason="analysis_finished",
    )
    transition_job_state(
        job,
        JobStatus.CUTTING,
        module="gaming_pipeline",
        reason="cutting_started",
    )
    transition_job_state(
        job,
        JobStatus.CUT,
        module="gaming_pipeline",
        reason="cutting_finished",
    )
    transition_job_state(
        job,
        JobStatus.RENDERING,
        module="gaming_pipeline",
        reason="rendering_started",
    )
    transition_job_state(
        job,
        JobStatus.RENDERED,
        module="gaming_pipeline",
        reason="rendering_finished",
    )
    transition_job_state(
        job,
        JobStatus.ASSEMBLED,
        module="pipeline_runner",
        reason="export_finished",
    )

    checkpoint = build_job_state_checkpoint(
        job=job,
        step_name="assembled",
        reason="export_finished",
    )
    persisted_checkpoint = persist_job_state_checkpoint(
        job=job,
        export_dir=tmp_path,
        step_name="assembled",
        reason="export_finished",
    )

    checkpoint_path = tmp_path / "job_state_checkpoint.json"
    checkpoint_jsonl_path = tmp_path / "job_state_checkpoints.jsonl"

    assert checkpoint["status"] == "assembled"
    assert persisted_checkpoint["status"] == "assembled"
    assert checkpoint_path.exists()
    assert checkpoint_jsonl_path.exists()
    assert len(checkpoint_jsonl_path.read_text(encoding="utf-8").splitlines()) == 1

    recovery_report = build_recovery_report(job, export_dir=tmp_path)
    apply_recovery_report_to_job(job, recovery_report)

    assert job.status == JobStatus.ASSEMBLED
    assert len(job.state_history) == 7
    assert recovery_report["recovery_status"] == "clean_complete"
    assert recovery_report["resume_safety"] == "safe"
    assert recovery_report["recommended_action"] == "review_or_publish"
    assert recovery_report["checkpoint_count"] == 1
    assert recovery_report["state_history_count"] == 7

    json.dumps(job.to_dict())
    json.dumps(checkpoint)
    json.dumps(persisted_checkpoint)
    json.dumps(recovery_report)


def test_job_system_files_have_no_bom_and_end_with_newline():
    files = [
        "core/job_profile_metadata.py",
        "core/job_state_transitions.py",
        "core/job_state_persistence.py",
        "core/job_recovery.py",
        "tests/test_job_profile_metadata_smoke.py",
        "tests/test_job_state_transitions_smoke.py",
        "tests/test_job_state_persistence_smoke.py",
        "tests/test_job_recovery_smoke.py",
        "tests/test_job_system_final_audit_smoke.py",
    ]

    for relative_path in files:
        path = ROOT_DIR / relative_path
        data = path.read_bytes()

        has_bom = (
            len(data) >= 3
            and data[0] == 239
            and data[1] == 187
            and data[2] == 191
        )

        assert path.exists(), f"{relative_path} missing"
        assert not has_bom, f"{relative_path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{relative_path} has no newline at EOF"
