from __future__ import annotations

import math
import shutil
import wave
from pathlib import Path
from types import SimpleNamespace

from core.audio_peak_detector import AudioPeakDetector
from core.final_render_driver import FinalRenderDriver


SAMPLE_RATE = 44_100
TMP_DIR = Path("tmp_audio_peak_detection_smoke")


def _write_wav(path: Path, sections: list[tuple[float, float]]) -> None:
    """
    sections: list of (duration_seconds, amplitude)
    amplitude 0.0 = silence
    amplitude > 0 = sine wave
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)

        for duration, amplitude in sections:
            frame_count = int(duration * SAMPLE_RATE)

            for i in range(frame_count):
                if amplitude <= 0.0:
                    value = 0
                else:
                    sample = math.sin(2.0 * math.pi * 440.0 * (i / SAMPLE_RATE))
                    value = int(max(-1.0, min(1.0, sample * amplitude)) * 32767)

                wav.writeframesraw(value.to_bytes(2, byteorder="little", signed=True))


def _assert_valid_peak(peak: dict) -> None:
    assert "start" in peak, f"Peak missing start: {peak}"
    assert "end" in peak, f"Peak missing end: {peak}"
    assert "peak_db" in peak, f"Peak missing peak_db: {peak}"

    start = float(peak["start"])
    end = float(peak["end"])
    duration = end - start
    peak_db = float(peak["peak_db"])

    assert start >= 0.0, f"Peak start must be >= 0: {peak}"
    assert end > start, f"Peak end must be > start: {peak}"
    assert duration > 0.0, f"Peak duration must be > 0: {peak}"
    assert -90.0 < peak_db <= 0.0, f"Peak dB value looks invalid: {peak}"


def _test_audio_peak_detector_detects_real_peaks() -> list[dict]:
    detector = AudioPeakDetector()

    ffmpeg_path = Path(detector._FFMPEG)
    assert ffmpeg_path.exists(), f"ffmpeg not found at expected path: {ffmpeg_path}"

    mixed_audio = TMP_DIR / "mixed_quiet_and_loud_sections.wav"

    _write_wav(
        mixed_audio,
        sections=[
            (1.0, 0.0),   # silence
            (1.2, 0.65),  # loud peak
            (1.0, 0.0),   # silence
            (1.2, 0.28),  # second clear peak
            (1.0, 0.0),   # silence
        ],
    )

    peaks = detector.detect_peaks(
        video_path=str(mixed_audio),
        segment_start=0.0,
        segment_duration=5.4,
        threshold_db=-25.0,
        min_duration=0.4,
        use_normalization=False,
    )

    assert isinstance(peaks, list), "detect_peaks must return a list"
    assert len(peaks) >= 2, f"Expected at least 2 audio peaks, got {len(peaks)}: {peaks}"

    for peak in peaks:
        _assert_valid_peak(peak)

    assert any(0.6 <= float(peak["start"]) <= 1.3 for peak in peaks), (
        f"Expected a peak around the first loud section, got: {peaks}"
    )
    assert any(2.8 <= float(peak["start"]) <= 3.5 for peak in peaks), (
        f"Expected a peak around the second loud section, got: {peaks}"
    )

    return peaks


def _test_silence_does_not_create_false_peaks() -> None:
    detector = AudioPeakDetector()

    silent_audio = TMP_DIR / "silence_only.wav"

    _write_wav(
        silent_audio,
        sections=[
            (3.0, 0.0),
        ],
    )

    peaks = detector.detect_peaks(
        video_path=str(silent_audio),
        segment_start=0.0,
        segment_duration=3.0,
        threshold_db=-25.0,
        min_duration=0.4,
        use_normalization=False,
    )

    assert peaks == [], f"Silence-only audio must not produce peaks, got: {peaks}"


def _test_audio_peaks_drive_render_zoom_filter() -> None:
    driver = FinalRenderDriver()

    segment = SimpleNamespace(
        segment_id="seg_audio_peak_smoke",
        segment_role="peak",
        start_time=10.0,
    )

    dynamic_edit_plan = SimpleNamespace(
        zoom_instructions=[
            SimpleNamespace(segment_id="seg_audio_peak_smoke")
        ]
    )

    audio_peaks = [
        {"start": 10.0, "end": 11.2, "peak_db": -12.0},  # LARGE
        {"start": 12.0, "end": 13.2, "peak_db": -15.0},  # MEDIUM
        {"start": 14.0, "end": 15.2, "peak_db": -18.0},  # SMALL
        {"start": 16.0, "end": 17.2, "peak_db": -22.0},  # TINY / quiet
    ]

    filter_complex, output_label = driver._build_filter_complex(
        segment=segment,
        reframe_plan=None,
        dynamic_edit_plan=dynamic_edit_plan,
        audio_peaks=audio_peaks,
        src_w=3840,
        src_h=1080,
    )

    assert output_label == "[out]", f"Unexpected output label: {output_label}"
    assert "fc_tiny" in filter_complex, "TINY PiP layer missing"
    assert "fc_small" in filter_complex, "SMALL PiP layer missing"
    assert "fc_medium" in filter_complex, "MEDIUM PiP layer missing"
    assert "fc_large" in filter_complex, "LARGE PiP layer missing"

    assert "between(t,0.0,1.2)" in filter_complex, "LARGE peak timing not used"
    assert "between(t,2.0,3.2)" in filter_complex, "MEDIUM peak timing not used"
    assert "between(t,4.0,5.2)" in filter_complex, "SMALL peak timing not used"


def main() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)

    try:
        TMP_DIR.mkdir(parents=True, exist_ok=True)

        peaks = _test_audio_peak_detector_detects_real_peaks()
        _test_silence_does_not_create_false_peaks()
        _test_audio_peaks_drive_render_zoom_filter()

        print(f"Detected peaks: {len(peaks)}")
        print("AUDIO PEAK DETECTION SMOKE TEST PASSED")

    finally:
        shutil.rmtree(TMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
