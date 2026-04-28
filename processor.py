"""
processor.py — Zenith video processing step (pipeline stage 2).

Picks up every pending gaming job from data/jobs.json, runs audio-energy-based
highlight detection with moviepy + numpy, cuts the segments, and writes the
results to output/processed/{job_id}/.

Run directly:
  python processor.py

Or import run_processor() for programmatic use.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from moviepy.editor import VideoFileClip

JOBS_PATH = Path("data/jobs.json")
OUTPUT_BASE = Path("output/processed")

_GAMING_CHANNELS = frozenset({"gaming_main", "gaming_uncut"})

# Audio energy percentile threshold: top 20 % of chunks = highlight
_ENERGY_PERCENTILE = 80
# Merge segments that are closer than this many seconds apart
_MERGE_GAP_SECONDS = 3


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------ #
#  Analysis helpers                                                    #
# ------------------------------------------------------------------ #

def get_audio_energy(video_path: str) -> list[tuple[float, float, float]]:
    """Return per-second audio energy as (t_start, t_end, rms) tuples."""
    clip = VideoFileClip(str(video_path))
    audio = clip.audio

    if audio is None:
        clip.close()
        return []

    fps = 22050
    chunk_size = 1.0
    energies: list[tuple[float, float, float]] = []

    all_frames = list(audio.iter_frames(fps=fps))
    frames_per_chunk = int(fps * chunk_size)

    for i in range(0, len(all_frames) - frames_per_chunk, frames_per_chunk):
        chunk = all_frames[i:i + frames_per_chunk]
        arr = np.array(chunk)
        rms = float(np.sqrt(np.mean(arr ** 2)))
        t_start = i / fps
        t_end = t_start + chunk_size
        energies.append((t_start, t_end, rms))

    clip.close()
    return energies


def _find_highlight_segments(
    energies: list[tuple[float, float, float]], duration: float
) -> list[dict]:
    """
    Convert (t_start, t_end, rms) tuples into merged highlight segments.
    Returns list of {start, end, energy_score} dicts.
    """
    if not energies:
        return [{"start": 0.0, "end": duration, "energy_score": 0.0}]

    rms_values = [rms for _, _, rms in energies]
    threshold = float(np.percentile(rms_values, _ENERGY_PERCENTILE))
    hot = [(t0, t1, rms) for t0, t1, rms in energies if rms >= threshold]

    if not hot:
        return [{"start": 0.0, "end": duration, "energy_score": 0.0}]

    segments: list[dict] = []
    seg_start, seg_end, _ = hot[0]
    seg_energies = [hot[0][2]]

    for t_start, t_end, rms in hot[1:]:
        if t_start - seg_end <= _MERGE_GAP_SECONDS:
            seg_end = t_end
            seg_energies.append(rms)
        else:
            segments.append({
                "start": seg_start,
                "end": seg_end,
                "energy_score": float(np.mean(seg_energies)),
            })
            seg_start = t_start
            seg_end = t_end
            seg_energies = [rms]

    segments.append({
        "start": seg_start,
        "end": seg_end,
        "energy_score": float(np.mean(seg_energies)),
    })

    return segments


# ------------------------------------------------------------------ #
#  Per-job processor                                                   #
# ------------------------------------------------------------------ #

def _process_job(job: dict) -> str:
    """
    Run the full processing pipeline for one job dict.
    Returns the output directory path as string.
    Raises on failure (caller updates job status).
    """
    job_id = job["job_id"]
    video_path = job["raw_video_path"]

    print(f"[processor] PROCESSING {job_id}  video={video_path!r}")

    out_dir = OUTPUT_BASE / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[processor] AUDIO     {job_id}  extracting energy profile")
    energies = get_audio_energy(video_path)

    clip = VideoFileClip(video_path)

    try:
        print(
            f"[processor] INFO      {job_id}"
            f"  duration={clip.duration:.1f}s"
            f"  {clip.w}x{clip.h}"
            f"  fps={clip.fps}"
        )

        segments = _find_highlight_segments(energies, clip.duration)
        print(f"[processor] SEGMENTS  {job_id}  {len(segments)} highlight(s) found")

        metadata_entries: list[dict] = []

        for idx, seg in enumerate(segments, start=1):
            out_path = out_dir / f"highlight_{idx}.mp4"
            t_start = seg["start"]
            t_end = min(seg["end"], clip.duration)

            print(
                f"[processor] CUT       {job_id}"
                f"  #{idx}  {t_start:.1f}s–{t_end:.1f}s"
                f"  → {out_path.name}"
            )

            sub = clip.subclip(t_start, t_end)
            sub.write_videofile(
                str(out_path),
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )

            metadata_entries.append({
                "highlight": idx,
                "start_time": t_start,
                "end_time": t_end,
                "energy_score": round(seg["energy_score"], 6),
                "file": out_path.name,
            })

        video_info = {
            "duration": clip.duration,
            "width": clip.w,
            "height": clip.h,
            "fps": clip.fps,
        }

    finally:
        clip.close()

    meta_path = out_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(
            {"job_id": job_id, "video_info": video_info, "highlights": metadata_entries},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[processor] META      {job_id}  → {meta_path}")

    return str(out_dir)


# ------------------------------------------------------------------ #
#  Batch dispatcher                                                    #
# ------------------------------------------------------------------ #

def run_processor(jobs_path: str = str(JOBS_PATH)) -> list[dict]:
    """
    Load all pending gaming jobs from jobs.json and process each one.
    Returns a list of result dicts: {"job_id": ..., "status": "ok"|"error", ...}
    """
    path = Path(jobs_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    jobs_map: dict = data["jobs"]

    pending = [
        job for job in jobs_map.values()
        if job.get("status") == "pending"
        and job.get("channel_type") in _GAMING_CHANNELS
        and job.get("raw_video_path")
    ]

    print(f"[processor] {len(pending)} pending gaming job(s) found")

    results: list[dict] = []

    for job in pending:
        job_id = job["job_id"]
        try:
            out_dir = _process_job(job)

            job["status"] = "processed"
            job["video_path"] = out_dir
            job["updated_at"] = _utc_now()
            jobs_map[job_id] = job

            print(f"[processor] DONE      {job_id}  status=processed  output={out_dir!r}")
            results.append({"job_id": job_id, "status": "ok", "output": out_dir})

        except Exception as exc:
            job["status"] = "failed"
            job["error_message"] = str(exc)
            job["updated_at"] = _utc_now()
            jobs_map[job_id] = job

            print(f"[processor] ERROR     {job_id}  {exc}")
            results.append({"job_id": job_id, "status": "error", "error": str(exc)})

        # Write after each job so a crash mid-batch doesn't lose progress
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return results


# ------------------------------------------------------------------ #
#  CLI entry point                                                     #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    results = run_processor()

    ok = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "error")

    print(f"\n[processor] Done — ok={ok}  failed={failed}")

    for r in results:
        icon = "✓" if r["status"] == "ok" else "✗"
        print(f"  {icon}  {r['job_id']}")
        if r["status"] == "error":
            print(f"       {r['error']}")

    sys.exit(0 if failed == 0 else 1)
