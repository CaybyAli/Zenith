from __future__ import annotations

import wave
from pathlib import Path
from types import SimpleNamespace

from core.reaction_focus_decisions import (
    inject_selected_reaction_focus_decisions,
    refine_friend_reaction_candidates,
)


def _write_pcm_wav(path: Path, *, duration_seconds: float, tones: list[tuple[float, float]]) -> None:
    sample_rate = 1000
    amplitude = 9000
    frame_count = int(duration_seconds * sample_rate)

    frames = bytearray()
    for frame_index in range(frame_count):
        timestamp = frame_index / sample_rate
        sample = amplitude if any(start <= timestamp < end for start, end in tones) else 0
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
