from __future__ import annotations

from core.ffmpeg_capability_resolver_runner import run_ffmpeg_capability_resolver
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


def _job() -> Job:
    return Job(
        job_id="job_runner",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        ffmpeg_path_hint=r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        ffprobe_path_hint=r"D:\Tools\ffmpeg\bin\ffprobe.exe",
        ffmpeg_resolver_allow_tool_probe=True,
    )


def test_runner_writes_job_fields() -> None:
    def fake_probe(argv: list[str]) -> tuple[bool, str, str]:
        joined = " ".join(argv)
        if "-version" in joined:
            return True, "ffmpeg version runner-test\n", ""
        if "-encoders" in joined:
            return True, "libx264\naac\nh264_nvenc\n", ""
        if "-decoders" in joined:
            return True, "h264\n", ""
        if "-filters" in joined:
            return True, "scale\nloudnorm\nconcat\n", ""
        if "-hwaccels" in joined:
            return True, "cuda\n", ""
        return False, "", "unexpected"

    job = _job()
    report = run_ffmpeg_capability_resolver(job, probe_runner=fake_probe)

    assert report.status == "ffmpeg_capability_ready"
    assert job.ffmpeg_capability_status == "ffmpeg_capability_ready"
    assert job.ffmpeg_capability_resolver_report["status"] == "ffmpeg_capability_ready"
    assert job.ffmpeg_tool_probe_attempted is True
    assert job.ffmpeg_tool_probe_succeeded is True
    assert job.ffmpeg_has_h264 is True
    assert job.ffmpeg_has_aac is True
    assert job.ffmpeg_has_nvenc is True
    assert job.ffmpeg_has_scale_filter is True
    assert job.ffmpeg_has_loudnorm_filter is True
    assert job.ffmpeg_can_prepare_real_render_tools is True
    assert job.ffmpeg_can_render is False
    assert job.ffmpeg_can_process_media is False
    assert job.ffmpeg_can_write_media is False
    assert job.ffmpeg_can_probe_media_files is False


def test_job_from_dict_loads_ffmpeg_fields_and_keeps_media_permissions_false() -> None:
    data = _job().to_dict()
    data.update(
        {
            "ffmpeg_capability_status": "ffmpeg_capability_ready",
            "ffmpeg_path_hint": r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
            "ffprobe_path_hint": r"D:\Tools\ffmpeg\bin\ffprobe.exe",
            "ffmpeg_resolver_allow_tool_probe": True,
            "ffmpeg_tool_probe_attempted": True,
            "ffmpeg_tool_probe_succeeded": True,
            "ffmpeg_has_h264": True,
            "ffmpeg_has_aac": True,
            "ffmpeg_has_nvenc": True,
            "ffmpeg_has_scale_filter": True,
            "ffmpeg_has_concat_support": True,
            "ffmpeg_has_loudnorm_filter": True,
            "ffmpeg_can_prepare_real_render_tools": True,
            "ffmpeg_can_render": True,
            "ffmpeg_can_process_media": True,
            "ffmpeg_can_write_media": True,
            "ffmpeg_can_probe_media_files": True,
        }
    )

    loaded = Job.from_dict(data)

    assert loaded.ffmpeg_capability_status == "ffmpeg_capability_ready"
    assert loaded.ffmpeg_resolver_allow_tool_probe is True
    assert loaded.ffmpeg_tool_probe_attempted is True
    assert loaded.ffmpeg_tool_probe_succeeded is True
    assert loaded.ffmpeg_has_h264 is True
    assert loaded.ffmpeg_has_aac is True
    assert loaded.ffmpeg_has_nvenc is True
    assert loaded.ffmpeg_has_scale_filter is True
    assert loaded.ffmpeg_has_concat_support is True
    assert loaded.ffmpeg_has_loudnorm_filter is True
    assert loaded.ffmpeg_can_prepare_real_render_tools is True
    assert loaded.ffmpeg_can_render is False
    assert loaded.ffmpeg_can_process_media is False
    assert loaded.ffmpeg_can_write_media is False
    assert loaded.ffmpeg_can_probe_media_files is False
