from enum import Enum


class JobType(str, Enum):
    GAMING = "gaming"
    FACELESS = "faceless"


class ChannelType(str, Enum):
    GAMING_MAIN = "gaming_main"
    GAMING_UNCUT = "gaming_uncut"
    FACELESS_TREND = "faceless_trend"
    VLOG_MAIN = "vlog_main"

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
    ASSEMBLED = "assembled"
    PUBLISHED = "published"
    FAILED = "failed"


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