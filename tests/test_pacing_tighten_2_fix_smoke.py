from __future__ import annotations

from core.pacing_tighten import PacingTightenConfig, apply_pacing_tighten


def test_start_snaps_to_owner_not_friend_or_silence():
    ranked = [{"segment_id": "intro", "start_seconds": 10.0, "end_seconds": 40.0}]
    combined = [
        {"start_seconds": 10.0, "end_seconds": 12.0, "speaker": "FRIEND"},
        {"start_seconds": 15.0, "end_seconds": 20.0, "speaker": "OWNER"},
    ]
    owner = [{"start_seconds": 15.0, "end_seconds": 20.0, "speaker": "OWNER"}]
    raw = [{"start_seconds": 10.0, "end_seconds": 40.0, "audio_peak_score": 0.1}]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=combined,
        owner_speech_regions=owner,
        owner_speech_source="reports/owner_track1_speech_regions.json",
        raw_windows=raw,
        config=PacingTightenConfig(internal_silence_min_seconds=99.0),
    )

    assert out[0]["start_seconds"] == 15.0
    assert audit["hard_checks"]["owner_onset_plausible"]["status"] == "JA"


def test_action_stretch_gets_zero_internal_cuts_and_full_fight_coverage():
    ranked = [
        {"segment_id": "intro", "start_seconds": 10.0, "end_seconds": 20.0},
        {"segment_id": "fight", "start_seconds": 100.0, "end_seconds": 270.0, "mandatory_keep": True},
    ]
    combined = [
        {"start_seconds": 12.0, "end_seconds": 15.0},
        {"start_seconds": 110.0, "end_seconds": 130.0},
        {"start_seconds": 150.0, "end_seconds": 160.0},
        {"start_seconds": 220.0, "end_seconds": 250.0},
    ]
    owner = [{"start_seconds": 12.0, "end_seconds": 15.0}]
    raw = [
        {"start_seconds": 10.0, "end_seconds": 20.0, "audio_peak_score": 0.1},
        {"start_seconds": 100.0, "end_seconds": 270.0, "audio_peak_score": 1.0},
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=combined,
        owner_speech_regions=owner,
        owner_speech_source="reports/owner_track1_speech_regions.json",
        raw_windows=raw,
    )

    fight_row = next(row for row in audit["per_segment"] if row["source_segment_id"] == "fight")

    assert fight_row["classification"] == "ACTION"
    assert fight_row["internal_cut_count"] == 0
    assert audit["hard_checks"]["round1_fight_full_coverage"]["status"] == "JA"


def test_calm_stretch_gets_dead_beat_cuts():
    ranked = [
        {"segment_id": "intro", "start_seconds": 10.0, "end_seconds": 20.0},
        {"segment_id": "calm", "start_seconds": 50.0, "end_seconds": 60.0},
    ]
    combined = [
        {"start_seconds": 12.0, "end_seconds": 15.0},
        {"start_seconds": 50.0, "end_seconds": 52.0},
        {"start_seconds": 53.0, "end_seconds": 55.0},
        {"start_seconds": 56.0, "end_seconds": 60.0},
    ]
    owner = [{"start_seconds": 12.0, "end_seconds": 15.0}]
    raw = [
        {"start_seconds": 10.0, "end_seconds": 20.0, "audio_peak_score": 0.1},
        {"start_seconds": 50.0, "end_seconds": 52.0, "audio_peak_score": 0.1},
        {"start_seconds": 52.0, "end_seconds": 53.0, "audio_peak_score": 0.0},
        {"start_seconds": 53.0, "end_seconds": 55.0, "audio_peak_score": 0.1},
        {"start_seconds": 55.0, "end_seconds": 56.0, "audio_peak_score": 0.0},
        {"start_seconds": 56.0, "end_seconds": 60.0, "audio_peak_score": 0.1},
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=combined,
        owner_speech_regions=owner,
        owner_speech_source="reports/owner_track1_speech_regions.json",
        raw_windows=raw,
        config=PacingTightenConfig(internal_silence_min_seconds=0.8),
    )

    calm_row = next(row for row in audit["per_segment"] if row["source_segment_id"] == "calm")

    assert calm_row["classification"] == "CALM"
    assert calm_row["internal_cut_count"] == 2
    assert audit["removed_speech_seconds"] == 0.0


def test_payoff_is_locked_exact_when_is_payoff_true():
    ranked = [
        {"segment_id": "intro", "start_seconds": 10.0, "end_seconds": 20.0},
        {"segment_id": "payoff", "start_seconds": 1756.0, "end_seconds": 1810.817, "payoff_tail": True},
    ]
    combined = [
        {"start_seconds": 12.0, "end_seconds": 15.0},
        {"start_seconds": 1757.0, "end_seconds": 1810.0},
    ]
    owner = [{"start_seconds": 12.0, "end_seconds": 15.0}]
    raw = [
        {"start_seconds": 10.0, "end_seconds": 20.0, "audio_peak_score": 0.1},
        {"start_seconds": 1756.0, "end_seconds": 1810.817, "audio_peak_score": 0.1},
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=combined,
        owner_speech_regions=owner,
        owner_speech_source="reports/owner_track1_speech_regions.json",
        raw_windows=raw,
        payoff_tail_segments=[ranked[1]],
    )

    payoff = next(row for row in out if row["metadata"]["pacing_tighten_source_segment_id"] == "payoff")

    assert payoff["start_seconds"] == 1756.0
    assert payoff["end_seconds"] == 1810.817
    assert audit["hard_checks"]["payoff_locked_exact"]["status"] == "JA"
