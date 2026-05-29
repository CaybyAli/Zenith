from __future__ import annotations

import json
from pathlib import Path

from core.style_dna_aggregator import build_style_dna


def _fingerprint(
    *,
    cuts_per_minute: float,
    scene_length: float,
    audio_db: float,
    voice: str,
    hook: str,
    intensity: str,
    focus: str,
    opening: str,
    transcript_key: str,
    transcript_text: str,
    speaker_distribution: dict | None = None,
) -> dict:
    data = {
        "cuts_per_minute": cuts_per_minute,
        "median_scene_length_seconds": scene_length,
        "audio_dynamic_range_db": audio_db,
        "voice_intensity": voice,
        "hook_type": hook,
        "intensity_clustering": intensity,
        "focus": focus,
        "opening_type": opening,
        transcript_key: transcript_text,
    }
    if speaker_distribution is not None:
        data["speaker_distribution"] = speaker_distribution
    return data


def _write(path: Path, payload: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "style_fingerprint.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def test_style_dna_aggregator_handles_transcript_aliases_and_taxonomy(tmp_path: Path) -> None:
    corpus = tmp_path / "learning_corpus"

    _write(
        corpus / "pairs" / "pair_001",
        _fingerprint(
            cuts_per_minute=6.0,
            scene_length=4.0,
            audio_db=27.0,
            voice="normal",
            hook="narrative",
            intensity="front_loaded",
            focus="gameplay",
            opening="story",
            transcript_key="first_window_text",
            transcript_text="pair transcript text",
            speaker_distribution={"ali": 0.7, "friend": 0.3},
        ),
    )
    _write(
        corpus / "pairs_singletrack_backup" / "pair_001",
        _fingerprint(
            cuts_per_minute=99.0,
            scene_length=99.0,
            audio_db=99.0,
            voice="bruellen",
            hook="question",
            intensity="back_loaded",
            focus="backup",
            opening="backup",
            transcript_key="first_window_text",
            transcript_text="backup transcript must be excluded",
            speaker_distribution={"ali": 0.1, "friend": 0.9},
        ),
    )
    _write(
        corpus / "top_solo" / "top_001",
        _fingerprint(
            cuts_per_minute=8.0,
            scene_length=3.5,
            audio_db=29.0,
            voice="leise_erhoeht",
            hook="high_reaction",
            intensity="burst",
            focus="facecam",
            opening="reaction",
            transcript_key="first_10s_text",
            transcript_text="solo transcript text",
        ),
    )
    _write(
        corpus / "vlogs" / "vlog_001",
        _fingerprint(
            cuts_per_minute=3.0,
            scene_length=8.0,
            audio_db=20.0,
            voice="normal",
            hook="question",
            intensity="even",
            focus="person",
            opening="talking",
            transcript_key="first_10s_text",
            transcript_text="vlog transcript text",
        ),
    )

    result = build_style_dna(corpus, tmp_path / "style_dna", strict_counts=False)
    manifest = result["manifest"]

    assert manifest["discovered_source_count"] == 4
    assert manifest["excluded_source_count"] == 1
    assert manifest["excluded_source_files"] == [
        "pairs_singletrack_backup\\pair_001\\style_fingerprint.json"
    ] or manifest["excluded_source_files"] == [
        "pairs_singletrack_backup/pair_001/style_fingerprint.json"
    ]

    assert manifest["total_source_count"] == 3
    assert manifest["source_counts"] == {
        "gaming_pairs": 1,
        "top_solo": 1,
        "vlog": 1,
    }

    pairs = result["dna"]["gaming_pairs"]
    solo = result["dna"]["top_solo"]
    vlog = result["dna"]["vlog"]

    assert pairs["transcript_key_resolution"]["key_counts"]["first_window_text"] == 1
    assert solo["transcript_key_resolution"]["key_counts"]["first_10s_text"] == 1
    assert vlog["is_descriptive_only"] is True

    assert pairs["numeric"]["scene_length_seconds"]["median"] == 4.0
    assert pairs["numeric"]["audio_dynamic_range_db"]["median"] == 27.0
    assert pairs["distributions"]["voice_intensity"]["percent"]["normal"] == 100.0
    assert pairs["distributions"]["hook"]["counts"]["narrative"] == 1

    assert pairs["distributions"]["intensity_clustering"]["counts"]["front_loaded"] == 1
    assert solo["distributions"]["intensity_clustering"]["counts"]["burst"] == 1
    assert "kmeans" not in json.dumps(result, ensure_ascii=False).lower()

    assert pairs["speaker_distribution"]["ali"]["median"] == 0.7
    assert pairs["speaker_distribution"]["friend"]["median"] == 0.3

    print("P5_G3_SMOKE source_count=3 excluded_backups=1 transcript_aliases_ok taxonomy_frequency_ok")
