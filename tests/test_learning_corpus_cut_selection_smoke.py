from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.learning_corpus_cut_selection import (
    build_cut_selection_map,
    build_final_kept_segments,
    extract_scene_boundaries_seconds,
)
from core.learning_corpus_cut_selection_writer import (
    CutSelectionValidationError,
    sum_kept_seconds,
    validate_cut_selection_map,
    write_cut_selection_map,
)


def _write_fixture_pair(pair_dir: Path) -> None:
    pair_dir.mkdir(parents=True, exist_ok=True)

    style_fingerprint = {
        "video_id": "pair_001",
        "scene_changes": {
            "boundaries_seconds": [12.0, 24.0, 36.0, 48.0],
        },
    }

    meta = {
        "raw_duration_seconds": 100.0,
        "final_duration_seconds": 60.0,
    }

    (pair_dir / "style_fingerprint.json").write_text(
        json.dumps(style_fingerprint, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    (pair_dir / "meta.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
        newline="\n",
    )


def test_scene_inventory_extracts_boundaries_smoke():
    payload = {
        "scene_changes": {
            "boundaries_seconds": [24.0, 12.0, 12.0, "36.0", -1, "bad"],
        }
    }

    assert extract_scene_boundaries_seconds(payload) == [12.0, 24.0, 36.0]


def test_scene_inventory_builds_final_kept_segments_smoke():
    segments = build_final_kept_segments(
        boundaries_seconds=[12.0, 24.0, 36.0, 48.0],
        final_duration_seconds=60.0,
    )

    assert len(segments) == 5
    assert segments[0] == {
        "final_start_s": 0.0,
        "final_end_s": 12.0,
        "estimated_duration_s": 12.0,
    }
    assert segments[-1] == {
        "final_start_s": 48.0,
        "final_end_s": 60.0,
        "estimated_duration_s": 12.0,
    }
    assert sum(segment["estimated_duration_s"] for segment in segments) == 60.0


def test_scene_inventory_build_map_smoke(tmp_path):
    pair_dir = tmp_path / "pair_001"
    _write_fixture_pair(pair_dir)

    result = build_cut_selection_map(pair_dir)
    validation = validate_cut_selection_map(result)

    assert result["pair_id"] == "pair_001"
    assert result["mapping_version"] == "2"
    assert result["mapping_method"] == "final_scene_inventory"
    assert result["mapping_notes"] == "audio_alignment_not_feasible_structural_encoding_mismatch"
    assert result["alignment_confidence"] is None
    assert result["alignment_notes"] == "final_scene_inventory_method_no_raw_alignment"

    assert len(result["kept_segments"]) == 5
    assert result["raw_duration_seconds"] == 100.0
    assert result["final_duration_seconds"] == 60.0
    assert result["total_kept_seconds"] == 60.0
    assert result["total_cut_seconds"] == 40.0
    assert result["cut_ratio"] == 0.4

    assert validation.valid is True
    assert validation.total_kept_seconds == 60.0
    assert validation.final_duration_seconds == 60.0
    assert validation.cut_ratio == 0.4


def test_scene_inventory_writer_smoke(tmp_path):
    pair_dir = tmp_path / "pair_001"
    _write_fixture_pair(pair_dir)

    payload = build_cut_selection_map(pair_dir)
    output_path = write_cut_selection_map(pair_dir, payload)

    assert output_path.exists()

    written = json.loads(output_path.read_text(encoding="utf-8"))
    validation = validate_cut_selection_map(written)

    assert written["mapping_version"] == "2"
    assert written["mapping_method"] == "final_scene_inventory"
    assert written["alignment_confidence"] is None
    assert sum_kept_seconds(written) == 60.0
    assert validation.valid is True


def test_scene_inventory_rejects_missing_scene_changes(tmp_path):
    pair_dir = tmp_path / "pair_001"
    pair_dir.mkdir(parents=True)

    (pair_dir / "style_fingerprint.json").write_text(
        json.dumps({"video_id": "pair_001"}),
        encoding="utf-8",
        newline="\n",
    )
    (pair_dir / "meta.json").write_text(
        json.dumps({"raw_duration_seconds": 100.0, "final_duration_seconds": 60.0}),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValueError):
        build_cut_selection_map(pair_dir)


def test_scene_inventory_writer_rejects_wrong_method(tmp_path):
    pair_dir = tmp_path / "pair_001"
    _write_fixture_pair(pair_dir)

    payload = build_cut_selection_map(pair_dir)
    payload["mapping_method"] = "old_audio_alignment"

    with pytest.raises(CutSelectionValidationError):
        write_cut_selection_map(pair_dir, payload, report_dir=tmp_path / "reports")

    assert (tmp_path / "reports" / "STOPP_CUT_SELECTION_pair_001.md").exists()


def test_scene_inventory_writer_rejects_bad_duration_sum(tmp_path):
    pair_dir = tmp_path / "pair_001"
    _write_fixture_pair(pair_dir)

    payload = build_cut_selection_map(pair_dir)
    payload["kept_segments"][0]["estimated_duration_s"] = 1.0

    with pytest.raises(CutSelectionValidationError):
        write_cut_selection_map(pair_dir, payload, report_dir=tmp_path / "reports")

    assert (tmp_path / "reports" / "STOPP_CUT_SELECTION_pair_001.md").exists()
