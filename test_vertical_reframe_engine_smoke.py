from __future__ import annotations

import json
import os
import shutil
import subprocess

from moviepy import VideoFileClip

from core.vertical_reframe_engine import VerticalReframeEngine


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

def _make_source_video(path: str, duration: int = 20) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [
        r"D:\Tools\ffmpeg\bin\ffmpeg.exe", "-y",
        "-f", "lavfi", "-i", f"testsrc=size=1920x1080:rate=30:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=44100:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _make_srt(path: str, start_offset: float = 0.0) -> None:
    """Write a two-cue SRT whose timestamps are relative to the SOURCE video."""
    def ts(t: float) -> str:
        h, m = int(t // 3600), int((t % 3600) // 60)
        s, ms = int(t % 60), int(round((t % 1) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    t0 = start_offset + 0.5
    t1 = start_offset + 2.0
    t2 = start_offset + 3.0
    t3 = start_offset + 5.0

    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f"1\n{ts(t0)} --> {ts(t1)}\nErste Untertitelzeile\n\n"
            f"2\n{ts(t2)} --> {ts(t3)}\nZweite Untertitelzeile\n"
        )


def _make_whisper_json(path: str, start_offset: float = 0.0) -> None:
    """Write a minimal Whisper-style JSON transcript."""
    data = {
        "segments": [
            {"start": start_offset + 0.3, "end": start_offset + 1.8, "text": " Hallo Welt"},
            {"start": start_offset + 2.5, "end": start_offset + 4.5, "text": " Hier ist Zenith"},
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


# ------------------------------------------------------------------ #
#  Tests                                                               #
# ------------------------------------------------------------------ #

def test_basic_9_16_output() -> None:
    """Engine must produce a 1080×1920 portrait video, not 16:9."""
    test_dir = os.path.join("tmp", "vre_smoke_basic")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    source = os.path.join(test_dir, "source.mp4")
    output = os.path.join(test_dir, "short_9x16.mp4")
    _make_source_video(source, duration=20)

    VerticalReframeEngine().reframe(
        source_path=source,
        start_time=2.0,
        duration=8.0,
        output_path=output,
        focus_kind="center",
        subtitle_path=None,
    )

    assert os.path.exists(output), "Output file not created"

    with VideoFileClip(output) as clip:
        w, h = clip.w, clip.h
        dur = float(clip.duration or 0.0)

    assert w == 1080, f"Expected width=1080, got {w}"
    assert h == 1920, f"Expected height=1920, got {h}"
    assert abs(dur - 8.0) <= 1.0, f"Expected ~8 s, got {dur:.3f} s"

    print(f"\n[PASS] test_basic_9_16_output  →  {w}×{h}  {dur:.2f}s")


def test_focus_kinds_produce_valid_output() -> None:
    """Each named focus_kind must produce a valid 1080×1920 file."""
    test_dir = os.path.join("tmp", "vre_smoke_focus")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    source = os.path.join(test_dir, "source.mp4")
    _make_source_video(source, duration=15)

    engine = VerticalReframeEngine()

    for focus in ("facecam", "gameplay", "balanced", "center"):
        output = os.path.join(test_dir, f"short_{focus}.mp4")
        engine.reframe(
            source_path=source,
            start_time=1.0,
            duration=6.0,
            output_path=output,
            focus_kind=focus,
            subtitle_path=None,
        )
        assert os.path.exists(output), f"Output missing for focus_kind={focus}"
        with VideoFileClip(output) as clip:
            assert clip.w == 1080, f"focus={focus}: width {clip.w} != 1080"
            assert clip.h == 1920, f"focus={focus}: height {clip.h} != 1920"

    print(f"\n[PASS] test_focus_kinds_produce_valid_output")


def test_auto_detect_falls_back_gracefully() -> None:
    """focus_kind='auto' must not crash on a synthetic video."""
    test_dir = os.path.join("tmp", "vre_smoke_auto")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    source = os.path.join(test_dir, "source.mp4")
    output = os.path.join(test_dir, "short_auto.mp4")
    _make_source_video(source, duration=15)

    VerticalReframeEngine().reframe(
        source_path=source,
        start_time=0.0,
        duration=7.0,
        output_path=output,
        focus_kind="auto",
        subtitle_path=None,
    )

    assert os.path.exists(output)
    with VideoFileClip(output) as clip:
        assert clip.w == 1080
        assert clip.h == 1920

    print(f"\n[PASS] test_auto_detect_falls_back_gracefully")


def test_srt_subtitle_overlay() -> None:
    """SRT subtitles must be burned in without errors; output must still be 9:16."""
    test_dir = os.path.join("tmp", "vre_smoke_srt")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    source = os.path.join(test_dir, "source.mp4")
    srt_path = os.path.join(test_dir, "subtitles.srt")
    output = os.path.join(test_dir, "short_srt.mp4")

    _make_source_video(source, duration=15)
    _make_srt(srt_path, start_offset=3.0)   # segment starts at 3 s

    VerticalReframeEngine().reframe(
        source_path=source,
        start_time=3.0,
        duration=8.0,
        output_path=output,
        focus_kind="center",
        subtitle_path=srt_path,
    )

    assert os.path.exists(output)
    with VideoFileClip(output) as clip:
        assert clip.w == 1080
        assert clip.h == 1920
        assert abs(float(clip.duration or 0.0) - 8.0) <= 1.0

    print(f"\n[PASS] test_srt_subtitle_overlay")


def test_whisper_json_subtitle_overlay() -> None:
    """Whisper JSON must be converted to SRT and burned in without errors."""
    test_dir = os.path.join("tmp", "vre_smoke_whisper")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    source = os.path.join(test_dir, "source.mp4")
    whisper_json = os.path.join(test_dir, "source_whisper.json")
    output = os.path.join(test_dir, "short_whisper.mp4")

    _make_source_video(source, duration=15)
    _make_whisper_json(whisper_json, start_offset=2.0)

    VerticalReframeEngine().reframe(
        source_path=source,
        start_time=2.0,
        duration=8.0,
        output_path=output,
        focus_kind="center",
        subtitle_path=whisper_json,
    )

    assert os.path.exists(output)
    with VideoFileClip(output) as clip:
        assert clip.w == 1080
        assert clip.h == 1920

    print(f"\n[PASS] test_whisper_json_subtitle_overlay")


def test_no_subtitle_path_skips_silently() -> None:
    """subtitle_path=None must produce a clean video without any error."""
    test_dir = os.path.join("tmp", "vre_smoke_nosub")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    source = os.path.join(test_dir, "source.mp4")
    output = os.path.join(test_dir, "short_nosub.mp4")
    _make_source_video(source, duration=12)

    VerticalReframeEngine().reframe(
        source_path=source,
        start_time=1.0,
        duration=6.0,
        output_path=output,
        focus_kind="balanced",
        subtitle_path=None,
    )

    assert os.path.exists(output)
    with VideoFileClip(output) as clip:
        assert clip.w == 1080
        assert clip.h == 1920

    print(f"\n[PASS] test_no_subtitle_path_skips_silently")


def test_auto_subtitle_discovery() -> None:
    """subtitle_path='auto' (default) must find the .srt next to the source."""
    test_dir = os.path.join("tmp", "vre_smoke_autodiscovery")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    source = os.path.join(test_dir, "gaming_clip.mp4")
    # Co-located SRT — same stem
    srt_path = os.path.join(test_dir, "gaming_clip.srt")
    output = os.path.join(test_dir, "short_autodiscovery.mp4")

    _make_source_video(source, duration=12)
    _make_srt(srt_path, start_offset=0.0)

    # subtitle_path defaults to "auto" → engine will find gaming_clip.srt
    VerticalReframeEngine().reframe(
        source_path=source,
        start_time=0.0,
        duration=8.0,
        output_path=output,
        focus_kind="center",
    )

    assert os.path.exists(output)
    with VideoFileClip(output) as clip:
        assert clip.w == 1080
        assert clip.h == 1920

    print(f"\n[PASS] test_auto_subtitle_discovery")


# ------------------------------------------------------------------ #
#  Dynamic duration via ShortsDecisionEngine                           #
# ------------------------------------------------------------------ #

def test_dynamic_duration_in_decision_engine() -> None:
    """High-scoring segments must get 60 s, mid 45 s, low 30 s."""
    from core.shorts_decision_engine import ShortsDecisionEngine
    from types import SimpleNamespace

    job = SimpleNamespace(job_id="job_vre_dur_smoke")
    analysis = SimpleNamespace(duration_seconds=600.0)
    edit_decision = SimpleNamespace()

    decision = ShortsDecisionEngine().decide(job, analysis, edit_decision)

    assert decision.shorts_count >= 1, "Expected at least one segment for 600 s video"

    for seg in decision.selected_segments:
        dur = seg["duration_seconds"]
        assert 30.0 <= dur <= 60.0, (
            f"Duration {dur} s is outside 30–60 s range for segment {seg['label']}"
        )
        score = seg["score"]
        if score >= 0.88:
            assert dur == 60.0, f"score={score} should give 60 s, got {dur}"
        elif score >= 0.78:
            assert dur == 45.0, f"score={score} should give 45 s, got {dur}"
        else:
            assert dur == 30.0, f"score={score} should give 30 s, got {dur}"

    durations = [s["duration_seconds"] for s in decision.selected_segments]
    print(f"\n[PASS] test_dynamic_duration_in_decision_engine")
    print(f"  segments={decision.shorts_count}  durations={durations}")


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main() -> None:
    test_basic_9_16_output()
    test_focus_kinds_produce_valid_output()
    test_auto_detect_falls_back_gracefully()
    test_srt_subtitle_overlay()
    test_whisper_json_subtitle_overlay()
    test_no_subtitle_path_skips_silently()
    test_auto_subtitle_discovery()
    test_dynamic_duration_in_decision_engine()
    print("\n=== ALL VERTICAL REFRAME ENGINE SMOKE TESTS PASSED ===")


if __name__ == "__main__":
    main()
