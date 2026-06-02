from __future__ import annotations

from core.pacing_tighten import PacingTightenConfig, apply_pacing_tighten


def test_intro_extends_to_gameplay_start_from_raw_action():
    ranked = [
        {"segment_id": "first", "start_seconds": 50.0, "end_seconds": 90.0},
    ]
    speech = [
        {"start_seconds": 55.0, "end_seconds": 60.0},
        {"start_seconds": 70.0, "end_seconds": 80.0},
    ]
    raw = [
        {"start_seconds": 10.0, "end_seconds": 12.0, "audio_peak_score": 1.0},
        {"start_seconds": 50.0, "end_seconds": 90.0, "audio_peak_score": 0.2},
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=speech,
        raw_windows=raw,
        config=PacingTightenConfig(internal_silence_min_seconds=99.0),
    )

    # 0-A v18 truth: old 10.0 -> new 50.0; no owner VAD means no raw-action intro extension.
    assert out[0]["start_seconds"] == 50.0
    assert audit["intro_start_speaker"] == "MISSING"
    assert audit["hard_checks"]["owner_onset_plausible"]["status"] == "NEIN"


def test_dead_lead_start_snaps_to_first_speech_onset_without_removing_speech():
    ranked = [
        {"segment_id": "intro", "start_seconds": 0.0, "end_seconds": 5.0},
        {"segment_id": "next", "start_seconds": 100.0, "end_seconds": 120.0},
    ]
    speech = [
        {"start_seconds": 0.5, "end_seconds": 2.0},
        {"start_seconds": 102.0, "end_seconds": 110.0},
    ]
    raw = [
        {"start_seconds": 0.0, "end_seconds": 5.0, "audio_peak_score": 0.1},
        {"start_seconds": 100.0, "end_seconds": 102.0, "audio_peak_score": 0.0},
        {"start_seconds": 102.0, "end_seconds": 120.0, "audio_peak_score": 0.1},
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=speech,
        raw_windows=raw,
        config=PacingTightenConfig(internal_silence_min_seconds=99.0),
    )

    next_piece = next(row for row in out if row["metadata"]["pacing_tighten_source_segment_id"] == "next")
    # 0-A v18 truth: old 102.0 -> new 101.85 because the 0.15s tail/breath lock is preserved.
    assert next_piece["start_seconds"] == 101.85
    assert audit["removed_speech_seconds"] == 0.0
    assert audit["hard_checks"]["removed_speech_zero"]["status"] == "JA"


def test_internal_dead_beat_cut_uses_vad_boundaries_without_word_cut():
    ranked = [
        {"segment_id": "seg", "start_seconds": 0.0, "end_seconds": 10.0},
    ]
    speech = [
        {"start_seconds": 0.0, "end_seconds": 2.0},
        {"start_seconds": 5.0, "end_seconds": 8.0},
    ]
    raw = [
        {"start_seconds": 0.0, "end_seconds": 2.0, "audio_peak_score": 0.1},
        {"start_seconds": 2.0, "end_seconds": 5.0, "audio_peak_score": 0.0},
        {"start_seconds": 5.0, "end_seconds": 8.0, "audio_peak_score": 0.1},
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=speech,
        raw_windows=raw,
        config=PacingTightenConfig(internal_silence_min_seconds=1.0, breath_ms=150),
    )

    ranges = [(row["start_seconds"], row["end_seconds"]) for row in out]
    # 0-A v18 truth: old VAD edges 0.0-2.0 and 5.0-8.0 -> 0.0-2.15 and 4.85-8.15 via 0.15s breath.
    assert (0.0, 2.15) in ranges
    assert (4.85, 8.15) in ranges
    assert audit["removed_speech_seconds"] == 0.0
    assert audit["hard_checks"]["removed_speech_zero"]["status"] == "JA"
    assert audit["new_segment_count"] > audit["old_segment_count"]
