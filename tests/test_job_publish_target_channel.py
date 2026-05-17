from models.job import Job
from shared.enums import ChannelType


def _base_job_data(**overrides):
    data = {
        "job_id": "job-publish-target-test",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }
    data.update(overrides)
    return data


def test_old_job_without_publish_target_channel_uses_editing_channel():
    job = Job.from_dict(_base_job_data())

    assert job.channel_type == ChannelType.GAMING_MAIN
    assert job.publish_target_channel is None
    assert job.effective_publish_channel == ChannelType.GAMING_MAIN

    data = job.to_dict()
    assert "publish_target_channel" in data
    assert data["publish_target_channel"] is None


def test_publish_target_channel_override_is_used_for_publish_target():
    job = Job.from_dict(
        _base_job_data(
            channel_type="gaming_main",
            publish_target_channel="vlog_main",
        )
    )

    assert job.channel_type == ChannelType.GAMING_MAIN
    assert job.publish_target_channel == ChannelType.VLOG_MAIN
    assert job.effective_publish_channel == ChannelType.VLOG_MAIN


def test_publish_target_channel_roundtrip_is_stable():
    job = Job.from_dict(
        _base_job_data(
            channel_type="gaming_uncut",
            publish_target_channel="vlog_uncut",
        )
    )

    restored = Job.from_dict(job.to_dict())

    assert restored.channel_type == ChannelType.GAMING_UNCUT
    assert restored.publish_target_channel == ChannelType.VLOG_UNCUT
    assert restored.effective_publish_channel == ChannelType.VLOG_UNCUT
