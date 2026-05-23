from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.learning_corpus_cut_selection import build_cut_selection_map
from core.learning_corpus_cut_selection_writer import (
    sum_kept_seconds,
    validate_cut_selection_map,
    write_cut_selection_map,
)


@pytest.mark.corpus_ingest_real
def test_cut_selection_real_pair_001_marker(tmp_path):
    pair_dir = Path("learning_corpus/pairs/pair_001")
    style_fingerprint_path = pair_dir / "style_fingerprint.json"
    meta_path = pair_dir / "meta.json"

    assert pair_dir.exists(), f"Missing real pair folder: {pair_dir}"
    assert style_fingerprint_path.exists(), f"Missing style_fingerprint.json: {style_fingerprint_path}"
    assert meta_path.exists(), f"Missing meta.json: {meta_path}"

    style_fingerprint = json.loads(style_fingerprint_path.read_text(encoding="utf-8-sig"))
    scene_changes = style_fingerprint.get("scene_changes") or {}
    boundaries = scene_changes.get("boundaries_seconds") or []

    if not boundaries:
        pytest.skip(
            "P5-2 real marker blocked: style_fingerprint scene_changes.boundaries_seconds is empty"
        )

    result = build_cut_selection_map(pair_dir)
    validation = validate_cut_selection_map(result)

    assert result["pair_id"] == "pair_001"
    assert result["mapping_version"] == "2"
    assert result["mapping_method"] == "final_scene_inventory"
    assert result["alignment_confidence"] is None
    assert result["alignment_notes"] == "final_scene_inventory_method_no_raw_alignment"

    assert 0.0 <= result["cut_ratio"] <= 1.0
    assert abs(sum_kept_seconds(result) - result["final_duration_seconds"]) <= 5.0
    assert validation.valid is True

    output_dir = tmp_path / "pair_001"
    output_path = write_cut_selection_map(output_dir, result)

    written = json.loads(output_path.read_text(encoding="utf-8"))
    validate_cut_selection_map(written)

    assert written["mapping_version"] == "2"
    assert written["mapping_method"] == "final_scene_inventory"
    assert written["alignment_confidence"] is None
