from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.learning_corpus_fingerprint_writer import validate_style_fingerprint
from core.learning_corpus_ingestor import LearningCorpusIngestor, probe_audio_stream_count


@pytest.mark.corpus_ingest_real
def test_learning_corpus_real_pair_001_ingest_marker():
    pair_dir = Path("learning_corpus/pairs/pair_001")
    raw_path = pair_dir / "raw.mp4"
    meta_path = pair_dir / "meta.json"

    assert pair_dir.exists(), f"Missing real corpus folder: {pair_dir}"
    assert raw_path.exists(), f"Missing real raw video: {raw_path}"
    assert meta_path.exists(), f"Missing real meta.json: {meta_path}"

    def transcript_extractor(path, **kwargs):
        assert Path(path).exists()
        assert kwargs.get("power_profile") == "balanced"
        return {
            "language": "unknown",
            "segments_count": 0,
            "first_10s_text": "",
        }

    def scene_change_extractor(path, **kwargs):
        assert Path(path).exists()
        return {
            "count": 0,
            "rate_per_minute": 0.0,
            "boundaries_seconds": [],
        }

    def audio_profile_extractor(path, **kwargs):
        assert Path(path).exists()
        return {
            "lufs_integrated": 0.0,
            "rms_curve_sampled": [],
            "peak_db": 0.0,
        }

    original_audio_streams = probe_audio_stream_count(raw_path)

    ingestor = LearningCorpusIngestor(
        corpus_root=Path("learning_corpus"),
        power_profile="balanced",
        transcript_extractor=transcript_extractor,
        scene_change_extractor=scene_change_extractor,
        audio_profile_extractor=audio_profile_extractor,
    )

    result = ingestor.ingest_video_folder(pair_dir)

    assert result.source_video_path == raw_path
    assert result.prepared_audio_path.exists()
    assert result.prepared_audio_path.name == "raw_mixed_audio.mp4"
    assert result.audio_stream_count == original_audio_streams

    fingerprint_path = pair_dir / "style_fingerprint.json"
    assert result.fingerprint_path == fingerprint_path
    assert fingerprint_path.exists()

    payload = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    validate_style_fingerprint(payload)

    assert payload["video_id"]
    assert payload["type"] in {"gaming_main", "vlog_main"}
    assert payload["ingest_version"] == "1"
