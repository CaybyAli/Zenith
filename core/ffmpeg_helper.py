from __future__ import annotations

import os
import shutil
from pathlib import Path


_WINDOWS_FFMPEG = Path(r"D:\Tools\ffmpeg\bin\ffmpeg.exe")
_WINDOWS_FFPROBE = Path(r"D:\Tools\ffmpeg\bin\ffprobe.exe")


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
