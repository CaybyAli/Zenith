from enum import Enum


class JobType(str, Enum):
    GAMING = "gaming"
    FACELESS = "faceless"


class ChannelType(str, Enum):
    GAMING_MAIN = "gaming_main"
    VLOG_MAIN = "vlog_main"
    GAMING_UNCUT = "gaming_uncut"
    REACTION_UNCUT = "reaction_uncut"
    VLOG_UNCUT = "vlog_uncut"
    FACELESS_TREND = "faceless_trend"  # Phase 15 - Faceless, noch nicht aktiv


ACTIVE_CHANNEL_TYPES = (
    ChannelType.GAMING_MAIN,
    ChannelType.VLOG_MAIN,
    ChannelType.GAMING_UNCUT,
    ChannelType.REACTION_UNCUT,
    ChannelType.VLOG_UNCUT,
)

class PlatformType(str, Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM_REELS = "instagram_reels"    


class TargetFormat(str, Enum):
    LONGFORM = "longform"
    SHORT = "short"
    BOTH = "both"


class Mode(str, Enum):
    NORMAL = "normal"
    VACATION = "vacation"


class PipelineType(str, Enum):
    GAMING = "gaming_pipeline"
    FACELESS = "faceless_pipeline"
    VLOG = "vlog_pipeline"


class JobStatus(str, Enum):
    CREATED = "created"
    STORED = "stored"
    ROUTED = "routed"
    PENDING = "pending"
    PROCESSING = "processing"

    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    CUTTING = "cutting"
    CUT = "cut"
    RENDERING = "rendering"
    SHORTS_GENERATING = "shorts_generating"

    RENDERED = "rendered"
    SHORTS_RENDERED = "shorts_rendered"
    RENDER_BLOCKED = "render_blocked"
    VALIDATION_FAILED = "validation_failed"
    APPROVAL_PENDING = "approval_pending"
    APPROVED = "approved"
    ASSEMBLED = "assembled"
    DONE = "done"
    PUBLISHED = "published"
    FAILED = "failed"
    CRASHED = "crashed"
    SKIPPED = "skipped"


class AssetType(str, Enum):
    RAW_VIDEO = "raw_video"
    TRANSCRIPT = "transcript"
    DRAFT_VIDEO = "draft_video"
    FINAL_VIDEO = "final_video"
    SUBTITLE = "subtitle"
    THUMBNAIL = "thumbnail"


class AssetStatus(str, Enum):
    REGISTERED = "registered"
    READY = "ready"
    FAILED = "failed"


class AutopublishClass(str, Enum):
    MANUAL_ONLY = "manual_only"
    CONDITIONAL = "conditional"
    SAFE_AUTO = "safe_auto"


class ValidatorStatus(str, Enum):
    NOT_VALIDATED = "not_validated"
    PASSED = "passed"
    FAILED = "failed"

# 2.C.1 Runner status contract
#
# Technical render completion alone is not a successful job.
# Current pre-2.C.6 mode:
# - ok: rendered + validated + Phase-2B ready, represented as APPROVAL_PENDING
# - failed: validator/stabilization failed or Python crash
# - skipped: nothing to process / already existing job
#
# After the future approval CLI, APPROVAL_PENDING can be split from final user-approved ok.
RUNNER_OK_JOB_STATUSES = {
    JobStatus.APPROVAL_PENDING,
    JobStatus.APPROVED,
    JobStatus.PUBLISHED,
}

RUNNER_FAILED_JOB_STATUSES = {
    JobStatus.VALIDATION_FAILED,
    JobStatus.RENDER_BLOCKED,
    JobStatus.CRASHED,
    JobStatus.FAILED,
}

RUNNER_SKIPPED_JOB_STATUSES = {
    JobStatus.SKIPPED,
}


def _job_status_value(status) -> str:
    return str(getattr(status, "value", status))


def classify_job_status_for_runner(status) -> str:
    value = _job_status_value(status)

    if value in {item.value for item in RUNNER_OK_JOB_STATUSES}:
        return "ok"

    if value in {item.value for item in RUNNER_SKIPPED_JOB_STATUSES}:
        return "skip"

    if value in {item.value for item in RUNNER_FAILED_JOB_STATUSES}:
        return "error"

    return "error"

