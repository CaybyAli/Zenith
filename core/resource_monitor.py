from __future__ import annotations

import contextlib
import ctypes
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Iterator

LOGGER = logging.getLogger(__name__)

RAM_USAGE_LIMIT_PERCENT = 80.0
VRAM_LIMIT_MB = 18 * 1024
GPU_TEMPERATURE_LIMIT_C = 80
NVENC_SESSION_LIMIT = 2
RESOURCE_POLL_SECONDS = 5.0
RESOURCE_MAX_WAIT_SECONDS = 60.0

_NVENC_SEMAPHORE = threading.BoundedSemaphore(NVENC_SESSION_LIMIT)


@dataclass(frozen=True)
class MemorySnapshot:
    total_mb: float
    used_mb: float
    available_mb: float
    percent: float
    source: str


@dataclass(frozen=True)
class GpuSnapshot:
    memory_used_mb: float
    memory_total_mb: float
    temperature_c: float
    source: str = "nvidia-smi"


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def memory_snapshot() -> MemorySnapshot | None:
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        total_mb = float(vm.total) / (1024 * 1024)
        available_mb = float(vm.available) / (1024 * 1024)
        used_mb = float(vm.used) / (1024 * 1024)
        return MemorySnapshot(
            total_mb=total_mb,
            used_mb=used_mb,
            available_mb=available_mb,
            percent=float(vm.percent),
            source="psutil",
        )
    except Exception:
        pass

    if os.name == "nt":
        try:
            status = _MemoryStatusEx()
            status.dwLength = ctypes.sizeof(_MemoryStatusEx)
            ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            if ok:
                total_mb = float(status.ullTotalPhys) / (1024 * 1024)
                available_mb = float(status.ullAvailPhys) / (1024 * 1024)
                used_mb = max(0.0, total_mb - available_mb)
                percent = (used_mb / total_mb * 100.0) if total_mb else 0.0
                return MemorySnapshot(
                    total_mb=total_mb,
                    used_mb=used_mb,
                    available_mb=available_mb,
                    percent=percent,
                    source="windows_global_memory_status",
                )
        except Exception:
            return None

    return None


def gpu_snapshot() -> GpuSnapshot | None:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None

    if completed.returncode != 0:
        return None

    line = str(completed.stdout or "").strip().splitlines()
    if not line:
        return None

    try:
        used_text, total_text, temp_text = [part.strip() for part in line[0].split(",")]
        return GpuSnapshot(
            memory_used_mb=float(used_text),
            memory_total_mb=float(total_text),
            temperature_c=float(temp_text),
        )
    except (TypeError, ValueError):
        return None


def command_uses_nvenc(cmd: list[str]) -> bool:
    return any("nvenc" in str(part).lower() for part in cmd)


def wait_for_ram_below(
    max_percent: float = RAM_USAGE_LIMIT_PERCENT,
    *,
    poll_seconds: float = RESOURCE_POLL_SECONDS,
    max_wait_seconds: float = RESOURCE_MAX_WAIT_SECONDS,
    sleeper=time.sleep,
) -> MemorySnapshot | None:
    deadline = time.monotonic() + max_wait_seconds
    snapshot = memory_snapshot()
    while snapshot is not None and snapshot.percent > max_percent:
        if time.monotonic() >= deadline:
            LOGGER.warning(
                "RAM usage remains high after wait: %.1f%% > %.1f%%",
                snapshot.percent,
                max_percent,
            )
            return snapshot
        LOGGER.warning(
            "RAM usage high before pipeline stage: %.1f%% > %.1f%%; waiting %.1fs",
            snapshot.percent,
            max_percent,
            poll_seconds,
        )
        sleeper(poll_seconds)
        snapshot = memory_snapshot()
    return snapshot


def wait_for_gpu_resources(
    *,
    max_vram_mb: float = VRAM_LIMIT_MB,
    max_temperature_c: float = GPU_TEMPERATURE_LIMIT_C,
    poll_seconds: float = RESOURCE_POLL_SECONDS,
    max_wait_seconds: float = RESOURCE_MAX_WAIT_SECONDS,
    sleeper=time.sleep,
) -> GpuSnapshot | None:
    deadline = time.monotonic() + max_wait_seconds
    snapshot = gpu_snapshot()
    while snapshot is not None and (
        snapshot.memory_used_mb > max_vram_mb
        or snapshot.temperature_c > max_temperature_c
    ):
        if time.monotonic() >= deadline:
            LOGGER.warning(
                "GPU resources remain high after wait: vram=%.0fMB temp=%.0fC",
                snapshot.memory_used_mb,
                snapshot.temperature_c,
            )
            return snapshot
        LOGGER.warning(
            "GPU resources high before NVENC stage: vram=%.0fMB temp=%.0fC; waiting %.1fs",
            snapshot.memory_used_mb,
            snapshot.temperature_c,
            poll_seconds,
        )
        sleeper(poll_seconds)
        snapshot = gpu_snapshot()
    return snapshot


@contextlib.contextmanager
def guarded_ffmpeg_execution(cmd: list[str]) -> Iterator[None]:
    wait_for_ram_below()

    acquired_nvenc = False
    if command_uses_nvenc(cmd):
        wait_for_gpu_resources()
        _NVENC_SEMAPHORE.acquire()
        acquired_nvenc = True

    try:
        yield
    finally:
        if acquired_nvenc:
            _NVENC_SEMAPHORE.release()
