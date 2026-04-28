from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from core.runtime_mode_controller import RuntimeModeController
from core.vacation_controller import VacationController
from shared.runtime_modes import RuntimeAction
from storage.local_storage_provider import LocalStorageProvider


QUEUE_FILE = r"D:\Zenith\data\rerender_queue.json"
RERENDER_JOBS_FILE = r"D:\Zenith\data\rerender_jobs.json"
EXPORTS_BASE_PATH = "exports"

runtime_mode_controller = RuntimeModeController()
vacation_controller = VacationController()
storage_provider = LocalStorageProvider()


def get_storage_provider(provider=None):
    return provider or storage_provider


def is_runtime_action_allowed(action, controller=None):
    active_controller = controller or runtime_mode_controller
    state = active_controller.get_state()
    allowed = action in active_controller.get_allowed_actions(state.mode)

    if not allowed:
        print(
            "[RerenderWorker] Runtime action blocked:",
            action.value if hasattr(action, "value") else str(action),
            "| mode:",
            state.mode.value,
        )

    return allowed


def get_effective_operation_mode(controller=None):
    active_controller = controller or vacation_controller
    return active_controller.get_effective_mode()


def is_vacation_action_allowed(action, controller=None):
    active_controller = controller or vacation_controller
    active = active_controller.is_active_now()

    blocked_actions = {
        RuntimeAction.RERENDER_QUEUE_INTAKE,
        RuntimeAction.RERENDER_PIPELINE,
    }

    allowed = (not active) or (action not in blocked_actions)

    if not allowed:
        print(
            "[RerenderWorker] Vacation action blocked:",
            action.value if hasattr(action, "value") else str(action),
            "| effective_mode:",
            active_controller.get_effective_mode().value,
        )

    return allowed


def load_json_list(file_path, provider=None):
    storage = get_storage_provider(provider)

    if not storage.exists(file_path):
        return []

    try:
        data = storage.read_json(file_path)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_json_list(file_path, data, provider=None):
    storage = get_storage_provider(provider)
    absolute_path = storage.abspath(file_path)

    storage.write_json(file_path, data, indent=4)

    print("JSON GESPEICHERT:")
    print("Pfad:", absolute_path)
    print("Einträge:", len(data) if isinstance(data, list) else "kein list-objekt")


def create_rerender_job_from_queue(
    queue_file=QUEUE_FILE,
    rerender_jobs_file=RERENDER_JOBS_FILE,
    provider=None,
):
    if not is_runtime_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE):
        print("Rerender queue intake ist durch Runtime Mode blockiert.")
        return

    if not is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE):
        print("Rerender queue intake ist durch Vacation Mode blockiert.")
        return

    queue = load_json_list(queue_file, provider=provider)

    if not queue:
        print("Rerender queue ist leer.")
        return

    next_job = queue.pop(0)

    print("RERENDER WIRD AUS QUEUE ÜBERNOMMEN:")
    print("Job ID:", next_job["job_id"])
    print("Channel:", next_job["channel_type"])
    print("Video:", next_job["video_path"])

    save_json_list(queue_file, queue, provider=provider)
    print("Job aus rerender_queue entfernt.")

    rerender_jobs = load_json_list(rerender_jobs_file, provider=provider)

    new_rerender_job = {
        "rerender_job_id": f"rerender_{uuid4().hex[:12]}",
        "source_job_id": next_job["job_id"],
        "channel_type": next_job["channel_type"],
        "video_path": next_job["video_path"],
        "title": next_job["title"],
        "description": next_job["description"],
        "status": "pending",
        "retry_count": 0,
        "max_retry_attempts": 3,
        "retry_delay_minutes": 15,
        "next_retry_at": None,
        "last_retry_at": None,
        "last_retry_reason": None,
        "permanently_failed": False,
    }

    rerender_jobs.append(new_rerender_job)
    save_json_list(rerender_jobs_file, rerender_jobs, provider=provider)

    print("NEUER RERENDER JOB ANGELEGT:")
    print("Rerender Job ID:", new_rerender_job["rerender_job_id"])


def process_next_rerender_job(
    rerender_jobs_file=RERENDER_JOBS_FILE,
    exports_base_path=EXPORTS_BASE_PATH,
    provider=None,
):
    storage = get_storage_provider(provider)
    rerender_jobs = load_json_list(rerender_jobs_file, provider=storage)

    for job in rerender_jobs:
        status = job.get("status")

        if status == "pending":
            pass
        elif status == "scheduled_retry":
            next_retry_at = job.get("next_retry_at")

            if not next_retry_at:
                print("Rerender retry ohne next_retry_at:", job.get("rerender_job_id"))
                continue

            try:
                retry_dt = datetime.strptime(next_retry_at, "%Y-%m-%d %H:%M")
            except ValueError:
                print("Ungültiges retry Datum:", next_retry_at)
                continue

            if datetime.now() < retry_dt:
                continue
        else:
            continue

        if not is_runtime_action_allowed(RuntimeAction.RERENDER_PIPELINE):
            print("Rerender pipeline ist durch Runtime Mode blockiert.")
            return

        if not is_vacation_action_allowed(RuntimeAction.RERENDER_PIPELINE):
            print("Rerender pipeline ist durch Vacation Mode blockiert.")
            return

        job["status"] = "processing"
        save_json_list(rerender_jobs_file, rerender_jobs, provider=storage)

        print("RERENDER JOB IN BEARBEITUNG:")
        print("Rerender Job ID:", job["rerender_job_id"])
        print("Source Job ID:", job["source_job_id"])
        print("Channel:", job["channel_type"])

        print("STARTE NEUE PIPELINE FÜR RERENDER...")

        video_path = job["video_path"]

        if not storage.exists(video_path):
            channel_aliases = {
                "main": "gaming_main",
                "uncut": "gaming_uncut",
            }

            channel_folder = channel_aliases.get(job["channel_type"], job["channel_type"])
            fallback_video_path = storage.join(
                exports_base_path,
                channel_folder,
                job["source_job_id"],
                "video.mp4",
            )

            if storage.exists(fallback_video_path):
                video_path = fallback_video_path
                print("Fallback video_path verwendet:", video_path)
            else:
                source_job_file = storage.join(
                    exports_base_path,
                    channel_folder,
                    job["source_job_id"],
                    "job.json",
                )

                source_job_data = {}
                if storage.exists(source_job_file):
                    source_job_data = storage.read_json(source_job_file)

                source_video_path = source_job_data.get("video_path")
                raw_video_path = source_job_data.get("raw_video_path")

                if source_video_path and storage.exists(source_video_path):
                    video_path = source_video_path
                    print("Source job video_path verwendet:", video_path)
                elif raw_video_path and storage.exists(raw_video_path):
                    video_path = raw_video_path
                    print("Source job raw_video_path verwendet:", video_path)
                else:
                    job["status"] = "failed_missing_source"
                    job["error_reason"] = (
                        "Kein gültiger Rerender-Video-Pfad gefunden. "
                        f"Original: {job['video_path']} | "
                        f"Export-Fallback: {fallback_video_path} | "
                        f"Source-Job-Datei: {source_job_file}"
                    )
                    job["next_retry_at"] = None
                    job["last_retry_at"] = datetime.now().isoformat()
                    job["last_retry_reason"] = job["error_reason"]
                    job["permanently_failed"] = True
                    save_json_list(rerender_jobs_file, rerender_jobs, provider=storage)

                    print("RERENDER JOB FEHLGESCHLAGEN:")
                    print("Rerender Job ID:", job["rerender_job_id"])
                    print("Grund:", job["error_reason"])
                    return

        from app import run_pipeline

        try:
            run_pipeline(
                video_path=video_path,
                channel_type=job["channel_type"],
                source_job_id=job["source_job_id"],
                is_rerender=True,
            )

            job["status"] = "done"
            job["next_retry_at"] = None
            job["last_retry_at"] = datetime.now().isoformat()
            job["last_retry_reason"] = None
            job["permanently_failed"] = False
            save_json_list(rerender_jobs_file, rerender_jobs, provider=storage)

            print("RERENDER JOB ABGESCHLOSSEN:")
            print("Rerender Job ID:", job["rerender_job_id"])
            return

        except Exception as e:
            current_retry_count = int(job.get("retry_count", 0))
            max_retry_attempts = int(job.get("max_retry_attempts", 3))
            retry_delay_minutes = int(job.get("retry_delay_minutes", 15))
            new_retry_count = current_retry_count + 1

            job["retry_count"] = new_retry_count
            job["max_retry_attempts"] = max_retry_attempts
            job["retry_delay_minutes"] = retry_delay_minutes
            job["last_retry_at"] = datetime.now().isoformat()
            job["last_retry_reason"] = str(e)
            job["error_reason"] = str(e)

            if new_retry_count < max_retry_attempts:
                next_retry_dt = datetime.now() + timedelta(minutes=retry_delay_minutes)
                job["status"] = "scheduled_retry"
                job["next_retry_at"] = next_retry_dt.strftime("%Y-%m-%d %H:%M")
                job["permanently_failed"] = False

                print("RERENDER RETRY GEPLANT:")
                print("Rerender Job ID:", job["rerender_job_id"])
                print("Nächster Retry:", job["next_retry_at"])
            else:
                job["status"] = "failed_runtime"
                job["next_retry_at"] = None
                job["permanently_failed"] = True

                print("RERENDER JOB LAUFZEITFEHLER:")
                print("Rerender Job ID:", job["rerender_job_id"])
                print("Grund:", job["error_reason"])

            save_json_list(rerender_jobs_file, rerender_jobs, provider=storage)
            return

    print("Kein pending oder fälliger retry rerender job gefunden.")


def main():
    print("=== Zenith Rerender Worker ===")
    create_rerender_job_from_queue()
    process_next_rerender_job()


if __name__ == "__main__":
    main()