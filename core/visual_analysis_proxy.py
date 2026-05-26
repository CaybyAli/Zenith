from __future__ import annotations

import os
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

from core.ffmpeg_helper import apply_ffmpeg_thread_cap, get_ffmpeg_path
from core.resource_monitor import guarded_ffmpeg_execution


VISUAL_ANALYSIS_PROXY_SELECTED_TYPE = "visual_analysis_proxy"

_DEFAULT_PROXY_FPS = 2.0
_DEFAULT_PROXY_WIDTH = 960
_DEFAULT_PROXY_HEIGHT = 270
_DEFAULT_MIN_SOURCE_BYTES = 512 * 1024 * 1024
_DEFAULT_TIMEOUT_SECONDS = 900


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _set_value(target: Any, key: str, value: Any) -> None:
    if isinstance(target, dict):
        target[key] = value
        return
    try:
        setattr(target, key, value)
    except Exception:
        return


def _float_from_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _int_from_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _proxy_disabled() -> bool:
    value = str(os.getenv("ZENITH_DISABLE_VISUAL_ANALYSIS_PROXY", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _source_is_large_enough(source_path: Path) -> bool:
    min_bytes = _int_from_env(
        "ZENITH_VISUAL_ANALYSIS_PROXY_MIN_SOURCE_BYTES",
        _DEFAULT_MIN_SOURCE_BYTES,
    )
    try:
        return source_path.stat().st_size >= max(0, min_bytes)
    except OSError:
        return False


def _safe_proxy_name() -> str:
    fps = _float_from_env("ZENITH_VISUAL_ANALYSIS_PROXY_FPS", _DEFAULT_PROXY_FPS)
    width = _int_from_env("ZENITH_VISUAL_ANALYSIS_PROXY_WIDTH", _DEFAULT_PROXY_WIDTH)
    height = _int_from_env("ZENITH_VISUAL_ANALYSIS_PROXY_HEIGHT", _DEFAULT_PROXY_HEIGHT)
    fps_label = str(fps).replace(".", "p")
    return f"analysis_proxy_{width}x{height}_{fps_label}fps.mp4"


def resolve_visual_analysis_proxy_path(job: Any, source_path: str | Path | None) -> Path | None:
    manifest = _get_value(job, "preprocessing_manifest")
    temp_dir = None
    if isinstance(manifest, dict):
        temp_dir = manifest.get("temp_dir")

    if not temp_dir:
        manifest_path = _get_value(job, "preprocessing_manifest_path")
        if manifest_path:
            temp_dir = Path(str(manifest_path)).parent / "temp"

    if not temp_dir:
        job_id = str(_get_value(job, "job_id", "") or "").strip()
        if job_id:
            temp_dir = Path("preprocessed") / job_id / "temp"

    if not temp_dir and source_path:
        temp_dir = Path(source_path).resolve().parent

    if not temp_dir:
        return None

    return Path(temp_dir) / _safe_proxy_name()


def _existing_proxy_is_reusable(proxy_path: Path) -> bool:
    try:
        return proxy_path.is_file() and proxy_path.stat().st_size > 0
    except OSError:
        return False


def _build_proxy_command(
    *,
    ffmpeg_path: str,
    source_path: Path,
    output_path: Path,
    use_cuda_filters: bool,
) -> list[str]:
    fps = _float_from_env("ZENITH_VISUAL_ANALYSIS_PROXY_FPS", _DEFAULT_PROXY_FPS)
    width = _int_from_env("ZENITH_VISUAL_ANALYSIS_PROXY_WIDTH", _DEFAULT_PROXY_WIDTH)
    height = _int_from_env("ZENITH_VISUAL_ANALYSIS_PROXY_HEIGHT", _DEFAULT_PROXY_HEIGHT)

    command: list[str] = [
        ffmpeg_path,
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "error",
        "-y",
    ]
    if use_cuda_filters:
        command.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])

    command.extend(["-i", str(source_path), "-an"])
    if use_cuda_filters:
        command.extend(
            [
                "-vf",
                f"scale_cuda={width}:{height},hwdownload,format=nv12,fps={fps:g}",
            ]
        )
    else:
        command.extend(["-vf", f"fps={fps:g},scale={width}:{height}"])

    command.extend(
        [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p4",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]
    )
    return apply_ffmpeg_thread_cap(command)


def _run_proxy_command(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[bytes]:
    with guarded_ffmpeg_execution(command):
        return subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )


def _record_proxy_status(
    job: Any,
    *,
    status: str,
    path: Path | None = None,
    error: str | None = None,
) -> None:
    _set_value(job, "visual_analysis_proxy_status", status)
    if path is not None:
        _set_value(job, "visual_analysis_proxy_path", str(path))
    if error:
        _set_value(job, "visual_analysis_proxy_error", error[-1000:])


def ensure_visual_analysis_proxy_for_job(
    job: Any,
    source_path: str | Path | None,
) -> str | None:
    if _proxy_disabled() or not source_path:
        return None

    source = Path(str(source_path))
    if not source.is_file() or not _source_is_large_enough(source):
        return None

    proxy = resolve_visual_analysis_proxy_path(job, source)
    if proxy is None:
        return None

    if _existing_proxy_is_reusable(proxy):
        _record_proxy_status(job, status="ready", path=proxy)
        return str(proxy)

    try:
        ffmpeg_path = get_ffmpeg_path()
    except FileNotFoundError as exc:
        _record_proxy_status(job, status="unavailable", error=str(exc))
        return None

    proxy.parent.mkdir(parents=True, exist_ok=True)
    temp_output = proxy.with_suffix(".tmp.mp4")
    try:
        temp_output.unlink(missing_ok=True)
    except OSError:
        pass

    timeout_seconds = _int_from_env(
        "ZENITH_VISUAL_ANALYSIS_PROXY_TIMEOUT_SECONDS",
        _DEFAULT_TIMEOUT_SECONDS,
    )

    errors: list[str] = []
    for use_cuda_filters in (True, False):
        command = _build_proxy_command(
            ffmpeg_path=ffmpeg_path,
            source_path=source,
            output_path=temp_output,
            use_cuda_filters=use_cuda_filters,
        )
        try:
            completed = _run_proxy_command(command, timeout_seconds=timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(str(exc))
            continue

        if completed.returncode == 0 and _existing_proxy_is_reusable(temp_output):
            temp_output.replace(proxy)
            _record_proxy_status(job, status="ready", path=proxy)
            return str(proxy)

        stderr = completed.stderr.decode("utf-8", errors="replace") if completed.stderr else ""
        errors.append(stderr[-1000:] or f"ffmpeg_returncode={completed.returncode}")

        try:
            temp_output.unlink(missing_ok=True)
        except OSError:
            pass

    _record_proxy_status(job, status="failed", path=proxy, error=" | ".join(errors))
    return None


def with_visual_analysis_proxy_source_selection(
    source_selection: Any,
    proxy_path: str | None,
) -> Any:
    if not proxy_path:
        return source_selection

    original_path = _get_value(source_selection, "selected_path")
    original_type = _get_value(source_selection, "selected_type")
    checked_sources = list(_get_value(source_selection, "checked_sources", []) or [])
    checked_sources.append(
        {
            "source_type": VISUAL_ANALYSIS_PROXY_SELECTED_TYPE,
            "path": proxy_path,
            "exists": True,
            "status": "exists",
        }
    )
    warnings = list(_get_value(source_selection, "warnings", []) or [])
    if "visual_analysis_proxy_used" not in warnings:
        warnings.append("visual_analysis_proxy_used")
    metadata = dict(_get_value(source_selection, "metadata", {}) or {})
    metadata.update(
        {
            "visual_analysis_proxy_path": proxy_path,
            "visual_analysis_original_path": original_path,
            "visual_analysis_original_type": original_type,
        }
    )

    try:
        return replace(
            source_selection,
            selected_path=proxy_path,
            selected_type=VISUAL_ANALYSIS_PROXY_SELECTED_TYPE,
            checked_sources=checked_sources,
            warnings=warnings,
            metadata=metadata,
        )
    except Exception:
        _set_value(source_selection, "selected_path", proxy_path)
        _set_value(source_selection, "selected_type", VISUAL_ANALYSIS_PROXY_SELECTED_TYPE)
        _set_value(source_selection, "checked_sources", checked_sources)
        _set_value(source_selection, "warnings", warnings)
        _set_value(source_selection, "metadata", metadata)
        return source_selection
