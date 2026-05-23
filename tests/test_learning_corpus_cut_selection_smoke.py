from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from core.learning_corpus_cut_selection import align_final_to_raw, build_cut_selection_map
from core.learning_corpus_cut_selection_writer import (
    CutSelectionValidationError,
    sum_kept_seconds,
    validate_cut_selection_map,
    write_cut_selection_map,
)


RAW_FIXTURE = Path("tests/fixtures/test_pair_raw_10s.wav")
FINAL_FIXTURE = Path("tests/fixtures/test_pair_final_6s.wav")


def test_cut_selection_alignment_smoke():
    result = align_final_to_raw(RAW_FIXTURE, FINAL_FIXTURE)

    assert result["alignment_confidence"] > 0.85
    assert abs(result["raw_start_s"] - 2.0) <= 0.35


def test_cut_selection_build_map_smoke(tmp_path):
    pair_dir = tmp_path / "pair_001"
    pair_dir.mkdir()

    shutil.copy2(RAW_FIXTURE, pair_dir / "raw_mixed_audio.mp4")
    shutil.copy2(FINAL_FIXTURE, pair_dir / "final.mp4")

    result = build_cut_selection_map(
        pair_dir,
        raw_audio_path=pair_dir / "raw_mixed_audio.mp4",
        final_audio_path=pair_dir / "final.mp4",
    )

    validation = validate_cut_selection_map(result)

    assert result["pair_id"] == "pair_001"
    assert result["alignment_confidence"] > 0.85
    assert abs(result["kept_segments"][0]["raw_start_s"] - 2.0) <= 0.35
    assert abs(sum_kept_seconds(result) - result["final_duration_seconds"]) <= 1.0
    assert validation.valid is True


def test_cut_selection_writer_smoke(tmp_path):
    pair_dir = tmp_path / "pair_001"
    pair_dir.mkdir()

    payload = {
        "pair_id": "pair_001",
        "raw_duration_seconds": 10.0,
        "final_duration_seconds": 6.0,
        "kept_segments": [
            {"raw_start_s": 2.0, "raw_end_s": 8.0, "final_start_s": 0.0}
        ],
        "cut_segments": [
            {"raw_start_s": 0.0, "raw_end_s": 2.0, "cut_reason_class": "low_action"},
            {"raw_start_s": 8.0, "raw_end_s": 10.0, "cut_reason_class": "dead_air"},
        ],
        "alignment_confidence": 0.95,
        "mapping_version": "1",
    }

    output_path = write_cut_selection_map(pair_dir, payload)

    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["pair_id"] == "pair_001"
    assert written["alignment_confidence"] == 0.95


def test_cut_selection_writer_rejects_duration_mismatch(tmp_path):
    pair_dir = tmp_path / "pair_001"
    pair_dir.mkdir()

    payload = {
        "pair_id": "pair_001",
        "raw_duration_seconds": 10.0,
        "final_duration_seconds": 6.0,
        "kept_segments": [
            {"raw_start_s": 2.0, "raw_end_s": 4.0, "final_start_s": 0.0}
        ],
        "cut_segments": [
            {"raw_start_s": 0.0, "raw_end_s": 2.0, "cut_reason_class": "unknown"}
        ],
        "alignment_confidence": 0.95,
        "mapping_version": "1",
    }

    with pytest.raises(CutSelectionValidationError):
        write_cut_selection_map(pair_dir, payload, report_dir=tmp_path / "reports")

    assert not (pair_dir / "cut_selection_map.json").exists()
    assert (tmp_path / "reports" / "STOPP_CUT_SELECTION_pair_001.md").exists()


def test_cut_selection_writer_rejects_low_confidence(tmp_path):
    pair_dir = tmp_path / "pair_001"
    pair_dir.mkdir()

    payload = {
        "pair_id": "pair_001",
        "raw_duration_seconds": 10.0,
        "final_duration_seconds": 6.0,
        "kept_segments": [
            {"raw_start_s": 2.0, "raw_end_s": 8.0, "final_start_s": 0.0}
        ],
        "cut_segments": [],
        "alignment_confidence": 0.40,
        "mapping_version": "1",
    }

    with pytest.raises(CutSelectionValidationError):
        write_cut_selection_map(pair_dir, payload, report_dir=tmp_path / "reports")

    assert not (pair_dir / "cut_selection_map.json").exists()
    assert (tmp_path / "reports" / "STOPP_CUT_SELECTION_pair_001.md").exists()
