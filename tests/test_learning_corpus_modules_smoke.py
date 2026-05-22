from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.learning_corpus_audio_profile import extract_audio_profile
from core.learning_corpus_fingerprint_writer import (
    build_style_fingerprint,
    fingerprint_for_determinism_compare,
    validate_style_fingerprint,
    write_style_fingerprint,
)
from core.learning_corpus_hook_identifier import identify_hook
from core.learning_corpus_ingestor import LearningCorpusIngestor, ensure_mixed_audio
from core.learning_corpus_pacing_metrics import extract_pacing_metrics
from core.learning_corpus_reaction_timing import extract_reaction_timing
from core.learning_corpus_scene_change import extract_scene_changes
from core.learning_corpus_transcript import extract_transcript


FIXTURE_VIDEO = Path("tests/fixtures/test_5s.mp4")


class DummyTranscriber:
    def transcribe(self, media_path: str, **kwargs):
        assert Path(media_path).exists()
        assert kwargs.get("language") is None
        segments = [
            {"start": 0.0, "end": 1.5, "text": "Was passiert hier"},
            {"start": 2.0, "end": 4.0, "text": "das ist ein Test"},
            {"start": 11.0, "end": 12.0, "text": "zu spaet"},
        ]
        info = SimpleNamespace(language="de")
        return segments, info


def test_learning_corpus_ingestor_smoke(tmp_path):
    pair_dir = tmp_path / "pairs" / "pair_001"
    pair_dir.mkdir(parents=True)
    shutil.copy2(FIXTURE_VIDEO, pair_dir / "raw.mp4")
    (pair_dir / "meta.json").write_text(
        json.dumps(
            {
                "video_id": "pair_001",
                "type": "gaming_main",
                "game": "fixture",
                "date": "2026-01-01",
                "quality_tier": "top",
                "youtube_url": "",
                "raw_duration_seconds": 5,
                "final_duration_seconds": 5,
            }
        ),
        encoding="utf-8",
    )

    def transcript_extractor(path, **kwargs):
        return {"language": "de", "segments_count": 1, "first_10s_text": "Was passiert hier"}

    def scene_change_extractor(path, **kwargs):
        return {"count": 1, "rate_per_minute": 12.0, "boundaries_seconds": [2.0]}

    def audio_profile_extractor(path, **kwargs):
        return {"lufs_integrated": -16.0, "rms_curve_sampled": [-20.0], "peak_db": -1.0}

    ingestor = LearningCorpusIngestor(
        corpus_root=tmp_path,
        power_profile="balanced",
        transcript_extractor=transcript_extractor,
        scene_change_extractor=scene_change_extractor,
        audio_profile_extractor=audio_profile_extractor,
    )

    result = ingestor.ingest_video_folder(pair_dir)

    assert result.fingerprint_path.exists()
    assert result.prepared_audio_path.name == "raw_mixed_audio.mp4"
    payload = json.loads(result.fingerprint_path.read_text(encoding="utf-8"))
    validate_style_fingerprint(payload)
    assert payload["video_id"] == "pair_001"


def test_learning_corpus_transcript_smoke():
    result = extract_transcript(FIXTURE_VIDEO, transcriber=DummyTranscriber())

    assert result == {
        "language": "de",
        "segments_count": 3,
        "first_10s_text": "Was passiert hier das ist ein Test",
    }


def test_learning_corpus_scene_change_smoke():
    result = extract_scene_changes(FIXTURE_VIDEO)

    assert set(result) == {"count", "rate_per_minute", "boundaries_seconds"}
    assert isinstance(result["count"], int)
    assert isinstance(result["rate_per_minute"], float)
    assert isinstance(result["boundaries_seconds"], list)


def test_learning_corpus_audio_profile_smoke():
    result = extract_audio_profile(FIXTURE_VIDEO, sample_interval_seconds=5.0)

    assert set(result) == {"lufs_integrated", "rms_curve_sampled", "peak_db"}
    assert isinstance(result["lufs_integrated"], float)
    assert isinstance(result["rms_curve_sampled"], list)
    assert isinstance(result["peak_db"], float)


def test_learning_corpus_pacing_metrics_smoke():
    result = extract_pacing_metrics([1.0, 3.0], duration_seconds=5.0)

    assert result["cut_count"] == 2
    assert result["cuts_per_minute"] == 24.0
    assert result["median_clip_seconds"] == 2.0
    assert isinstance(result["clip_length_histogram_bins"], list)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Was passiert hier heute", "question"),
        ("Schau dir das an", "action"),
        ("heute testen wir zenith", "statement"),
        ("wir fragen Herr Müller dazu", "name_drop"),
        ("", "unknown"),
    ],
)
def test_learning_corpus_hook_identifier_smoke(text, expected):
    result = identify_hook(text)

    assert result["pattern_class"] == expected
    assert set(result) == {"first_words", "pattern_class"}


def test_learning_corpus_reaction_timing_smoke():
    result = extract_reaction_timing(
        video_type="vlog_main",
        transcript={"first_10s_text": "Start vom Vlog"},
        scene_changes={"boundaries_seconds": [1.0, 2.5]},
    )

    assert result["applicable"] is True
    assert isinstance(result["events"], list)

    not_applicable = extract_reaction_timing(video_type="gaming_main", meta={"game": "test"})
    assert not_applicable == {"applicable": False}


def test_learning_corpus_fingerprint_writer_smoke(tmp_path):
    meta = {"video_id": "video_001", "type": "top_main", "quality_tier": "top"}
    transcript = {"language": "de", "segments_count": 1, "first_10s_text": "Was passiert hier"}
    scene_changes = {"count": 1, "rate_per_minute": 12.0, "boundaries_seconds": [2.0]}
    audio = {"lufs_integrated": -16.0, "rms_curve_sampled": [-20.0], "peak_db": -1.0}
    pacing = extract_pacing_metrics([2.0], duration_seconds=5.0)
    hook = identify_hook(transcript)
    reaction_timing = {"applicable": False}

    fingerprint = build_style_fingerprint(
        meta=meta,
        transcript=transcript,
        scene_changes=scene_changes,
        audio=audio,
        pacing=pacing,
        hook=hook,
        reaction_timing=reaction_timing,
        ingest_timestamp_utc="2026-01-01T00:00:00Z",
    )
    validate_style_fingerprint(fingerprint)

    output_path = write_style_fingerprint(
        tmp_path,
        meta=meta,
        transcript=transcript,
        scene_changes=scene_changes,
        audio=audio,
        pacing=pacing,
        hook=hook,
        reaction_timing=reaction_timing,
        ingest_timestamp_utc="2026-01-01T00:00:00Z",
    )

    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert fingerprint_for_determinism_compare(written) == fingerprint_for_determinism_compare(fingerprint)


def test_learning_corpus_ensure_mixed_audio_smoke(tmp_path):
    pair_dir = tmp_path / "pair_001"
    pair_dir.mkdir()
    shutil.copy2(FIXTURE_VIDEO, pair_dir / "raw.mp4")

    prepared = ensure_mixed_audio(pair_dir)

    assert prepared.exists()
    assert prepared.name == "raw_mixed_audio.mp4"
