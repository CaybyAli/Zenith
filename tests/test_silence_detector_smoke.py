from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from core.edit_signal_extractor import EditSignalExtractor


def _write_test_wav(path: Path) -> None:
    sample_rate = 22050
    duration_seconds = 4.0
    amplitude = 12000
    frequency_hz = 440.0

    frames = bytearray()
    total_samples = int(sample_rate * duration_seconds)

    for sample_index in range(total_samples):
        t = sample_index / sample_rate

        if 1.25 <= t < 2.75:
            value = 0
        else:
            value = int(amplitude * math.sin(2.0 * math.pi * frequency_hz * t))

        frames.extend(struct.pack("<h", value))

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)


def _assert_valid_signal(signal) -> None:
    assert signal.start_time >= 0.0, "signal start_time must not be negative"
    assert signal.end_time > signal.start_time, "signal end_time must be after start_time"

    expected_duration = round(signal.end_time - signal.start_time, 3)
    assert signal.duration == expected_duration, "signal duration must match timestamps"

    assert signal.signal_type, "signal_type must be present"
    assert 0.0 <= signal.confidence <= 1.0, "confidence must be between 0 and 1"


def main() -> None:
    with TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "tone_silence_tone.wav"
        _write_test_wav(audio_path)

        job = SimpleNamespace(job_id="job_silence_smoke")
        extractor = EditSignalExtractor()

        signals = extractor._extract_audio_energy_signals(
            job=job,
            audio_path=str(audio_path),
            duration_seconds=4.0,
            window_size=0.5,
            step_size=0.25,
        )

    assert signals, "expected edit signals"

    sorted_signals = sorted(
        signals,
        key=lambda signal: (signal.start_time, signal.end_time, signal.signal_type),
    )
    assert signals == sorted_signals, "signals must be sorted"

    silence_segments = [
        signal for signal in signals
        if signal.signal_type == "silence_zone"
    ]

    assert silence_segments, "expected at least one silence_zone segment"

    for signal in silence_segments:
        _assert_valid_signal(signal)

    total_silence_seconds = round(
        sum(signal.duration for signal in silence_segments),
        3,
    )

    assert total_silence_seconds > 0.0, "total silence seconds must be positive"
    assert total_silence_seconds <= 4.0, "total silence seconds must be plausible"

    assert any(
        1.0 <= signal.start_time <= 2.75
        for signal in silence_segments
    ), "expected silence detection near the synthetic silent area"

    print("SILENCE DETECTOR SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
