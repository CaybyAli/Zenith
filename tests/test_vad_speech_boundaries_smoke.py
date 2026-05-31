from __future__ import annotations

from core.vad_speech_boundaries import (
    build_energy_frame_scores_from_pcm_i16,
    find_pollution_examples,
    invert_regions_to_silence_gaps,
    merge_regions,
    vad_regions_from_frame_scores,
    word_derived_speech_regions,
)


def test_invert_regions_to_silence_gaps():
    gaps = invert_regions_to_silence_gaps(
        [
            {"start_seconds": 1.0, "end_seconds": 3.0},
            {"start_seconds": 5.0, "end_seconds": 6.0},
        ],
        media_duration_seconds=8.0,
        source="test",
    )

    assert gaps[0]["start_seconds"] == 0.0
    assert gaps[0]["end_seconds"] == 1.0
    assert gaps[1]["start_seconds"] == 3.0
    assert gaps[1]["end_seconds"] == 5.0
    assert gaps[2]["start_seconds"] == 6.0
    assert gaps[2]["end_seconds"] == 8.0


def test_pollution_example_detects_vad_silence_hidden_by_long_word():
    words = [
        {"word": "richtig.", "start_seconds": 10.0, "end_seconds": 30.0, "duration_seconds": 20.0}
    ]
    word_regions = word_derived_speech_regions(words)
    word_gaps = invert_regions_to_silence_gaps(
        word_regions,
        media_duration_seconds=40.0,
        source="word",
    )
    vad_gaps = [
        {"start_seconds": 15.0, "end_seconds": 20.0, "duration_seconds": 5.0}
    ]

    examples = find_pollution_examples(
        vad_silence_gaps=vad_gaps,
        word_derived_silence_gaps=word_gaps,
        words=words,
        limit=3,
    )

    assert len(examples) == 1
    assert examples[0]["polluting_word"]["word"] == "richtig."
    assert examples[0]["word_derived_cover_ratio"] == 0.0


def test_energy_vad_detects_speech_region_from_louder_samples():
    sample_rate = 100
    silence = [0] * 100
    speech = [9000, -9000] * 50
    samples = silence + speech + silence

    frames = build_energy_frame_scores_from_pcm_i16(
        samples,
        sample_rate=sample_rate,
        frame_seconds=0.10,
    )

    regions = vad_regions_from_frame_scores(
        frames,
        threshold_db=-20.0,
        min_speech_seconds=0.2,
        min_silence_seconds=0.1,
        speech_pad_seconds=0.0,
        media_duration_seconds=3.0,
        source="test_energy",
    )

    assert len(regions) == 1
    assert 0.9 <= regions[0]["start_seconds"] <= 1.1
    assert 1.9 <= regions[0]["end_seconds"] <= 2.1


def test_merge_regions_closes_short_silence_gap():
    merged = merge_regions(
        [
            {"start_seconds": 1.0, "end_seconds": 2.0},
            {"start_seconds": 2.1, "end_seconds": 3.0},
            {"start_seconds": 5.0, "end_seconds": 6.0},
        ],
        max_gap_seconds=0.2,
        source="test",
    )

    assert len(merged) == 2
    assert merged[0]["start_seconds"] == 1.0
    assert merged[0]["end_seconds"] == 3.0
