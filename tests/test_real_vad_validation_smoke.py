from __future__ import annotations

from core.real_vad_validation import (
    coverage_seconds,
    invert_regions_to_silence_gaps,
    merge_regions,
    speech_share_percent,
    validate_real_vad_windows,
)


def test_merge_regions_closes_short_gap():
    merged = merge_regions(
        [
            {"start_seconds": 1.0, "end_seconds": 2.0},
            {"start_seconds": 2.1, "end_seconds": 3.0},
            {"start_seconds": 5.0, "end_seconds": 6.0},
        ],
        max_gap_seconds=0.2,
    )

    assert len(merged) == 2
    assert merged[0]["start_seconds"] == 1.0
    assert merged[0]["end_seconds"] == 3.0


def test_invert_regions_to_silence_gaps():
    gaps = invert_regions_to_silence_gaps(
        [
            {"start_seconds": 1.0, "end_seconds": 3.0},
            {"start_seconds": 5.0, "end_seconds": 6.0},
        ],
        media_duration_seconds=8.0,
    )

    assert gaps[0]["start_seconds"] == 0.0
    assert gaps[0]["end_seconds"] == 1.0
    assert gaps[1]["start_seconds"] == 3.0
    assert gaps[1]["end_seconds"] == 5.0
    assert gaps[2]["start_seconds"] == 6.0
    assert gaps[2]["end_seconds"] == 8.0


def test_coverage_seconds_counts_overlap():
    overlap = coverage_seconds(
        [
            {"start_seconds": 1.0, "end_seconds": 4.0},
            {"start_seconds": 10.0, "end_seconds": 12.0},
        ],
        start_seconds=2.0,
        end_seconds=11.0,
    )

    assert overlap == 3.0


def test_speech_share_percent():
    share = speech_share_percent(
        [
            {"start_seconds": 0.0, "end_seconds": 10.0, "duration_seconds": 10.0},
            {"start_seconds": 20.0, "end_seconds": 30.0, "duration_seconds": 10.0},
        ],
        media_duration_seconds=40.0,
    )

    assert share == 50.0


def test_validate_known_windows_passes_with_expected_regions():
    speech_regions = [
        {"start_seconds": 285.0, "end_seconds": 288.0, "duration_seconds": 3.0},
        {"start_seconds": 767.0, "end_seconds": 768.0, "duration_seconds": 1.0},
        {"start_seconds": 1786.0, "end_seconds": 1810.0, "duration_seconds": 24.0},
        {"start_seconds": 100.0, "end_seconds": 800.0, "duration_seconds": 700.0},
    ]
    silence_gaps = [
        {"start_seconds": 599.15, "end_seconds": 615.46, "duration_seconds": 16.31},
        {"start_seconds": 258.62, "end_seconds": 278.62, "duration_seconds": 20.0},
    ]

    result = validate_real_vad_windows(
        speech_regions=speech_regions,
        silence_gaps=silence_gaps,
        media_duration_seconds=1800.0,
    )

    assert result["known_speech_checks"][0]["status"] == "PASS"
    assert result["known_silence_checks"][0]["status"] == "PASS"


def test_validate_known_windows_fails_too_low_speech_share():
    result = validate_real_vad_windows(
        speech_regions=[
            {"start_seconds": 1786.0, "end_seconds": 1810.0, "duration_seconds": 24.0},
        ],
        silence_gaps=[
            {"start_seconds": 599.15, "end_seconds": 615.46, "duration_seconds": 16.31},
            {"start_seconds": 258.62, "end_seconds": 278.62, "duration_seconds": 20.0},
        ],
        media_duration_seconds=1800.0,
    )

    assert result["speech_share_status"] == "FAIL"
    assert result["overall_status"] == "FAIL"
