from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
from array import array
from pathlib import Path


def _tool(name: str) -> str:
    candidates = [
        Path(r"D:\Tools\ffmpeg\bin") / f"{name}.exe",
        Path(r"C:\ffmpeg\bin") / f"{name}.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return name


FFMPEG = _tool("ffmpeg")
FFPROBE = _tool("ffprobe")


def _resolve_video(value: str) -> Path:
    raw = Path(value)
    if raw.exists():
        return raw.resolve()

    matches = []
    if not raw.is_absolute():
        for p in Path.cwd().rglob(raw.name):
            if p.is_file():
                matches.append(p)

    if not matches:
        raise FileNotFoundError(
            f"Video not found: {value}\n"
            f"Tip: run again with --video \"FULL_PATH_TO_VIDEO\""
        )

    matches = sorted(matches, key=lambda p: (len(str(p)), str(p).lower()))
    return matches[0].resolve()


def _run_json(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    return json.loads(p.stdout)


def _duration_seconds(video: Path) -> float:
    data = _run_json([
        FFPROBE,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video),
    ])
    return float(data["format"]["duration"])


def _audio_streams(video: Path) -> list[dict]:
    data = _run_json([
        FFPROBE,
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index,codec_name,channels:stream_tags=title,language",
        "-of", "json",
        str(video),
    ])
    streams = data.get("streams", [])
    out = []
    for ordinal, stream in enumerate(streams):
        tags = stream.get("tags") or {}
        out.append({
            "track": ordinal + 1,
            "ordinal": ordinal,
            "stream_index": stream.get("index"),
            "codec": stream.get("codec_name"),
            "channels": stream.get("channels"),
            "title": tags.get("title", ""),
            "language": tags.get("language", ""),
        })
    return out


def _decode_audio_chunk(video: Path, audio_ordinal: int, start: float, seconds: float, sr: int) -> bytes:
    cmd = [
        FFMPEG,
        "-hide_banner",
        "-nostdin",
        "-v", "error",
        "-ss", f"{start:.3f}",
        "-t", f"{seconds:.3f}",
        "-i", str(video),
        "-map", f"0:a:{audio_ordinal}",
        "-vn",
        "-sn",
        "-dn",
        "-ac", "1",
        "-ar", str(sr),
        "-f", "s16le",
        "pipe:1",
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        err = p.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(err.strip())
    return p.stdout


def _db(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-9))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return -120.0
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * pct / 100.0
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _longest_true_run(flags: list[bool]) -> int:
    best = 0
    cur = 0
    for flag in flags:
        if flag:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def _pcm_window_stats(raw: bytes, sr: int, window_seconds: float = 0.20) -> list[tuple[float, float]]:
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()

    step = max(1, int(sr * window_seconds))
    rows = []

    for start in range(0, max(0, len(samples) - step + 1), step):
        chunk = samples[start:start + step]
        if not chunk:
            continue

        sq = 0.0
        peak = 0
        for v in chunk:
            av = abs(v)
            if av > peak:
                peak = av
            sq += float(v) * float(v)

        rms = math.sqrt(sq / len(chunk)) / 32768.0
        peak_norm = peak / 32768.0
        rows.append((_db(rms), _db(peak_norm)))

    return rows


def _sample_starts(duration: float, chunk_seconds: float) -> list[float]:
    if duration <= chunk_seconds:
        return [0.0]

    fractions = [0.02, 0.08, 0.16, 0.28, 0.40, 0.52, 0.64, 0.76, 0.88]
    starts = []
    max_start = max(0.0, duration - chunk_seconds - 1.0)

    for frac in fractions:
        s = min(max_start, max(0.0, duration * frac))
        if all(abs(s - old) > chunk_seconds * 0.75 for old in starts):
            starts.append(s)

    return starts


def _analyze_track(video: Path, stream: dict, duration: float, chunk_seconds: float, sr: int) -> dict:
    rows = []
    starts = _sample_starts(duration, chunk_seconds)

    for start in starts:
        raw = _decode_audio_chunk(video, stream["ordinal"], start, chunk_seconds, sr)
        rows.extend(_pcm_window_stats(raw, sr))

    if not rows:
        raise RuntimeError(f"No audio samples decoded for track {stream['track']}")

    rms_db = [r[0] for r in rows]
    peak_db = [r[1] for r in rows]

    floor_db = _percentile(rms_db, 10)
    median_db = _percentile(rms_db, 50)
    p90_db = _percentile(rms_db, 90)
    p95_db = _percentile(rms_db, 95)
    max_peak_db = max(peak_db)

    lin_rms = [10.0 ** (d / 20.0) for d in rms_db]
    avg_db = _db(statistics.fmean(lin_rms))

    active_threshold = max(floor_db + 10.0, -55.0)
    speech_threshold = max(median_db + 4.0, floor_db + 12.0, -52.0)

    active_flags = [d >= active_threshold for d in rms_db]
    speech_flags = [d >= speech_threshold for d in rms_db]

    active_ratio = sum(active_flags) / len(active_flags)
    speech_like_ratio = sum(speech_flags) / len(speech_flags)

    dynamic_range = p90_db - floor_db
    burst_over_median = p95_db - median_db
    longest_active_ratio = _longest_true_run(active_flags) / len(active_flags)

    ideal_activity = _clamp01(1.0 - abs(active_ratio - 0.35) / 0.35)
    not_constant = _clamp01(1.0 - max(0.0, active_ratio - 0.75) / 0.25)
    dyn_score = _clamp01((dynamic_range - 8.0) / 22.0)
    burst_score = _clamp01((burst_over_median - 6.0) / 18.0)
    not_empty = _clamp01(active_ratio / 0.08)

    voice_score = 100.0 * not_empty * (
        0.34 * ideal_activity +
        0.28 * not_constant +
        0.23 * dyn_score +
        0.15 * burst_score
    )

    if active_ratio < 0.03 and avg_db < -58.0:
        guess = "probably_empty_or_silent"
    elif active_ratio > 0.82 and median_db > -50.0:
        guess = "probably_fullmix_ingame_or_music"
    elif voice_score >= 55.0:
        guess = "voice_like_candidate"
    elif speech_like_ratio >= 0.05:
        guess = "possible_voice_or_effects"
    else:
        guess = "unclear_or_quiet"

    return {
        **stream,
        "sampled_chunks": len(starts),
        "sampled_seconds": round(len(starts) * chunk_seconds, 2),
        "avg_energy_dbfs": round(avg_db, 2),
        "median_dbfs": round(median_db, 2),
        "floor_dbfs_p10": round(floor_db, 2),
        "peak_dbfs": round(max_peak_db, 2),
        "active_ratio": round(active_ratio, 4),
        "estimated_speech_ratio": round(speech_like_ratio, 4),
        "dynamic_range_db": round(dynamic_range, 2),
        "burst_over_median_db": round(burst_over_median, 2),
        "longest_active_ratio": round(longest_active_ratio, 4),
        "voice_score": round(voice_score, 2),
        "guess": guess,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="Minecraft Full Video.mp4")
    ap.add_argument("--chunk-seconds", type=float, default=12.0)
    ap.add_argument("--sample-rate", type=int, default=16000)
    args = ap.parse_args()

    out_dir = Path("reports") / "reaction_signal"
    out_dir.mkdir(parents=True, exist_ok=True)

    video = _resolve_video(args.video)
    duration = _duration_seconds(video)
    streams = _audio_streams(video)

    if not streams:
        raise RuntimeError("No audio streams found.")

    results = []
    for stream in streams:
        results.append(_analyze_track(video, stream, duration, args.chunk_seconds, args.sample_rate))

    best = max(results, key=lambda r: r["voice_score"])

    report = {
        "stage": "A_track_identification",
        "video": str(video),
        "duration_seconds": round(duration, 3),
        "audio_tracks_found": len(streams),
        "best_guess_track": best["track"],
        "best_guess_voice_score": best["voice_score"],
        "results": results,
        "note": "This is a heuristic. Ali must confirm the owner mic track before Stage B.",
    }

    json_path = out_dir / "stufe_a_track_probe_minecraft.json"
    txt_path = out_dir / "stufe_a_track_probe_minecraft.txt"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = []
    lines.append("STUFE A - AUDIO TRACK PROBE")
    lines.append(f"Video: {video}")
    lines.append(f"Duration seconds: {duration:.2f}")
    lines.append(f"Audio tracks found: {len(streams)}")
    lines.append("")
    lines.append(
        "Track | stream | codec | ch | avg_dbfs | speech_pct | active_pct | peak_dbfs | voice_score | guess"
    )
    lines.append("-" * 120)

    for r in sorted(results, key=lambda x: x["track"]):
        lines.append(
            f"{r['track']:>5} | "
            f"{str(r['stream_index']):>6} | "
            f"{str(r['codec']):>5} | "
            f"{str(r['channels']):>2} | "
            f"{r['avg_energy_dbfs']:>8.2f} | "
            f"{r['estimated_speech_ratio'] * 100:>9.2f}% | "
            f"{r['active_ratio'] * 100:>8.2f}% | "
            f"{r['peak_dbfs']:>9.2f} | "
            f"{r['voice_score']:>11.2f} | "
            f"{r['guess']}"
        )

    lines.append("")
    lines.append(
        f"BEST GUESS: Track {best['track']} as Ali voice/mic candidate "
        f"(voice_score={best['voice_score']})."
    )
    lines.append("")
    lines.append("ALI CONFIRMATION NEEDED:")
    lines.append(f"Is Track {best['track']} your voice? Answer: JA or NEIN, and correct track number if needed.")
    lines.append("")
    lines.append(f"JSON report: {json_path}")
    lines.append(f"TXT report:  {txt_path}")

    txt = "\n".join(lines)
    txt_path.write_text(txt, encoding="utf-8")
    print(txt)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
