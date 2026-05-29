from __future__ import annotations

import hashlib
import json
import os
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from core.transcription_engine import (
    DEFAULT_TRANSCRIPTION_ENGINE,
    normalize_transcription_engine_name,
)
from models.job import Job
from shared.errors import NotFoundError, StorageError
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


_SLIM_EXCLUDE: frozenset[str] = frozenset({
    "rms_energy_context_timeline",
    "rms_energy_context_adapter",
    "rms_energy_timeline_result",
    "rms_energy_report",
    "energy_peak_report",
    "stutter_detection_points",
    "stutter_detection_report",
    "unified_edit_signals",
    "unified_edit_signal_report",
    "reaction_shot_candidates",
    "face_reaction_points",
    "screen_content_points",
    "visual_energy_points",
    "motion_analysis_points",
    "continuity_check_issues",
    "transition_decision_decisions",
    "beat_detection_beats",
})
_PERSIST_STRIP_PATTERNS: tuple[str, ...] = (
    "_result",
    "_report",
    "_segments",
    "_peaks",
)
_PERSIST_STRIP_SIZE_THRESHOLD_BYTES = 100_000
_PERSIST_STRIP_CONTAINER_TYPES = (dict, list, tuple, set)
_PERSIST_STRIP_SCALAR_TYPES = (str, bytes, bytearray, int, float, bool, type(None), Enum)
_TRANSCRIPTION_ENGINE_FIELD = "transcription_engine"


def _serialized_size_bytes(value: Any) -> int:
    try:
        return len(json.dumps(value, default=str, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError, RecursionError):
        return 0


def _estimated_serialized_size_exceeds(value: Any, threshold: int) -> bool:
    if threshold <= 0:
        return True

    total = 0
    seen: set[int] = set()
    stack: list[Any] = [value]

    while stack:
        item = stack.pop()

        if isinstance(item, str):
            total += len(item.encode("utf-8")) + 2
        elif isinstance(item, (bytes, bytearray)):
            total += len(item) + 2
        elif isinstance(item, Enum):
            total += len(str(item.value).encode("utf-8")) + 2
        elif isinstance(item, (int, float, bool)) or item is None:
            total += len(str(item))
        elif isinstance(item, dict):
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            total += 2 + max(0, len(item) - 1)
            for key, child in item.items():
                total += len(str(key).encode("utf-8")) + 4
                stack.append(child)
        elif isinstance(item, (list, tuple, set, frozenset)):
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            total += 2 + max(0, len(item) - 1)
            stack.extend(item)
        elif is_dataclass(item):
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            total += 2
            for item_field in fields(item):
                total += len(item_field.name.encode("utf-8")) + 4
                stack.append(getattr(item, item_field.name))
        else:
            total += len(str(item).encode("utf-8")) + 2

        if total > threshold:
            return True

    return False


def _serialized_size_exceeds_threshold(value: Any, threshold: int) -> bool:
    if isinstance(value, _PERSIST_STRIP_SCALAR_TYPES):
        return _serialized_size_bytes(value) > threshold
    if _estimated_serialized_size_exceeds(value, threshold):
        return True
    return _serialized_size_bytes(value) > threshold


def _with_default_transcription_engine(job_dict: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(job_dict)
    enriched[_TRANSCRIPTION_ENGINE_FIELD] = normalize_transcription_engine_name(
        enriched.get(_TRANSCRIPTION_ENGINE_FIELD) or DEFAULT_TRANSCRIPTION_ENGINE
    )
    return enriched


def should_strip_persisted_field(
    key: str,
    value: Any,
    *,
    explicit_exclude: frozenset[str] = _SLIM_EXCLUDE,
) -> bool:
    if key in explicit_exclude:
        return True
    if not key.endswith(_PERSIST_STRIP_PATTERNS):
        return (
            isinstance(value, _PERSIST_STRIP_CONTAINER_TYPES)
            and _serialized_size_exceeds_threshold(
                value,
                _PERSIST_STRIP_SIZE_THRESHOLD_BYTES,
            )
        )
    return _serialized_size_exceeds_threshold(
        value,
        _PERSIST_STRIP_SIZE_THRESHOLD_BYTES,
    )


def compact_job_dict_for_persistence(
    job_dict: dict[str, Any],
    *,
    explicit_exclude: frozenset[str] = _SLIM_EXCLUDE,
) -> dict[str, Any]:
    enriched_job_dict = _with_default_transcription_engine(job_dict)
    return {
        key: value
        for key, value in enriched_job_dict.items()
        if not should_strip_persisted_field(
            key,
            value,
            explicit_exclude=explicit_exclude,
        )
    }


class JobStore:
    """
    JSON file-based persistence for Zenith jobs.

    Current storage:
    - data/jobs/<job_id>.json per job

    Legacy compatibility:
    - data/jobs.json can still be read/migrated when no per-job files exist
    - _write_raw() is kept for compatibility, but create_job()/update_job()
      no longer rewrite the monolithic jobs.json file.
    """

    def __init__(
        self,
        db_path: str = "data/jobs.json",
        storage_provider: BaseStorageProvider | None = None,
    ) -> None:
        self.db_path = db_path
        self.storage = storage_provider or LocalStorageProvider()
        self._last_hash: dict[str, str] = {}

        parent_dir = os.path.dirname(self.db_path)
        if parent_dir:
            self.storage.ensure_dir(parent_dir)

        self.jobs_dir = str(Path(self.db_path).parent / "jobs")
        self.storage.ensure_dir(self.jobs_dir)

    def create_job(self, job: Job) -> Job:
        job_dict = job.to_dict()
        job_id = self._job_id_from_dict(job_dict, fallback=job.job_id)

        jobs = self._read_all_jobs()
        if job_id in jobs:
            raise StorageError(f"Job already exists: {job_id}")

        self._last_hash[job_id] = self._job_hash(job_dict)
        self._write_job(job_id, job_dict)
        return job

    def update_job(self, job: Job) -> Job:
        initial_dict = job.to_dict()
        job_id = self._job_id_from_dict(initial_dict, fallback=job.job_id)

        if not self._job_exists(job_id):
            raise NotFoundError(f"Job not found: {job_id}")

        compact = self._compact_job_dict_for_persistence(initial_dict)
        current_hash = self._job_hash_from_compact(compact)
        if self._last_hash.get(job_id) == current_hash:
            return job

        job.touch()
        compact["updated_at"] = job.updated_at
        new_hash = self._job_hash_from_compact(compact)

        if self._last_hash.get(job_id) == new_hash:
            return job

        self._last_hash[job_id] = new_hash
        self._write_compact_job(job_id, compact)
        return job

    def get_job(self, job_id: str) -> Job:
        job_path = self._job_path(job_id)

        if self.storage.exists(str(job_path)):
            try:
                return Job.from_dict(self.storage.read_json(str(job_path)))
            except Exception as exc:
                raise StorageError(f"Could not read job file {job_id}: {exc}") from exc

        jobs = self._read_all_jobs()
        if job_id not in jobs:
            raise NotFoundError(f"Job not found: {job_id}")

        return Job.from_dict(jobs[job_id])

    def list_jobs(self) -> list[Job]:
        jobs = self._read_all_jobs()
        return [Job.from_dict(item) for item in jobs.values()]

    def _job_path(self, job_id: str) -> Path:
        safe_job_id = str(job_id).replace("/", "_").replace("\\", "_")
        return Path(self.jobs_dir) / f"{safe_job_id}.json"

    def _job_id_from_dict(self, job_dict: dict[str, Any], *, fallback: str | None = None) -> str:
        job_id = job_dict.get("job_id") or job_dict.get("id") or fallback
        if not job_id:
            raise StorageError("Job dictionary does not contain job_id/id")
        return str(job_id)

    def _job_hash(self, job_dict: dict[str, Any]) -> str:
        compact = self._compact_job_dict_for_persistence(job_dict)
        return self._job_hash_from_compact(compact)

    def _job_hash_from_compact(self, compact: dict[str, Any]) -> str:
        content = json.dumps(compact, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()

    def _job_exists(self, job_id: str) -> bool:
        if self.storage.exists(str(self._job_path(job_id))):
            return True

        jobs = self._read_all_jobs()
        return job_id in jobs

    def _read_all_jobs(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        jobs_dir_path = Path(self.jobs_dir)

        if jobs_dir_path.exists():
            for job_file in jobs_dir_path.glob("*.json"):
                try:
                    job_data = self.storage.read_json(str(job_file))
                    job_id = self._job_id_from_dict(job_data, fallback=job_file.stem)
                    result[job_id] = _with_default_transcription_engine(job_data)
                    self._last_hash.setdefault(job_id, self._job_hash(job_data))
                except Exception:
                    continue

        if result:
            return result

        if self.storage.exists(self.db_path):
            try:
                legacy = self.storage.read_json(self.db_path)
                legacy_jobs = legacy.get("jobs", legacy) if isinstance(legacy, dict) else {}

                if isinstance(legacy_jobs, dict):
                    for legacy_id, legacy_job_data in legacy_jobs.items():
                        if not isinstance(legacy_job_data, dict):
                            continue

                        job_id = self._job_id_from_dict(
                            legacy_job_data,
                            fallback=str(legacy_id),
                        )
                        enriched_job_data = _with_default_transcription_engine(legacy_job_data)
                        result[job_id] = enriched_job_data
                        self._write_job(job_id, enriched_job_data)
                        self._last_hash[job_id] = self._job_hash(enriched_job_data)

                    legacy_path = Path(self.db_path)
                    backup_path = Path(str(self.db_path) + ".bak")
                    if legacy_path.exists() and not backup_path.exists():
                        legacy_path.rename(backup_path)

            except Exception:
                pass

        return result

    def _compact_job_dict_for_persistence(
        self, job_dict: dict[str, Any]
    ) -> dict[str, Any]:
        return compact_job_dict_for_persistence(job_dict)

    def _write_job(self, job_id: str, job_dict: dict[str, Any]) -> None:
        try:
            compact = self._compact_job_dict_for_persistence(job_dict)
            self._write_compact_job(job_id, compact)
        except Exception as exc:
            raise StorageError(f"Could not write job file {job_id}: {exc}") from exc

    def _write_compact_job(self, job_id: str, compact: dict[str, Any]) -> None:
        try:
            self.storage.write_json(str(self._job_path(job_id)), compact, indent=2)
        except Exception as exc:
            raise StorageError(f"Could not write job file {job_id}: {exc}") from exc

    def _read_raw(self) -> dict[str, Any]:
        try:
            return {"jobs": self._read_all_jobs()}
        except Exception as exc:
            raise StorageError(f"Could not read job store: {exc}") from exc

    def _write_raw(self, data: dict[str, Any]) -> None:
        try:
            self.storage.write_json(self.db_path, data, indent=2)
        except Exception as exc:
            raise StorageError(f"Could not write job store: {exc}") from exc
