from __future__ import annotations

import core.ffmpeg_helper as ffmpeg_helper
import core.resource_monitor as resource_monitor
from core.resource_monitor import GpuSnapshot, MemorySnapshot


def test_apply_ffmpeg_thread_cap_inserts_configured_threads(monkeypatch) -> None:
    monkeypatch.setenv("ZENITH_FFMPEG_THREADS", "12")

    cmd = ffmpeg_helper.apply_ffmpeg_thread_cap(["ffmpeg", "-y", "-i", "in.mp4"])

    assert cmd[:3] == ["ffmpeg", "-threads", "12"]


def test_apply_ffmpeg_thread_cap_does_not_duplicate_threads() -> None:
    cmd = ffmpeg_helper.apply_ffmpeg_thread_cap(
        ["ffmpeg", "-threads", "8", "-i", "in.mp4"],
        threads=12,
    )

    assert cmd.count("-threads") == 1
    assert cmd[cmd.index("-threads") + 1] == "8"


def test_command_uses_nvenc_detects_nvenc_encoder() -> None:
    assert resource_monitor.command_uses_nvenc(["ffmpeg", "-c:v", "h264_nvenc"])
    assert not resource_monitor.command_uses_nvenc(["ffmpeg", "-c:v", "libx264"])


def test_wait_for_ram_below_waits_until_under_limit(monkeypatch) -> None:
    snapshots = iter(
        [
            MemorySnapshot(100.0, 90.0, 10.0, 90.0, "test"),
            MemorySnapshot(100.0, 70.0, 30.0, 70.0, "test"),
        ]
    )
    sleeps: list[float] = []
    monkeypatch.setattr(resource_monitor, "memory_snapshot", lambda: next(snapshots))

    result = resource_monitor.wait_for_ram_below(
        max_percent=80.0,
        poll_seconds=0.1,
        max_wait_seconds=10.0,
        sleeper=sleeps.append,
    )

    assert result is not None
    assert result.percent == 70.0
    assert sleeps == [0.1]


def test_wait_for_gpu_resources_waits_for_vram_and_temperature(monkeypatch) -> None:
    snapshots = iter(
        [
            GpuSnapshot(19_000.0, 24_000.0, 82.0),
            GpuSnapshot(10_000.0, 24_000.0, 60.0),
        ]
    )
    sleeps: list[float] = []
    monkeypatch.setattr(resource_monitor, "gpu_snapshot", lambda: next(snapshots))

    result = resource_monitor.wait_for_gpu_resources(
        max_vram_mb=18_000.0,
        max_temperature_c=80.0,
        poll_seconds=0.1,
        max_wait_seconds=10.0,
        sleeper=sleeps.append,
    )

    assert result is not None
    assert result.memory_used_mb == 10_000.0
    assert result.temperature_c == 60.0
    assert sleeps == [0.1]
