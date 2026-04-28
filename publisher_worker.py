from datetime import datetime, timedelta
import os
import time

from core.content_variant_repository import ContentVariantRepository
from core.cross_platform_publish_orchestrator import CrossPlatformPublishOrchestrator
from core.platform_policy_resolver import PlatformPolicyResolver
from core.publish_package_builder import PublishPackageBuilder
from core.publish_result_repository import PublishResultRepository
from core.publisher import Publisher
from core.runtime_mode_controller import RuntimeModeController
from core.vacation_controller import VacationController
from models.job import Job
from models.publish_decision import PublishDecision
from models.publish_package import PublishPackage
from shared.channel_policies import (
    get_platform,
    get_retry_attempts,
    get_retry_delay_minutes,
)
from shared.enums import TargetFormat
from shared.runtime_modes import RuntimeAction
from storage.local_storage_provider import LocalStorageProvider


EXPORTS_BASE_PATH = r"D:\Zenith\exports"
RERENDER_QUEUE_FILE = r"D:\Zenith\data\rerender_queue.json"

TERMINAL_PUBLISH_STATUSES = {
    "published",
    "queued_for_approval",
    "policy_resolved",
}

runtime_mode_controller = RuntimeModeController()
vacation_controller = VacationController()
storage_provider = LocalStorageProvider()
content_variant_repository = ContentVariantRepository()
publish_result_repository = PublishResultRepository()
publish_package_builder = PublishPackageBuilder()
cross_platform_publish_orchestrator = CrossPlatformPublishOrchestrator(
    publisher=Publisher(),
    publish_result_repository=publish_result_repository,
)

def get_storage_provider(provider=None):
    return provider or storage_provider


def is_runtime_action_allowed(action, controller=None):
    active_controller = controller or runtime_mode_controller
    state = active_controller.get_state()
    allowed = action in active_controller.get_allowed_actions(state.mode)

    if not allowed:
        print(
            "[PublisherWorker] Runtime action blocked:",
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
        RuntimeAction.REPOST_DISPATCH,
    }

    allowed = (not active) or (action not in blocked_actions)

    if not allowed:
        print(
            "[PublisherWorker] Vacation action blocked:",
            action.value if hasattr(action, "value") else str(action),
            "| effective_mode:",
            active_controller.get_effective_mode().value,
        )

    return allowed


def get_target_platforms(job: dict) -> list[str]:
    if job.get("target_platforms"):
        return list(job.get("target_platforms"))

    if job.get("platform_targets"):
        return list(job.get("platform_targets"))

    return [get_platform(job["channel_type"])]


def build_publish_packages_from_job_data(
    job: dict,
    video_path: str,
    title: str,
    description: str,
    hashtags: list[str] | None = None,
    thumbnail_path: str | None = None,
    short_id: str | None = None,
    target_format_override: TargetFormat | None = None,
    platform_targets_override: list[str] | None = None,
) -> list[PublishPackage]:
    resolved_target_platforms = (
        list(platform_targets_override)
        if platform_targets_override
        else get_target_platforms(job)
    )

    job_model_data = dict(job)
    job_model_data["target_platforms"] = resolved_target_platforms

    if target_format_override is not None:
        job_model_data["target_format"] = target_format_override.value

    job_model = Job.from_dict(job_model_data)
    resolver = PlatformPolicyResolver()

    publish_packages: list[PublishPackage] = []

    for platform in job_model.target_platforms:
        resolved_policy = resolver.resolve_for_job_platform(job_model, platform)

        publish_packages.append(
            PublishPackage(
                job_id=job_model.job_id,
                video_path=video_path,
                title=title or "",
                description=description or "",
                hashtags=list(hashtags or []),
                thumbnail_path=(
                    thumbnail_path
                    if resolved_policy.thumbnail_required
                    else None
                ),
                platform=resolved_policy.platform,
                channel_type=job_model.channel_type,
                target_format=job_model.target_format,
                requires_manual_approval=resolved_policy.requires_manual_approval,
                title_mode=resolved_policy.title_mode,
                description_mode=resolved_policy.description_mode,
                hashtags_mode=resolved_policy.hashtags_mode,
                subtitle_style=resolved_policy.subtitle_style,
                packaging_profile=resolved_policy.packaging_profile,
                length_profile=resolved_policy.length_profile,
                preferred_aspect_ratio=resolved_policy.preferred_aspect_ratio,
                thumbnail_required=resolved_policy.thumbnail_required,
                uploader_backend=resolved_policy.uploader_backend,
                source_video_path=job.get("raw_video_path"),
                short_id=short_id,
            )
        )

    return publish_packages


def summarize_publish_results(publish_results) -> tuple[str, str | None]:
    for result in publish_results:
        if result.publish_status == "published":
            return "published", result.platform_video_id

    for result in publish_results:
        if result.publish_status == "queued_for_approval":
            return "queued_for_approval", None

    for result in publish_results:
        if result.publish_status == "unsupported_backend":
            return "policy_resolved", None

    return "blocked", None


def load_all_job_files(base_path=EXPORTS_BASE_PATH, provider=None):
    storage = get_storage_provider(provider)
    job_files = []

    if not storage.exists(base_path):
        return job_files

    for channel in storage.list_dir(base_path):
        channel_path = storage.join(base_path, channel)

        if not storage.is_dir(channel_path):
            continue

        for job_folder in storage.list_dir(channel_path):
            job_path = storage.join(channel_path, job_folder)

            if not storage.is_dir(job_path):
                continue

            job_file = storage.join(job_path, "job.json")

            if storage.exists(job_file):
                job_files.append(job_file)

    return job_files


def load_job_data(job_file, provider=None):
    storage = get_storage_provider(provider)

    try:
        return storage.read_json(job_file)
    except Exception as e:
        print("Fehler in job.json:", job_file)
        print("Grund:", e)
        return None

def get_export_path_from_job_file(job_file, provider=None):
    storage = get_storage_provider(provider)
    return storage.dirname(job_file)


def build_publish_packages_for_export(
    job: dict,
    export_path: str,
    provider=None,
) -> list[PublishPackage]:
    variants = content_variant_repository.load_variants(export_path)

    if variants:
        return publish_package_builder.build(variants)

    return build_publish_packages_from_job_data(
        job=job,
        video_path=job["video_path"],
        title=job.get("title") or "",
        description=job.get("description") or "",
        hashtags=[],
        thumbnail_path=job.get("thumbnail_path"),
    )


def execute_publish_packages(
    publish_packages: list[PublishPackage],
    publish_decision: PublishDecision,
    export_path: str | None = None,
    results_filename: str = "publish_results.json",
):
    return cross_platform_publish_orchestrator.execute(
        publish_packages=publish_packages,
        publish_decision=publish_decision,
        export_path=export_path,
        results_filename=results_filename,
    )

def get_short_results_filename(short_id: str) -> str:
    return f"publish_results_{short_id}.json"

def is_due(scheduled_at):
    if not scheduled_at:
        return False

    try:
        scheduled_time = datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M")
        return datetime.now() >= scheduled_time
    except ValueError:
        print("Falsches Datumformat:", scheduled_at)
        return False


def mark_rerender_in_progress(job_file, provider=None):
    storage = get_storage_provider(provider)
    job = storage.read_json(job_file)

    job["rerender_requested"] = False
    job["rerender_in_progress"] = True

    storage.write_json(job_file, job, indent=4)

    print("RERENDER IN PROGRESS:", job["job_id"])


def mark_job_publish_state(
    job_file,
    publish_status,
    platform_video_id=None,
    provider=None,
):
    storage = get_storage_provider(provider)
    job = storage.read_json(job_file)
    now_iso = datetime.now().isoformat()

    job["publish_status"] = publish_status
    job["error_message"] = None
    job["retry_count"] = 0
    job["next_retry_at"] = None
    job["last_retry_at"] = now_iso
    job["last_retry_reason"] = None
    job["retry_status"] = None
    job["permanently_failed"] = False
    job["is_scheduled"] = False
    job["scheduled_at"] = None

    if publish_status == "published":
        job["published_at"] = now_iso

    if "performance_tracking" not in job:
        job["performance_tracking"] = {
            "enabled": True,
            "youtube_video_id": None,
            "last_synced_at": None,
            "metrics": {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "ctr": None,
                "average_view_duration": None,
                "average_percentage_viewed": None,
            },
        }

    if platform_video_id is not None:
        job["performance_tracking"]["youtube_video_id"] = platform_video_id
        job["performance_tracking"]["last_synced_at"] = now_iso

    storage.write_json(job_file, job, indent=4)

    print("JOB STATUS AKTUALISIERT:", job["job_id"])
    print("NEUER PUBLISH STATUS:", publish_status)
    print("VIDEO ID:", platform_video_id)


def mark_as_published(job_file, platform_video_id=None, provider=None):
    mark_job_publish_state(
        job_file=job_file,
        publish_status="published",
        platform_video_id=platform_video_id,
        provider=provider,
    )


def mark_job_repost_state(
    job_file,
    repost_status,
    platform_video_id=None,
    provider=None,
):
    storage = get_storage_provider(provider)
    job = storage.read_json(job_file)
    now_iso = datetime.now().isoformat()

    job["repost_requested"] = False
    job["repost_status"] = repost_status
    job["next_repost_at"] = None

    if repost_status == "reposted":
        job["repost_count"] = int(job.get("repost_count", 0)) + 1
        job["last_repost_at"] = now_iso
        job["publish_status"] = "published"
    else:
        job["publish_status"] = repost_status

    if "performance_tracking" not in job:
        job["performance_tracking"] = {
            "enabled": True,
            "youtube_video_id": None,
            "last_synced_at": None,
            "metrics": {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "ctr": None,
                "average_view_duration": None,
                "average_percentage_viewed": None,
            },
        }

    if platform_video_id is not None:
        job["performance_tracking"]["youtube_video_id"] = platform_video_id
        job["performance_tracking"]["last_synced_at"] = now_iso

    storage.write_json(job_file, job, indent=4)

    print("REPOST STATUS AKTUALISIERT:", job["job_id"])
    print("NEUER REPOST STATUS:", repost_status)
    print("VIDEO ID:", platform_video_id)


def mark_as_reposted(job_file, platform_video_id=None, provider=None):
    mark_job_repost_state(
        job_file=job_file,
        repost_status="reposted",
        platform_video_id=platform_video_id,
        provider=provider,
    )


def schedule_retry_or_fail(job_file, error_message, provider=None):
    storage = get_storage_provider(provider)
    job = storage.read_json(job_file)

    current_retry_count = int(job.get("retry_count", 0))
    max_retry_attempts = int(
        job.get("max_retry_attempts")
        if job.get("max_retry_attempts") is not None
        else get_retry_attempts(job["channel_type"])
    )
    retry_delay_minutes = int(
        job.get("retry_delay_minutes")
        if job.get("retry_delay_minutes") is not None
        else get_retry_delay_minutes(job["channel_type"])
    )

    new_retry_count = current_retry_count + 1

    job["error_message"] = str(error_message)
    job["retry_count"] = new_retry_count
    job["max_retry_attempts"] = max_retry_attempts
    job["retry_delay_minutes"] = retry_delay_minutes
    job["last_retry_at"] = datetime.now().isoformat()
    job["last_retry_reason"] = str(error_message)

    if new_retry_count < max_retry_attempts:
        next_retry_dt = datetime.now() + timedelta(minutes=retry_delay_minutes)

        job["next_retry_at"] = next_retry_dt.strftime("%Y-%m-%d %H:%M")
        job["retry_status"] = "scheduled_retry"
        job["permanently_failed"] = False
        job["is_scheduled"] = False
        job["scheduled_at"] = None

        print("RETRY GEPLANT:", job["job_id"])
        print("NÄCHSTER RETRY:", job["next_retry_at"])
    else:
        job["next_retry_at"] = None
        job["retry_status"] = "permanently_failed"
        job["permanently_failed"] = True
        job["publish_status"] = "failed"
        job["is_scheduled"] = False
        job["scheduled_at"] = None

        print("DAUERHAFT FEHLGESCHLAGEN:", job["job_id"])

    storage.write_json(job_file, job, indent=4)


def mark_short_publish_state(
    job_file,
    short_id,
    publish_status,
    platform_video_id=None,
    provider=None,
):
    storage = get_storage_provider(provider)
    job = storage.read_json(job_file)
    now_iso = datetime.now().isoformat()

    normalized_shorts = []
    for index, short in enumerate(job.get("shorts", []), start=1):
        current_short_id = (
            short.get("short_id")
            if isinstance(short, dict) and short.get("short_id")
            else f"short_{index}"
        )

        short_data = {
            "short_id": current_short_id,
            "path": short.get("path") if isinstance(short, dict) else short,
            "status": (
                short.get("status")
                if isinstance(short, dict) and short.get("status")
                else "generated"
            ),
            "review_status": (
                short.get("review_status")
                if isinstance(short, dict) and short.get("review_status")
                else "pending"
            ),
            "platform_targets": (
                list(short.get("platform_targets"))
                if isinstance(short, dict) and short.get("platform_targets")
                else list(get_target_platforms(job))
            ),
            "publish_status": (
                publish_status
                if current_short_id == short_id
                else (
                    short.get("publish_status")
                    if isinstance(short, dict) and short.get("publish_status") is not None
                    else "not_published"
                )
            ),
            "retry_count": (
                0
                if current_short_id == short_id
                else (
                    int(short.get("retry_count", 0))
                    if isinstance(short, dict)
                    else 0
                )
            ),
            "max_retry_attempts": (
                None
                if current_short_id == short_id
                else (
                    int(short["max_retry_attempts"])
                    if isinstance(short, dict) and short.get("max_retry_attempts") is not None
                    else None
                )
            ),
            "retry_delay_minutes": (
                None
                if current_short_id == short_id
                else (
                    int(short["retry_delay_minutes"])
                    if isinstance(short, dict) and short.get("retry_delay_minutes") is not None
                    else None
                )
            ),
            "next_retry_at": (
                None
                if current_short_id == short_id
                else (
                    short.get("next_retry_at")
                    if isinstance(short, dict)
                    else None
                )
            ),
            "last_retry_at": (
                now_iso
                if current_short_id == short_id
                else (
                    short.get("last_retry_at")
                    if isinstance(short, dict)
                    else None
                )
            ),
            "last_retry_reason": (
                None
                if current_short_id == short_id
                else (
                    short.get("last_retry_reason")
                    if isinstance(short, dict)
                    else None
                )
            ),
            "retry_status": (
                None
                if current_short_id == short_id
                else (
                    short.get("retry_status")
                    if isinstance(short, dict)
                    else None
                )
            ),
            "permanently_failed": (
                False
                if current_short_id == short_id
                else (
                    bool(short.get("permanently_failed", False))
                    if isinstance(short, dict)
                    else False
                )
            ),
            "segment": (
                {
                    "label": short["segment"].get("label"),
                    "start_seconds": float(short["segment"].get("start_seconds", 0.0)),
                    "end_seconds": float(short["segment"].get("end_seconds", 0.0)),
                    "duration_seconds": float(short["segment"].get("duration_seconds", 0.0)),
                    "score": float(short["segment"].get("score", 0.0)),
                    "selection_reason": str(
                        short["segment"].get("selection_reason", "unknown")
                    ),
                }
                if isinstance(short, dict) and isinstance(short.get("segment"), dict)
                else None
            ),
        }

        if short_data["path"]:
            normalized_shorts.append(short_data)

    job["shorts"] = normalized_shorts

    storage.write_json(job_file, job, indent=4)

    print("SHORT STATUS AKTUALISIERT:", job["job_id"], "/", short_id)
    print("NEUER SHORT STATUS:", publish_status)
    print("VIDEO ID:", platform_video_id)


def mark_short_as_published(job_file, short_id, platform_video_id=None, provider=None):
    mark_short_publish_state(
        job_file=job_file,
        short_id=short_id,
        publish_status="published",
        platform_video_id=platform_video_id,
        provider=provider,
    )


def schedule_short_retry_or_fail(job_file, short_id, error_message, provider=None):
    storage = get_storage_provider(provider)
    job = storage.read_json(job_file)

    normalized_shorts = []
    for index, short in enumerate(job.get("shorts", []), start=1):
        current_short_id = (
            short.get("short_id")
            if isinstance(short, dict) and short.get("short_id")
            else f"short_{index}"
        )

        short_data = {
            "short_id": current_short_id,
            "path": short.get("path") if isinstance(short, dict) else short,
            "status": (
                short.get("status")
                if isinstance(short, dict) and short.get("status")
                else "generated"
            ),
            "review_status": (
                short.get("review_status")
                if isinstance(short, dict) and short.get("review_status")
                else "pending"
            ),
            "platform_targets": (
                list(short.get("platform_targets"))
                if isinstance(short, dict) and short.get("platform_targets")
                else list(get_target_platforms(job))
            ),
            "publish_status": (
                short.get("publish_status")
                if isinstance(short, dict) and short.get("publish_status") is not None
                else "not_published"
            ),
            "retry_count": (
                int(short.get("retry_count", 0))
                if isinstance(short, dict)
                else 0
            ),
            "max_retry_attempts": (
                int(short["max_retry_attempts"])
                if isinstance(short, dict) and short.get("max_retry_attempts") is not None
                else None
            ),
            "retry_delay_minutes": (
                int(short["retry_delay_minutes"])
                if isinstance(short, dict) and short.get("retry_delay_minutes") is not None
                else None
            ),
            "next_retry_at": (
                short.get("next_retry_at")
                if isinstance(short, dict)
                else None
            ),
            "last_retry_at": (
                short.get("last_retry_at")
                if isinstance(short, dict)
                else None
            ),
            "last_retry_reason": (
                short.get("last_retry_reason")
                if isinstance(short, dict)
                else None
            ),
            "retry_status": (
                short.get("retry_status")
                if isinstance(short, dict)
                else None
            ),
            "permanently_failed": (
                bool(short.get("permanently_failed", False))
                if isinstance(short, dict)
                else False
            ),
            "segment": (
                {
                    "label": short["segment"].get("label"),
                    "start_seconds": float(short["segment"].get("start_seconds", 0.0)),
                    "end_seconds": float(short["segment"].get("end_seconds", 0.0)),
                    "duration_seconds": float(short["segment"].get("duration_seconds", 0.0)),
                    "score": float(short["segment"].get("score", 0.0)),
                    "selection_reason": str(
                        short["segment"].get("selection_reason", "unknown")
                    ),
                }
                if isinstance(short, dict) and isinstance(short.get("segment"), dict)
                else None
            ),
        }

        if current_short_id == short_id:
            current_retry_count = short_data["retry_count"]
            max_retry_attempts = (
                short_data["max_retry_attempts"]
                if short_data["max_retry_attempts"] is not None
                else get_retry_attempts(job["channel_type"])
            )
            retry_delay_minutes = (
                short_data["retry_delay_minutes"]
                if short_data["retry_delay_minutes"] is not None
                else get_retry_delay_minutes(job["channel_type"])
            )

            new_retry_count = current_retry_count + 1

            short_data["retry_count"] = new_retry_count
            short_data["max_retry_attempts"] = max_retry_attempts
            short_data["retry_delay_minutes"] = retry_delay_minutes
            short_data["last_retry_at"] = datetime.now().isoformat()
            short_data["last_retry_reason"] = str(error_message)

            if new_retry_count < max_retry_attempts:
                next_retry_dt = datetime.now() + timedelta(minutes=retry_delay_minutes)
                short_data["next_retry_at"] = next_retry_dt.strftime("%Y-%m-%d %H:%M")
                short_data["retry_status"] = "scheduled_retry"
                short_data["permanently_failed"] = False
                short_data["publish_status"] = None

                print("SHORT RETRY GEPLANT:", job["job_id"], "/", short_id)
                print("NÄCHSTER SHORT RETRY:", short_data["next_retry_at"])
            else:
                short_data["next_retry_at"] = None
                short_data["retry_status"] = "permanently_failed"
                short_data["permanently_failed"] = True
                short_data["publish_status"] = "failed"

                print("SHORT DAUERHAFT FEHLGESCHLAGEN:", job["job_id"], "/", short_id)

        if short_data["path"]:
            normalized_shorts.append(short_data)

    job["shorts"] = normalized_shorts

    storage.write_json(job_file, job, indent=4)


def add_to_rerender_queue(job, queue_file=RERENDER_QUEUE_FILE, provider=None):
    storage = get_storage_provider(provider)

    if storage.exists(queue_file):
        try:
            queue = storage.read_json(queue_file)
        except Exception:
            queue = []
    else:
        queue = []

    queue.append({
        "job_id": job["job_id"],
        "channel_type": job["channel_type"],
        "video_path": job["video_path"],
        "title": job["title"],
        "description": job["description"],
    })

    storage.write_json(queue_file, queue, indent=4)

    print("IN RERENDER QUEUE:", job["job_id"])


def main():
    print("=== Zenith Publisher Worker ===")
    print("Arbeitsverzeichnis:", os.getcwd())
    print("Suche in:", EXPORTS_BASE_PATH)

    job_files = load_all_job_files()

    for job_file in job_files:
        job = load_job_data(job_file)

        if job is None:
            continue

        if job.get("rerender_requested") is True:
            if not is_runtime_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE):
                print("-> RERENDER QUEUE INTAKE GEBLOCKT für", job.get("job_id"))
                continue

            if not is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE):
                print("-> RERENDER QUEUE INTAKE DURCH VACATION GEBLOCKT für", job.get("job_id"))
                continue

            print("-> RERENDER ANGEFORDERT für", job.get("job_id"))
            mark_rerender_in_progress(job_file)
            add_to_rerender_queue(job)
            continue

        short_retry_processed = False

        for index, short in enumerate(job.get("shorts", []), start=1):
            short_id = (
                short.get("short_id")
                if isinstance(short, dict) and short.get("short_id")
                else f"short_{index}"
            )

            short_path = short.get("path") if isinstance(short, dict) else short
            short_review_status = (
                short.get("review_status")
                if isinstance(short, dict) and short.get("review_status")
                else "pending"
            )
            short_publish_status = (
                short.get("publish_status")
                if isinstance(short, dict) and short.get("publish_status") is not None
                else "not_published"
            )
            short_retry_status = short.get("retry_status") if isinstance(short, dict) else None
            short_next_retry_at = short.get("next_retry_at") if isinstance(short, dict) else None
            short_permanently_failed = (
                bool(short.get("permanently_failed", False))
                if isinstance(short, dict)
                else False
            )
            short_platform_targets = (
                list(short.get("platform_targets"))
                if isinstance(short, dict) and short.get("platform_targets")
                else list(get_target_platforms(job))
            )

            if not short_path:
                continue
            if short_review_status != "approved":
                continue
            if short_publish_status in TERMINAL_PUBLISH_STATUSES:
                continue
            if short_permanently_failed:
                continue
            if short_retry_status != "scheduled_retry":
                continue
            if not short_next_retry_at:
                print("-> SHORT übersprungen: retry ohne next_retry_at", short_id)
                continue
            if not is_due(short_next_retry_at):
                print("-> SHORT übersprungen: retry noch nicht fällig", short_id)
                continue

            if not is_runtime_action_allowed(RuntimeAction.SHORT_RETRY_DISPATCH):
                print("-> SHORT RETRY durch Runtime Mode geblockt", short_id)
                continue

            print("READY TO PUBLISH SHORT RETRY:")
            print("Job ID:", job["job_id"])
            print("Short ID:", short_id)
            print("Channel:", job["channel_type"])
            print("Title:", f'{job["title"]} [{short_id}]')
            print("Next retry at:", short_next_retry_at)
            print("---")

            short_publish_packages = build_publish_packages_from_job_data(
                job=job,
                video_path=short_path,
                title=f'{job["title"]} [{short_id}]',
                description=job.get("description") or "",
                hashtags=[],
                thumbnail_path=job.get("thumbnail_path"),
                short_id=short_id,
                target_format_override=TargetFormat.SHORT,
                platform_targets_override=short_platform_targets,
            )

            short_publish_decision = PublishDecision(
                job_id=job["job_id"],
                decision="autopublish_allowed",
                reason=f"Automatic short retry via publisher worker: {short_id}",
            )

            export_path = get_export_path_from_job_file(job_file)

            try:
                publish_results = execute_publish_packages(
                    publish_packages=short_publish_packages,
                    publish_decision=short_publish_decision,
                    export_path=export_path,
                    results_filename=get_short_results_filename(short_id),
                )

                for publish_result in publish_results:
                    print("SHORT PUBLISH RESULT:", publish_result)

                overall_status, platform_video_id = summarize_publish_results(
                    publish_results
                )

                if overall_status == "blocked":
                    raise ValueError(f"Short retry blocked for all platforms: {short_id}")

                mark_short_publish_state(
                    job_file=job_file,
                    short_id=short_id,
                    publish_status=overall_status,
                    platform_video_id=platform_video_id,
                )
            except Exception as e:
                print("SHORT PUBLISH FEHLER:", e)
                schedule_short_retry_or_fail(job_file, short_id, str(e))

            short_retry_processed = True
            break

        if short_retry_processed:
            continue

        if job.get("repost_requested") is True:
            if not is_runtime_action_allowed(RuntimeAction.REPOST_DISPATCH):
                print("-> REPOST durch Runtime Mode geblockt für", job.get("job_id"))
                continue

            if not is_vacation_action_allowed(RuntimeAction.REPOST_DISPATCH):
                print("-> REPOST durch Vacation Mode geblockt für", job.get("job_id"))
                continue

            print("-> REPOST ANGEFORDERT für", job.get("job_id"))

            export_path = get_export_path_from_job_file(job_file)
            publish_packages = build_publish_packages_for_export(
                job=job,
                export_path=export_path,
            )

            publish_decision = PublishDecision(
                job_id=job["job_id"],
                decision="autopublish_allowed",
                reason="Manual repost via dashboard",
            )

            publisher = Publisher()

            try:
                publish_results = execute_publish_packages(
                    publish_packages=publish_packages,
                    publish_decision=publish_decision,
                    export_path=export_path,
                )

                for publish_result in publish_results:
                    print("REPOST RESULT:", publish_result)

                overall_status, platform_video_id = summarize_publish_results(
                    publish_results
                )

                if overall_status == "published":
                    mark_as_reposted(job_file, platform_video_id)
                elif overall_status == "queued_for_approval":
                    mark_job_repost_state(job_file, "queued_for_approval")
                elif overall_status == "policy_resolved":
                    mark_job_repost_state(job_file, "policy_resolved")
                else:
                    mark_job_repost_state(job_file, "blocked")
            except Exception as e:
                print("REPOST FEHLER:", e)

            continue

        if job.get("publish_status") in TERMINAL_PUBLISH_STATUSES:
            print("-> Übersprungen: Publish bereits terminal verarbeitet")
            continue

        if job.get("permanently_failed") is True:
            print("-> Übersprungen: dauerhaft fehlgeschlagen")
            continue

        print("\nJOB GEFUNDEN:")
        print("job_id:", job.get("job_id"))
        print("channel_type:", job.get("channel_type"))
        print("review_status:", job.get("review_status"))
        print("is_scheduled:", job.get("is_scheduled"))
        print("scheduled_at:", job.get("scheduled_at"))

        if job.get("review_status") != "approved":
            print("-> Übersprungen: nicht approved")
            continue

        if job.get("retry_status") == "scheduled_retry":
            if not job.get("next_retry_at"):
                print("-> Übersprungen: retry ohne next_retry_at")
                continue

            if not is_due(job.get("next_retry_at")):
                print("-> Übersprungen: retry noch nicht fällig")
                continue
        else:
            if not job.get("is_scheduled", False):
                print("-> Übersprungen: nicht scheduled")
                continue

            if not is_due(job.get("scheduled_at")):
                print("-> Übersprungen: noch nicht fällig")
                continue

        if not is_runtime_action_allowed(RuntimeAction.PUBLISH_DISPATCH):
            print("-> PUBLISH durch Runtime Mode geblockt für", job.get("job_id"))
            continue

        print("READY TO PUBLISH:")
        print("Job ID:", job["job_id"])
        print("Channel:", job["channel_type"])
        print("Title:", job["title"])
        print("Scheduled at:", job["scheduled_at"])
        print("---")

        export_path = get_export_path_from_job_file(job_file)
        publish_packages = build_publish_packages_for_export(
            job=job,
            export_path=export_path,
        )

        publish_decision = PublishDecision(
            job_id=job["job_id"],
            decision="autopublish_allowed",
            reason="Approved and due via publisher worker",
        )

        publisher = Publisher()
        try:
            publish_results = execute_publish_packages(
                publish_packages=publish_packages,
                publish_decision=publish_decision,
                export_path=export_path,
            )

            for publish_result in publish_results:
                print("PUBLISH RESULT:", publish_result)

            overall_status, platform_video_id = summarize_publish_results(
                publish_results
            )

            if overall_status == "blocked":
                raise ValueError(
                    f"Publish blocked for all platforms: {job.get('job_id')}"
                )

            if overall_status == "published":
                mark_as_published(job_file, platform_video_id)
            else:
                mark_job_publish_state(job_file, overall_status, platform_video_id)
        except Exception as e:
            print("PUBLISH FEHLER:", e)
            schedule_retry_or_fail(job_file, str(e))


if __name__ == "__main__":
    while True:
        main()
        print("Warte 30 Sekunden...\n")
        time.sleep(30)