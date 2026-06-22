from __future__ import annotations

import wave
from pathlib import Path
from types import SimpleNamespace

from core.reaction_focus_decisions import (
    inject_selected_reaction_focus_decisions,
    refine_friend_reaction_candidates,
)


def _write_pcm_wav(path: Path, *, duration_seconds: float, tones: list[tuple[float, ...]]) -> None:
    sample_rate = 1000
    default_amplitude = 9000
    frame_count = int(duration_seconds * sample_rate)

    frames = bytearray()
    for frame_index in range(frame_count):
        timestamp = frame_index / sample_rate
        sample = 0
        for tone in tones:
            start, end = tone[0], tone[1]
            amplitude = int(tone[2]) if len(tone) > 2 else default_amplitude
            if start <= timestamp < end and abs(amplitude) > abs(sample):
                sample = amplitude
        frames.extend(int(sample).to_bytes(2, byteorder="little", signed=True))

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames))


def test_refine_reaction_candidates_sets_zoom_mode_boundaries_and_word_padding(tmp_path: Path) -> None:
    audio_path = tmp_path / "a2.wav"
    _write_pcm_wav(audio_path, duration_seconds=6.0, tones=[(0.5, 5.3)])

    candidates = [
        {"source_index": 0, "start": 0.55, "end": 2.15, "friend_text": "instant edge"},
        {"source_index": 1, "start": 2.55, "end": 3.25, "friend_text": "held word"},
        {"source_index": 2, "start": 3.55, "end": 5.25, "friend_text": "long sentence"},
    ]
    friend_segments = [
        {
            "words": [
                {"word": "one", "start": 0.60, "end": 1.19},
                {"word": "two", "start": 1.20, "end": 1.79},
                {"word": "three", "start": 1.80, "end": 2.10},
            ],
        },
        {
            "words": [
                {"word": "held", "start": 2.60, "end": 3.21},
            ],
        },
        {
            "words": [
                {"word": "one", "start": 3.60, "end": 4.19},
                {"word": "two", "start": 4.20, "end": 4.79},
                {"word": "three", "start": 4.80, "end": 5.20},
            ],
        },
    ]

    accepted, rejected_silence, presence_policy = refine_friend_reaction_candidates(
        candidates,
        friend_segments,
        audio_path,
    )

    assert rejected_silence == []
    assert presence_policy["accepted_count"] == 3
    rows_by_index = {row["source_index"]: row for row in accepted}

    instant = rows_by_index[0]
    assert instant["zoom_mode"] == "instant"
    assert instant["max_word_dur"] == 0.59
    assert instant["total_dur"] == 1.5
    assert instant["zoom_start"] == 0.55
    assert instant["zoom_end"] == 2.15

    assert rows_by_index[1]["zoom_mode"] == "smooth"
    assert rows_by_index[1]["max_word_dur"] == 0.61
    assert rows_by_index[1]["zoom_start"] == 2.55
    assert rows_by_index[1]["zoom_end"] == 3.26

    assert rows_by_index[2]["zoom_mode"] == "smooth"
    assert rows_by_index[2]["total_dur"] == 1.6
    assert rows_by_index[2]["zoom_start"] == 3.55
    assert rows_by_index[2]["zoom_end"] == 5.25


def test_refine_reaction_candidates_rejects_silence_and_accepts_presence(tmp_path: Path) -> None:
    audio_path = tmp_path / "a2.wav"
    _write_pcm_wav(audio_path, duration_seconds=3.0, tones=[(1.5, 2.0)])

    candidates = [
        {"source_index": 0, "start": 0.55, "end": 0.95, "friend_text": "silent row"},
        {"source_index": 1, "start": 1.55, "end": 1.95, "friend_text": "voice row"},
    ]
    friend_segments = [
        {"words": [{"word": "silent", "start": 0.60, "end": 0.90}]},
        {"words": [{"word": "voice", "start": 1.60, "end": 1.90}]},
    ]

    accepted, rejected_silence, presence_policy = refine_friend_reaction_candidates(
        candidates,
        friend_segments,
        audio_path,
    )

    assert [row["source_index"] for row in accepted] == [1]
    assert [row["source_index"] for row in rejected_silence] == [0]
    assert rejected_silence[0]["rejected_reason"] == "rejected_silence"
    assert presence_policy["accepted_count"] == 1
    assert presence_policy["rejected_silence_count"] == 1

    required_keys = {
        "start",
        "end",
        "zoom_start",
        "zoom_end",
        "zoom_mode",
        "first_word_start",
        "last_word_end",
        "max_word_dur",
        "total_dur",
        "friend_rms_db",
        "friend_peak_db",
        "energie_voice_end",
        "friend_text",
    }
    assert required_keys <= accepted[0].keys()
    assert float(rejected_silence[0]["friend_rms_db"]) == -120.0
    assert float(accepted[0]["friend_rms_db"]) > -20.0


def test_refine_reaction_candidates_trims_trailing_segment_silence(tmp_path: Path) -> None:
    audio_path = tmp_path / "a2.wav"
    _write_pcm_wav(
        audio_path,
        duration_seconds=3.0,
        tones=[(0.60, 0.85, 9000), (0.85, 1.15, 50), (2.10, 2.30, 8000)],
    )

    candidates = [
        {"source_index": 0, "start": 0.55, "end": 1.95, "friend_text": "Digga."},
        {"source_index": 1, "start": 2.05, "end": 2.35, "friend_text": "floor row"},
    ]
    friend_segments = [
        {
            "start": 0.55,
            "end": 1.95,
            "words": [{"word": "Digga.", "start": 0.60, "end": 1.80}],
        },
        {
            "start": 2.05,
            "end": 2.35,
            "words": [{"word": "floor", "start": 2.10, "end": 2.30}],
        },
    ]

    accepted, rejected_silence, _presence_policy = refine_friend_reaction_candidates(
        candidates,
        friend_segments,
        audio_path,
    )

    assert [row["source_index"] for row in accepted] == [0]
    assert [row["source_index"] for row in rejected_silence] == [1]
    row = accepted[0]
    assert row["start"] == 0.55
    assert row["end"] == 1.2
    assert row["zoom_end"] == 1.2
    assert row["zoom_dauer"] == 0.65
    assert row["zoom_mode"] == "instant"
    assert row["reaction_tail_validation"]["last_voiced_subwindow"]["end"] == 1.15
    assert row["reaction_tail_validation"]["clamped_by_trailing_silence"] is True
    assert row["reaction_tail_validation"]["min_duration_applied"] is False


def test_refine_reaction_candidates_clamps_inflated_last_word_end(tmp_path: Path) -> None:
    audio_path = tmp_path / "a2.wav"
    _write_pcm_wav(audio_path, duration_seconds=12.0, tones=[(0.5, 1.3)])

    candidates = [
        {
            "source_index": 0,
            "start": 0.55,
            "end": 10.0,
            "friend_text": "Die will ich nie wieder spielen.",
        },
    ]
    friend_segments = [
        {
            "start": 0.55,
            "end": 10.0,
            "words": [
                {"word": "Die", "start": 0.60, "end": 0.70},
                {"word": "will", "start": 0.72, "end": 0.82},
                {"word": "ich", "start": 0.84, "end": 0.94},
                {"word": "nie", "start": 0.96, "end": 1.04},
                {"word": "wieder", "start": 1.06, "end": 1.16},
                {"word": "spielen.", "start": 1.18, "end": 10.0},
            ],
        },
    ]

    accepted, rejected_silence, _presence_policy = refine_friend_reaction_candidates(
        candidates,
        friend_segments,
        audio_path,
    )

    assert rejected_silence == []
    row = accepted[0]
    assert row["start"] == 0.55
    assert row["end"] == 2.13
    assert row["zoom_start"] == 0.55
    assert row["zoom_end"] == 2.13
    assert row["last_word_end"] == 2.08
    assert row["zoom_mode"] == "smooth"
    assert row["energy_validated_last_word"]["clamped_by_silence_gap"] is True


def test_refine_reaction_candidates_stops_before_internal_word_gap(tmp_path: Path) -> None:
    audio_path = tmp_path / "a2.wav"
    _write_pcm_wav(audio_path, duration_seconds=4.0, tones=[(0.5, 0.9), (2.0, 2.4)])

    candidates = [
        {
            "source_index": 0,
            "start": 0.55,
            "end": 2.3,
            "friend_text": "Nein später",
        },
    ]
    friend_segments = [
        {
            "start": 0.55,
            "end": 2.3,
            "words": [
                {"word": "Nein", "start": 0.60, "end": 0.80},
                {"word": "später", "start": 2.00, "end": 2.20},
            ],
        },
    ]

    accepted, rejected_silence, _presence_policy = refine_friend_reaction_candidates(
        candidates,
        friend_segments,
        audio_path,
    )

    assert rejected_silence == []
    row = accepted[0]
    assert row["start"] == 0.55
    assert row["end"] == 0.85
    assert row["zoom_start"] == 0.55
    assert row["zoom_end"] == 0.85
    assert row["zoom_mode"] == "instant"
    assert [word["word"] for word in row["words"]] == ["Nein"]
    assert row["internal_word_gap_clamp"]["gap_seconds"] == 1.2


def test_refine_reaction_candidates_clamps_leading_silence_inside_last_word(tmp_path: Path) -> None:
    audio_path = tmp_path / "a2.wav"
    _write_pcm_wav(audio_path, duration_seconds=5.0, tones=[(0.5, 0.95), (3.8, 4.0)])

    candidates = [
        {
            "source_index": 0,
            "start": 0.55,
            "end": 4.0,
            "friend_text": "Ich habe ihn gesehen!",
        },
    ]
    friend_segments = [
        {
            "start": 0.55,
            "end": 4.0,
            "words": [
                {"word": "Ich", "start": 0.60, "end": 0.70},
                {"word": "habe", "start": 0.72, "end": 0.82},
                {"word": "ihn", "start": 0.84, "end": 0.94},
                {"word": "gesehen!", "start": 0.96, "end": 4.0},
            ],
        },
    ]

    accepted, rejected_silence, _presence_policy = refine_friend_reaction_candidates(
        candidates,
        friend_segments,
        audio_path,
    )

    assert rejected_silence == []
    row = accepted[0]
    assert row["start"] == 0.55
    assert row["end"] == 1.81
    assert row["zoom_start"] == 0.55
    assert row["zoom_end"] == 1.81
    assert row["last_word_end"] == 1.76
    assert row["energy_validated_last_word"]["clamped_by_leading_silence_gap"] is True


def test_inject_selected_reaction_focus_decisions_uses_refined_zoom_window_and_mode() -> None:
    job = SimpleNamespace(focus_decisions=[])

    injected = inject_selected_reaction_focus_decisions(
        job,
        [
            {
                "is_real_reaction": True,
                "zoom_mode": "instant",
                "zoom_start": 10.0,
                "zoom_end": 11.2,
                "start": 10.1,
                "end": 11.1,
                "confidence": 0.95,
                "reason": "confirmed",
                "friend_text": "nice",
                "ali_context_text": "context",
            }
        ],
    )

    assert len(injected) == 1
    decision = injected[0]
    assert decision["zoom_mode"] == "instant"
    assert decision["focus_start_seconds"] == 10.0
    assert decision["focus_end_seconds"] == 11.2
    assert decision["focus_target"] == "gameplay"
    assert decision["gameplay_zoom"] == 1.4
    assert decision["facecam_opacity"] == 0.0
    assert "zoom_mode" in decision
    assert job.focus_decisions == injected
    assert job.focus_decisions_count == 1


def test_inject_selected_reaction_focus_decisions_skips_non_real_reactions() -> None:
    job = SimpleNamespace(focus_decisions=[])

    injected = inject_selected_reaction_focus_decisions(
        job,
        [
            {
                "is_real_reaction": False,
                "zoom_mode": "instant",
                "zoom_start": 10.0,
                "zoom_end": 11.2,
                "start": 10.1,
                "end": 11.1,
                "confidence": 0.95,
            }
        ],
    )

    assert injected == []
    assert job.focus_decisions == []
    assert job.focus_decisions_count == 0


def test_inject_selected_reaction_focus_decisions_passes_smooth_zoom_mode_through() -> None:
    job = SimpleNamespace(focus_decisions=[])

    injected = inject_selected_reaction_focus_decisions(
        job,
        [
            {
                "is_real_reaction": True,
                "zoom_mode": "smooth",
                "zoom_start": 20.0,
                "zoom_end": 22.0,
                "start": 20.1,
                "end": 21.9,
                "confidence": 0.8,
            }
        ],
    )

    assert len(injected) == 1
    assert injected[0]["zoom_mode"] == "smooth"


def test_inject_selected_reaction_focus_decisions_appends_existing_focus_decisions() -> None:
    existing = {"timestamp": 1.0, "focus_target": "balanced"}
    job = SimpleNamespace(focus_decisions=[existing])

    injected = inject_selected_reaction_focus_decisions(
        job,
        [
            {
                "is_real_reaction": True,
                "zoom_mode": "instant",
                "zoom_start": 30.0,
                "zoom_end": 31.0,
                "start": 30.1,
                "end": 30.9,
                "confidence": 0.8,
            }
        ],
    )

    assert len(injected) == 1
    assert job.focus_decisions == [existing, injected[0]]
    assert job.focus_decisions_count == 2
