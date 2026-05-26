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
  python pipeline_runner.py <video>
  python pipeline_runner.py --approve <job_id>
  python pipeline_runner.py --list-blocked

Or import run_pending_jobs() for programmatic use (e.g. from tests).
"""
from __future__ import annotations
import argparse
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
from core.job_store import JobStore, compact_job_dict_for_persistence
from core.job_state_transitions import transition_job_state
from core.job_state_persistence import persist_job_state_checkpoint
from core.job_recovery import (
    apply_recovery_report_to_job,
    build_recovery_report,
)
from core.error_logger import log_error
from core.job_log_index import update_job_log_index
from core.power_profile import PowerProfile
from core.render_versioning import next_render_version, versioned_final_path
from core.approval_store import write_job_approval
from shared.enums import (
    ChannelType,
    JobStatus,
    Mode,
    TargetFormat,
    classify_job_status_for_runner,
)

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
    slim_dict = compact_job_dict_for_persistence(job.to_dict())

    with job_json_path.open("w", encoding="utf-8") as handle:
        json.dump(slim_dict, handle, indent=4, ensure_ascii=False)

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
    approved_job_id: str | None = None,
    power_profile: str | None = None,
) -> list[dict]:
    """
    Scan the job store and process every CREATED / STORED job.

    Returns a list of result dicts, one per processed job:
      {"job_id": ..., "status": "ok"|"skip"|"error", ...}
    """
    if input_video_path and approved_job_id:
        raise ValueError("input_video_path and approved_job_id are mutually exclusive")

    job_store = JobStore(db_path=db_path)
    cli_video_path: Path | None = None

    if approved_job_id:
        approved_job = job_store.get_job(approved_job_id)
        channel = str(getattr(approved_job.channel_type, "value", approved_job.channel_type))
        if not approved_job.raw_video_path:
            raise FileNotFoundError(f"Approved job has no raw_video_path: {approved_job_id}")

        raw_video_path = Path(approved_job.raw_video_path)
        if not raw_video_path.exists() or not raw_video_path.is_file():
            raise FileNotFoundError(f"Approved job raw video not found: {approved_job.raw_video_path}")

        approval_path = write_job_approval(
            job_id=approved_job.job_id,
            channel=channel,
            approved_by="cli",
            exports_base=EXPORTS_BASE,
        )
        print(
            f"[pipeline_runner] APPROVE  {approved_job.job_id}  "
            f"path={approval_path}"
        )
        print(
            f"[pipeline_runner] APPROVE RERUN  {approved_job.job_id}  "
            f"video={approved_job.raw_video_path!r}"
        )

        approved_job.power_profile = PowerProfile.normalize(
            power_profile or getattr(approved_job, "power_profile", PowerProfile.DEFAULT)
        )
        approved_job.status = JobStatus.CREATED
        approved_job.error_message = ""
        approved_job.touch()
        job_store.update_job(approved_job)

    elif input_video_path:
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
            job.power_profile = PowerProfile.normalize(
                power_profile or PowerProfile.DEFAULT
            )
            job_store.update_job(job)
            print(f"[pipeline_runner] CLI JOB    {job.job_id}  created")
    else:
        _scan_inbox_and_create_jobs(job_store)

    all_jobs = job_store.list_jobs()
    if approved_job_id is not None:
        pending = [j for j in all_jobs if j.job_id == approved_job_id]
    elif cli_video_path is not None:
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
        if power_profile is not None:
            job.power_profile = PowerProfile.normalize(power_profile)
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
                    JobStatus.APPROVAL_PENDING,
                    module="pipeline_runner",
                    reason="legacy_rendered_without_validation_failure",
                )
            elif job.status in {
                JobStatus.APPROVAL_PENDING,
                JobStatus.APPROVED,
                JobStatus.PUBLISHED,
                JobStatus.VALIDATION_FAILED,
                JobStatus.FAILED,
                JobStatus.CRASHED,
            }:
                job.touch()
            else:
                job.touch()

            runner_status = classify_job_status_for_runner(job.status)
            job_status_value = str(getattr(job.status, "value", job.status))

            persist_job_state_checkpoint(
                job=job,
                job_store=job_store,
                export_dir=export_dir,
                step_name=f"runner_{runner_status}",
                reason=f"pipeline_finished_status_{job_status_value}",
            )

            recovery_report = build_recovery_report(job, export_dir=export_dir)
            apply_recovery_report_to_job(job, recovery_report)
            _safe_update_job_log_index(job, export_dir)
            job_store.update_job(job)

            _write_export_job_json(job, export_dir)

            results.append({
                "job_id":     job.job_id,
                "channel":    channel,
                "status":     runner_status,
                "job_status": job_status_value,
                "pipeline":   channel,
                "result":     result,
                "error":      "" if runner_status == "ok" else (
                    getattr(job, "error_message", None) or job_status_value
                ),
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
            job.status = JobStatus.CRASHED
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

def _print_results(results: list[dict]) -> int:
    ok = sum(1 for r in results if r["status"] == "ok")
    skipped = sum(1 for r in results if r["status"] == "skip")
    failed = sum(1 for r in results if r["status"] == "error")

    if results:
        print(
            f"\n[pipeline_runner] Done ? ok={ok}  "
            f"skipped={skipped}  failed={failed}"
        )
        for r in results:
            icon = {"ok": "?", "skip": "?", "error": "?"}.get(r["status"], "?")
            print(
                f"  {icon}  {r['job_id']}  "
                f"({r.get('pipeline', r.get('reason', ''))})"
            )
            if r["status"] == "error":
                print(f"       {r['error']}")

    return failed


def _list_blocked_jobs(db_path: str = "data/jobs.json") -> list[dict]:
    job_store = JobStore(db_path=db_path)
    blocked = [
        job for job in job_store.list_jobs()
        if str(getattr(job.status, "value", job.status)) == JobStatus.RENDER_BLOCKED.value
    ]

    if not blocked:
        print("[pipeline_runner] BLOCKED  none")
        return []

    results: list[dict] = []
    for job in blocked:
        channel = str(getattr(job.channel_type, "value", job.channel_type))
        print(
            f"[pipeline_runner] BLOCKED  {job.job_id}  "
            f"channel={channel}  video={job.raw_video_path!r}"
        )
        results.append(
            {
                "job_id": job.job_id,
                "channel": channel,
                "status": "skip",
                "reason": "render_blocked",
            }
        )
    return results


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Zenith pending jobs or approve one blocked job."
    )
    parser.add_argument(
        "input_video_path",
        nargs="?",
        help="Optional raw video path for CLI job mode.",
    )
    parser.add_argument(
        "--approve",
        dest="approve_job_id",
        metavar="JOB_ID",
        help="Persist explicit approval for one job and rerun it.",
    )
    parser.add_argument(
        "--list-blocked",
        action="store_true",
        help="List jobs currently in render_blocked status.",
    )
    parser.add_argument(
        "--power-profile",
        dest="power_profile",
        choices=PowerProfile.ALL,
        default=PowerProfile.DEFAULT,
        help="Pipeline power profile: off|eco|balanced|performance|full_power (default: balanced)",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=None,
        help="Output directory for probe-clip mode.",
    )
    parser.add_argument(
        "--start-sec",
        dest="start_sec",
        type=float,
        default=None,
        help="Start offset in seconds for probe-clip render.",
    )
    parser.add_argument(
        "--duration",
        dest="duration",
        type=float,
        default=None,
        help="Duration in seconds for probe-clip render.",
    )
    args = parser.parse_args(argv)

    selected_modes = sum(
        bool(item)
        for item in (
            args.input_video_path,
            args.approve_job_id,
            args.list_blocked,
        )
    )
    if selected_modes > 1:
        parser.error("Use only one mode: <video>, --approve <job_id>, or --list-blocked")

    probe_args_present = any(
        value is not None
        for value in (args.output_dir, args.start_sec, args.duration)
    )
    if probe_args_present and (args.approve_job_id or args.list_blocked):
        parser.error("Probe-clip arguments cannot be combined with --approve or --list-blocked")
    if probe_args_present and not args.input_video_path:
        parser.error("Probe-clip arguments require <video>")
    if (args.start_sec is not None or args.duration is not None) and args.output_dir is None:
        parser.error("--start-sec and --duration require --output-dir")
    if args.duration is not None and args.duration <= 0:
        parser.error("--duration must be greater than 0")

    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    # ---- Probe-Clip Mode -------------------------------------------
    if args.input_video_path and args.output_dir is not None:
        from core.probe_clip_runner import run_probe_clip

        return run_probe_clip(
            video_path=args.input_video_path,
            output_dir=args.output_dir,
            start_sec=args.start_sec or 0.0,
            duration=args.duration or 10.0,
        )

    if args.list_blocked:
        _list_blocked_jobs()
        return 0

    results = run_pending_jobs(
        input_video_path=args.input_video_path,
        approved_job_id=args.approve_job_id,
        power_profile=args.power_profile,
    )
    failed = _print_results(results)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
