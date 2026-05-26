from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path


_WINDOWS_FFMPEG = Path(r"D:\Tools\ffmpeg\bin\ffmpeg.exe")
_WINDOWS_FFPROBE = Path(r"D:\Tools\ffmpeg\bin\ffprobe.exe")
_RESERVED_CPU_CORES = 4
_MIN_FFMPEG_THREADS = 4


def _resolve_executable(
    *,
    env_var: str,
    executable_name: str,
    fallback: Path,
) -> Path:
    env_value = os.environ.get(env_var)
    if env_value:
        env_path = Path(env_value)
        if env_path.exists():
            return env_path
        raise FileNotFoundError(
            f"{env_var} points to a missing executable: {env_path}"
        )

    path_value = shutil.which(executable_name)
    if path_value:
        return Path(path_value)

    if fallback.exists():
        return fallback

    raise FileNotFoundError(
        f"Could not find {executable_name}. Set {env_var}, add {executable_name} "
        f"to PATH, or install it at {fallback}."
    )


def get_ffmpeg_path() -> str:
    return str(
        _resolve_executable(
            env_var="ZENITH_FFMPEG_PATH",
            executable_name="ffmpeg",
            fallback=_WINDOWS_FFMPEG,
        )
    )


def get_ffprobe_path() -> str:
    return str(
        _resolve_executable(
            env_var="ZENITH_FFPROBE_PATH",
            executable_name="ffprobe",
            fallback=_WINDOWS_FFPROBE,
        )
    )


def ensure_ffmpeg_on_path() -> None:
    ffmpeg_bin = str(Path(get_ffmpeg_path()).resolve().parent)
    path_parts = os.environ.get("PATH", "").split(os.pathsep)

    if not any(Path(part).resolve() == Path(ffmpeg_bin) for part in path_parts if part):
        os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")


@lru_cache(maxsize=1)
def _physical_cpu_count() -> int:
    try:
        import psutil  # type: ignore

        count = psutil.cpu_count(logical=False)
        if count:
            return int(count)
    except Exception:
        pass

    if os.name == "nt":
        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-CimInstance Win32_Processor | "
                    "Measure-Object -Property NumberOfCores -Sum).Sum",
                ],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            value = int(str(completed.stdout or "").strip())
            if value > 0:
                return value
        except Exception:
            pass

    return int(os.cpu_count() or (_MIN_FFMPEG_THREADS + _RESERVED_CPU_CORES))


def resolve_ffmpeg_thread_count() -> int:
    configured = os.environ.get("ZENITH_FFMPEG_THREADS")
    if configured:
        try:
            value = int(configured)
            if value > 0:
                return value
        except ValueError:
            pass

    return max(_MIN_FFMPEG_THREADS, _physical_cpu_count() - _RESERVED_CPU_CORES)


def apply_ffmpeg_thread_cap(
    cmd: list[str],
    threads: int | None = None,
) -> list[str]:
    if not cmd:
        return []

    capped = list(cmd)
    if "-threads" in capped:
        return capped

    thread_count = int(threads or resolve_ffmpeg_thread_count())
    if thread_count <= 0:
        return capped

    return [capped[0], "-threads", str(thread_count), *capped[1:]]
