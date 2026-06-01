from __future__ import annotations

import json

from core.highlight_ranking import HighlightRankingConfig, rank_highlight_segments
from core.pacing_tighten import PacingTightenConfig, apply_pacing_tighten
from core.semantic_content_layer import SemanticContentConfig, analyze_semantic_content, build_utterances


def test_utterance_segmentation_uses_pause_and_marks_thought_boundaries() -> None:
    words = [
        {"word": "Nee", "start_seconds": 1.0, "end_seconds": 1.2},
        {"word": "wenn", "start_seconds": 1.25, "end_seconds": 1.45},
        {"word": "dann", "start_seconds": 1.5, "end_seconds": 1.7},
        {"word": "hier.", "start_seconds": 1.75, "end_seconds": 2.0},
        {"word": "Links", "start_seconds": 3.2, "end_seconds": 3.45},
        {"word": "einer!", "start_seconds": 3.5, "end_seconds": 3.9},
    ]

    utterances, meta = build_utterances(
        words,
        [{"start_seconds": 1.0, "end_seconds": 2.1}, {"start_seconds": 3.2, "end_seconds": 4.0}],
        config=SemanticContentConfig(max_pause_boundary_seconds=0.8),
    )

    assert meta["utterance_count"] == 2
    assert utterances[0]["text"] == "Nee wenn dann hier."
    assert utterances[0]["thought_boundary"]["start"] is True
    assert utterances[1]["start_seconds"] == 3.2


def test_dead_filler_event_callout_and_cache_are_deterministic(tmp_path) -> None:
    words = [
        {"word": "Okay", "start_seconds": 0.0, "end_seconds": 0.2},
        {"word": "okay.", "start_seconds": 0.25, "end_seconds": 0.5},
        {"word": "Links", "start_seconds": 2.0, "end_seconds": 2.2},
        {"word": "ein", "start_seconds": 2.25, "end_seconds": 2.35},
        {"word": "Gegner!", "start_seconds": 2.4, "end_seconds": 2.8},
    ]
    speech = [{"start_seconds": 0.0, "end_seconds": 0.6}, {"start_seconds": 2.0, "end_seconds": 3.0}]
    cache = tmp_path / "semantic.json"

    first = analyze_semantic_content(
        words_raw=words,
        speech_regions_raw=speech,
        video_duration_seconds=4.0,
        config=SemanticContentConfig(),
        cache_path=cache,
    )
    second = analyze_semantic_content(
        words_raw=words,
        speech_regions_raw=speech,
        video_duration_seconds=4.0,
        config=SemanticContentConfig(),
        cache_path=cache,
    )

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    filler = next(row for row in first["utterances"] if row["text"].startswith("Okay"))
    callout = next(row for row in first["utterances"] if row["text"].startswith("Links"))
    assert filler["is_dead_or_filler"] is True
    assert callout["is_event_callout"] is True
    assert callout["relevance_score"] > filler["relevance_score"]
    assert first["silence_units"][0]["is_dead_or_filler"] is True


def test_semantic_relevance_can_change_highlight_ranking() -> None:
    content = [
        {"segment_id": "filler", "start_seconds": 0.0, "end_seconds": 10.0},
        {"segment_id": "callout", "start_seconds": 10.0, "end_seconds": 20.0},
    ]
    raw = [
        {"start_seconds": 0.0, "end_seconds": 10.0, "audio_peak_score": 0.1},
        {"start_seconds": 10.0, "end_seconds": 20.0, "audio_peak_score": 0.1},
    ]
    semantic = [
        {"utterance_id": "u1", "start_seconds": 0.0, "end_seconds": 10.0, "relevance_score": 0.0, "is_dead_or_filler": True},
        {"utterance_id": "u2", "start_seconds": 10.0, "end_seconds": 20.0, "relevance_score": 1.0, "is_event_callout": True},
    ]

    out, audit = rank_highlight_segments(
        content_segments=content,
        raw_windows=raw,
        semantic_units=semantic,
        target_seconds=10.0,
        config=HighlightRankingConfig(min_target_seconds=0.0, semantic_weight=0.5),
    )

    assert len(out) == 1
    assert out[0]["start_seconds"] == 10.0
    row = next(item for item in audit["ranked_rows"] if item["start_seconds"] == 10.0)
    assert row["semantic_relevance_score"] == 1.0


def test_pacing_cuts_calm_subrange_inside_action_stretch_outside_combat() -> None:
    ranked = [{"segment_id": "action", "start_seconds": 0.0, "end_seconds": 10.0, "mandatory_keep": True}]
    speech = [{"start_seconds": 0.0, "end_seconds": 2.0}, {"start_seconds": 4.0, "end_seconds": 10.0}]
    raw = [
        {"start_seconds": 0.0, "end_seconds": 2.0, "audio_peak_score": 1.0},
        {"start_seconds": 2.0, "end_seconds": 4.0, "audio_peak_score": 0.0},
        {"start_seconds": 4.0, "end_seconds": 10.0, "audio_peak_score": 1.0},
    ]
    semantic = [
        {
            "utterance_id": "silence",
            "start_seconds": 2.0,
            "end_seconds": 4.0,
            "word_count": 0,
            "relevance_score": 0.0,
            "is_dead_or_filler": True,
        }
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=speech,
        raw_windows=raw,
        semantic_units=semantic,
        config=PacingTightenConfig(
            round1_fight_start_seconds=100.0,
            round1_fight_end_seconds=200.0,
            min_plausible_duration_seconds=0.0,
        ),
    )

    assert [(row["start_seconds"], row["end_seconds"]) for row in out] == [(0.0, 2.15), (3.85, 10.0)]
    assert audit["removed_speech_seconds"] == 0.0
    assert audit["per_segment"][0]["internal_cut_count"] == 1
    hard = audit["hard_checks"]["cut_count_increased_but_action_locked"]
    assert hard["combat_ranges_zero_internal_cuts"] is True
    assert hard["action_rows_zero_internal_cuts"] is False


def test_pacing_cuts_sustained_dead_pocket_inside_locked_action_range() -> None:
    ranked = [{"segment_id": "fight", "start_seconds": 100.0, "end_seconds": 130.0, "mandatory_keep": True}]
    speech = [{"start_seconds": 100.0, "end_seconds": 110.0}, {"start_seconds": 115.0, "end_seconds": 130.0}]
    raw = [
        {"start_seconds": 100.0, "end_seconds": 110.0, "audio_peak_score": 1.0},
        {"start_seconds": 110.0, "end_seconds": 115.0, "audio_peak_score": 0.0},
        {"start_seconds": 115.0, "end_seconds": 130.0, "audio_peak_score": 1.0},
    ]
    semantic = [
        {
            "utterance_id": "locked_dead",
            "start_seconds": 110.0,
            "end_seconds": 115.0,
            "word_count": 0,
            "relevance_score": 0.0,
            "is_dead_or_filler": True,
            "is_event_callout": False,
        }
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=speech,
        raw_windows=raw,
        semantic_units=semantic,
        config=PacingTightenConfig(
            round1_fight_start_seconds=100.0,
            round1_fight_end_seconds=130.0,
            min_plausible_duration_seconds=0.0,
        ),
    )

    assert [(row["start_seconds"], row["end_seconds"]) for row in out] == [(100.0, 110.15), (114.85, 130.0)]
    fight_check = audit["hard_checks"]["round1_fight_full_coverage"]
    assert fight_check["status"] == "JA"
    assert fight_check["coverage"] < 1.0
    assert fight_check["internal_cut_count"] == 0
    assert audit["removed_speech_seconds"] == 0.0


def test_pacing_keeps_callout_peak_and_speech_inside_locked_action_range() -> None:
    ranked = [{"segment_id": "fight", "start_seconds": 100.0, "end_seconds": 130.0, "mandatory_keep": True}]
    speech = [{"start_seconds": 122.0, "end_seconds": 124.0}]
    raw = [
        {"start_seconds": 100.0, "end_seconds": 115.0, "audio_peak_score": 0.0},
        {"start_seconds": 115.0, "end_seconds": 120.0, "audio_peak_score": 1.0},
        {"start_seconds": 120.0, "end_seconds": 130.0, "audio_peak_score": 0.0},
    ]
    semantic = [
        {
            "utterance_id": "callout",
            "start_seconds": 105.0,
            "end_seconds": 110.0,
            "word_count": 0,
            "is_dead_or_filler": True,
            "is_event_callout": True,
        },
        {
            "utterance_id": "audio_peak",
            "start_seconds": 115.0,
            "end_seconds": 120.0,
            "word_count": 0,
            "is_dead_or_filler": True,
            "is_event_callout": False,
        },
        {
            "utterance_id": "speech",
            "start_seconds": 122.0,
            "end_seconds": 124.0,
            "word_count": 0,
            "is_dead_or_filler": True,
            "is_event_callout": False,
        },
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=speech,
        raw_windows=raw,
        semantic_units=semantic,
        config=PacingTightenConfig(
            round1_fight_start_seconds=100.0,
            round1_fight_end_seconds=130.0,
            min_plausible_duration_seconds=0.0,
        ),
    )

    assert [(row["start_seconds"], row["end_seconds"]) for row in out] == [(100.0, 130.0)]
    fight_row = audit["per_segment"][0]
    assert fight_row["internal_cut_count"] == 0
    assert audit["hard_checks"]["round1_fight_full_coverage"]["status"] == "JA"


def test_pacing_calm_cut_keeps_breathing_room_around_words() -> None:
    ranked = [{"segment_id": "calm", "start_seconds": 0.0, "end_seconds": 10.0}]
    speech = [{"start_seconds": 0.0, "end_seconds": 2.0}, {"start_seconds": 4.0, "end_seconds": 10.0}]
    raw = [{"start_seconds": 0.0, "end_seconds": 10.0, "audio_peak_score": 0.0}]
    semantic = [
        {
            "utterance_id": "silence",
            "start_seconds": 2.0,
            "end_seconds": 4.0,
            "word_count": 0,
            "is_dead_or_filler": True,
        }
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=speech,
        raw_windows=raw,
        semantic_units=semantic,
        config=PacingTightenConfig(
            internal_silence_min_seconds=0.8,
            min_plausible_duration_seconds=0.0,
            round1_fight_start_seconds=100.0,
            round1_fight_end_seconds=200.0,
            breath_ms=150,
        ),
    )

    assert [(row["start_seconds"], row["end_seconds"]) for row in out] == [(0.0, 2.15), (3.85, 10.0)]
    assert audit["hard_checks"]["breathing_room"]["status"] == "JA"
    check = audit["breathing_room_checks"][0]
    assert check["left_gap_after_previous_word_seconds"] == 0.15
    assert check["right_gap_before_next_word_seconds"] == 0.15


def test_round_transition_tail_trims_and_next_round_starts_with_breath() -> None:
    ranked = [{"segment_id": "rounds", "start_seconds": 100.0, "end_seconds": 200.0, "mandatory_keep": True}]
    speech = [
        {"start_seconds": 130.0, "end_seconds": 145.0},
        {"start_seconds": 148.0, "end_seconds": 150.0},
        {"start_seconds": 160.0, "end_seconds": 165.0},
    ]
    raw = [{"start_seconds": 100.0, "end_seconds": 200.0, "audio_peak_score": 1.0}]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=speech,
        raw_windows=raw,
        config=PacingTightenConfig(
            round1_fight_start_seconds=120.0,
            round1_fight_end_seconds=140.0,
            min_plausible_duration_seconds=0.0,
            breath_ms=150,
        ),
    )

    assert [(row["start_seconds"], row["end_seconds"]) for row in out] == [(100.0, 145.15), (159.85, 200.0)]
    assert audit["hard_checks"]["round_transition_tightened"]["status"] == "JA"
    assert all(row["internal_cut_count"] == 0 for row in audit["per_segment"] if row["is_action"])
    transition = audit["round_transition_cuts"][0]
    assert transition["round1_last_beat_seconds"] == 145.0
    assert transition["round2_first_speech_onset_seconds"] == 160.0


def test_pacing_cuts_spoken_semantic_filler_in_calm_stretch_on_boundaries() -> None:
    ranked = [{"segment_id": "calm", "start_seconds": 0.0, "end_seconds": 8.0}]
    speech = [{"start_seconds": 1.0, "end_seconds": 7.0}]
    raw = [{"start_seconds": 0.0, "end_seconds": 8.0, "audio_peak_score": 0.0}]
    semantic = [
        {
            "utterance_id": "filler",
            "start_seconds": 2.0,
            "end_seconds": 4.0,
            "word_count": 3,
            "text": "okay ja okay",
            "relevance_score": 0.0,
            "is_dead_or_filler": True,
            "thought_boundary": {"start": True, "end": True},
        }
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=speech,
        raw_windows=raw,
        semantic_units=semantic,
        config=PacingTightenConfig(
            internal_silence_min_seconds=99.0,
            min_plausible_duration_seconds=0.0,
            round1_fight_start_seconds=100.0,
            round1_fight_end_seconds=200.0,
        ),
    )

    assert [(row["start_seconds"], row["end_seconds"]) for row in out] == [(0.0, 2.0), (4.0, 8.0)]
    assert audit["removed_speech_seconds"] == 0.0
    assert audit["per_segment"][0]["internal_cuts"][0]["reason"] == "semantic_dead_or_filler"


def test_pacing_snaps_mid_thought_segment_start_back_to_boundary() -> None:
    ranked = [
        {"segment_id": "intro", "start_seconds": 0.0, "end_seconds": 1.0},
        {"segment_id": "mid_thought", "start_seconds": 5.0, "end_seconds": 8.0},
    ]
    speech = [{"start_seconds": 0.0, "end_seconds": 1.0}, {"start_seconds": 3.5, "end_seconds": 8.0}]
    raw = [
        {"start_seconds": 0.0, "end_seconds": 1.0, "audio_peak_score": 0.1},
        {"start_seconds": 3.5, "end_seconds": 8.0, "audio_peak_score": 0.1},
    ]
    semantic = [
        {
            "utterance_id": "thought",
            "start_seconds": 3.5,
            "end_seconds": 6.0,
            "word_count": 4,
            "text": "Nee wenn dann hier",
            "relevance_score": 0.6,
            "thought_boundary": {"start": True, "end": True},
        }
    ]

    out, audit = apply_pacing_tighten(
        ranked_segments=ranked,
        combined_speech_regions=speech,
        raw_windows=raw,
        semantic_units=semantic,
        config=PacingTightenConfig(internal_silence_min_seconds=99.0, min_plausible_duration_seconds=0.0),
    )

    second = next(row for row in out if row["metadata"]["pacing_tighten_source_segment_id"] == "mid_thought")
    assert second["start_seconds"] == 3.5
    row = next(item for item in audit["per_segment"] if item["source_segment_id"] == "mid_thought")
    assert "start_extended_to_semantic_thought_boundary" in row["operations"]
