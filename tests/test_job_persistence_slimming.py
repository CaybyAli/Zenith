from __future__ import annotations

import json
from types import SimpleNamespace

from core.job_store import (
    _PERSIST_STRIP_SIZE_THRESHOLD_BYTES,
    compact_job_dict_for_persistence,
)
from pipeline_runner import _write_export_job_json


def _large_payload() -> dict[str, str]:
    return {"blob": "x" * (_PERSIST_STRIP_SIZE_THRESHOLD_BYTES + 1)}


def test_persistence_slimming_strips_large_pattern_fields_only() -> None:
    payload = {
        "job_id": "job_slim_001",
        "small_silence_detection_report": {"status": "ok"},
        "large_face_reaction_result": _large_payload(),
        "large_motion_analysis_segments": _large_payload(),
        "large_audio_peaks": _large_payload(),
    }

    compact = compact_job_dict_for_persistence(payload)

    assert compact["job_id"] == "job_slim_001"
    assert compact["small_silence_detection_report"] == {"status": "ok"}
    assert "large_face_reaction_result" not in compact
    assert "large_motion_analysis_segments" not in compact
    assert "large_audio_peaks" not in compact


def test_persistence_slimming_strips_non_matching_large_containers() -> None:
    payload = {
        "job_id": "job_slim_002",
        "large_non_stage_blob": _large_payload(),
    }

    compact = compact_job_dict_for_persistence(payload)

    assert "large_non_stage_blob" not in compact


def test_persistence_slimming_keeps_non_matching_large_scalars() -> None:
    payload = {
        "job_id": "job_slim_002b",
        "large_transcript_text": "x" * (_PERSIST_STRIP_SIZE_THRESHOLD_BYTES + 1),
    }

    compact = compact_job_dict_for_persistence(payload)

    assert compact["large_transcript_text"] == payload["large_transcript_text"]


def test_persistence_slimming_keeps_unserializable_pattern_fields() -> None:
    marker = []
    marker.append(marker)
    payload = {
        "job_id": "job_slim_003",
        "custom_result": marker,
    }

    compact = compact_job_dict_for_persistence(payload)

    assert compact["custom_result"] is marker


def test_export_job_json_uses_pattern_threshold_slimming(tmp_path) -> None:
    job = SimpleNamespace(
        job_id="job_export_slim_001",
        to_dict=lambda: {
            "job_id": "job_export_slim_001",
            "small_silence_detection_report": {"status": "ok"},
            "large_face_reaction_result": _large_payload(),
        },
    )

    output_path = _write_export_job_json(job, tmp_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["job_id"] == "job_export_slim_001"
    assert payload["small_silence_detection_report"] == {"status": "ok"}
    assert "large_face_reaction_result" not in payload
