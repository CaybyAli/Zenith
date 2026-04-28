"""
pipeline_runner.py — Zenith batch dispatch loop.

Reads data/jobs.json, picks up every CREATED or STORED job and routes
it to the correct pipeline:

  gaming_main    →  run_gaming_pipeline_for_job()  (app.py)
  gaming_uncut   →  run_gaming_pipeline_for_job()  (app.py)
  faceless_trend →  FacelessPipeline().run()        (core/faceless_pipeline.py)

Run directly:
  python pipeline_runner.py

Or import run_pending_jobs() for programmatic use (e.g. from tests).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from core.faceless_pipeline import FacelessPipeline
from core.intake_manager import IntakeManager
from core.job_store import JobStore
from shared.enums import ChannelType, JobStatus, Mode, TargetFormat

EXPORTS_BASE = Path("exports")


def _make_export_dir(channel: str, job_id: str) -> Path:
    export_dir = EXPORTS_BASE / channel / job_id
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def _copy_shorts_to_export(shorts_paths: list, export_dir: Path) -> None:
    """Copy short clip files into exports/{channel}/{job_id}/shorts/."""
    if not shorts_paths:
        return
    shorts_dir = export_dir / "shorts"
    shorts_dir.mkdir(exist_ok=True)
    for src in shorts_paths:
        src_path = Path(src) if src else None
        if src_path and src_path.exists():
            shutil.copy2(src_path, shorts_dir / src_path.name)


_GAMING_CHANNELS = frozenset({
    ChannelType.GAMING_MAIN.value,
    ChannelType.GAMING_UNCUT.value,
})
_FACELESS_CHANNELS = frozenset({
    ChannelType.FACELESS_TREND.value,
})

_INBOX_CHANNEL_MAP: dict[str, ChannelType] = {
    "gaming_main": ChannelType.GAMING_MAIN,
    "gaming_uncut": ChannelType.GAMING_UNCUT,
}


# ------------------------------------------------------------------ #
#  Inbox scanner                                                       #
# ------------------------------------------------------------------ #

def _scan_inbox_and_create_jobs(job_store: JobStore) -> None:
    """Scan inbox folders and create a gaming job for every new MP4."""
    existing_paths = {
        str(Path(job.raw_video_path).resolve())
        for job in job_store.list_jobs()
        if job.raw_video_path
    }

    intake = IntakeManager(job_store)

    for folder_name, channel_type in _INBOX_CHANNEL_MAP.items():
        inbox_dir = Path("inbox") / folder_name
        if not inbox_dir.is_dir():
            continue

        for mp4 in sorted(inbox_dir.glob("*.mp4")):
            normalized = str(mp4.resolve())
            if normalized in existing_paths:
                print(f"[pipeline_runner] INBOX SKIP  {mp4.name}  (job already exists)")
                continue

            print(f"[pipeline_runner] INBOX NEW   {mp4.name}  channel={channel_type.value}")
            job = intake.create_gaming_job(
                channel_type=channel_type,
                raw_video_path=str(mp4),
                target_format=TargetFormat.LONGFORM,
                target_platforms=["youtube"],
                mode=Mode.NORMAL,
            )
            existing_paths.add(normalized)
            print(f"[pipeline_runner] INBOX JOB   {job.job_id}  created")


# ------------------------------------------------------------------ #
#  Service factory (lazy — only built when a gaming job is present)   #
# ------------------------------------------------------------------ #

def _build_gaming_services() -> dict:
    from core.gaming_analyzer import GamingAnalyzer
    from core.gaming_cutter import GamingCutter
    from core.metadata_generator import MetadataGenerator
    from core.publish_package_builder import PublishPackageBuilder
    from core.render_processor import RenderProcessor
    from core.shorts_decision_engine import ShortsDecisionEngine
    from core.subtitle_processor import SubtitleProcessor
    from core.thumbnail_forge import ThumbnailForge
    from core.title_generator import TitleGenerator
    from core.validator import Validator

    return {
        "analyzer": GamingAnalyzer(),
        "cutter": GamingCutter(),
        "shorts_engine": ShortsDecisionEngine(),
        "renderer": RenderProcessor(),
        "subtitle_processor": SubtitleProcessor(),
        "title_gen": TitleGenerator(),
        "metadata_gen": MetadataGenerator(),
        "thumbnail_forge": ThumbnailForge(),
        "validator": Validator(),
        "publish_package_builder": PublishPackageBuilder(),
    }


# ------------------------------------------------------------------ #
#  Individual job runners                                              #
# ------------------------------------------------------------------ #

def run_faceless_pipeline_for_job(job) -> dict:
    """Run the full faceless pipeline for a single Job and return its result."""
    return FacelessPipeline().run(job)


def run_gaming_pipeline_for_job(job, *, gaming_services: dict) -> dict:
    """Delegate to the gaming pipeline in app.py with the given services."""
    from app import run_gaming_pipeline_for_job as _gaming_runner

    if not job.raw_video_path:
        raise ValueError(f"Gaming job {job.job_id} has no raw_video_path")

    return _gaming_runner(job=job, **gaming_services)


# ------------------------------------------------------------------ #
#  Batch dispatcher                                                    #
# ------------------------------------------------------------------ #

def run_pending_jobs(db_path: str = "data/jobs.json") -> list[dict]:
    """
    Scan the job store and process every CREATED / STORED job.

    Returns a list of result dicts, one per processed job:
      {"job_id": ..., "status": "ok"|"skip"|"error", ...}
    """
    job_store = JobStore(db_path=db_path)
    _scan_inbox_and_create_jobs(job_store)
    all_jobs = job_store.list_jobs()

    results: list[dict] = []
    gaming_services: dict | None = None

    for job in all_jobs:
        if job.status not in (JobStatus.CREATED, JobStatus.STORED):
            continue

        channel = job.channel_type.value

        # ---- Faceless ------------------------------------------------
        if channel in _FACELESS_CHANNELS:
            print(f"[pipeline_runner] FACELESS  {job.job_id}  topic={job.topic!r}")
            try:
                result = run_faceless_pipeline_for_job(job)
                export_dir = _make_export_dir(channel, job.job_id)
                print(f"[pipeline_runner] EXPORT    {job.job_id}  → {export_dir}")
                job.status = JobStatus.ROUTED
                job.review_status = "waiting_for_review"
                job.touch()
                job_store.update_job(job)
                results.append({
                    "job_id": job.job_id,
                    "channel": channel,
                    "status": "ok",
                    "pipeline": "faceless",
                    "result": result,
                })
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                job.touch()
                job_store.update_job(job)
                results.append({
                    "job_id": job.job_id,
                    "channel": channel,
                    "status": "error",
                    "pipeline": "faceless",
                    "error": str(exc),
                })

        # ---- Gaming --------------------------------------------------
        elif channel in _GAMING_CHANNELS:
            if not job.raw_video_path:
                print(
                    f"[pipeline_runner] SKIP {job.job_id}  "
                    f"channel={channel}  reason=no_raw_video_path"
                )
                results.append({
                    "job_id": job.job_id,
                    "channel": channel,
                    "status": "skip",
                    "reason": "no_raw_video_path",
                })
                continue

            print(
                f"[pipeline_runner] GAMING   {job.job_id}  "
                f"channel={channel}  video={job.raw_video_path!r}"
            )

            if gaming_services is None:
                gaming_services = _build_gaming_services()

            try:
                result = run_gaming_pipeline_for_job(
                    job, gaming_services=gaming_services
                )
                export_dir = _make_export_dir(channel, job.job_id)
                _copy_shorts_to_export(result.get("shorts_paths", []), export_dir)
                print(f"[pipeline_runner] EXPORT    {job.job_id}  → {export_dir}")
                job.status = JobStatus.ROUTED
                job.touch()
                job_store.update_job(job)
                results.append({
                    "job_id": job.job_id,
                    "channel": channel,
                    "status": "ok",
                    "pipeline": "gaming",
                    "result": result,
                })
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                job.touch()
                job_store.update_job(job)
                results.append({
                    "job_id": job.job_id,
                    "channel": channel,
                    "status": "error",
                    "pipeline": "gaming",
                    "error": str(exc),
                })

        # ---- Unknown channel -----------------------------------------
        else:
            print(f"[pipeline_runner] UNKNOWN channel={channel!r}  job={job.job_id}")
            results.append({
                "job_id": job.job_id,
                "channel": channel,
                "status": "skip",
                "reason": "unknown_channel",
            })

    return results


# ------------------------------------------------------------------ #
#  CLI entry point                                                     #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    results = run_pending_jobs()

    ok = sum(1 for r in results if r["status"] == "ok")
    skipped = sum(1 for r in results if r["status"] == "skip")
    failed = sum(1 for r in results if r["status"] == "error")

    print(f"\n[pipeline_runner] Done — ok={ok}  skipped={skipped}  failed={failed}")

    for r in results:
        icon = {"ok": "✓", "skip": "—", "error": "✗"}.get(r["status"], "?")
        print(f"  {icon}  {r['job_id']}  ({r.get('pipeline', r.get('reason', ''))})")
        if r["status"] == "error":
            print(f"       {r['error']}")

    sys.exit(0 if failed == 0 else 1)
