from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.clip_duration_runner import run_clip_duration_optimization_for_job


def _write_style_dna(path: Path, target_clip_seconds: float = 6.25) -> None:
    payload = {
        "content_type": "gaming_pairs",
        "source_count": 1,
        "cuts_per_minute": {"median": 5.0},
        "median_clip_seconds": {"median": target_clip_seconds},
        "audio_dynamic_range": {"median": 12.0},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _job(
    *,
    proposed_action: str = "KEEP",
    segment_type: str = "highlight",
    duration_seconds: float = 2.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        cut_list_items=[
            {
                "source_item_id": "item_1",
                "segment_id": "seg_1",
                "start_seconds": 0.0,
                "end_seconds": duration_seconds,
                "duration_seconds": duration_seconds,
                "proposed_action": proposed_action,
                "segment_type": segment_type,
                "confidence": 0.9,
                "reason": "test_item",
                "source_signal_ids": [],
                "metadata": {},
            }
        ]
    )


def _first_recommendation(report):
    assert report.recommendation_count == 1
    assert report.recommendations
    return report.recommendations[0]


def test_style_dna_opt_in_influences_clip_duration_target(tmp_path: Path) -> None:
    style_dna_path = tmp_path / "style_dna.json"
    _write_style_dna(style_dna_path, target_clip_seconds=6.25)

    report = run_clip_duration_optimization_for_job(
        _job(proposed_action="KEEP", segment_type="highlight", duration_seconds=2.0),
        metadata={
            "style_dna_pacing_enabled": True,
            "style_dna_path": str(style_dna_path),
        },
    )

    rec = _first_recommendation(report)

    assert rec.recommended_target_duration_seconds == pytest.approx(6.25)
    assert rec.suggested_duration_seconds == pytest.approx(6.25)
    assert report.metadata["style_dna_pacing_profile_applied"] is True
    assert report.metadata["style_dna_pacing_decision"]["loaded"] is True


def test_without_style_dna_opt_in_keeps_standard_target(tmp_path: Path) -> None:
    style_dna_path = tmp_path / "style_dna.json"
    _write_style_dna(style_dna_path, target_clip_seconds=6.25)

    report = run_clip_duration_optimization_for_job(
        _job(proposed_action="KEEP", segment_type="highlight", duration_seconds=2.0),
        metadata={"style_dna_path": str(style_dna_path)},
    )

    rec = _first_recommendation(report)

    assert rec.recommended_target_duration_seconds != pytest.approx(6.25)
    assert rec.recommended_target_duration_seconds == pytest.approx(18.0)
    assert report.metadata.get("style_dna_pacing_profile_applied") is not True


def test_style_dna_does_not_override_protect_duration(tmp_path: Path) -> None:
    style_dna_path = tmp_path / "style_dna.json"
    _write_style_dna(style_dna_path, target_clip_seconds=6.25)

    report = run_clip_duration_optimization_for_job(
        _job(
            proposed_action="PROTECT",
            segment_type="protected_context",
            duration_seconds=2.0,
        ),
        metadata={
            "style_dna_pacing_enabled": True,
            "style_dna_path": str(style_dna_path),
        },
    )

    rec = _first_recommendation(report)

    assert rec.duration_status == "protect_duration"
    assert rec.suggested_duration_seconds is None
    assert rec.recommended_target_duration_seconds is None


def test_style_dna_does_not_override_censor_keep_duration(tmp_path: Path) -> None:
    style_dna_path = tmp_path / "style_dna.json"
    _write_style_dna(style_dna_path, target_clip_seconds=6.25)

    report = run_clip_duration_optimization_for_job(
        _job(
            proposed_action="CENSOR_KEEP",
            segment_type="censor_required_segment",
            duration_seconds=2.0,
        ),
        metadata={
            "style_dna_pacing_enabled": True,
            "style_dna_path": str(style_dna_path),
        },
    )

    rec = _first_recommendation(report)

    assert rec.duration_status == "censor_keep_duration"
    assert rec.suggested_duration_seconds is None
    assert rec.recommended_target_duration_seconds is None


def test_missing_style_dna_file_does_not_crash(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing_style_dna.json"

    report = run_clip_duration_optimization_for_job(
        _job(proposed_action="KEEP", segment_type="highlight", duration_seconds=2.0),
        metadata={
            "style_dna_pacing_enabled": True,
            "style_dna_path": str(missing_path),
        },
    )

    assert report.status != "failed"
    assert report.metadata["style_dna_pacing_profile_applied"] is False
    assert report.metadata["style_dna_pacing_decision"]["loaded"] is False
