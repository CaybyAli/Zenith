"""
pipeline_runner.py – Zenith batch dispatch loop.

Reads data/jobs.json, picks up every CREATED or STORED job and routes
it to the correct pipeline module:

  gaming_main    →  core/gaming_pipeline.py
  gaming_uncut   →  core/uncut_pipeline.py   (Phase 4 stub)
  vlog_main      →  core/vlog_pipeline.py    (Phase 2.B stub)
  faceless_trend →  core/faceless_pipeline.py (Phase 8 stub)

Run directly:
  python pipeline_runner.py

Or import run_pending_jobs() for programmatic use (e.g. from tests).
"""
from __future__ import annotations
import json
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import shutil
import sys
from pathlib import Path

from core.intake_manager import IntakeManager
from core.job_store import JobStore
from core.job_state_transitions import transition_job_state
from core.job_state_persistence import persist_job_state_checkpoint
from core.job_recovery import (
    apply_recovery_report_to_job,
    build_recovery_report,
)
from core.error_logger import log_error
from core.job_log_index import update_job_log_index
from core.render_versioning import next_render_version, versioned_final_path
from shared.enums import ChannelType, JobStatus, Mode, TargetFormat

from core.gaming_pipeline import (
    run_gaming_pipeline_for_job,
    _build_gaming_services,
)
from core.vlog_pipeline import run_vlog_pipeline_for_job
from core.uncut_pipeline import run_uncut_pipeline_for_job
from core.faceless_pipeline import run_faceless_pipeline_for_job

EXPORTS_BASE = Path("exports")


def _safe_log_error(
    job,
    export_dir: Path,
    module: str,
    phase: str,
    error: BaseException,
    details: dict | None = None,
):
    try:
        return log_error(
            job=job,
            export_dir=export_dir,
            module=module,
            phase=phase,
            error=error,
            details=details,
        )
    except Exception as log_exc:
        print(
            f"[pipeline_runner] ERROR_LOG_WARN "
            f"job={getattr(job, 'job_id', '-')} error={log_exc}"
        )
        return None




def _safe_update_job_log_index(job, export_dir: Path):
    try:
        return update_job_log_index(job, export_dir)
    except Exception as exc:
        print(
            f"[pipeline_runner] LOG_INDEX_WARN "
            f"job={getattr(job, 'job_id', '-')} error={exc}"
        )
        return None


def _make_export_dir(channel: str, job_id: str) -> Path:
    export_dir = EXPORTS_BASE / channel / job_id
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def _copy_gaming_outputs_to_export(job_id: str, export_dir: Path) -> dict | None:
    """Copy gaming pipeline output to a versioned final MP4 in export folder."""
    output_dir = Path("output")
    src_file = output_dir / f"{job_id}_final.mp4"

    if not src_file.exists():
        return None

    render_version = next_render_version(export_dir, job_id)
    dest_file = versioned_final_path(export_dir, job_id, render_version)
    shutil.copy2(src_file, dest_file)
    print(
        f"[pipeline_runner] EXPORT_VERSION {job_id} "
        f"version={render_version} file={dest_file.name}"
    )
    print("[pipeline_runner] COPIED   1 file(s) to export")
    return {
        "render_version": render_version,
        "exported_video_path": str(dest_file),
        "exported_video_name": dest_file.name,
    }


def _cleanup_output_files(job_id: str) -> None:
    """Lösche Output-Files nach erfolgreichem Export."""
    output_dir = Path("output")

    patterns = [
        f"{job_id}_final.mp4",
    ]

    deleted_count = 0
    for pattern in patterns:
        for file_path in output_dir.glob(pattern):
            if file_path.exists():
                file_path.unlink()
                deleted_count += 1

    if deleted_count > 0:
        print(
            f"[pipeline_runner] CLEANUP  Deleted {deleted_count} "
            f"temporary file(s) from output/"
        )


_INBOX_CHANNEL_MAP: dict[str, ChannelType] = {
    "gaming_main":  ChannelType.GAMING_MAIN,
    "gaming_uncut": ChannelType.GAMING_UNCUT,
    "vlog_main":    ChannelType.VLOG_MAIN,
    "faceless":     ChannelType.FACELESS_TREND,
}

def _write_export_job_json(job, export_dir: Path) -> Path:
    job_json_path = export_dir / "job.json"

    with job_json_path.open("w", encoding="utf-8") as handle:
        json.dump(job.to_dict(), handle, indent=4, ensure_ascii=False)

    print(f"[pipeline_runner] JOB_JSON  {job.job_id}  path={job_json_path}")
    return job_json_path



# ------------------------------------------------------------------ #
#  Inbox scanner                                                       #
# ------------------------------------------------------------------ #

def _scan_inbox_and_create_jobs(job_store: JobStore) -> None:
    """Scan inbox folders and create a job for every new MP4."""
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
                print(
                    f"[pipeline_runner] INBOX SKIP  {mp4.name}  "
                    f"(job already exists)"
                )
                continue

            print(
                f"[pipeline_runner] INBOX NEW   {mp4.name}  "
                f"channel={channel_type.value}"
            )
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
#  Dispatcher                                                          #
# ------------------------------------------------------------------ #

def _dispatch_pipeline(job, services: dict) -> dict:
    """Route a job to its channel-specific pipeline module."""
    channel = job.channel_type

    if channel == ChannelType.GAMING_MAIN:
        return run_gaming_pipeline_for_job(job, services)

    if channel == ChannelType.VLOG_MAIN:
        return run_vlog_pipeline_for_job(job, services)

    if channel == ChannelType.GAMING_UNCUT:
        return run_uncut_pipeline_for_job(job, services)

    if channel == ChannelType.FACELESS_TREND:
        return run_faceless_pipeline_for_job(job, services)

    raise ValueError(f"Unbekannter Channel-Type: {channel}")


# ------------------------------------------------------------------ #
#  Batch dispatcher                                                    #
# ------------------------------------------------------------------ #

def run_pending_jobs(
    db_path: str = "data/jobs.json",
    input_video_path: str | None = None,
) -> list[dict]:
    """
    Scan the job store and process every CREATED / STORED job.

    Returns a list of result dicts, one per processed job:
      {"job_id": ..., "status": "ok"|"skip"|"error", ...}
    """
    job_store = JobStore(db_path=db_path)
    cli_video_path: Path | None = None
    if input_video_path:
        cli_video_path = Path(input_video_path)
        if not cli_video_path.exists() or not cli_video_path.is_file():
            raise FileNotFoundError(f"Input video not found: {input_video_path}")

        existing_jobs = job_store.list_jobs()
        existing_paths = {
            str(Path(job.raw_video_path).resolve())
            for job in existing_jobs
            if job.raw_video_path
        }
        normalized = str(cli_video_path.resolve())
        has_pending_cli_job = any(
            job.status in (JobStatus.CREATED, JobStatus.STORED)
            and job.raw_video_path
            and str(Path(job.raw_video_path).resolve()) == normalized
            for job in existing_jobs
        )
        if normalized in existing_paths and has_pending_cli_job:
            print(
                f"[pipeline_runner] CLI SKIP   {cli_video_path.name}  "
                f"(pending job already exists)"
            )
        else:
            print(
                f"[pipeline_runner] CLI NEW    {cli_video_path.name}  "
                f"channel={ChannelType.GAMING_MAIN.value}"
            )
            job = IntakeManager(job_store).create_gaming_job(
                channel_type=ChannelType.GAMING_MAIN,
                raw_video_path=str(cli_video_path),
                target_format=TargetFormat.LONGFORM,
                target_platforms=["youtube"],
                mode=Mode.NORMAL,
            )
            print(f"[pipeline_runner] CLI JOB    {job.job_id}  created")
    else:
        _scan_inbox_and_create_jobs(job_store)

    all_jobs = job_store.list_jobs()
    if cli_video_path is not None:
        cli_normalized = str(cli_video_path.resolve())
        pending = [
            j for j in all_jobs
            if j.status in (JobStatus.CREATED, JobStatus.STORED)
            and j.raw_video_path
            and str(Path(j.raw_video_path).resolve()) == cli_normalized
        ]
    else:
        pending = [
            j for j in all_jobs
            if j.status in (JobStatus.CREATED, JobStatus.STORED)
        ]

    # ---- Empty-state ------------------------------------------------
    if not pending:
        print("[pipeline_runner] Keine aktuellen Rohdateien.")
        return []

    results: list[dict] = []
    gaming_services: dict | None = None

    for job in pending:
        channel = job.channel_type.value

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

        # Lazy-init services (only built once, reused across jobs)
        if gaming_services is None:
            gaming_services = _build_gaming_services()
            gaming_services["job_store"] = job_store

        channel_label = channel.upper().replace("_", " ")
        print(
            f"[pipeline_runner] {channel_label}  {job.job_id}  "
            f"video={job.raw_video_path!r}"
        )

        try:
            result = _dispatch_pipeline(job, gaming_services)

            export_dir = _make_export_dir(channel, job.job_id)
            export_info = _copy_gaming_outputs_to_export(job.job_id, export_dir)
            _cleanup_output_files(job.job_id)
            print(f"[pipeline_runner] EXPORT    {job.job_id}  → {export_dir}")
            if export_info is not None:
                result["render_version"] = export_info["render_version"]
                result["exported_video_path"] = export_info["exported_video_path"]
                job.render_version = export_info["render_version"]
                job.video_path = export_info["exported_video_path"]

            title_package = result.get("title_package")
            if title_package is not None:
                job.title = title_package.primary_title
            if job.status == JobStatus.RENDERED:
                transition_job_state(
                    job,
                    JobStatus.ASSEMBLED,
                    module="pipeline_runner",
                    reason="export_finished",
                )
            else:
                job.status = JobStatus.ASSEMBLED
                job.touch()

            persist_job_state_checkpoint(
                job=job,
                job_store=job_store,
                export_dir=export_dir,
                step_name="assembled",
                reason="export_finished",
            )

            recovery_report = build_recovery_report(job, export_dir=export_dir)
            apply_recovery_report_to_job(job, recovery_report)
            _safe_update_job_log_index(job, export_dir)
            job_store.update_job(job)

            _write_export_job_json(job, export_dir)

            results.append({
                "job_id":   job.job_id,
                "channel":  channel,
                "status":   "ok",
                "pipeline": channel,
                "result":   result,
            })

        except NotImplementedError as exc:
            # Stub-Pipeline noch nicht implementiert — kein Crash
            print(
                f"[pipeline_runner] AWAITING_PIPELINE  {job.job_id}  "
                f"{channel} not yet implemented"
            )
            job.status = "awaiting_pipeline_implementation"
            job.touch()
            job_store.update_job(job)
            results.append({
                "job_id":   job.job_id,
                "channel":  channel,
                "status":   "skip",
                "reason":   "awaiting_pipeline_implementation",
                "error":    str(exc),
            })

        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.touch()

            export_dir = _make_export_dir(channel, job.job_id)

            _safe_log_error(
                job=job,
                export_dir=export_dir,
                module="pipeline_runner",
                phase="dispatch",
                error=exc,
                details={
                    "channel": channel,
                    "raw_video_path": str(job.raw_video_path),
                },
            )

            try:
                recovery_report = build_recovery_report(job, export_dir=export_dir)
                apply_recovery_report_to_job(job, recovery_report)
            except Exception as recovery_exc:
                print(
                    f"[pipeline_runner] RECOVERY_AFTER_ERROR_WARN "
                    f"job={job.job_id} error={recovery_exc}"
                )

            _safe_update_job_log_index(job, export_dir)
            job_store.update_job(job)

            try:
                _write_export_job_json(job, export_dir)
            except Exception as job_json_exc:
                print(
                    f"[pipeline_runner] JOB_JSON_AFTER_ERROR_WARN "
                    f"job={job.job_id} error={job_json_exc}"
                )

            results.append({
                "job_id":   job.job_id,
                "channel":  channel,
                "status":   "error",
                "pipeline": channel,
                "error":    str(exc),
            })

    return results


# ------------------------------------------------------------------ #
#  CLI entry point                                                     #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    input_video_path = sys.argv[1] if len(sys.argv) > 1 else None
    results = run_pending_jobs(input_video_path=input_video_path)

    ok      = sum(1 for r in results if r["status"] == "ok")
    skipped = sum(1 for r in results if r["status"] == "skip")
    failed  = sum(1 for r in results if r["status"] == "error")

    if results:
        print(
            f"\n[pipeline_runner] Done — ok={ok}  "
            f"skipped={skipped}  failed={failed}"
        )
        for r in results:
            icon = {"ok": "✓", "skip": "–", "error": "✗"}.get(r["status"], "?")
            print(
                f"  {icon}  {r['job_id']}  "
                f"({r.get('pipeline', r.get('reason', ''))})"
            )
            if r["status"] == "error":
                print(f"       {r['error']}")

    sys.exit(0 if failed == 0 else 1)

