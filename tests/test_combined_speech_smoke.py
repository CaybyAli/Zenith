from __future__ import annotations

from core.combined_speech import (
    build_combined_silence_gaps,
    build_combined_speech_summary,
    combine_speech_regions,
    find_friend_speaks_owner_silent_examples,
)
from core.real_vad_validation import coverage_seconds


def test_union_two_tracks_one_talks_counts_as_speech():
    owner = [{"start_seconds": 10.0, "end_seconds": 12.0, "duration_seconds": 2.0}]
    friend = [{"start_seconds": 20.0, "end_seconds": 22.0, "duration_seconds": 2.0}]

    combined = combine_speech_regions(owner_regions=owner, friend_regions=friend)

    assert len(combined) == 2
    assert coverage_seconds(combined, start_seconds=10.0, end_seconds=12.0) == 2.0
    assert coverage_seconds(combined, start_seconds=20.0, end_seconds=22.0) == 2.0


def test_both_silent_becomes_combined_silence():
    owner = [{"start_seconds": 10.0, "end_seconds": 12.0, "duration_seconds": 2.0}]
    friend = [{"start_seconds": 20.0, "end_seconds": 22.0, "duration_seconds": 2.0}]

    combined = combine_speech_regions(owner_regions=owner, friend_regions=friend)
    gaps = build_combined_silence_gaps(
        combined_speech_regions=combined,
        media_duration_seconds=30.0,
    )

    assert any(gap["start_seconds"] == 12.0 and gap["end_seconds"] == 20.0 for gap in gaps)


def test_overlapping_tracks_merge_to_single_anyone_speech_region():
    owner = [{"start_seconds": 10.0, "end_seconds": 13.0, "duration_seconds": 3.0}]
    friend = [{"start_seconds": 12.0, "end_seconds": 15.0, "duration_seconds": 3.0}]

    combined = combine_speech_regions(owner_regions=owner, friend_regions=friend)

    assert len(combined) == 1
    assert combined[0]["start_seconds"] == 10.0
    assert combined[0]["end_seconds"] == 15.0
    assert combined[0]["roles"] == ["owner", "friend"]


def test_friend_speaks_owner_silent_example_is_detected():
    owner = [{"start_seconds": 10.0, "end_seconds": 12.0, "duration_seconds": 2.0}]
    friend = [{"start_seconds": 20.0, "end_seconds": 23.0, "duration_seconds": 3.0}]

    combined = combine_speech_regions(owner_regions=owner, friend_regions=friend)
    examples = find_friend_speaks_owner_silent_examples(
        owner_regions=owner,
        friend_regions=friend,
        combined_regions=combined,
        min_duration_seconds=0.5,
    )

    assert len(examples) == 1
    assert examples[0]["status"] == "PASS"
    assert examples[0]["owner_overlap_seconds"] == 0.0
    assert examples[0]["combined_overlap_seconds"] == 3.0


def test_combined_speech_share_is_not_lower_than_single_tracks():
    owner = [{"start_seconds": 0.0, "end_seconds": 10.0, "duration_seconds": 10.0}]
    friend = [{"start_seconds": 20.0, "end_seconds": 30.0, "duration_seconds": 10.0}]
    combined = combine_speech_regions(owner_regions=owner, friend_regions=friend)
    gaps = build_combined_silence_gaps(
        combined_speech_regions=combined,
        media_duration_seconds=40.0,
    )

    summary = build_combined_speech_summary(
        owner_regions=owner,
        friend_regions=friend,
        combined_regions=combined,
        combined_silence_gaps=gaps,
        media_duration_seconds=40.0,
    )

    assert summary["owner_speech_share_percent"] == 25.0
    assert summary["friend_speech_share_percent"] == 25.0
    assert summary["combined_speech_share_percent"] == 50.0
