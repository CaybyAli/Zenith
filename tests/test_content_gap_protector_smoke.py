from __future__ import annotations

from core.content_gap_protector import (
    ContentGapProtectorConfig,
    protect_content_gaps,
)


def test_high_audio_gap_with_little_speech_is_content_via_action():
    kept_segments = [
        {"segment_id": "a", "start_seconds": 0.0, "end_seconds": 10.0},
        {"segment_id": "b", "start_seconds": 20.0, "end_seconds": 30.0},
    ]
    raw_windows = [
        {"start_seconds": 0.0, "end_seconds": 10.0, "audio_peak_score": "0.10", "audio_activity": "0.10", "motion_score": "0.10"},
        {"start_seconds": 10.0, "end_seconds": 20.0, "audio_peak_score": "1.00", "audio_activity": "0.90", "motion_score": "0.20"},
        {"start_seconds": 20.0, "end_seconds": 30.0, "audio_peak_score": "0.20", "audio_activity": "0.20", "motion_score": "0.10"},
    ]

    new_segments, audit = protect_content_gaps(
        kept_segments=kept_segments,
        raw_windows=raw_windows,
        combined_speech_regions=[
            {"start_seconds": 12.0, "end_seconds": 12.5},
        ],
        reactions=[],
        g6_states=[
            {"start_seconds": 10.0, "end_seconds": 20.0, "state": "transition_dead_time"},
        ],
        config=ContentGapProtectorConfig(),
    )

    assert audit["metric_discovery"]["audio_keys"] == ["audio_peak_score", "audio_activity"]
    assert audit["gap_rows"][0]["audio_action"] is True
    assert audit["gap_rows"][0]["content_reason"]["audio_action"] is True
    assert audit["gap_rows"][0]["classification"] == "CONTENT"
    assert audit["reincluded_gap_count"] == 1
    assert len(new_segments) == 1
    assert new_segments[0]["start_seconds"] == 0.0
    assert new_segments[0]["end_seconds"] == 30.0


def test_combat_gap_hard_check_uses_configured_range():
    kept_segments = [
        {"segment_id": "a", "start_seconds": 0.0, "end_seconds": 10.0},
        {"segment_id": "b", "start_seconds": 20.0, "end_seconds": 30.0},
    ]
    raw_windows = [
        {"start_seconds": 0.0, "end_seconds": 10.0, "audio_peak_score": "0.10"},
        {"start_seconds": 10.0, "end_seconds": 20.0, "audio_peak_score": "1.00"},
        {"start_seconds": 20.0, "end_seconds": 30.0, "audio_peak_score": "0.20"},
    ]

    _, audit = protect_content_gaps(
        kept_segments=kept_segments,
        raw_windows=raw_windows,
        combined_speech_regions=[{"start_seconds": 12.0, "end_seconds": 12.5}],
        reactions=[],
        g6_states=[{"start_seconds": 10.0, "end_seconds": 20.0, "state": "transition_dead_time"}],
        protected_ranges={"combat": {"start_seconds": 10.0, "end_seconds": 20.0}},
        config=ContentGapProtectorConfig(),
    )

    hard = audit["hard_checks"]
    # alt: round1_gap_142_166_content_and_reincluded / round1_gap_172_246_content_and_reincluded
    # neu: combat_content_gaps_reincluded.
    # Grund: Der Audit prueft alle Content-Gaps innerhalb der per-video Combat-Range.
    check = hard["combat_content_gaps_reincluded"]
    assert check["configured"] is True
    assert check["status"] == "JA"
    assert check["content_gap_count"] == 1


def test_long_gap_low_audio_with_sparse_speech_stays_dead():
    kept_segments = [
        {"segment_id": "a", "start_seconds": 0.0, "end_seconds": 10.0},
        {"segment_id": "b", "start_seconds": 30.0, "end_seconds": 40.0},
    ]
    raw_windows = [
        {"start_seconds": 0.0, "end_seconds": 10.0, "audio_peak_score": "0.90", "motion_score": "0.10"},
        {"start_seconds": 10.0, "end_seconds": 30.0, "audio_peak_score": "0.10", "motion_score": "1.00"},
        {"start_seconds": 30.0, "end_seconds": 40.0, "audio_peak_score": "0.90", "motion_score": "0.10"},
    ]

    new_segments, audit = protect_content_gaps(
        kept_segments=kept_segments,
        raw_windows=raw_windows,
        combined_speech_regions=[
            {"start_seconds": 15.0, "end_seconds": 16.5},
        ],
        reactions=[],
        g6_states=[
            {"start_seconds": 10.0, "end_seconds": 30.0, "state": "transition_dead_time"},
        ],
        config=ContentGapProtectorConfig(),
    )

    assert audit["gap_rows"][0]["audio_action"] is False
    assert audit["gap_rows"][0]["speech_seconds"] == 1.5
    assert audit["gap_rows"][0]["longest_speech_run_seconds"] == 1.5
    assert audit["gap_rows"][0]["speech_share"] < 0.5
    assert audit["gap_rows"][0]["content_reason"]["motion_used_as_primary_reason"] is False
    assert audit["gap_rows"][0]["classification"] == "DEAD"
    assert audit["reincluded_gap_count"] == 0
    assert len(new_segments) == 2


def test_dense_speech_gap_is_content_even_when_audio_below_floor():
    kept_segments = [
        {"segment_id": "a", "start_seconds": 0.0, "end_seconds": 10.0},
        {"segment_id": "b", "start_seconds": 30.0, "end_seconds": 40.0},
    ]
    raw_windows = [
        {"start_seconds": 0.0, "end_seconds": 10.0, "audio_peak_score": "0.90", "motion_score": "0.10"},
        {"start_seconds": 10.0, "end_seconds": 30.0, "audio_peak_score": "0.10", "motion_score": "0.20"},
        {"start_seconds": 30.0, "end_seconds": 40.0, "audio_peak_score": "0.90", "motion_score": "0.10"},
    ]

    new_segments, audit = protect_content_gaps(
        kept_segments=kept_segments,
        raw_windows=raw_windows,
        combined_speech_regions=[
            {"start_seconds": 12.0, "end_seconds": 24.0},
        ],
        reactions=[],
        g6_states=[
            {"start_seconds": 10.0, "end_seconds": 30.0, "state": "transition_dead_time"},
        ],
        config=ContentGapProtectorConfig(),
    )

    assert audit["gap_rows"][0]["audio_action"] is False
    assert audit["gap_rows"][0]["speech_share"] > 0.5
    assert audit["gap_rows"][0]["content_reason"]["speech_content"] is True
    assert audit["gap_rows"][0]["classification"] == "CONTENT"
    assert audit["reincluded_gap_count"] == 1
    assert len(new_segments) == 1
    assert new_segments[0]["start_seconds"] == 0.0
    assert new_segments[0]["end_seconds"] == 40.0
