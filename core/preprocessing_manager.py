from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models.preprocessing_manifest import PreprocessingManifest


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_source_fingerprint(source_path: str | Path) -> dict[str, Any]:
    path = Path(source_path)
    exists = path.exists()

    fingerprint = {
        "path": str(path),
        "exists": exists,
        "size_bytes": None,
        "mtime_ns": None,
    }

    if exists:
        stat = path.stat()
        fingerprint["size_bytes"] = stat.st_size
        fingerprint["mtime_ns"] = stat.st_mtime_ns

    return fingerprint


def build_cache_key(source_fingerprint: dict[str, Any]) -> str:
    raw = json.dumps(source_fingerprint, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def build_preprocessing_paths(
    job_id: str,
    root_dir: str | Path = "preprocessed",
) -> dict[str, str]:
    base = Path(root_dir) / job_id

    return {
        "preprocessed_dir": str(base),
        "audio_dir": str(base / "audio"),
        "frames_dir": str(base / "frames"),
        "thumbnails_dir": str(base / "thumbnails"),
        "temp_dir": str(base / "temp"),
        "manifest_path": str(base / "manifest.json"),
        "analysis_audio_path": str(base / "audio" / "analysis.wav"),
        "speech_audio_path": str(base / "audio" / "speech_16k_mono.wav"),
        "music_audio_path": str(base / "audio" / "music_reference.wav"),
        "frame_pattern": str(base / "frames" / "frame_%06d.jpg"),
        "thumbnail_pattern": str(base / "thumbnails" / "thumb_%06d.jpg"),
    }


def build_preprocessing_manifest(
    job_id: str,
    source_path: str | Path,
    root_dir: str | Path = "preprocessed",
    reused_cache: bool = False,
    status: str = "ready",
    metadata: dict[str, Any] | None = None,
) -> PreprocessingManifest:
    fingerprint = build_source_fingerprint(source_path)
    cache_key = build_cache_key(fingerprint)
    paths = build_preprocessing_paths(job_id=job_id, root_dir=root_dir)
    now = _utc_now_iso()

    warnings: list[str] = []
    errors: list[str] = []

    if not fingerprint.get("exists"):
        errors.append("source_missing")
        status = "missing_source"

    return PreprocessingManifest(
        job_id=job_id,
        source_path=str(source_path),
        source_fingerprint=fingerprint,
        cache_key=cache_key,
        preprocessed_dir=paths["preprocessed_dir"],
        audio_dir=paths["audio_dir"],
        frames_dir=paths["frames_dir"],
        thumbnails_dir=paths["thumbnails_dir"],
        temp_dir=paths["temp_dir"],
        manifest_path=paths["manifest_path"],
        analysis_audio_path=paths["analysis_audio_path"],
        speech_audio_path=paths["speech_audio_path"],
        music_audio_path=paths["music_audio_path"],
        frame_pattern=paths["frame_pattern"],
        thumbnail_pattern=paths["thumbnail_pattern"],
        status=status,
        reused_cache=reused_cache,
        created_at=now,
        updated_at=now,
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )


def write_preprocessing_manifest(manifest: PreprocessingManifest) -> Path:
    manifest_path = Path(manifest.manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=4, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return manifest_path


def load_preprocessing_manifest(path: str | Path) -> PreprocessingManifest | None:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return None

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return PreprocessingManifest.from_dict(data)


def should_reuse_preprocessing_cache(
    existing_manifest: PreprocessingManifest | None,
    source_fingerprint: dict[str, Any],
) -> bool:
    if existing_manifest is None:
        return False

    expected_cache_key = build_cache_key(source_fingerprint)
    return existing_manifest.cache_key == expected_cache_key


def _ensure_workspace_dirs(manifest: PreprocessingManifest) -> None:
    for path in [
        manifest.preprocessed_dir,
        manifest.audio_dir,
        manifest.frames_dir,
        manifest.thumbnails_dir,
        manifest.temp_dir,
    ]:
        Path(path).mkdir(parents=True, exist_ok=True)


def prepare_preprocessing_workspace(
    job_id: str,
    source_path: str | Path,
    root_dir: str | Path = "preprocessed",
    metadata: dict[str, Any] | None = None,
) -> PreprocessingManifest:
    fingerprint = build_source_fingerprint(source_path)
    paths = build_preprocessing_paths(job_id=job_id, root_dir=root_dir)
    existing = load_preprocessing_manifest(paths["manifest_path"])

    reused_cache = should_reuse_preprocessing_cache(existing, fingerprint)

    if reused_cache and existing is not None:
        existing.reused_cache = True
        existing.updated_at = _utc_now_iso()
        _ensure_workspace_dirs(existing)
        write_preprocessing_manifest(existing)
        return existing

    manifest = build_preprocessing_manifest(
        job_id=job_id,
        source_path=source_path,
        root_dir=root_dir,
        reused_cache=False,
        metadata=metadata,
    )
    _ensure_workspace_dirs(manifest)
    write_preprocessing_manifest(manifest)
    return manifest


def apply_preprocessing_manifest_to_job(
    job: Any,
    manifest: PreprocessingManifest,
) -> Any:
    job.preprocessing_dir = manifest.preprocessed_dir
    job.preprocessing_manifest_path = manifest.manifest_path
    job.preprocessing_manifest = manifest.to_dict()
    job.preprocessing_status = manifest.status
    job.preprocessing_cache_key = manifest.cache_key
    job.preprocessing_reused_cache = manifest.reused_cache

    if hasattr(job, "touch"):
        job.touch()

    return job
