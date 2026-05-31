from core.speech_foundation import (
    build_silence_gaps,
    build_speech_segments,
    find_phrase_occurrences,
    speech_coverage_percent,
)


def test_speech_segments_merge_words_when_gap_is_below_default_threshold():
    words = [
        {"word": "Nils", "start_seconds": 1.0, "end_seconds": 1.2, "confidence": 0.9},
        {"word": "hinter", "start_seconds": 1.45, "end_seconds": 1.7, "confidence": 0.9},
        {"word": "dir", "start_seconds": 2.2, "end_seconds": 2.4, "confidence": 0.9},
    ]

    segments = build_speech_segments(words, merge_gap=0.3)

    assert len(segments) == 2
    assert segments[0]["text"] == "Nils hinter"
    assert segments[0]["start_seconds"] == 1.0
    assert segments[0]["end_seconds"] == 1.7
    assert segments[0]["word_count"] == 2
    assert segments[1]["text"] == "dir"


def test_silence_gaps_are_built_between_speech_segments():
    segments = [
        {"start_seconds": 1.0, "end_seconds": 1.7, "duration_seconds": 0.7},
        {"start_seconds": 2.2, "end_seconds": 2.4, "duration_seconds": 0.2},
        {"start_seconds": 3.0, "end_seconds": 3.4, "duration_seconds": 0.4},
    ]

    gaps = build_silence_gaps(segments)

    assert gaps == [
        {"start_seconds": 1.7, "end_seconds": 2.2, "duration_seconds": 0.5},
        {"start_seconds": 2.4, "end_seconds": 3.0, "duration_seconds": 0.6},
    ]


def test_phrase_finder_normalizes_fuer_and_umlaut():
    words = [
        {"word": "Was", "start_seconds": 10.0, "end_seconds": 10.1},
        {"word": "ist", "start_seconds": 10.2, "end_seconds": 10.3},
        {"word": "das", "start_seconds": 10.4, "end_seconds": 10.5},
        {"word": "für", "start_seconds": 10.6, "end_seconds": 10.7},
        {"word": "ein", "start_seconds": 10.8, "end_seconds": 10.9},
        {"word": "Auto", "start_seconds": 11.0, "end_seconds": 11.2},
    ]

    matches = find_phrase_occurrences(words, "Was ist das fuer ein Auto")

    assert len(matches) == 1
    assert [word["word"] for word in matches[0]] == ["Was", "ist", "das", "für", "ein", "Auto"]


def test_speech_coverage_percent_uses_segment_durations():
    segments = [
        {"start_seconds": 0.0, "end_seconds": 2.0, "duration_seconds": 2.0},
        {"start_seconds": 5.0, "end_seconds": 7.0, "duration_seconds": 2.0},
    ]

    assert speech_coverage_percent(segments, media_duration_seconds=10.0) == 40.0
