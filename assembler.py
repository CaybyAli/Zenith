"""
assembler.py — Zenith video assembly step (pipeline stage 3).

Takes all highlight clips for a processed job, sorts them by original
start_time, concatenates them with a short crossfade, and writes the
final longform video to exports/{channel_type}/{job_id}/final_video.mp4.

Run directly:
  python assembler.py

Or import run_assembler() for programmatic use.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from moviepy.editor import VideoFileClip, concatenate_videoclips

JOBS_PATH = Path("data/jobs.json")
PROCESSED_BASE = Path("output/processed")   # temp highlight clips
EXPORTS_BASE = Path("exports")              # final output — read by dashboard & publisher

_CROSSFADE_DURATION = 0.3


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------ #
#  Per-job assembler                                                   #
# ------------------------------------------------------------------ #

def _assemble_job(job: dict) -> str:
    """
    Concatenate all highlight clips for one job into a final video.
    Returns the output file path as string.
    Raises on failure (caller updates job status).
    """
    job_id = job["job_id"]
    processed_dir = PROCESSED_BASE / job_id

    # Load and validate metadata
    meta_path = processed_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"metadata.json not found: {meta_path}")

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    highlights = metadata.get("highlights", [])

    if not highlights:
        raise ValueError(f"No highlights found in metadata for job {job_id}")

    # Sort by original start_time to preserve chronological order
    highlights = sorted(highlights, key=lambda h: h["start_time"])

    print(f"[assembler] CLIPS     {job_id}  {len(highlights)} highlight(s) to assemble")

    # Verify all clip files exist before loading
    clip_paths = []
    for entry in highlights:
        clip_path = processed_dir / entry["file"]
        if not clip_path.exists():
            raise FileNotFoundError(f"Highlight clip not found: {clip_path}")
        clip_paths.append(clip_path)

    channel_type = job.get("channel_type", "unknown")
    out_dir = EXPORTS_BASE / channel_type / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "final_video.mp4"

    clips = [VideoFileClip(str(p)) for p in clip_paths]

    try:
        for i, cp in enumerate(clips):
            print(
                f"[assembler] LOAD      {job_id}"
                f"  #{i + 1}  {cp.duration:.1f}s  {cp.w}x{cp.h}"
            )

        print(f"[assembler] CONCAT    {job_id}  applying crossfade={_CROSSFADE_DURATION}s")

        try:
            # Apply crossfadein to every clip except the first
            faded = [clips[0]]
            for clip in clips[1:]:
                faded.append(clip.crossfadein(_CROSSFADE_DURATION))

            final = concatenate_videoclips(
                faded,
                method="compose",
                padding=-_CROSSFADE_DURATION,
            )
        except Exception as cf_exc:
            print(
                f"[assembler] WARN      {job_id}"
                f"  crossfade failed ({cf_exc}) — falling back to hard cuts"
            )
            final = concatenate_videoclips(clips, method="compose")

        print(f"[assembler] WRITE     {job_id}  → {out_path}  ({final.duration:.1f}s total)")

        final.write_videofile(
            str(out_path),
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )

    finally:
        for clip in clips:
            clip.close()

    print(f"[assembler] DONE      {job_id}  → {out_path}")
    return str(out_path)


# ------------------------------------------------------------------ #
#  Batch dispatcher                                                    #
# ------------------------------------------------------------------ #

def run_assembler(jobs_path: str = str(JOBS_PATH)) -> list[dict]:
    """
    Load all processed jobs from jobs.json and assemble each one.
    Returns a list of result dicts: {"job_id": ..., "status": "ok"|"error", ...}
    """
    path = Path(jobs_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    jobs_map: dict = data["jobs"]

    pending = [
        job for job in jobs_map.values()
        if job.get("status") == "processed"
    ]

    print(f"[assembler] {len(pending)} processed job(s) found")

    results: list[dict] = []

    for job in pending:
        job_id = job["job_id"]

        # Mark as in-progress immediately
        job["status"] = "assembling"
        job["updated_at"] = _utc_now()
        jobs_map[job_id] = job
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"[assembler] START     {job_id}  channel={job.get('channel_type', '?')}")

        try:
            out_file = _assemble_job(job)

            job["status"] = "assembled"
            job["video_path"] = out_file
            job["updated_at"] = _utc_now()
            jobs_map[job_id] = job

            results.append({"job_id": job_id, "status": "ok", "output": out_file})

        except Exception as exc:
            job["status"] = "assembly_failed"
            job["error_message"] = str(exc)
            job["updated_at"] = _utc_now()
            jobs_map[job_id] = job

            print(f"[assembler] ERROR     {job_id}  {exc}")
            results.append({"job_id": job_id, "status": "error", "error": str(exc)})

        # Persist after every job so a crash mid-batch doesn't lose progress
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return results


# ------------------------------------------------------------------ #
#  CLI entry point                                                     #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    results = run_assembler()

    ok = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "error")

    print(f"\n[assembler] Done — ok={ok}  failed={failed}")

    for r in results:
        icon = "✓" if r["status"] == "ok" else "✗"
        print(f"  {icon}  {r['job_id']}")
        if r["status"] == "error":
            print(f"       {r['error']}")

    sys.exit(0 if failed == 0 else 1)
