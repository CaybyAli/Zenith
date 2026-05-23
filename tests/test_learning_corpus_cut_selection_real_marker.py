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
    raw_mixed_path = pair_dir / "raw_mixed_audio.mp4"
    raw_path = pair_dir / "raw.mp4"
    final_path = pair_dir / "final.mp4"

    assert pair_dir.exists(), f"Missing real pair folder: {pair_dir}"
    assert raw_path.exists(), f"Missing raw.mp4: {raw_path}"
    assert raw_mixed_path.exists(), f"Missing required mixed audio: {raw_mixed_path}"
    assert final_path.exists(), f"Missing final.mp4: {final_path}"

    result = build_cut_selection_map(
        pair_dir,
        raw_audio_path=raw_mixed_path,
        final_audio_path=final_path,
        power_profile="balanced",
    )

    validation = validate_cut_selection_map(result)

    assert result["pair_id"] == "pair_001"
    assert result["alignment_confidence"] > 0.85
    assert validation.valid is True
    assert abs(sum_kept_seconds(result) - result["final_duration_seconds"]) <= 1.0

    output_dir = tmp_path / "pair_001"
    output_path = write_cut_selection_map(output_dir, result)

    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    validate_cut_selection_map(written)
    assert written["alignment_confidence"] > 0.85
