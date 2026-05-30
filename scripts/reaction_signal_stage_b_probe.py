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


def _run(cmd: list[str], *, text: bool = False):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text)
    if p.returncode != 0:
        err = p.stderr if text else p.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(err.strip())
    return p.stdout


def _run_json(cmd: list[str]) -> dict:
    return json.loads(_run(cmd, text=True))


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
            f"Run again with --video FULL_PATH_TO_VIDEO"
        )

    return sorted(matches, key=lambda p: (len(str(p)), str(p).lower()))[0].resolve()


def _duration_seconds(video: Path) -> float:
    data = _run_json([
        FFPROBE,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video),
    ])
    return float(data["format"]["duration"])


def _video_size(video: Path) -> tuple[int, int]:
    data = _run_json([
        FFPROBE,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(video),
    ])
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def _parse_crop(value: str, video_w: int, video_h: int) -> tuple[int, int, int, int]:
    parts = [int(p.strip()) for p in value.split(",")]
    if len(parts) != 4:
        raise ValueError("Crop must be x,y,w,h")
    x, y, w, h = parts
    x = max(0, min(video_w - 1, x))
    y = max(0, min(video_h - 1, y))
    w = max(1, min(video_w - x, w))
    h = max(1, min(video_h - y, h))
    return x, y, w, h


def _db(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-9))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return -180.0
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


def _ts(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _safe_time_name(seconds: float) -> str:
    return str(int(round(seconds))).zfill(5)


def _extract_facecam_proof_images(
    video: Path,
    out_dir: Path,
    crop: tuple[int, int, int, int],
    duration: float,
) -> list[dict]:
    x, y, w, h = crop
    times = []
    for t in [60.0, 300.0, 900.0, 1500.0]:
        if 1.0 < t < duration - 1.0:
            times.append(t)

    if not times:
        times = [min(5.0, max(0.0, duration / 2.0))]

    images = []
    for t in times:
        name = _safe_time_name(t)
        boxed = out_dir / f"stufe_b_facecam_box_t{name}.jpg"
        cropped = out_dir / f"stufe_b_facecam_crop_t{name}.jpg"

        draw = f"drawbox=x={x}:y={y}:w={w}:h={h}:color=red@0.85:t=6"

        _run([
            FFMPEG, "-y",
            "-hide_banner", "-nostdin",
            "-v", "error",
            "-ss", f"{t:.3f}",
            "-i", str(video),
            "-frames:v", "1",
            "-vf", draw,
            "-q:v", "2",
            str(boxed),
        ])

        _run([
            FFMPEG, "-y",
            "-hide_banner", "-nostdin",
            "-v", "error",
            "-ss", f"{t:.3f}",
            "-i", str(video),
            "-frames:v", "1",
            "-vf", f"crop={w}:{h}:{x}:{y}",
            "-q:v", "2",
            str(cropped),
        ])

        images.append({
            "time_seconds": t,
            "timestamp": _ts(t),
            "boxed_image": str(boxed),
            "crop_image": str(cropped),
        })

    return images


def _decode_audio(video: Path, track_1based: int, sr: int) -> bytes:
    ordinal = track_1based - 1
    return _run([
        FFMPEG,
        "-hide_banner",
        "-nostdin",
        "-v", "error",
        "-i", str(video),
        "-map", f"0:a:{ordinal}",
        "-vn", "-sn", "-dn",
        "-ac", "1",
        "-ar", str(sr),
        "-f", "s16le",
        "pipe:1",
    ])


def _audio_windows(raw: bytes, sr: int, win_seconds: float) -> tuple[list[float], list[float]]:
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()

    step = max(1, int(sr * win_seconds))
    rms_db = []
    peak_db = []

    for start in range(0, len(samples) - step + 1, step):
        chunk = samples[start:start + step]
        sq = 0.0
        peak = 0
        for v in chunk:
            av = abs(v)
            if av > peak:
                peak = av
            sq += float(v) * float(v)

        rms = math.sqrt(sq / len(chunk)) / 32768.0
        peak_norm = peak / 32768.0
        rms_db.append(_db(rms))
        peak_db.append(_db(peak_norm))

    return rms_db, peak_db


def _decode_facecam_motion(
    video: Path,
    crop: tuple[int, int, int, int],
    fps: int,
    scaled_w: int,
    scaled_h: int,
) -> list[float]:
    x, y, w, h = crop
    vf = f"crop={w}:{h}:{x}:{y},scale={scaled_w}:{scaled_h},fps={fps},format=gray"

    raw = _run([
        FFMPEG,
        "-hide_banner",
        "-nostdin",
        "-v", "error",
        "-i", str(video),
        "-map", "0:v:0",
        "-vf", vf,
        "-an", "-sn", "-dn",
        "-f", "rawvideo",
        "pipe:1",
    ])

    frame_size = scaled_w * scaled_h
    frame_count = len(raw) // frame_size
    if frame_count <= 1:
        return [0.0]

    motion = [0.0]
    prev = raw[0:frame_size]

    for i in range(1, frame_count):
        cur = raw[i * frame_size:(i + 1) * frame_size]
        diff_sum = 0
        for a, b in zip(cur, prev):
            diff_sum += abs(a - b)
        motion.append((diff_sum / frame_size) / 255.0)
        prev = cur

    return motion


def _group_candidates(rows: list[dict], max_gap_seconds: float) -> list[dict]:
    if not rows:
        return []

    groups = []
    current = [rows[0]]

    for row in rows[1:]:
        if row["time_seconds"] - current[-1]["time_seconds"] <= max_gap_seconds:
            current.append(row)
        else:
            groups.append(current)
            current = [row]

    groups.append(current)

    events = []
    for group in groups:
        best = max(group, key=lambda r: r["fusion_score"])
        events.append({
            "start": group[0]["time_seconds"],
            "end": group[-1]["time_seconds"] + 0.5,
            "best_time": best["time_seconds"],
            "timestamp": _ts(best["time_seconds"]),
            "duration_seconds": round(group[-1]["time_seconds"] + 0.5 - group[0]["time_seconds"], 2),
            "mic_rise_db": best["mic_rise_db"],
            "mic_peak_over_baseline_db": best["mic_peak_over_baseline_db"],
            "facecam_change": best["facecam_change"],
            "fusion_score": best["fusion_score"],
            "reason": best["reason"],
        })

    return events


def _find_candidates(
    rms_db: list[float],
    peak_db: list[float],
    motion_raw: list[float],
    win_seconds: float,
) -> tuple[list[dict], dict]:
    active_floor = _percentile(rms_db, 20)
    active_threshold = max(active_floor + 6.0, -55.0)
    active_rms = [v for v in rms_db if v >= active_threshold]
    active_peak = [p for r, p in zip(rms_db, peak_db) if r >= active_threshold]

    if len(active_rms) < 10:
        active_rms = rms_db
        active_peak = peak_db

    baseline_rms = _percentile(active_rms, 50)
    baseline_peak = _percentile(active_peak, 50)

    motion_p50 = _percentile(motion_raw, 50)
    motion_p90 = _percentile(motion_raw, 90)
    motion_span = max(0.0001, motion_p90 - motion_p50)

    n = min(len(rms_db), len(peak_db), len(motion_raw))
    prelim = []

    for i in range(n):
        t = i * win_seconds
        mic_rise = rms_db[i] - baseline_rms
        peak_over = peak_db[i] - baseline_peak
        face_change_raw = motion_raw[i]
        face_norm = _clamp01((face_change_raw - motion_p50) / motion_span)

        audio_rise_norm = _clamp01((mic_rise - 3.0) / 10.0)
        peak_norm = _clamp01((peak_over - 6.0) / 14.0)

        fusion = (0.58 * audio_rise_norm) + (0.27 * peak_norm) + (0.15 * face_norm)

        reasons = []
        if mic_rise >= 5.0:
            reasons.append("audio_rise")
        if peak_over >= 9.0:
            reasons.append("mic_peak")
        if face_norm >= 0.60:
            reasons.append("facecam")

        if (audio_rise_norm >= 0.18 or peak_norm >= 0.18) and fusion >= 0.22:
            prelim.append({
                "time_seconds": t,
                "mic_rise_db": round(mic_rise, 2),
                "mic_peak_over_baseline_db": round(peak_over, 2),
                "facecam_change": round(face_norm, 3),
                "fusion_score": round(fusion, 3),
                "reason": "+".join(reasons) if reasons else "weak_audio_candidate",
            })

    grouped = _group_candidates(prelim, max_gap_seconds=2.0)

    strongest = sorted(grouped, key=lambda e: e["fusion_score"], reverse=True)[:30]
    strongest = sorted(strongest, key=lambda e: e["best_time"])

    calibration = {
        "active_threshold_dbfs": round(active_threshold, 2),
        "normal_speech_baseline_rms_dbfs": round(baseline_rms, 2),
        "normal_speech_baseline_peak_dbfs": round(baseline_peak, 2),
        "facecam_motion_p50": round(motion_p50, 6),
        "facecam_motion_p90": round(motion_p90, 6),
        "candidate_logic": "preliminary Stage B only; final thresholds come after Ali ground truth in Stage D",
    }

    return strongest, calibration


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="Minecraft Full Video.mp4")
    ap.add_argument("--mic-track", type=int, default=1)
    ap.add_argument("--discord-track", type=int, default=2)
    ap.add_argument("--gameplay-track", type=int, default=3)
    ap.add_argument("--facecam-crop", default="0,0,1150,1080")
    ap.add_argument("--audio-sr", type=int, default=8000)
    ap.add_argument("--window-seconds", type=float, default=0.5)
    args = ap.parse_args()

    out_dir = Path("reports") / "reaction_signal"
    out_dir.mkdir(parents=True, exist_ok=True)

    video = _resolve_video(args.video)
    duration = _duration_seconds(video)
    video_w, video_h = _video_size(video)
    crop = _parse_crop(args.facecam_crop, video_w, video_h)

    stage_a_confirmation = {
        "stage": "A_owner_confirmation",
        "video": str(video),
        "confirmed_by": "Ali",
        "confirmed_owner_mic_track": args.mic_track,
        "confirmed_discord_track": args.discord_track,
        "confirmed_gameplay_track": args.gameplay_track,
        "note": "This confirmation applies to this old Minecraft test video. New OBS config differs: track 1 is joker/fullmix, track 2 should be mic.",
    }
    (out_dir / "stufe_a_ali_confirmation.json").write_text(
        json.dumps(stage_a_confirmation, indent=2),
        encoding="utf-8",
    )

    proof_images = _extract_facecam_proof_images(video, out_dir, crop, duration)

    raw_audio = _decode_audio(video, args.mic_track, args.audio_sr)
    rms_db, peak_db = _audio_windows(raw_audio, args.audio_sr, args.window_seconds)

    motion = _decode_facecam_motion(
        video,
        crop,
        fps=2,
        scaled_w=96,
        scaled_h=54,
    )

    candidates, calibration = _find_candidates(
        rms_db,
        peak_db,
        motion,
        args.window_seconds,
    )

    report = {
        "stage": "B_facecam_and_reaction_candidates",
        "video": str(video),
        "duration_seconds": round(duration, 3),
        "video_size": {
            "width": video_w,
            "height": video_h,
        },
        "confirmed_tracks_for_this_video": {
            "ali_mic": args.mic_track,
            "discord": args.discord_track,
            "gameplay": args.gameplay_track,
        },
        "facecam_crop_candidate": {
            "x": crop[0],
            "y": crop[1],
            "w": crop[2],
            "h": crop[3],
            "needs_ali_confirmation": True,
        },
        "proof_images": proof_images,
        "preliminary_calibration": calibration,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "note": "These are Stage B candidates only. Ali must mark JA/NEIN in Stage C before detector thresholds are finalized.",
    }

    json_path = out_dir / "stufe_b_candidates_minecraft.json"
    txt_path = out_dir / "stufe_b_candidates_minecraft.txt"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = []
    lines.append("STUFE B - FACECAM + REACTION CANDIDATES")
    lines.append(f"Video: {video}")
    lines.append(f"Video size: {video_w}x{video_h}")
    lines.append(f"Confirmed Ali mic track for this video: {args.mic_track}")
    lines.append(f"Confirmed Discord track for this video: {args.discord_track}")
    lines.append(f"Confirmed Gameplay track for this video: {args.gameplay_track}")
    lines.append("")
    lines.append(f"Facecam crop candidate: x={crop[0]}, y={crop[1]}, w={crop[2]}, h={crop[3]}")
    lines.append("Proof images:")
    for img in proof_images:
        lines.append(f"- {img['timestamp']} boxed: {img['boxed_image']}")
        lines.append(f"- {img['timestamp']} crop:  {img['crop_image']}")
    lines.append("")
    lines.append("Preliminary calibration:")
    for k, v in calibration.items():
        lines.append(f"- {k}: {v}")

    lines.append("")
    lines.append("Candidates Ali must review:")
    lines.append("Nr | timestamp    | mic_rise_db | mic_peak_over | facecam | score | reason")
    lines.append("-" * 86)

    for idx, c in enumerate(candidates, start=1):
        lines.append(
            f"{idx:>2} | "
            f"{c['timestamp']:<12} | "
            f"{c['mic_rise_db']:>11.2f} | "
            f"{c['mic_peak_over_baseline_db']:>13.2f} | "
            f"{c['facecam_change']:>7.3f} | "
            f"{c['fusion_score']:>5.3f} | "
            f"{c['reason']}"
        )

    lines.append("")
    lines.append(f"JSON report: {json_path}")
    lines.append(f"TXT report:  {txt_path}")
    lines.append("")
    lines.append("ALI CHECK NEEDED:")
    lines.append("1) Does the facecam crop image contain your face clearly?")
    lines.append("2) Mark candidate timestamps as real reaction JA/NEIN in Stage C.")

    txt = "\n".join(lines)
    txt_path.write_text(txt, encoding="utf-8")
    print(txt)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
