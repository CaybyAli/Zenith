
from core.pacing_tighten import (
    PacingTightenConfig,
    _p4_action_candidate_cuts,
)
from core.semantic_content_layer import SemanticContentConfig, build_utterances


def test_sustained_dead_in_combat_is_cut():
    config = PacingTightenConfig(
        min_dead_in_combat_seconds=4.0,
        round1_fight_start_seconds=142.0,
        round1_fight_end_seconds=246.0,
    )
    candidate_cuts = [
        {
            "start_seconds": 199.0,
            "end_seconds": 207.0,
            "duration_seconds": 8.0,
            "reason": "semantic_dead_or_filler",
        }
    ]

    kept = _p4_action_candidate_cuts(
        candidate_cuts,
        combined_speech_regions=[
            {"start_seconds": 190.0, "end_seconds": 198.5},
            {"start_seconds": 207.5, "end_seconds": 215.0},
        ],
        raw_windows=[
            {"start_seconds": 199.0, "end_seconds": 207.0, "audio_peak_score": 0.01}
        ],
        semantic_units=[
            {
                "utterance_id": "silence_00001",
                "start_seconds": 199.0,
                "end_seconds": 207.0,
                "is_dead_or_filler": True,
                "semantic_reasons": ["vad_silence_gap"],
            }
        ],
        audio_peak_floor=0.50,
        config=config,
    )

    assert len(kept) == 1
    assert kept[0]["reason"] == "sustained_dead_in_combat"
    assert kept[0]["combat_dead_cut"] is True


def test_short_combat_lull_is_not_cut():
    config = PacingTightenConfig(
        min_dead_in_combat_seconds=4.0,
        round1_fight_start_seconds=142.0,
        round1_fight_end_seconds=246.0,
    )
    candidate_cuts = [
        {
            "start_seconds": 201.0,
            "end_seconds": 202.5,
            "duration_seconds": 1.5,
            "reason": "semantic_dead_or_filler",
        }
    ]

    kept = _p4_action_candidate_cuts(
        candidate_cuts,
        combined_speech_regions=[],
        raw_windows=[
            {"start_seconds": 201.0, "end_seconds": 202.5, "audio_peak_score": 0.01}
        ],
        semantic_units=[
            {
                "utterance_id": "silence_00002",
                "start_seconds": 201.0,
                "end_seconds": 202.5,
                "is_dead_or_filler": True,
                "semantic_reasons": ["vad_silence_gap"],
            }
        ],
        audio_peak_floor=0.50,
        config=config,
    )

    assert kept == []


def test_thought_survives_short_pause_same_speaker_language():
    config = SemanticContentConfig(
        sentence_end_pause_seconds=0.20,
        thought_gap_seconds=2.0,
        max_utterance_seconds=20.0,
        max_words_per_utterance=50,
    )

    words = [
        {"word": "Hoer", "start_seconds": 388.00, "end_seconds": 388.20, "word_index": 1, "speaker": "OWNER", "language": "de"},
        {"word": "mal", "start_seconds": 388.25, "end_seconds": 388.45, "word_index": 2, "speaker": "OWNER", "language": "de"},
        {"word": "zu", "start_seconds": 388.50, "end_seconds": 388.65, "word_index": 3, "speaker": "OWNER", "language": "de"},
        {"word": "Sportsfreund.", "start_seconds": 388.70, "end_seconds": 389.00, "word_index": 4, "speaker": "OWNER", "language": "de"},
        {"word": "ich", "start_seconds": 390.20, "end_seconds": 390.40, "word_index": 5, "speaker": "OWNER", "language": "de"},
        {"word": "rede", "start_seconds": 390.45, "end_seconds": 390.65, "word_index": 6, "speaker": "OWNER", "language": "de"},
        {"word": "weiter", "start_seconds": 390.70, "end_seconds": 391.00, "word_index": 7, "speaker": "OWNER", "language": "de"},
    ]

    utterances, metadata = build_utterances(words, [], config=config)

    assert len(utterances) == 1
    assert "Sportsfreund" in utterances[0]["text"]
    assert "weiter" in utterances[0]["text"]


def test_unlabeled_words_still_split_on_real_pause():
    config = SemanticContentConfig(max_pause_boundary_seconds=0.8)
    words = [
        {"word": "hier.", "start_seconds": 1.75, "end_seconds": 2.0},
        {"word": "Links", "start_seconds": 3.2, "end_seconds": 3.45},
    ]

    utterances, metadata = build_utterances(words, [], config=config)

    assert metadata["utterance_count"] == 2
