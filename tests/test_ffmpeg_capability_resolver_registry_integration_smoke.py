from __future__ import annotations

from core.ffmpeg_capability_resolver_runner import run_ffmpeg_capability_resolver
from core.unified_edit_signal_registry import build_unified_edit_signal_result
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
        job_id="job_registry",
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


def test_registry_collects_ffmpeg_capability_signals() -> None:
    def fake_probe(argv: list[str]) -> tuple[bool, str, str]:
        joined = " ".join(argv)
        if "-version" in joined:
            return True, "ffmpeg version registry-test\n", ""
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
    run_ffmpeg_capability_resolver(job, probe_runner=fake_probe)

    result = build_unified_edit_signal_result(job)
    data = result.to_dict() if hasattr(result, "to_dict") else result

    signals = data.get("signals", [])
    signal_types = {signal.get("signal_type") for signal in signals}
    sources = {signal.get("source") for signal in signals}

    assert "ffmpeg_capability_resolver" in sources
    assert "ffmpeg_capability_ready" in signal_types
    assert "ffmpeg_tool_probe_succeeded" in signal_types
    assert "ffmpeg_h264_available" in signal_types
    assert "ffmpeg_aac_available" in signal_types
    assert "ffmpeg_nvenc_available" in signal_types
    assert "ffmpeg_loudnorm_available" in signal_types
    assert "ffmpeg_real_render_tools_preparable" in signal_types
    assert "ffmpeg_render_still_not_allowed_here" in signal_types
